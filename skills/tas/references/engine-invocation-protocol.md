# Engine Invocation Protocol

MetaAgent reads this file in Phase 1 and uses it to spawn AND poll the Python
dialectic engine (`run-dialectic.sh`) within a single Execute Mode Agent()
call. MainOrchestrator (SKILL.md Phase 2) receives only the final synthesized
`status: completed | halted` JSON — it does NOT poll and does NOT manage
engine lifecycle directly. This is Phase 3.1 Scenario B (see Plan Review
Issue #2 close-out).

## Why this protocol exists

A single dialectic round takes 8–12 minutes (thesis → antithesis LLM roundtrip).
Multi-round steps routinely exceed 10 minutes. The Claude Code Bash tool
**hard-caps foreground timeout at 600,000ms (10 min)**. Specifying
`timeout: 900000` or any value above 600,000 does **not** raise the cap — the
tool silently transitions the command to background at 10 min and returns a
shell ID instead of stdout.

More critically: when a subagent (MetaAgent, invoked via `Agent()`) spawns a
command with `Bash(run_in_background: true)`, the Claude Code harness registers
the background shell under a `bash_id` bound to the subagent's session. **When
the subagent returns, the harness reaps every `bash_id` it registered** —
killing the engine process mid-round. See `FINDINGS-nohup-bg-pattern.md` §7 for
the EXPERIMENT-3v2 evidence chain (30-minute orphan survival verification,
2026-04-21).

Therefore: **the subagent spawns the engine as a fire-and-forget orphan using
`nohup ... &`**, captures the PID on stdout via `echo $!`, and then **polls
file markers (`engine.done` / `engine.exit`) locally within the same Agent()
call** in chunks of ≤9.5 minutes (within the Bash cap). Polling stays inside
MetaAgent because (a) the Agent() context is kept open by foreground Bash calls
each returning in <10 min, (b) MainOrchestrator does not know the per-step
marker paths, and (c) MetaAgent synthesizes the final `status: completed |
halted` JSON from exit code + last log line, preserving the existing Phase 2
handler shape.

## Standard invocation pattern

From **inside the MetaAgent subagent** (meta.md Execute Phase 2d step 7):

```
Bash({
  command: "nohup bash ${SKILL_DIR}/runtime/run-dialectic.sh ${LOG_DIR}/step-config.json > ${LOG_DIR}/engine.log 2>&1 & echo $!",
  run_in_background: false,
  description: "Spawn dialectic engine for step {S.id}"
})
```

**The three components are non-negotiable:**
1. `nohup` — detaches from the shell session so SIGHUP on subagent return is
   ignored.
2. `&` — backgrounds the job so bash returns immediately instead of waiting.
3. `echo $!` — captures the last-backgrounded PID to stdout for the caller.

Each of the three is load-bearing: remove any one and orphan survival fails
(see FINDINGS §2).

**`run_in_background: false`** (not `true`) is critical — `true` would register
a `bash_id` in the subagent session and reactivate the harness reap. The
`&` inside the command string performs shell-level backgrounding instead, which
the harness does not track.

The `Bash(...)` call returns in milliseconds with stdout being a single integer
(the engine PID). Do **NOT** attach a `timeout:` parameter to this `Bash(...)`
call — the call itself is ms-long; the engine runs independently.

**Bash wrapper parent-process requirement (Issue #1 close-out):** `run-dialectic.sh`
itself MUST NOT use the `exec` keyword on the final invocation lines (both
branches — the `timeout`-wrapped and the degraded direct path). `exec` would
replace the bash shell with the Python process, which prevents the EXIT trap
from firing and therefore suppresses `engine.done` / `engine.exit` marker
writes. Empirically: `bash -c 'trap "echo TRAP" EXIT; exec echo hi'` prints
`hi` but NOT `TRAP`. Without `exec`, the trap fires normally. Phase 3.1 Plan 02
removes `exec` from both Layer B branches; Phase 3.1 Plan 07 installs a static
regression guard (`grep -c "^[[:space:]]*exec " skills/tas/runtime/run-dialectic.sh`
must output `0`).

## Return metadata schema

### Internal envelope (MetaAgent-owned, not exposed to MainOrchestrator)

After spawning, MetaAgent holds a per-step metadata record used only inside
Phase 2d:

```json
{
  "engine_pid": <int>,
  "log_path": "<absolute path to engine.log>",
  "heartbeat_path": "<absolute path to heartbeat.txt>",
  "exit_path": "<absolute path to engine.exit>",
  "done_path": "<absolute path to engine.done>",
  "step_id": "<step id>",
  "iteration": <int>,
  "workspace": "<WORKSPACE>"
}
```

This record is **never serialized out to MainOrchestrator** in Scenario B.
It is MetaAgent-internal scratch state consumed by the local polling loop.

### Final envelope (MetaAgent → MainOrchestrator, Scenario B)

After polling terminates and classification runs, MetaAgent synthesizes the
existing `status: completed | halted` JSON shape — byte-compatible with the
pre-Phase-3.1 handler in SKILL.md Phase 2:

```json
// Normal completion — from last log line when EXIT=0 and JSON parses
{ "status": "completed", "workspace": "...", "summary": "...", "iterations": N,
  "early_exit": bool, "rounds_total": N, "engine_invocations": N }

// Or HALT — synthesized locally from marker classification
{ "status": "halted", "halt_reason": "bash_wrapper_kill" | "step_transition_hang" | "engine_crash" | "sdk_session_hang",
  "watchdog_layer": "A" | "B" | null,
  "last_heartbeat": "...",
  "wrapper_exit": <int>,
  ... }
```

Each invocation still counts toward `engine_invocations` in the final
attestation JSON (see meta.md Phase 5). No new `status: engine_launched`
envelope is exposed — that was an earlier draft replaced in Scenario B.

## Lifecycle ownership

| Actor | Owns |
|-------|------|
| `run-dialectic.sh` EXIT trap | Writes `engine.done` (boolean existence) + `engine.exit` (integer exit code + newline) atomically on every exit path — normal exit, Python raise, Layer A `asyncio.timeout` re-raise, Layer B coreutils `timeout` SIGTERM (exit 124 or 143 depending on whether timeout(1) reports its own code or the bash wrapper's 128+SIGTERM code; both observable — see §Failure classification). **NOTE:** bash MUST remain Python's parent process — the `exec` keyword is forbidden anywhere inside `run-dialectic.sh` on the final invocation lines (Issue #1). See Phase 3.1 TOPO-01 trap block in `run-dialectic.sh`. |
| MetaAgent (Agent subagent) | Spawns the engine via `nohup ... & echo $!`, captures PID, AND polls `engine.done` / `kill -0 $PID` in ≤9.5-min Bash-cap-safe chunks within the same Agent() call. Reads `engine.exit` + `tail -n 1 engine.log` after polling terminates. Classifies the result via the table below (Phase 3 D-05 + Phase 3.1 D-TOPO-05). Synthesizes the final `status: completed | halted` JSON returned to MainOrchestrator. |
| MainOrchestrator (SKILL.md) | Consumes MetaAgent's final `status: completed | halted` JSON via the existing (pre-Phase-3.1) Phase 2 handler path. No polling. No direct engine lifecycle involvement. Info-hiding boundary preserved — SKILL.md Allowed Read list is unchanged from Phase 2 D-07 (`checkpoint.json`, `plan.json`, `REQUEST.md` only). |
| MetaAgent (HALT forensics) | Reads `heartbeat.txt` via `cat` when synthesizing `bash_wrapper_kill` / `step_transition_hang` HALT JSON to fill `last_heartbeat`. Already MetaAgent-local; no boundary change. |

## Liveness probe

Two complementary checks run inside MetaAgent's local polling loop (meta.md
step 8):

```bash
# 1. Marker existence (authoritative "engine finished")
test -f "$DONE_PATH"

# 2. PID liveness (fallback: engine died without writing marker — hang path)
kill -0 "$PID" 2>/dev/null
```

`kill -0` sends no signal — it only checks whether the caller can signal the
PID. `permission denied` (EPERM) is treated as **alive** by convention (this
is why PPID=1 reparented processes remain probeable from the orchestrator).

The polling Bash call shape (inside MetaAgent):

```
Bash({
  command: "for i in $(seq 1 19); do
              test -f \"$DONE_PATH\" && { echo done; exit 0; };
              kill -0 \"$ENGINE_PID\" 2>/dev/null || { echo dead; exit 0; };
              sleep \"${TAS_POLL_INTERVAL_SEC:-30}\";
            done; echo pending",
  run_in_background: false,
  description: "Poll engine for step <S.id> (<=9.5min)"
})
```

Each call returns in ≤570s (19 × 30s), comfortably under the 600,000ms Bash
cap. MetaAgent repeats the call until stdout ends with `done` or `dead`.
`run_in_background: true` is forbidden here too — same harness-reap reasoning.

## Failure classification

After polling terminates, MetaAgent computes:

```bash
EXIT="$(cat "$EXIT_PATH" 2>/dev/null || echo "lost")"
LAST="$(tail -n 1 "$LOG_PATH" 2>/dev/null)"
```

Apply Phase 3 03-CONTEXT.md §D-05 + Phase 3.1 D-TOPO-05 (single source of
truth — reproduced here for locality):

| EXIT code | LAST JSON | classification | `halt_reason` | `watchdog_layer` |
|-----------|-----------|----------------|---------------|------------------|
| `0` | `verdict: ACCEPT` / `PASS` / `FAIL` | normal completion | — | — |
| `0` | `status: halted`, `halt_reason: sdk_session_hang` | Layer A hit | `sdk_session_hang` | `A` |
| `0` | `status: halted`, other `halt_reason` | engine internal HALT | (pass through) | null |
| `124` / `137` | (any) | Layer B SIGTERM / SIGKILL (timeout(1) reports its own code) | `bash_wrapper_kill` | `B` |
| `143` | (any) | Layer B SIGTERM propagation through bash EXIT trap (128+15; observed when bash captures the SIGTERM first, Plan 02 Test C ordering) | `bash_wrapper_kill` | `B` |
| `0` | JSON absent or parse-fail | step-transition hang | `step_transition_hang` | `B` |
| `"lost"` (exit file absent, PID dead, done file absent) | (any) | polling orphan — PID died without trap | `step_transition_hang` | `B` |
| non-zero (other) | JSON absent | engine crash | `engine_crash` | null |

For `bash_wrapper_kill` / `step_transition_hang`, MetaAgent synthesizes a HALT
JSON locally with `last_heartbeat` filled from `heartbeat.txt` (MetaAgent
forensics path — NOT SKILL.md). No new `halt_reason` enum is introduced in
Phase 3.1 (D-TOPO-05): the "lost" / missing-marker path is absorbed by the
existing `step_transition_hang`. 124 and 143 share a row for classification
purposes — either is a valid `bash_wrapper_kill` observation.

## What NOT to do

- ❌ `Bash(..., timeout: 900000)` — above the 600,000 cap, silently ignored
- ❌ `Bash(..., timeout: <any>)` on the spawn call — the spawn itself is ms-long;
  the engine's lifetime is not what you're timing
- ❌ `Bash(..., run_in_background: true, "bash run-dialectic.sh ...")` from a
  subagent — registers a `bash_id` that the harness reaps on subagent return,
  killing the engine mid-round (this was the Phase 3 close blocker; see
  FINDINGS §1)
- ❌ `Bash(..., run_in_background: true)` for the polling loop — same subagent
  reap hazard applies; poll with foreground Bash calls that return in <9.5min
- ❌ `exec` keyword anywhere inside `run-dialectic.sh` on the final invocation
  lines (both the `timeout`-wrapped branch and the degraded direct branch).
  `exec` replaces the bash shell with the Python process and suppresses EXIT
  trap firing, breaking marker writes (Phase 3.1 Plan Review Issue #1)
- ❌ SKILL.md reading any of `heartbeat.txt` / `dialogue.md` / `round-*.md` /
  `deliverable.md` / `lessons.md` during polling — info-hiding regression
  (Phase 2 D-07 Allowed Read list, Canary #4 guards). In Scenario B,
  MainOrchestrator does not poll at all, so this is a *no-change* from pre-3.1
- ❌ Using `Monitor` tool on the output file — Monitor is for streaming events,
  not one-shot completion; duplicate Monitor calls produce harness warnings
- ❌ Re-invoking `run-dialectic.sh` because "it seems stuck" — overwrites the
  `log_dir` artifacts and destroys forensic evidence. Use the liveness probe
  instead
- ❌ Inventing a new halt-reason enum value for the marker-absent path.
  Forbidden names that past drafts tried include
  `engine_lost` / `polling_orphan_death` / `engine_exit_missing`.
  Phase 3.1 D-TOPO-05 explicitly absorbs that path into `step_transition_hang`
  instead.
- ❌ Exposing the internal spawn metadata envelope (`engine_pid` / path fields)
  to MainOrchestrator as a `status: engine_launched` intermediate JSON —
  Scenario B keeps this strictly MetaAgent-internal. MainOrchestrator sees
  only the final `status: completed | halted` synthesized JSON

## Diagnostic-only: `ps -eo args` pattern

This pattern is **no longer** the primary liveness check (superseded by
`kill -0 $PID` in the polling loop), but remains useful for post-hoc forensics
when a workspace needs to be investigated without a captured PID:

```bash
WS_KEY=$(basename "{WORKSPACE%/}")
ps -eo args 2>/dev/null | grep -v ' grep ' \
  | grep -F "dialectic.py" | grep -qF "/$WS_KEY/"
```

Exit 0 = a dialectic.py matching this workspace is still running. Exit 1 = no
such process. Borrowed from `hooks/stop-check.sh`. **Do not invent other pgrep
patterns** — strings like `"run-dialectic"` or `"step-config.json"` appear at
different points in argv on different platforms and produce false negatives.
