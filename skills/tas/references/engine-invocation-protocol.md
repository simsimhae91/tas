# Engine Invocation Protocol

MetaAgent reads this file in Phase 1 and uses it to invoke the Python dialectic
engine (`run-dialectic.sh`) and to capture its result.

## Why this protocol exists

A single dialectic round takes 8–12 minutes (thesis → antithesis LLM roundtrip).
Multi-round steps routinely exceed 10 minutes. The Claude Code Bash tool
**hard-caps foreground timeout at 600,000ms (10 min)**. Specifying
`timeout: 900000` or any value above 600,000 does **not** raise the cap — the
tool silently transitions the command to background at 10 min and returns a
shell ID instead of stdout. Any protocol that assumes synchronous completion
breaks at that moment.

Therefore: **never invoke the engine in the foreground.** Always use
`run_in_background: true` from the start and rely on completion notifications.

## Standard invocation pattern

```
Bash({
  command: "bash {SKILL_DIR}/runtime/run-dialectic.sh {LOG_DIR}/step-config.json",
  run_in_background: true,
  description: "Run dialectic engine for step {S.id}"
})
```

The tool returns a result of the form:

```
Command running in background with ID: <bash_id>.
Output is being written to: <output_file_path>
```

Capture both `bash_id` and `output_file_path`.

## Completion handling

The harness emits a `<task-notification>` system-reminder when the process
exits — this arrives automatically on a subsequent turn. Do not poll for it.
On receiving the notification with `status: completed`:

1. `Read(<output_file_path>)` — the file contains the engine's full stdout
2. The **last non-empty line** is the engine's final JSON result:
   - Standard: `{"status":"completed","rounds":N,"verdict":"ACCEPT","deliverable_path":"..."}`
   - Inverted: `{"status":"completed","rounds":N,"verdict":"PASS|FAIL",...}`
   - Halt:     `{"status":"halted","rounds":N,"verdict":"HALT","halt_reason":"...",...}`
3. Parse this line. Discard everything above it (progress logs / stderr).

Each invocation counts toward `engine_invocations` in the final attestation
JSON (see meta.md Phase 5).

## Liveness probe (diagnostic only — do not use for routing decisions)

If a notification has not arrived after a very long wait (>30 min) and you
need to verify the engine process is still alive, use **this exact pattern**,
which matches the process argv after `run-dialectic.sh`'s `exec` into Python:

```bash
WS_KEY=$(basename "{WORKSPACE%/}")
ps -eo args 2>/dev/null | grep -v ' grep ' \
  | grep -F "dialectic.py" | grep -qF "/$WS_KEY/"
```

Exit 0 = alive. Exit 1 = not alive. This pattern is borrowed verbatim from
`hooks/stop-check.sh` line 63, which is the canonical liveness check for this
engine.

**Do not invent other pgrep patterns.** Strings like `"run-dialectic"` or
`"step-config.json"` appear at different points in argv on different platforms
and can produce false negatives. The `dialectic.py` + workspace-basename AND
pattern is the only one validated across macOS and Linux.

## Failure classification

| Condition | Evidence | Action |
|-----------|----------|--------|
| Engine completed normally | Notification `status: completed` (exit 0), last line is valid JSON | Parse JSON, proceed |
| Engine returned HALT verdict | Notification `status: completed` (exit 0), JSON `status: halted` | Propagate `halt_reason` upward |
| Engine crashed | Notification `status: completed` with non-zero exit, no valid JSON line | Log stderr from output file, return `halt_reason: engine_crash` |
| Engine still running after long wait | No notification, liveness probe exit 0 | Continue waiting — do not HALT |
| Engine stuck / zombied | No notification, liveness probe exit 1 | Return `halt_reason: engine_lost` with `output_file` path for forensics |

## What NOT to do

- ❌ `Bash(..., timeout: 900000)` — above the 600,000 cap, silently ignored
- ❌ `Bash(..., timeout: 300000)` — any foreground timeout still blocks on the cap
- ❌ `pgrep -fl "run-dialectic|dialectic.py|step-config.json"` — improvised pattern with false negatives; use the canonical `ps -eo args` form above
- ❌ Using `Monitor` tool on the output file — Monitor is for streaming events,
  not one-shot completion; duplicate Monitor calls produce harness warnings
- ❌ Re-invoking `run-dialectic.sh` because "it seems stuck" — this overwrites
  the `log_dir` artifacts and destroys forensic evidence. Use the liveness
  probe instead
