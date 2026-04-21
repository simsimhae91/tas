---
phase: 03-2-layer-hang-watchdog
plan: 02
subsystem: runtime
tags: [watchdog, layer-a, asyncio-timeout, python-3.10-fallback, stdlib-only, dialectic-engine]

# Dependency graph
requires:
  - phase: 01-checkpoint-foundation
    provides: dialectic.py --self-test schema regression harness (45/45 tests — Phase 1 D-07)
  - phase: 03-2-layer-hang-watchdog / 03-01
    provides: skills/tas/runtime/tests/ canary stubs (simulate_stdout_stall.py referenced post-Wave-3)
provides:
  - _sdk_timeout(coro, timeout) awaitable wrapper in dialectic.py
  - Python 3.11+ asyncio.timeout branch + Python 3.10 asyncio.wait_for fallback, both raising TimeoutError
  - query_and_collect now dispatches through _sdk_timeout(_raw(), timeout) (no direct asyncio.wait_for call-site)
  - query_with_reconnect documents TimeoutError forwarding contract (inline comment, no code change)
  - Extended stdlib import block covering later plans' needs (os, tempfile, datetime, contextlib.asynccontextmanager, typing.AsyncIterator/Awaitable/TypeVar)
affects:
  - 03-03-PLAN.md (_heartbeat helper — will use os + tempfile + datetime already imported here)
  - 03-04-PLAN.md (_build_halt_payload + run_dialectic outer try/except — owns TimeoutError per the routing contract documented in query_with_reconnect)
  - 03-05-PLAN.md (run-dialectic.sh Layer B wrapper — pairs with this Layer A layer)
  - 03-07-PLAN.md (Wave 3 canary #5 replaces Wave 0 stub; will exercise _sdk_timeout TimeoutError path)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Awaitable wrapper (Option B from Research §3.1) — sys.version_info branch isolated to one helper, call sites read as plain return await _sdk_timeout(coro, timeout)"
    - "No cross-module import between dialectic.py and checkpoint.py (PATTERNS Anti-pattern A1 preserved)"
    - "TimeoutError as bubble-through contract — helper never catches, query_with_reconnect never catches; routed to outer run_dialectic try/except (Plan 04)"
    - "Stdlib-only watchdog — asyncio.timeout + asyncio.wait_for + sys.version_info only; zero new PyPI deps (SP-3)"

key-files:
  created: []
  modified:
    - skills/tas/runtime/dialectic.py

key-decisions:
  - "Use Option B (awaitable wrapper _sdk_timeout) instead of D-01's original async-CM naming (_sdk_timeout_cm) — Research §3.1 REVISION NOTE established that asyncio.wait_for wraps coroutines, not CM bodies, so a faithful CM form cannot be provided for the 3.10 fallback. Semantics (TimeoutError on expiry) are identical to D-01's original intent."
  - "Extend stdlib import block NOW (os, tempfile, datetime+timezone, asynccontextmanager, AsyncIterator/Awaitable/TypeVar) so Plans 03-03/03-04 (_heartbeat, _build_halt_payload) do not re-edit this block. Single-diff import churn, consistent with PATTERNS M1.a order-stable append discipline."
  - "TimeoutError is explicitly NOT caught inside _sdk_timeout or query_and_collect. The inline comment block in query_with_reconnect makes the contract visible at the raise site so future edits do not introduce a double-catch that would break the D-04 halt emit contract."
  - "query_with_reconnect gets a documentation-only change (7-line comment). The existing `if not _is_cli_dead(exc): raise` path already forwards TimeoutError correctly — the comment just makes the behaviour code-auditable without touching any executable line (git-blame stability preserved)."

patterns-established:
  - "Layer A watchdog shape — single awaitable wrapper helper (_sdk_timeout) isolates sys.version_info branching; call sites stay a single-line `return await _sdk_timeout(coro, timeout)` dispatch"
  - "Per-phase documentation comments at critical exception-routing sites — comment block inside query_with_reconnect references the controlling decision IDs (CONTEXT D-01, Research §4.2, Plan 04 D-04) so the contract survives future refactors"

requirements-completed: [WATCH-01]

# Metrics
duration: 2m46s
completed: 2026-04-21
---

# Phase 3 Plan 02: Layer A asyncio.timeout Transition Summary

**`query_and_collect` now routes through a version-aware `_sdk_timeout` helper (asyncio.timeout on Python 3.11+, asyncio.wait_for fallback on 3.10) with a TimeoutError-passes-through contract documented inline at query_with_reconnect.**

## Performance

- **Duration:** 2m46s
- **Started:** 2026-04-21T08:42:06Z
- **Completed:** 2026-04-21T08:44:52Z
- **Tasks:** 3
- **Files modified:** 1

## Accomplishments
- Layer A watchdog runtime in place: `async def _sdk_timeout(coro, timeout)` uses `async with asyncio.timeout(timeout):` on 3.11+ and falls back to `asyncio.wait_for(coro, timeout=timeout)` on 3.10. Both raise `asyncio.TimeoutError` on expiry.
- `query_and_collect` body final line swapped from `return await asyncio.wait_for(_raw(), timeout=timeout)` → `return await _sdk_timeout(_raw(), timeout)`. Signature, docstring, and `_raw()` inner function are byte-identical to the pre-edit version.
- `query_with_reconnect` gets a 7-line documentation block (no executable change) that cites CONTEXT D-01 + Research §4.2 to record why `if not _is_cli_dead(exc): raise` already forwards `TimeoutError` to `run_dialectic`'s outer try/except (Plan 04 D-04).
- Stdlib import block extended with `os`, `tempfile`, `contextlib.asynccontextmanager`, `datetime.datetime/timezone`, `typing.AsyncIterator/Awaitable/TypeVar` — enough for this plan's `_sdk_timeout` and for 03-03/03-04's future `_heartbeat` + `_build_halt_payload`.
- Module-level `T = TypeVar("T")` declared once so the helper signature stays generic and reusable.
- Phase 1 regression guard (`python3 skills/tas/runtime/dialectic.py --self-test`) continues to return `PASS: 45/45 tests passed` / exit 0 on every task boundary.
- No `checkpoint.py` cross-import introduced (PATTERNS Anti-pattern A1 preserved); no new third-party deps; `checkpoint.json` 9-field schema untouched (A4 preserved).

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend imports in dialectic.py (T1)** — `c2ae615` (refactor)
2. **Task 2: Insert _sdk_timeout helper + swap query_and_collect body (T2, T3)** — `a6f830d` (feat)
3. **Task 3: Comment in query_with_reconnect explaining TimeoutError route (T4)** — `dfe74ce` (docs)

_Plan metadata commit (SUMMARY.md + STATE.md + ROADMAP.md) follows._

## Files Created/Modified
- `skills/tas/runtime/dialectic.py` — Extended imports (+5 lines net), added `T = TypeVar("T")` (+2 lines), inserted `_sdk_timeout` helper with 8-line doc comment header and 14-line body (+22 lines), swapped final line of `query_and_collect` (+/-1 line), inserted 7-line comment block in `query_with_reconnect` (+7 lines). Total: approximately +39 net lines, all surgical and order-stable.

## Decisions Made
- **Option B (awaitable wrapper) over D-01's original `_sdk_timeout_cm` naming.** Research §3.1 REVISION NOTE and PATTERNS Anti-pattern A6 establish that `asyncio.wait_for` wraps coroutines and not context-manager bodies, so a faithful CM shape for the 3.10 fallback is impossible. The plan's action text already mandates Option B — this summary records the decision for future readers of `dialectic.py` who may wonder why D-01 says "async context manager" but the code ships `async def _sdk_timeout(coro, timeout)`.
- **Extend all later-plan imports in Task 1 rather than churn this import block across 03-03/03-04.** Follows PATTERNS M1.a order-stable append discipline: alphabetical within the existing import group, no existing order perturbed.
- **Documentation-only change to `query_with_reconnect`.** The existing logic (`if not _is_cli_dead(exc): raise`) already forwards TimeoutError correctly because `_is_cli_dead(TimeoutError) → False` (only `CLIConnectionError` is CLI death). The comment block cites CONTEXT D-01 + Research §4.2 and explicitly warns against adding a `TimeoutError` catch (which would break D-04's halt emit contract).

## Deviations from Plan

### Spec-text contradictions resolved

**1. [Rule 1 — Plan self-contradiction] Task 3 acceptance criterion `grep -c 'if not _is_cli_dead(exc):' == 1` is satisfied by the executable code, but the plan's own `<action>` text literally instructs me to include the string `if not _is_cli_dead(exc): raise` inside a backtick-quoted phrase of the new comment block, so the raw `grep -c` returns **2** (one in the comment, one in the executable line).**

- **Found during:** Task 3 verification.
- **Issue:** The `<action>` mandates the exact comment phrasing `The `if not _is_cli_dead(exc): raise` path therefore forwards asyncio.TimeoutError...` while `<acceptance_criteria>` expects only one occurrence of the pattern in the file.
- **Interpretation:** The parenthetical "(unchanged — original logic preserved)" in the acceptance bullet clearly targets the **executable** path, not the textual literal. Verified programmatically by stripping comment lines and counting: exactly 1 **executable** occurrence of `if not _is_cli_dead(exc):` (line 196). The second raw match (line 188) is inside the plan-mandated comment literal.
- **Fix:** Documented here; no code change needed. The plan's action text is authoritative and the comment-embedded literal is required for the contract citation to be auditable.
- **Files modified:** none beyond the Task 3 commit itself.
- **Committed in:** `dfe74ce` (Task 3 commit).

---

**Total deviations:** 1 acceptance-criterion spec-contradiction resolved by documentation (no code change).
**Impact on plan:** None. All `<verification>` commands + all plan `<success_criteria>` + all orchestrator-defined success criteria pass.

## Issues Encountered
- `PreToolUse:Edit` hook emitted READ-BEFORE-EDIT reminders three times even though the file had been read earlier in the same session. Edits succeeded regardless (the runtime accepted them); the reminders appear to be informational/false-positive for a file already present in the agent's Read context. No corrective action taken; no impact on the three commits.

## User Setup Required
None. Layer A runtime transition is a pure Python refactor; no env vars, no external services, no auth gates, no dependency install.

## Next Phase Readiness

- **Wave 2 / Plan 03-03 unblocked:** the `_heartbeat` helper can be inserted at its scheduled anchor (~line 310) using the already-imported `os`, `tempfile`, `datetime`, `timezone`, `contextlib.asynccontextmanager`. Path `skills/tas/runtime/dialectic.py` is in the state Plan 03-03 expects.
- **Wave 2 / Plan 03-04 unblocked:** the outer `run_dialectic` try/except for TimeoutError/CancelledError is the designated owner of the TimeoutError that `_sdk_timeout` now emits. The inline comment in `query_with_reconnect` explicitly forwards readers to Plan 04 D-04 as the catching site.
- **Wave 2 / Plan 03-05 unblocked:** the Bash Layer B wrapper in `run-dialectic.sh` is orthogonal to Layer A; no dependency on this plan beyond the conceptual pairing documented in CONTEXT D-03.
- **Wave 3 / Plan 03-07 unblocked for Layer A canary body:** Research §3.8's `simulate_stdout_stall.py` content can replace the Wave 0 stub; the replacement will trip the exact `_sdk_timeout` TimeoutError path that this plan ships. `skills/tas/runtime/tests/simulate_stdout_stall.py` (created in 03-01) remains untouched.
- **Blockers / concerns:** None.

## TDD Gate Compliance

Not applicable — plan type is `execute`, not `tdd`. No RED/GREEN/REFACTOR gate sequence expected. Task frontmatter confirms `tdd="false"` on all three tasks.

## Self-Check: PASSED

Files (all `test -f`):
- FOUND: skills/tas/runtime/dialectic.py

Commits (all `git log --oneline --all | grep`):
- FOUND: c2ae615 (refactor(03-02): extend dialectic.py imports for Layer A watchdog (T1))
- FOUND: a6f830d (feat(03-02): Layer A watchdog — _sdk_timeout helper + query_and_collect swap (T2, T3))
- FOUND: dfe74ce (docs(03-02): comment in query_with_reconnect explaining TimeoutError route (T4))

Acceptance greps (all exit 0):
- FOUND: `async def _sdk_timeout`
- FOUND: `async with asyncio.timeout(timeout):`
- FOUND: `return await _sdk_timeout(_raw(), timeout)`
- FOUND: `sys.version_info`
- NOT FOUND: `from checkpoint` (A1 preserved)
- NOT FOUND: `asyncio.wait_for(_raw()` (old direct call removed)

Regression gate:
- `python3 skills/tas/runtime/dialectic.py --self-test` → `PASS: 45/45 tests passed` / exit 0

---
*Phase: 03-2-layer-hang-watchdog*
*Completed: 2026-04-21*
