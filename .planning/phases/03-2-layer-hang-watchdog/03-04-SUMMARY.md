---
phase: 03-2-layer-hang-watchdog
plan: 04
subsystem: runtime
tags: [watchdog, layer-a, halt-json, stdout-contract, d-04, pitfall-6, insertion-only]

# Dependency graph
requires:
  - phase: 03-2-layer-hang-watchdog / 03-02
    provides: asyncio.timeout wrapper (_sdk_timeout) that routes TimeoutError up through query_with_reconnect into run_dialectic's outer try
  - phase: 03-2-layer-hang-watchdog / 03-03
    provides: state trackers (run_started_at / current_round / current_speaker / halted_json_emitted) + _read_last_heartbeat helper — this plan consumes all five
provides:
  - _build_halt_payload helper — keyword-only constructor for the 12-field D-04 halt JSON schema
  - run_dialectic outer except (asyncio.TimeoutError, asyncio.CancelledError) block — emits halt_reason=sdk_session_hang + watchdog_layer=A + re-raises
  - run_dialectic finally fallback — emits halt_reason=engine_crash + watchdog_layer=null (flag-guarded, P3-02 double-emit mitigation)
  - Pre-return halted_json_emitted=True flag flip (P3-02 mitigation anchor)
  - __main__ try/except annotated with Layer A↔Layer B exit-code contract (D-05 classifier row 4)
affects:
  - 03-05-PLAN.md (MetaAgent classifier in meta.md — consumes halt_reason / watchdog_layer / last_heartbeat fields shipped here)
  - 03-06-PLAN.md (run-dialectic.sh Layer B — exit-code 124/137 vs non-zero-with-halt-JSON disambiguation enabled by this plan's contract)
  - 03-07-PLAN.md (Wave 3 canary #5 /tas-verify — asserts halt_reason=sdk_session_hang, watchdog_layer=A, 4-field last_heartbeat on the emitted JSON)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "D-04 halt JSON schema — 12 fields, 5 legacy + 7 nullable extensions (backward-compat for existing parsers)"
    - "Flag-guarded fallback emit — halted_json_emitted flipped BEFORE `return result` so finally's `if not flag` guard blocks double-emit on success (P3-02)"
    - "Double-exception guard — TimeoutError AND CancelledError both caught (Python docs: `asyncio.timeout()` transforms Cancelled into Timeout, but nested cancel scope can bubble Cancelled first)"
    - "str(project_root) at halt site — schema types workspace as string, project_root is a Path internally"
    - "workspace=str(project_root) not workspace=project_root — prevents JSON serialization error inside halt emit (defensive typing at boundary)"
    - "Comment-only annotation of __main__ try/except — no executable change, establishes the exit-code handshake contract for human readers and Layer B auditing"

key-files:
  created: []
  modified:
    - skills/tas/runtime/dialectic.py

key-decisions:
  - "workspace=str(project_root) at both halt sites — the D-04 schema types workspace as string, and project_root is a Path inside run_dialectic. Explicit str() conversion prevents JSON serialization surprises and makes the boundary auditable."
  - "halted_json_emitted=True placed inside the except block, AFTER `print(json.dumps(halt, ...))` — if print raised (very rare: stdout closed mid-run), the flag stays False and the finally fallback attempts a best-effort second emit. Given the fallback's own try/except-pass, double-emit on stdout-error is acceptable; lost-emit is not."
  - "Fallback try wraps _build_halt_payload AND print separately via a single `try: ... except Exception: pass` — Pitfall 6 prescribes 'must not mask original exc'. BLE001 silenced via noqa because swallowing is load-bearing (finally must not raise over the original exception)."
  - "__main__ comment placed AFTER the pre-existing `# ISSUE-11` comment, BEFORE `try:` — preserves ISSUE-11 traceability. The two comments stack as an annotation block explaining both concerns (JSON error contract + Layer A exit-code handshake)."

requirements-completed: [WATCH-01, VERIFY-01-a]

# Metrics
duration: 3m41s
completed: 2026-04-21
---

# Phase 3 Plan 04: Layer A Halt JSON Emit + Fallback Summary

**`_build_halt_payload` helper + `run_dialectic` outer `except (TimeoutError, CancelledError)` + flag-guarded `finally` fallback complete Layer A's stdout-last-line JSON contract (D-04); TimeoutError now flows from `_sdk_timeout` → `query_with_reconnect` → `run_dialectic` outer except → halted JSON on stdout → re-raise → `__main__` `sys.exit(1)` — exactly the handshake D-05 classifier row 4 depends on.**

## Performance

- **Duration:** 3m41s
- **Started:** 2026-04-21T09:03:35Z
- **Completed:** 2026-04-21T09:07:16Z
- **Tasks:** 3
- **Files modified:** 1

## Accomplishments

- Added `_build_halt_payload(*, reason, layer, log_dir, round_n, speaker, run_started_at, step_id, workspace, deliverable_path=None)` — 47 new lines (docstring + 12-field return dict) inserted after `_read_last_heartbeat` (line ~433) and before `_make_client` (line ~489). Keyword-only args per Research §3.3. Returns the 12-field D-04 schema with `duration_sec = round((now - run_started_at).total_seconds(), 3)`. Calls `_read_last_heartbeat(log_dir)` for best-effort forensic read (None on missing/corrupt).
- Extended `run_dialectic` outer try with a new `except (asyncio.TimeoutError, asyncio.CancelledError):` block (17 lines) between `return result` and `finally:`. Constructs halt payload with `reason="sdk_session_hang"`, `layer="A"`, `workspace=str(project_root)` using state trackers (`current_round`, `current_speaker`, `run_started_at`, `step_id`) from Plan 03; calls `print(json.dumps(halt, ensure_ascii=False), flush=True)`; flips `halted_json_emitted = True`; bare `raise` re-raises so `asyncio.run()` propagates TimeoutError to `main()`'s `except Exception` → `sys.exit(1)`.
- Extended `finally:` block with a flag-guarded defensive fallback emit (22 lines prepended; existing disconnect loop preserved byte-identically). `if not halted_json_emitted:` guard wraps a second `_build_halt_payload` call with `reason="engine_crash"`, `layer=None` — fires only when an unexpected exception bypasses both the success path AND the TimeoutError/CancelledError branch (Pitfall 6 false-negative closure). Inner `try: ... except Exception: pass` prevents the fallback from masking the original exception.
- Inserted `halted_json_emitted = True` immediately before the existing `return result` line (P3-02 mitigation). This is the only line the flag-flip occupies in the success path — finally's `if not flag:` guard then skips the fallback on successful runs.
- LIFO disconnect loop (antithesis → thesis) preserved byte-identically inside finally (verified via `git diff` — the loop just shifted down by the inserted fallback block, no reflow, no character change). Git-blame stability maintained per PATTERNS M1.g.
- Annotated `__main__`'s `try: result = asyncio.run(run_dialectic(config)) / except Exception as exc:` block with a 7-line comment explaining the Layer A→Layer B exit-code contract (non-zero exit + valid halted JSON with `halt_reason=sdk_session_hang` → D-05 classifier row 4). No executable line changed — `grep -c 'result = asyncio.run(run_dialectic(config))'` = 1 (unchanged).
- `_read_last_heartbeat` (defined in Plan 03) now has a single call-site in `_build_halt_payload` — the Pyright "not accessed" warning flagged for Plan 03's orphaned helper is cleared by this plan as specified in the context note.
- Phase 1 regression gate (`python3 skills/tas/runtime/dialectic.py --self-test`) remains `PASS: 45/45 tests passed` / exit 0 after all three commits.
- No `checkpoint.py` cross-module import introduced (A1 preserved — `grep -E '^(from checkpoint|import checkpoint)' dialectic.py` → exit 1). No `checkpoint.json` schema change. No PyPI deps added. `asynccontextmanager` and `AsyncIterator` imports remain present but unused (left for Plan 03-07 cleanup as per context note).

## Task Commits

Each task was committed atomically:

1. **Task 1: Insert `_build_halt_payload` helper** — `430431c` (feat)
2. **Task 2: Extend `run_dialectic` outer try with except + finally fallback + flag flip** — `22dcaf5` (feat)
3. **Task 3: Annotate `__main__` try/except with Layer A comment** — `953284d` (docs)

_Plan metadata commit (SUMMARY.md + STATE.md + ROADMAP.md) follows._

## Files Created/Modified

- `skills/tas/runtime/dialectic.py` — +47 lines (Task 1: `_build_halt_payload` helper with 12-line docstring + 14-line return dict + section header comment) + +42 lines (Task 2: 1 flag flip + 17-line except block + 22-line fallback-emit in finally) + +7 lines (Task 3: `__main__` Layer A contract comment). Total: +96 insertions, 0 deletions. All insertions; no existing executable line moved or modified. LIFO disconnect loop byte-identical to pre-change.

## Decisions Made

- **`workspace=str(project_root)` at both halt-emit sites (not `workspace=project_root`).** D-04 schema types `workspace` as string; `project_root` is internally a `Path` in `run_dialectic`. Explicit `str()` conversion at the boundary prevents `json.dumps` serialization error inside the emit path (which would itself defeat the "stdout last-line JSON contract" the emit exists to guarantee).
- **Flag flip `halted_json_emitted = True` placed AFTER `print(json.dumps(halt, ...))` inside the except block.** If `print` raised (e.g., stdout closed mid-run), the flag stays False and the finally fallback attempts a best-effort second emit. Given the fallback's own `try/except: pass` and the astronomically-rare nature of stdout-closure mid-run, benign double-emit-attempt is preferable to silent lost-emit. Success path's flag flip is placed BEFORE `return result` (not after — unreachable) — this is the canonical placement Pitfall 6 prescribes.
- **Fallback emit's `except Exception: pass` carries a BLE001 noqa.** The linter correctly flags broad-exception-silencing as a smell; here the silencing is load-bearing (Python's finally semantics: a raise inside finally masks the original exception that triggered it, violating Pitfall 6 "must not mask original exc"). The noqa comment documents why the rule is bypassed.
- **`__main__` comment placed AFTER the existing `# ISSUE-11` comment.** Two comments now stack as an annotation block explaining both concerns (Structured JSON error output + Layer A exit-code contract). Preserves ISSUE-11 traceability per project docs convention.

## Deviations from Plan

### Auto-fixed Issues

None. All three tasks executed byte-for-byte per the plan's `<action>` blocks. Zero deviations, zero Rule 1-3 fixups required.

### Out-of-scope observations (deferred, not fixed)

- `asynccontextmanager` and `AsyncIterator` imports (added in Plan 03-02 for `_sdk_timeout` — which was later revised to a plain async function, not an async context manager) remain present-but-unused. Per the orchestrator's context note, Plan 03-07 (or a later cleanup pass) owns the removal. No action here.
- `PreToolUse:Edit` hook emitted READ-BEFORE-EDIT reminders on all three edit calls to `dialectic.py` even though the file was read earlier in the session. Identical observation to 03-02 and 03-03 summaries. Informational / false-positive. Every edit succeeded.

---

**Total deviations:** 0 code changes beyond the plan's `<action>` specifications.
**Impact on plan:** None. All `<verification>` commands + `<success_criteria>` + all orchestrator-defined plan-acceptance-criteria greps pass.

## Issues Encountered

- **Premature `state advance-plan` invocation before task execution.** While discovering `gsd-tools.cjs` usage (the tool path was not pre-exported; had to probe `gsd-tools state` then `gsd-tools state advance-plan` which has no `--help`), I inadvertently advanced the plan counter. Reverted immediately by editing STATE.md's `Plan: 5 of 7` back to `Plan: 4 of 7` and restoring the original `last_updated` / `last_activity` values. No commits made between the accidental advance and the revert. The three task commits (`430431c`, `22dcaf5`, `953284d`) were authored against the reverted STATE.md, so STATE.md is re-advanced to `Plan: 5 of 7` deliberately in the SUMMARY metadata commit below. Root cause: `gsd-tools state advance-plan` runs as a side-effecting command rather than requiring an explicit `--execute` flag.

## User Setup Required

None. Halt-JSON runtime addition is a pure Python surgical edit; no env vars, no external services, no auth gates, no dependency install. All three edits are insertion-only into the existing `dialectic.py` file.

## Next Phase Readiness

- **Wave 2 / Plan 03-05 unblocked:** MetaAgent's `meta.md` Phase 2d step 7-9 classifier can now parse the new halted-JSON extensions (`watchdog_layer`, `last_heartbeat`, `round`, `speaker`, `duration_sec`, `halted_at`, `workspace`) on Layer A emit paths. D-05 classifier rows 2 and 4 have the fields they need.
- **Wave 2 / Plan 03-06 unblocked:** `run-dialectic.sh` Layer B (SIGTERM 124 / SIGKILL 137 paths) can disambiguate Layer A emits (exit non-zero + valid `halt_reason=sdk_session_hang` halted JSON) from `bash_wrapper_kill` (exit 124/137 with no emitted JSON) using the contract this plan's `__main__` annotation documents.
- **Wave 3 / Plan 03-07 unblocked for canary #5:** `simulate_sdk_hang.py` (Research §3.8 — Wave 0 placeholder now replaceable) has the exact stdout-last-line JSON shape to assert against — `{status:halted, halt_reason:sdk_session_hang, watchdog_layer:"A", last_heartbeat:{timestamp, round_n, speaker, phase}, round:N, speaker:..., duration_sec:..., halted_at:"run-dialectic/step-...", workspace:..., deliverable_path:null}`.
- **Blockers / concerns:** None.

## Known Stubs

None introduced. No placeholder data / hardcoded empty values / TODO markers added. The `engine_crash` fallback is not a stub — it is the defensive-last-resort emit Pitfall 6 prescribes; its existence is intentional even though it fires only on unexpected exceptions bypassing both success and TimeoutError paths.

## Threat Flags

None. All new surface was pre-analyzed in the plan's `<threat_model>` (T-3-04 info disclosure of absolute workspace path → accept per local-CLI-only scope; T-3-02 double-emit via race → mitigated by flag flip before `return result`; T-3-08 lost emit via unexpected exc → mitigated by finally fallback; T-3-09 DoS via emit loop → accepted per flag-guard + one-emit-per-run discipline). No new endpoints, auth paths, file access patterns, or trust-boundary schema changes introduced beyond the plan's design.

## TDD Gate Compliance

Not applicable — plan type is `execute`, not `tdd`. Task frontmatter confirms `tdd="false"` on all three tasks. Commit prefix distribution: `feat(...)` × 2 (new behavior: halt-JSON emit path + helper) + `docs(...)` × 1 (comment-only annotation). Appropriate per Conventional Commits conventions.

## Self-Check: PASSED

Files (all `test -f`):
- FOUND: skills/tas/runtime/dialectic.py
- FOUND: .planning/phases/03-2-layer-hang-watchdog/03-04-SUMMARY.md

Commits (all `git log --oneline --all | grep`):
- FOUND: 430431c (feat(03-04): add _build_halt_payload helper for D-04 halt JSON schema)
- FOUND: 22dcaf5 (feat(03-04): extend run_dialectic outer try with Layer A halt emit + fallback)
- FOUND: 953284d (docs(03-04): annotate __main__ try/except with Layer A watchdog contract)

Acceptance greps (all pass):
- FOUND: `^def _build_halt_payload(` → 1
- FOUND: `"watchdog_layer": layer`
- FOUND: `"last_heartbeat": _read_last_heartbeat(log_dir)`
- FOUND: `except (asyncio.TimeoutError, asyncio.CancelledError)`
- FOUND: `reason="sdk_session_hang"` → 1
- FOUND: `reason="engine_crash"` → 1
- FOUND: `halted_json_emitted = True` → 2 (one before `return result`, one in except block)
- FOUND: `for agent, name in [(antithesis, "antithesis"), (thesis, "thesis")]:` → LIFO disconnect byte-identical
- FOUND: `Layer A watchdog contract:`
- FOUND: `D-05 classifier row 4`
- `_read_last_heartbeat` references: 2 (def + usage in _build_halt_payload) — Pyright "not accessed" cleared
- NOT FOUND: `^(from checkpoint|import checkpoint)` (A1 preserved)

Regression gate:
- `python3 skills/tas/runtime/dialectic.py --self-test` → `PASS: 45/45 tests passed` / exit 0

---
*Phase: 03-2-layer-hang-watchdog*
*Completed: 2026-04-21*
