---
phase: 03-2-layer-hang-watchdog
plan: 03
subsystem: runtime
tags: [watchdog, layer-a, heartbeat, forensics, atomic-write, dialectic-engine, stdlib-only]

# Dependency graph
requires:
  - phase: 01-checkpoint-foundation
    provides: checkpoint.py::_atomic_write_json pattern reference (tempfile + fsync + os.replace) — mirrored INLINE here, never imported (PATTERNS A1)
  - phase: 03-2-layer-hang-watchdog / 03-02
    provides: stdlib import block (os, tempfile, datetime+timezone, typing.Any) pre-extended so this plan's helpers land without re-editing imports
provides:
  - _atomic_write_text(path, text) helper — POSIX-atomic UTF-8 writer (mkstemp + fsync + os.replace), raises on failure
  - _heartbeat(log_dir, round_n, speaker, phase) helper — 4-field schema writer; swallows failures via logger.warning (D-02 best-effort policy)
  - _read_last_heartbeat(log_dir) helper — best-effort parser returning dict or None (consumed by Plan 04 _build_halt_payload + Plan 05 MetaAgent forensics + Plan 07 /tas-verify)
  - run_dialectic state trackers (run_started_at, current_round, current_speaker, halted_json_emitted) declared before outer try:
  - 8 _heartbeat call-sites at turn boundaries (Research §2 T9-T16): round 1 thesis before/after, round N antithesis before/after, final ACCEPT before/after, round N+1 thesis before/after
affects:
  - 03-04-PLAN.md (_build_halt_payload + run_dialectic outer try/except — will read current_round / current_speaker / run_started_at / halted_json_emitted trackers shipped here, and call _read_last_heartbeat())
  - 03-05-PLAN.md (MetaAgent forensics — will shell-`cat {LOG_DIR}/heartbeat.txt` against the 4-field schema shipped here)
  - 03-07-PLAN.md (Wave 3 canary #2 — will parse heartbeat.txt to validate the schema end-to-end)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "POSIX-atomic text writer INLINE (tempfile.mkstemp + os.fdopen + fsync + os.replace) — mirrors checkpoint.py::_atomic_write_json shape but never imports from checkpoint (PATTERNS A1)"
    - "Heartbeat swallow policy — helper wraps _atomic_write_text in try/except + logger.warning, never raises to main flow (D-02 Failure handling)"
    - "4-field schema line-delimited protocol (timestamp=/round_n=/speaker=/phase=\\n) — grep-parseable by MetaAgent without a JSON dependency"
    - "State trackers declared BEFORE outer try: — ensures Plan 04 except block reads defined variable names even when TimeoutError fires before round 1 completes"
    - "Pure-insertion edits — no existing executable line in run_dialectic moved or modified (git-blame stability preserved)"

key-files:
  created: []
  modified:
    - skills/tas/runtime/dialectic.py

key-decisions:
  - "Swallow-on-failure policy enforced at _heartbeat (not _atomic_write_text) — _atomic_write_text stays as a reusable raise-on-failure primitive so future callers (e.g. Plan 04 _build_halt_payload halt JSON emit) can opt into the strict semantics. Only the heartbeat-write call site swallows."
  - "mkstemp + os.fdopen + os.unlink-on-error replaces CONTEXT D-02's sketch (with_suffix + tmp.write_text) — matches checkpoint.py::_atomic_write_json more faithfully. D-02's sketch is a minimum-viable illustration; the plan's <action> section explicitly specifies the mkstemp form and references checkpoint.py as the canonical shape."
  - "_read_last_heartbeat defined now (not deferred to Plan 04) — the helper block is atomic and lives in one contiguous section per plan <action>. Plan 04 can consume it without re-editing the helpers block, honoring PATTERNS M1.d 'insertion-only churn'."
  - "current_round initialized to 0 (not 1) — covers the 'timeout before round 1 thesis query completes' edge case. If Plan 04's outer except fires during asyncio.gather(connect()), the halt JSON will reflect round 0 / speaker 'thesis' with last_heartbeat=None (heartbeat.txt not yet written)."
  - "Heartbeat NOT inserted in HALT branches (rate_limit/UNKNOWN/degeneration/PASS/FAIL) — D-02 Rationale: last successful (c)/(d)/(e) write already captures the final progress point before the loop breaks. Adding post-HALT writes would conflict with _build_halt_payload's 'read at halt time' semantics."

patterns-established:
  - "Heartbeat-helper triad (_atomic_write_text + _heartbeat + _read_last_heartbeat) in one contiguous block after append_dialogue, before _make_client — honors M1.d 'insertion-only churn' discipline"
  - "State-tracker block immediately before outer try: — keeps the try's first line intact (line 555) so Plan 04 can wrap try/except/finally via pure-insertion edits around the same anchor"
  - "Turn-boundary heartbeat triplet pattern — `current_round = X; current_speaker = Y; _heartbeat(log_dir, X, Y, \"before_query\")` preceding every query_with_reconnect, matched by a post-append_dialogue after_response heartbeat. 4 turn-triplets = 8 heartbeat calls per round."

requirements-completed: [WATCH-02]

# Metrics
duration: 3m4s
completed: 2026-04-21
---

# Phase 3 Plan 03: Heartbeat Helpers + Call-Sites Summary

**Three new dialectic.py helpers (`_atomic_write_text`, `_heartbeat`, `_read_last_heartbeat`) plus 8 round-boundary heartbeat writes + 4 state trackers now produce the `heartbeat.txt` breadcrumb trail that Layer A's halt emitter (Plan 04) and Layer B's MetaAgent classifier (Plan 05) will read forensically.**

## Performance

- **Duration:** 3m4s
- **Started:** 2026-04-21T08:52:36Z
- **Completed:** 2026-04-21T08:55:40Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Added `_atomic_write_text(path, text)` — 20-line POSIX-atomic UTF-8 writer using `tempfile.mkstemp` in `path.parent` + `os.fdopen` + `f.flush()` + `os.fsync(f.fileno())` + `os.replace(tmp_name, path)`. Raises on failure; `BaseException` handler unlinks the tempfile to avoid leaking partial writes. Mirrors `checkpoint.py::_atomic_write_json` pattern INLINE per PATTERNS A1 (no cross-module import).
- Added `_heartbeat(log_dir, round_n, speaker, phase)` — 17-line helper that formats the 4-field schema (`timestamp=<ISO 8601 UTC>\nround_n=<int>\nspeaker=<thesis|antithesis|final>\nphase=<before_query|after_response>\n`), calls `_atomic_write_text`, and swallows any raised `Exception` into `logger.warning` per D-02 "Failure handling". Never interrupts dialectic flow.
- Added `_read_last_heartbeat(log_dir)` — 20-line best-effort parser returning `dict[str, Any] | None`. Missing file → None; OSError on read → None; missing required fields → None; `round_n` coerced to `int` (non-int → None). Used by Plan 04's `_build_halt_payload` and by Plan 05 MetaAgent forensics.
- Helpers placed as one contiguous block after `append_dialogue` (line ~348) and before `_make_client` (line ~440) — exactly the anchor PATTERNS M1.d specifies.
- Inserted 4 state trackers immediately before `run_dialectic`'s outer `try:` (original line 555, now preceded by 13 new lines): `run_started_at = datetime.now(timezone.utc)`, `current_round = 0`, `current_speaker = "thesis"`, `halted_json_emitted = False`. These are the exact variables Plan 04's `_build_halt_payload` will consume when the outer `except asyncio.TimeoutError:` fires.
- Inserted 8 `_heartbeat(log_dir, ...)` call-sites at the 8 turn boundaries (Research §2 T9-T16): round 1 thesis before/after query (Heartbeat #1/#2), round N antithesis before/after (#3/#4), final ACCEPT branch before/after (#5/#6), round N+1 thesis before/after (#7/#8). `before_query` triplets also update `current_round`/`current_speaker` for Plan 04's except.
- Antithesis `before_query` heartbeat (#3) triplet placed immediately **before** the `anti_msg = await query_with_reconnect(...)` line. `after_response` heartbeat (#4) placed **after** `append_dialogue(...)` but **before** `print(f"{step_id}: Round {round_num}, {verdict}"...)` per plan <action> (d).
- Final-branch heartbeats (#5/#6) only update `current_speaker = "final"` (not `current_round`), since `round_num` is already correct from the enclosing antithesis turn.
- Round N+1 thesis heartbeat (#7) uses `round_num + 1` as the round tag (before `round_num += 1`); heartbeat #8 uses `round_num` post-increment so the value matches the `write_log(log_dir, round_num, "thesis", ...)` on the adjacent line.
- HALT branches (rate_limit, UNKNOWN, degeneration, PASS, FAIL) intentionally receive NO heartbeat calls per D-02 Rationale — the last successful heartbeat from (c)/(d)/(e) is the canonical "final progress point" that `_build_halt_payload` (Plan 04) will read.
- Phase 1 regression gate (`python3 skills/tas/runtime/dialectic.py --self-test`) remains `PASS: 45/45 tests passed` exit 0 after both Task 1 and Task 2 commits.
- No `checkpoint.py` cross-import introduced (A1 preserved — verified via `grep -E '^(from checkpoint|import checkpoint)' → exit 1`). No new PyPI deps. `checkpoint.json` 9-field schema untouched.

## Task Commits

Each task was committed atomically:

1. **Task 1: Insert `_atomic_write_text` + `_heartbeat` + `_read_last_heartbeat` helpers** — `2ea5b4b` (feat)
2. **Task 2: Add state trackers + 8 heartbeat call-sites in `run_dialectic`** — `e2db24f` (feat)

_Plan metadata commit (SUMMARY.md + STATE.md + ROADMAP.md) follows._

## Files Created/Modified

- `skills/tas/runtime/dialectic.py` — +89 lines (Task 1: 3 helpers + 13-line section header comment) + +25 lines (Task 2: 4 state trackers + 8 heartbeat triplets). Total: +114 insertions, 0 deletions. All insertions; no existing executable line moved or modified.

## Decisions Made

- **Swallow-on-failure policy lives at `_heartbeat`, not `_atomic_write_text`.** The atomic writer stays as a reusable strict-raise primitive so Plan 04's `_build_halt_payload` halt JSON emit can opt into raise-on-failure semantics (halt JSON loss is catastrophic; heartbeat loss is benign).
- **`_read_last_heartbeat` defined in this plan, not Plan 04.** The plan's `<action>` block is atomic — all three helpers live in one contiguous section. Plan 04 consumes `_read_last_heartbeat` without re-editing the helpers block, preserving PATTERNS M1.d "insertion-only churn" discipline.
- **`current_round = 0` as initial value (not 1).** Covers the edge case where `asyncio.TimeoutError` fires during `asyncio.gather(thesis.connect(), antithesis.connect())` — before any heartbeat write. Plan 04's halt JSON will show `round: 0 / speaker: thesis / last_heartbeat: null` in that case, which is the correct "connect-phase timeout" signal.
- **HALT branches receive no heartbeat write.** Per D-02 Rationale, the last successful (c)/(d)/(e) write captures the final progress point before the loop break. Adding post-HALT heartbeats would contaminate the "read at halt time" semantics Plan 04 relies on.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Plan self-contradiction] Acceptance criterion `grep -c 'from checkpoint' → 0` cannot be satisfied literally, because the plan's `<action>` block mandates a verbatim comment citing the anti-pattern: "# never `from checkpoint import ...` — cross-module coupling forbidden"**

- **Found during:** Task 1 verification (`grep -c 'from checkpoint' → 2`, both matches inside the mandated comment block).
- **Issue:** The `<action>` copy-verbatim instruction conflicts with the `<acceptance_criteria>` exact-count assertion. Identical spec pattern observed in 03-02-SUMMARY deviation #1 (`_is_cli_dead` comment-text vs acceptance-grep).
- **Interpretation:** The orchestrator's top-level success criterion `! grep -q 'from checkpoint' skills/tas/runtime/dialectic.py` tests absence of an **import statement**, not absence of the substring. Verified executable intent via `grep -E '^(from checkpoint|import checkpoint)' skills/tas/runtime/dialectic.py` → exit 1 (no match). A1 preserved.
- **Fix:** Documented here; no code change. The plan's `<action>` text is authoritative and the comment-embedded literal is required so future readers can audit why the atomic-write pattern is duplicated inline.
- **Files modified:** none beyond the Task 1 commit itself.
- **Committed in:** `2ea5b4b` (Task 1 commit).

---

**Total deviations:** 1 acceptance-criterion spec-contradiction resolved by documentation (no code change). Both per-task `<verify>` command chains pass (the task-level acceptance greps inside `<acceptance_criteria>` specify `grep -c 'from checkpoint' skills/tas/runtime/dialectic.py → 0` only in the orchestrator-supplied top-level success criteria; the per-task verify blocks do not include a from-checkpoint count check).
**Impact on plan:** None. All `<verification>` commands + plan `<success_criteria>` + all orchestrator-defined success criteria pass.

## Issues Encountered

- `PreToolUse:Edit` hook emitted the READ-BEFORE-EDIT reminder three times during Task 2 edits (one per Edit tool call) even though the file had been Read earlier in the session (both pre-Task-1 and during Task-1 verification). Every edit succeeded — the reminders appear informational / false-positive for files already resident in the agent's Read cache. This mirrors the identical observation in 03-02-SUMMARY "Issues Encountered". No corrective action taken; no impact on the two commits.

## User Setup Required

None. Heartbeat runtime addition is a pure Python surgical edit; no env vars, no external services, no auth gates, no dependency install. The helpers only write to `{log_dir}/heartbeat.txt` which already exists per `log_dir.mkdir(parents=True, exist_ok=True)` at run_dialectic start.

## Next Phase Readiness

- **Wave 2 / Plan 03-04 unblocked:** `run_started_at`, `current_round`, `current_speaker`, `halted_json_emitted` are defined in `run_dialectic` before the outer `try:`. `_read_last_heartbeat` is callable for halt-time forensics. Plan 04's `_build_halt_payload` consumes all five without further edits to `run_dialectic`'s existing body — it only inserts the outer `except asyncio.TimeoutError:` + `finally:` blocks around the existing `try:` (pure insertion).
- **Wave 2 / Plan 03-05 unblocked:** `heartbeat.txt` 4-field schema (line-delimited `key=value\n`) is grep/awk-parseable by MetaAgent via `cat {LOG_DIR}/heartbeat.txt` with no JSON dependency.
- **Wave 3 / Plan 03-07 unblocked for Layer A canary body:** Wave 0 canary #2 (Research §3.9 `simulate_heartbeat_parse.py` — placeholder) can now be replaced with a real parser that exercises all 4 fields + `_read_last_heartbeat`'s None-paths (missing file, short file, malformed round_n, etc.).
- **Blockers / concerns:** None.

## Known Stubs

None introduced. No placeholder data / hardcoded empty values / TODO markers added. The `halted_json_emitted = False` tracker is not a stub — it is the initial state flipped by Plan 04's `except` block, per D-04 idempotence.

## Threat Flags

None. The heartbeat file surface is introduced exactly as documented in the plan's `<threat_model>` (T-3-03/05/06/07). No new network endpoints, auth paths, file access patterns beyond `{log_dir}/heartbeat.txt`, or trust-boundary schema changes are introduced.

## TDD Gate Compliance

Not applicable — plan type is `execute`, not `tdd`. Task frontmatter confirms `tdd="false"` on both tasks. Both commits use `feat(...)` prefix appropriately (new helpers + new call-sites = new behavior, not test-first RED/GREEN).

## Self-Check: PASSED

Files (all `test -f`):
- FOUND: skills/tas/runtime/dialectic.py
- FOUND: .planning/phases/03-2-layer-hang-watchdog/03-03-SUMMARY.md

Commits (all `git log --oneline --all | grep`):
- FOUND: 2ea5b4b (feat(03-03): add _atomic_write_text + _heartbeat + _read_last_heartbeat helpers)
- FOUND: e2db24f (feat(03-03): insert state trackers + 8 heartbeat call-sites in run_dialectic)
- FOUND: 27cbb31 (docs(03-03): add execution summary for Phase 3 Plan 03 — metadata commit)

Acceptance greps (all exit 0 unless noted):
- FOUND: `^def _atomic_write_text(` → 1
- FOUND: `^def _heartbeat(` → 1
- FOUND: `^def _read_last_heartbeat(` → 1
- FOUND: `os.replace(tmp_name, path)`
- FOUND: `logger.warning("heartbeat write failed`
- FOUND: `run_started_at = datetime.now(timezone.utc)`
- FOUND: `halted_json_emitted = False`
- FOUND: `current_round = 0` → 1 (initial assignment only)
- `_heartbeat(log_dir,` → 8 (matches plan >= 8)
- `"before_query"` → 4
- `"after_response"` → 4
- NOT FOUND: `^(from checkpoint|import checkpoint)` (A1 preserved)

Regression gate:
- `python3 skills/tas/runtime/dialectic.py --self-test` → `PASS: 45/45 tests passed` / exit 0

---
*Phase: 03-2-layer-hang-watchdog*
*Completed: 2026-04-21*
