# tas Regression Canaries

Dogfood scenarios for manually exercising known regression classes before
shipping changes that touch `meta.md`, `SKILL.md`, `dialectic.py`, or any
`references/*.md`. There is no CI — these are intentional manual runs.

## Why canaries (not tests)

The repo is prompt-text. A unit test can only check that a string exists;
it cannot verify that Claude (the interpreter of that string) behaves
correctly under load. The canaries are **high-friction scenarios** that
reliably trigger a specific regression class if it returns — run each one
end-to-end and inspect the workspace.

Run at least every canary whose related file changed in the PR.

---

## Canary #1 — Background-transition (10-min+ scenario)

**Guards**: CONCERNS.md §2 MetaAgent ↔ Bash tool background-transition gap.
Commits `a57053b`, `734ba1e`, `bb2f2d4` fixed the class.

**Exercise**: run a `/tas` request that reliably produces a multi-round
dialectic step whose wall-clock time exceeds **10 minutes**. A request
that induces deep disagreement is the most reliable trigger — e.g.:

```
/tas "design the public API for a retry library that needs to support
sync callbacks, async callbacks, per-attempt timeouts, circuit-breaker
integration, and custom backoff strategies. Justify every trade-off."
```

Track wall-clock time on the first `구현` round. If it passes 10 minutes
and the session survives to completion, the canary passed.

**Pass criteria**:
- Final result: `{"status": "completed", ...}` (NOT `halted`)
- `engine_invocations` ≥ `N_steps × N_iterations` (no skipped steps)
- `_workspace/quick/{ts}/DELIVERABLE.md` exists and is non-empty
- No "improvised pgrep" / "Monitor duplicate" warnings in the transcript

**Fail signals (regression)**:
- `{"status": "halted", "halt_reason": "..."}` where the halt_reason is
  not a genuine engine HALT (rate-limit / unparseable / degeneration /
  persistent_failure) — i.e., an improvised bail from MetaAgent
- `halt_reason` absent or set to something invented (`engine_died`,
  `engine_lost_unexpected`, etc.) while `ps aux | grep dialectic.py`
  shows the engine is actually alive

---

## Canary #2 — Dialectic engine monopoly

**Guards**: CONCERNS.md §2 "Dialectic bypass via Agent()". Fixed twice
historically (`d22de47`, `fb68640`); third regression would appear here.

**Exercise**: any standard `/tas` multi-step run. Inspect the workspace
after completion.

**Pass criteria**:
- For every `iteration-{N}/logs/step-{id}-{slug}/` directory, all of:
  - `step-config.json`
  - `round-1-thesis.md`
  - `dialogue.md`
  - `deliverable.md`
- Final JSON `engine_invocations ≥ 1` (zero is proof of protocol violation)
- No files at the workspace root matching `01_*.md`..`NN_*.md`,
  `*dialectic_log*`, `*research_note*`, `*ideation*` (these are forbidden
  MetaAgent-authored dialectic-format files)

**Fail signals**:
- `engine_invocations: 0` or missing, with `status: completed`
- Missing any of the 4 required files in a step's log dir

---

## Canary #3 — Retry-dir preservation

**Guards**: CONCERNS.md §2 "Ralph-retry directory overwrite".

**Exercise**: a `/tas` request that induces at least one 검증 or 테스트
FAIL → 구현 retry. Deliberately under-specified requests tend to trigger
this (e.g., "implement a rate limiter" with no pass criteria beyond
"should work").

**Pass criteria**:
- If any retry occurs, sibling dirs exist:
  `iteration-{N}/logs/step-{id}-{slug}-retry-1/`, `-retry-2/`, etc.
- The original `step-{id}-{slug}/` is preserved (not overwritten)
- Each retry dir has its own `step-config.json` and round logs

**Fail signals**:
- `step-{id}-{slug}/` contains logs from multiple attempts (overwrite)
- `-retry-N` dirs missing when `consecutive_fail_count` in the final
  JSON was > 1

---

## Canary #4 — Resume info-hiding (I-1 regression guard)

**Guards**: `.planning/phases/02-resume-entry/02-CONTEXT.md` D-07 Layer 2; RESUME-02.
Catches the regression class where `SKILL.md` Phase 0b (or any other Phase) reads
dialectic artifacts — breaks the MainOrchestrator info-hiding boundary.

**Exercise**: run the grep check against `skills/tas/SKILL.md`. This is a
static lint — no `/tas` invocation needed:

```bash
SKILL_PATH="${CLAUDE_PLUGIN_ROOT:-.}/skills/tas/SKILL.md"
grep -nE 'dialogue\.md|round-[0-9]+-(thesis|antithesis)\.md|deliverable\.md|lessons\.md|heartbeat\.txt' "$SKILL_PATH"
```

**Pass criteria**:
- Command exit code **1** (zero matches — SKILL.md does not reference any
  dialectic artifact filename as a Read target)
- No stdout lines
- Note: matches within SCOPE warning comments or anti-feature HTML blocks are
  ALLOWED (the regex is intentionally strict; reviewer visually confirms
  matches are only in forbidden-list documentation, not in Read() calls).
  Running this canary should still exit 1 overall — the SCOPE comment uses
  the filenames *as examples of forbidden targets*, and the line should be
  structured so the bare filenames do not appear literally in the SCOPE line
  (the SCOPE line uses them inside a narrative sentence — verify via diff
  against Plan 01 acceptance criteria).

**Fail signals (regression)**:
- Exit code 0 (any match found) → MainOrchestrator has developed an info-leak
  path; remove the reference and route users to `/tas-explain` or
  `/tas-workspace` for dialectic inspection instead (per CLAUDE.md line 128
  post-Phase-2 wording).
- Any stdout line like `NNN:<content containing dialogue.md, round-N-thesis.md,
  round-N-antithesis.md, deliverable.md, or lessons.md>` in a Read/Bash context

---

## Canary #5 — Layer A stdout-stall (VERIFY-01 a)

**Guards**: `.planning/phases/03-2-layer-hang-watchdog/03-CONTEXT.md` D-07 Canary #5;
WATCH-01; WATCH-02 (last_heartbeat read path). Catches the regression class where
`dialectic.py`'s outer try/except fails to emit a halted JSON with
`halt_reason=sdk_session_hang` + `watchdog_layer=A` + 4-field `last_heartbeat` after
a TimeoutError fires inside `query_and_collect` (Layer A asyncio.timeout).

**Exercise**: subprocess-spawn `dialectic.py` with a PYTHONPATH-injected mock
ClaudeSDKClient whose `receive_response` stalls longer than `query_timeout`.
stdlib-only. Target wall-clock ≤ 10s.

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-.}/skills/tas/runtime/tests/simulate_stdout_stall.py"
```

**Pass criteria**:
- Command exit code **0** and stdout contains the line `PASS: canary #5`
- Under the hood: spawned dialectic.py subprocess exit is non-zero (TimeoutError re-raise
  surfaces as sys.exit(1) in `__main__`)
- Among the last non-empty stdout lines of the spawned dialectic.py, one parses
  as JSON with `status == "halted"`, `halt_reason == "sdk_session_hang"`,
  `watchdog_layer == "A"`, and a 4-field `last_heartbeat` object
  (timestamp, round_n, speaker, phase). Note: dialectic.py's `main()` emits
  a trailing `{"status":"error"}` line after re-raise (ISSUE-11); the canary
  scans the last 5 lines for the halted JSON.

**Fail signals (regression)**:
- Exit code 1 with any `FAIL:` line → dialectic.py's Layer A halt emit regressed
  (missing field, wrong halt_reason, or no halted JSON at all)
- Wall-clock > 30s → Layer A may not be tripping; check that `_sdk_timeout` branch
  still uses `asyncio.timeout` on 3.11+ / `asyncio.wait_for` on 3.10

---

## Canary #6 — Layer B step-transition hang (VERIFY-01 b)

**Guards**: `.planning/phases/03-2-layer-hang-watchdog/03-CONTEXT.md` D-07 Canary #6;
WATCH-03; WATCH-04 (classification path). Catches regressions in the Bash watchdog
wrapper (`run-dialectic.sh` missing `--kill-after` or env var detection broken) and
in MetaAgent's classification of exit 0 + no-JSON → `step_transition_hang`.

**Exercise**: two parts. PART A drives Layer B SIGTERM/SIGKILL end-to-end (requires
coreutils `timeout` or `gtimeout` — SKIP on absent hosts per D-03 graceful degrade).
PART B unit-tests the classification function that mirrors meta.md D-05.

```bash
# PART A — end-to-end Layer B kill (SKIP on no-coreutils macOS)
bash "${CLAUDE_PLUGIN_ROOT:-.}/skills/tas/runtime/tests/simulate_step_transition.sh"

# PART B — classification table unit mirror
python3 "${CLAUDE_PLUGIN_ROOT:-.}/skills/tas/runtime/tests/simulate_step_transition_unit.py"
```

**Pass criteria**:
- PART A exit 0 with stdout `PASS: canary #6` OR `SKIP:` (SKIP only on hosts without
  `timeout`/`gtimeout` — SKIP is explicitly NOT a regression per D-03)
- PART A wall-clock ≤ 17s (TIMEOUT_SEC=5 + KILL_GRACE=2 + ~10s startup margin)
- Spawned `run-dialectic.sh` exit code must be 124 (SIGTERM) or 137 (SIGKILL)
- PART B: all 8 `unittest` test methods pass (exit 0 from `python3 ...simulate_step_transition_unit.py`)

**Fail signals (regression)**:
- PART A exit 1 with `FAIL:` line → Layer B wrapper or `--kill-after` broke; check
  `run-dialectic.sh` lines that detect `timeout`/`gtimeout` and the wrapped-exec
  branch
- PART A exit code not in {0, 124, 137} with coreutils installed → preflight
  regression (check `command -v` idiom)
- PART B unittest failure → MetaAgent classification drift (03-CONTEXT.md D-05);
  reconcile with the meta.md table the canary mirrors

---

## When to add a new canary

Add one whenever:
1. A regression is merged and fixed (commit the canary alongside the fix)
2. A class of failure affects the MetaAgent protocol that Python cannot check
3. A `CLAUDE.md` "Common Mistakes" bullet is added — should have a canary
   that would catch the next occurrence
