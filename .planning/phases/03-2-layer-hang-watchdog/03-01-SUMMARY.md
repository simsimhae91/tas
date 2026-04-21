---
phase: 03-2-layer-hang-watchdog
plan: 01
subsystem: testing
tags: [watchdog, canary, stdlib-unittest, bash, stubs, wave-0]

# Dependency graph
requires:
  - phase: 01-checkpoint-foundation
    provides: checkpoint.json schema + --self-test harness (context for future canary wiring)
  - phase: 02-resume-entry
    provides: Canary #4 registration pattern in skills/tas-verify/canaries.md (template for Canary #5/#6 registration in Plan 07)
provides:
  - skills/tas/runtime/tests/ directory under git
  - Canary #5 stub (simulate_stdout_stall.py) emitting `PASS: canary #5` + `SKIP: pending`
  - Canary #6 PART A stub (simulate_step_transition.sh) with TAS_WATCHDOG_TIMEOUT_SEC= grep token
  - Canary #6 sub-assertion stub (simulate_step_transition_unit.py) with class TestMetaAgentClassification
  - Stable file paths for Waves 1-3 to reference before real bodies land
affects:
  - 03-02-PLAN.md (Layer A transition — may reference canary #5 path)
  - 03-05-PLAN.md (run-dialectic.sh Layer B wrapper — may reference canary #6 shell path)
  - 03-07-PLAN.md (Wave 3 wires real bodies from Research §3.8/§3.9/§3.10 + registers paths in canaries.md)
  - /tas-verify runner (downstream canary registration)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - stdlib-only test discipline (no pytest / psutil / async_timeout) — Anti-pattern A3
    - SKIP-pending stub convention (emit grep token + `SKIP: pending` note, exit 0) so Wave 0 acceptance passes without real body
    - Grep-verifiable acceptance tokens embedded as stdout strings and/or in-body references

key-files:
  created:
    - skills/tas/runtime/tests/simulate_stdout_stall.py
    - skills/tas/runtime/tests/simulate_step_transition.sh
    - skills/tas/runtime/tests/simulate_step_transition_unit.py
  modified: []

key-decisions:
  - "Use exit-0 SKIP-pending stubs (not empty files) so Wave 0 acceptance greps and exec checks pass without Research §3.8/§3.9/§3.10 bodies"
  - "Embed `TAS_WATCHDOG_TIMEOUT_SEC=` as a bash comment (not an export) so the grep token is present while the stub remains side-effect-free"
  - "Wrap placeholder unittest method in @unittest.skip so runner reports OK (skipped=1) instead of FAIL — preserves `class TestMetaAgentClassification` grep token"

patterns-established:
  - "Pattern: Wave-0 scaffolding stubs carry (a) grep-verifiable token in stdout or comment, (b) human-readable SKIP note, (c) exit 0 so canary runner treats as benign"
  - "Pattern: stdlib-only tests directory discipline (skills/tas/runtime/tests/) for all watchdog canaries"

requirements-completed: [VERIFY-01-a, VERIFY-01-b]

# Metrics
duration: 2min
completed: 2026-04-21
---

# Phase 3 Plan 01: Wave 0 Canary Scaffolding Summary

**Created skills/tas/runtime/tests/ with three stdlib-only SKIP-pending stubs (simulate_stdout_stall.py, simulate_step_transition.sh, simulate_step_transition_unit.py) so Waves 1-3 can reference canary file paths before Research §3.8/§3.9/§3.10 bodies land.**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-04-21T08:33:03Z
- **Completed:** 2026-04-21T08:34:49Z
- **Tasks:** 3
- **Files modified:** 3 (all new)

## Accomplishments
- New `skills/tas/runtime/tests/` directory committed to git (first files live under it)
- Canary #5 (Layer A / sdk_session_hang) stub emits both `PASS: canary #5` grep token and `SKIP: pending` notice; exits 0
- Canary #6 PART A (Layer B / bash_wrapper_kill) bash stub sets `set -u`, references `TAS_WATCHDOG_TIMEOUT_SEC=` in-body (grep token), emits SKIP, exits 0
- Canary #6 sub-assertion unit stub has `class TestMetaAgentClassification` with a single `@unittest.skip`-decorated placeholder test; `python3 simulate_step_transition_unit.py` reports `Ran 1 test` / `OK (skipped=1)` / exit 0
- Wave 0 acceptance — all grep tokens (`PASS: canary #5`, `TAS_WATCHDOG_TIMEOUT_SEC=`, `class TestMetaAgentClassification`, `SKIP: pending`) present and no third-party imports (pytest / async_timeout / psutil) in any file

## Task Commits

Each task committed atomically:

1. **Task 1: simulate_stdout_stall.py (Canary #5 stub)** — `b0e7dee` (feat)
2. **Task 2: simulate_step_transition.sh (Canary #6 PART A stub)** — `75cb8fc` (feat)
3. **Task 3: simulate_step_transition_unit.py (Canary #6 sub-assertion stub)** — `a7d0bc0` (feat)

_Plan metadata commit (SUMMARY.md + STATE.md + ROADMAP.md) follows._

## Files Created/Modified

- `skills/tas/runtime/tests/simulate_stdout_stall.py` — Python 3 stdlib-only stub, emits `SKIP: pending` + `PASS: canary #5` (Research §3.8 body deferred to Wave 3 / Plan 07)
- `skills/tas/runtime/tests/simulate_step_transition.sh` — bash (set -u) stub with `TAS_WATCHDOG_TIMEOUT_SEC=` comment-embedded grep token (Research §3.9 body deferred to Wave 3 / Plan 07)
- `skills/tas/runtime/tests/simulate_step_transition_unit.py` — stdlib unittest skeleton with `class TestMetaAgentClassification` + `@unittest.skip` placeholder method (Research §3.10 body deferred to Wave 3 / Plan 07)

## Decisions Made

- **Stubs, not placeholders, as the scaffolding shape.** An empty file would satisfy `test -f` but not the `python3 ... | grep -q 'PASS: canary #5'` and similar acceptance greps documented in the plan's `<acceptance_criteria>` blocks. Using executable stubs with documented SKIP tokens keeps the Wave 0 verification story clean and lets /tas-verify canary runner (once registered in Wave 3) evaluate the stubs as benign no-regressions rather than failures.
- **Bash stub references `TAS_WATCHDOG_TIMEOUT_SEC=` in a comment, not as an `export`.** An export would mutate the invoking shell's environment with no matching unset and add behavioral coupling to downstream scripts; a literal comment-embedded `TAS_WATCHDOG_TIMEOUT_SEC=` satisfies the grep check without side effects.
- **`@unittest.skip` on the placeholder test method.** An unskipped placeholder would either (a) always pass trivially (hides wiring gaps) or (b) always fail (turns Wave 0 into a red test). `@unittest.skip` makes the pending state structurally visible in test output (`OK (skipped=1)`), keeps the test discovery path and class grep token alive, and lets Wave 3 replace the decorated method with 8 real classification assertions from Research §3.10.

## Deviations from Plan

None - plan executed exactly as written.

The plan provided exact file contents in each `<action>` block; execution matched those bodies verbatim. All acceptance-criteria commands returned the expected exit codes on the first verification run.

---

**Total deviations:** 0
**Impact on plan:** None.

## Issues Encountered

None. All three stubs passed verification on first invocation (stdlib-only check, shebang check, grep-token checks, exec-to-exit-0 check all green).

## User Setup Required

None — Wave 0 scaffolding has no external input surface, no auth gates, no env vars, and no dependency install.

## Next Phase Readiness

- **Waves 1-2 unblocked:** Plans 03-02 (Layer A transition) and 03-05 (Layer B wrapper) can now reference `skills/tas/runtime/tests/simulate_stdout_stall.py` and `simulate_step_transition.sh` by stable path without worrying about missing files.
- **Wave 3 (Plan 07) inputs:** Research §3.8 (Layer A canary body), §3.9 (Layer B bash canary body), §3.10 (unit-mirror 8 assertions) are the targets that will replace the three stub bodies. Class/script names already match so Wave 3 only rewrites bodies — no grep-token churn.
- **/tas-verify registration:** Canary registration in `skills/tas-verify/canaries.md` is a Wave 3 step (Plan 07). Registration pattern reference is Canary #4 block in that file (lines ~100-135).
- **Blockers / concerns:** None.

## TDD Gate Compliance

Not applicable — plan type is `execute`, not `tdd`. No RED/GREEN/REFACTOR gate sequence expected.

## Self-Check: PASSED

Files (all `test -f`):
- FOUND: skills/tas/runtime/tests/simulate_stdout_stall.py
- FOUND: skills/tas/runtime/tests/simulate_step_transition.sh
- FOUND: skills/tas/runtime/tests/simulate_step_transition_unit.py

Commits (all `git log --oneline --all | grep`):
- FOUND: b0e7dee
- FOUND: 75cb8fc
- FOUND: a7d0bc0

---
*Phase: 03-2-layer-hang-watchdog*
*Completed: 2026-04-21*
