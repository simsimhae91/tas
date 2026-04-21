---
phase: 03-2-layer-hang-watchdog
plan: 07
subsystem: docs+verify
tags: [watchdog, halt_reason, canary, info-hiding, phase-3-close]
requires:
  - WATCH-03 (run-dialectic.sh watchdog wrapper — Plan 05)
  - WATCH-04 (MetaAgent classification + meta.md step 8 — Plan 06)
  - Plan 03-01 Wave 0 canary scaffolding stubs
provides:
  - WATCH-05 (SKILL.md user-facing HALT labels + Korean recovery)
  - VERIFY-01 (a)+(b) end-to-end canary regression guards
  - engine-invocation-protocol.md bash_wrapper_kill + step_transition_hang rows
  - research/ARCHITECTURE.md §6.4 rename annotation (snapshot preservation)
affects:
  - skills/tas/SKILL.md (user-facing HALT display)
  - skills/tas/references/engine-invocation-protocol.md (MetaAgent reference)
  - .planning/research/ARCHITECTURE.md §6.4 (research snapshot)
  - skills/tas-verify/canaries.md (regression canary registry)
  - skills/tas/runtime/tests/ (Canary #5 + #6 bodies)
tech-stack:
  added: []
  patterns:
    - Order-stable append to existing tables (PATTERNS SP-5)
    - Info-hiding canary regex extension with new filename (PATTERNS A2)
    - Research document snapshot annotation via blockquote (PATTERNS A5)
    - Hunk-level git staging to exclude pre-existing WIP from commit
key-files:
  created: []
  modified:
    - skills/tas/SKILL.md
    - skills/tas/references/engine-invocation-protocol.md
    - .planning/research/ARCHITECTURE.md
    - skills/tas-verify/canaries.md
    - skills/tas/runtime/tests/simulate_stdout_stall.py
    - skills/tas/runtime/tests/simulate_step_transition.sh
    - skills/tas/runtime/tests/simulate_step_transition_unit.py
    - skills/tas/runtime/dialectic.py (unused-import cleanup only)
decisions:
  - Task 3 (.planning/research/ARCHITECTURE.md) persisted to disk but not git-committed — .planning/ is gitignored per project convention; edits are durable but never tracked, matching prior plans 03-01..03-06 pattern
  - Canary #5 assertion scans last 5 stdout lines for halted JSON (not lines[-1]) — dialectic.py main() emits a trailing {status:error} line after TimeoutError re-raise (ISSUE-11 comment); MetaAgent's D-05 classifier handles the same pattern via row 4, so scanning is the correct mirror
  - Canary #5 REPO_ROOT uses parents[4] not parents[3] — Research §3.8 sketch's "4 levels up" comment resolves to parents[4] (tests→runtime→tas→skills→REPO), not parents[3] which lands on skills/
  - Import cleanup kept separate commit from Canary wiring — dialectic.py touchpoints tracked atomically for Pyright hygiene vs behavioral feature commits
  - Pre-existing max_buffer_size=10MB WIP in _make_client deliberately excluded from this plan's commits via hunk-level staging (git apply --cached); remains in working tree for future ownership
metrics:
  duration: 9m22s
  completed: 2026-04-21T09:43:20Z
---

# Phase 3 Plan 07: Phase 3 Close — SKILL.md + engine-invocation-protocol + ARCHITECTURE snapshot + Canary #5/#6 Summary

Phase 3's final plan closes the user-facing documentation surface (3 halt_reason rows × 2 SKILL.md tables), aligns the reference engine-invocation-protocol + research ARCHITECTURE snapshot with ROADMAP-official enum names, wires real regression-canary bodies for Layer A + Layer B into the 3 Wave-0 scaffolding stubs, and registers Canary #5 + #6 in canaries.md with a Canary #4 info-hiding regex extension for the new `heartbeat.txt` file. WATCH-05 + VERIFY-01 (a)+(b) complete; Phase 3 done.

## Commits

| Task | Commit  | Type     | Message                                                                 |
| ---- | ------- | -------- | ----------------------------------------------------------------------- |
| 1    | 56d3fba | feat     | add Phase 3 halt_reason rows to SKILL.md tables                         |
| 2    | c3b15e3 | docs     | append 2 failure-classification rows to engine-invocation-protocol     |
| 3    | (n/a)   | disk-only | .planning/research/ARCHITECTURE.md §6.4 annotation — gitignored         |
| 4    | aac09a7 | feat     | wire real Canary #5 + #6 bodies; register in canaries.md               |
| +    | 90391c3 | refactor | remove unused imports left over from Plan 03-02                        |

Task 3 persisted to disk-tracked `.planning/` but the directory is gitignored (`.gitignore:5`), so the annotation is durable without a git commit — matching the pattern of prior plans 03-01 through 03-06 which all describe `.planning/` edits in commit messages but only commit `skills/`-tracked files.

## Work Completed

### Task 1 — SKILL.md HALT Reason Labels + Recovery Guidance tables (commit 56d3fba)

Appended 3 new rows to each of the two Phase 1/2 tables in `skills/tas/SKILL.md`, inserted immediately after `already_completed` (the last Phase-2 row) and before `(other)` (the catch-all):

**HALT Reason Labels (+3 rows):**
- `sdk_session_hang` → "SDK session hang (SDK 세션 무응답)"
- `step_transition_hang` → "Step transition hang (스텝 전환 중 무응답)"
- `bash_wrapper_kill` → "Watchdog forced termination (워치독 강제 종료)"

**Recovery Guidance (+3 rows)** — Korean user-facing messages reference `/tas --resume` + `TAS_WATCHDOG_TIMEOUT_SEC` env var per CONTEXT D-06:
- `sdk_session_hang` → SDK 무응답 복구 (재시도 또는 timeout 늘리기)
- `step_transition_hang` → 엔진 결과 없이 종료 복구 (재시도 또는 `/tas-workspace` 로그 확인)
- `bash_wrapper_kill` → Watchdog 강제 종료 복구 ("설정된 시간 내 응답 부재" — raw numeric 124/137 노출 회피)

**Order-stable append (PATTERNS SP-5):** all pre-existing 15 Labels rows + 12 Recovery rows preserved byte-identically. `(other)` catch-all stays at bottom of each table (grep count = 1 each). `heartbeat.txt` deliberately NOT introduced to SKILL.md (A2 info-hiding boundary preserved — `grep -nE 'heartbeat\.txt' skills/tas/SKILL.md` exit 1).

### Task 2 — engine-invocation-protocol.md Failure classification table (commit c3b15e3)

Appended 2 rows to the Failure classification table after the last existing row (`Engine stuck / zombied`) and before the `## What NOT to do` heading:

- `Bash wrapper killed engine | Notification exit 124 or 137 | Return halt_reason: bash_wrapper_kill, watchdog_layer: B, wrapper_exit: <code>; read {LOG_DIR}/heartbeat.txt for last_heartbeat`
- `Engine exit 0 + last line not JSON | Notification exit 0, no parseable JSON tail | Return halt_reason: step_transition_hang, watchdog_layer: B; read {LOG_DIR}/heartbeat.txt for last_heartbeat`

Both rows explicitly reference the `heartbeat.txt` forensic path for MetaAgent `last_heartbeat` synthesis (per CONTEXT D-05 · Plan 06 meta.md step 8). Header, 5 existing data rows, and all 4 surrounding sections (`## Why this protocol exists`, `## Standard invocation pattern`, `## Completion handling`, `## Liveness probe`, `## What NOT to do`) byte-identical.

Final file length: 96 lines (≥ 96 target).

### Task 3 — .planning/research/ARCHITECTURE.md §6.4 snapshot annotation (disk-only — .planning/ gitignored)

Added a single 9-line blockquote annotation at the TOP of `### 6.4 halt_reason 열거값 — M1 확장`, immediately after the heading and before the body:

```
> **2026-04-21 update (Phase 3 execution)**: `halt_reason` names were realigned
> to ROADMAP-official values: `sdk_session_timeout` → `sdk_session_hang`,
> `bash_timeout_killed` → `bash_wrapper_kill`. Additionally,
> `step_transition_hang` is a new enum ...
> Authoritative source: .planning/phases/03-2-layer-hang-watchdog/03-CONTEXT.md
> D-06 + SKILL.md HALT Reason Labels.
```

Body of §6.4 (old-name table with `sdk_session_timeout`/`bash_timeout_killed` + `chunk_merge_conflict`) preserved byte-identical as historical snapshot per PATTERNS A5. Both old names still grep-present in the file — reconciliation is done at the annotation header, not by rewriting the snapshot.

### Task 4 — Canary #5 + #6 real bodies + canaries.md registration (commit aac09a7)

Replaced 3 Wave-0 SKIP-pending stubs with real regression canaries (Research §3.8/§3.9/§3.10 bodies):

**`simulate_stdout_stall.py` (Canary #5, Layer A, PASS in 5.1s):**
- PYTHONPATH-injects a mock `claude_agent_sdk` module whose `ClaudeSDKClient.receive_response` stalls 60s via `asyncio.sleep`
- Spawns `dialectic.py` subprocess with `query_timeout=5` → Layer A `asyncio.timeout` trips at 5s
- Asserts non-zero exit + halted JSON (found by scanning last 5 lines) with `status=halted`, `halt_reason=sdk_session_hang`, `watchdog_layer=A`, 4-field `last_heartbeat` (timestamp, round_n, speaker, phase)
- stdlib-only (subprocess, json, tempfile, shutil, asyncio, pathlib, os, sys) — PATTERNS A3 preserved

**`simulate_step_transition.sh` (Canary #6 PART A, Layer B, SKIP on current host per D-03):**
- Coreutils `timeout`/`gtimeout` preflight — SKIP (exit 0) if absent (NOT a regression per D-03 graceful-degrade)
- On hosts with coreutils: spawns `run-dialectic.sh` with `TAS_WATCHDOG_TIMEOUT_SEC=5` + mock client `sleep(30)`, asserts exit 124/137 and wall-clock ≤ 17s
- Grep tokens preserved: `TAS_WATCHDOG_TIMEOUT_SEC=5` (export, not comment now — Wave 3 behavior), `timeout >/dev/null 2>&1` preflight

**`simulate_step_transition_unit.py` (Canary #6 PART B, PASS in 0.001s):**
- Pure-Python `classify(exit_code, last_line)` function mirrors meta.md Phase 2d step 8 / CONTEXT D-05 7-row classification table
- 8 unittest methods cover all D-05 rows: exit 0/124/137/non-zero × JSON present/absent/halted
- Wave-0 grep compatibility alias: `TestMetaAgentClassification = StepTransitionHangTest` (zero behavioral cost — class is discovered both ways, so 8 tests run twice = 16 reported)

**`canaries.md` — Canary #4 regex extension + Canary #5/#6 registration:**
- Canary #4 (SKILL.md info-hiding grep) regex extended with `|heartbeat\.txt` (PATTERNS A2). SKILL.md info-hiding boundary now covers the Phase 3 agent-internal artifact.
- Canary #5 + #6 sections inserted between Canary #4 and `## When to add a new canary`, each carrying 4 sub-blocks (**Guards** / **Exercise** / **Pass criteria** / **Fail signals**) matching Canary #4's template.
- Canary #5 Pass criteria documents the "scan last 5 lines" contract explicitly so future readers know why `lines[-1]` isn't the halted JSON.

### Bonus — Unused-import cleanup in dialectic.py (commit 90391c3)

Plan 03-02 pre-emptively imported `asynccontextmanager` + `AsyncIterator` for an async-CM design of `_sdk_timeout`, but Research §3.1 REVISION NOTE pivoted to the plain-async Option B signature. These names have been unused and Pyright-flagged through Waves 1-2.

- Drop `from contextlib import asynccontextmanager` (line 24)
- Drop `AsyncIterator` from `from typing import ...` (line 27); kept `Any, Awaitable, TypeVar`

Sanity: `python3 dialectic.py --self-test` → 45/45 green. Canaries still pass.

Staged via `git apply --cached` on a hand-built hunk-level patch (lines 22-28 of the header) to exclude the pre-existing uncommitted `max_buffer_size=10 * 1024 * 1024` WIP at line 518-520 — that one-liner is NOT a Phase 3 concern and remains in the working tree unstaged for later ownership.

## Phase-Wide Verification (10-point check from plan)

| # | Check | Result |
|---|-------|--------|
| 1 | `grep -cE 'sdk_session_hang\|step_transition_hang\|bash_wrapper_kill' skills/tas/SKILL.md` ≥ 6 | **6** ✓ |
| 2 | `grep -q '03-CONTEXT.md D-05' skills/tas/agents/meta.md` | exit 0 ✓ |
| 3 | `grep -q 'asyncio.timeout' skills/tas/runtime/dialectic.py` | exit 0 ✓ |
| 4 | `grep -c '_heartbeat(log_dir,' skills/tas/runtime/dialectic.py` ≥ 8 | **8** ✓ |
| 5 | `grep -qE 'command -v (timeout\|gtimeout)' skills/tas/runtime/run-dialectic.sh` | exit 0 ✓ |
| 6 | `grep -q -- '--kill-after' skills/tas/runtime/run-dialectic.sh` | exit 0 ✓ |
| 7 | `grep -q 'bash_wrapper_kill' skills/tas/references/engine-invocation-protocol.md` | exit 0 ✓ |
| 8 | `grep -q '2026-04-21 update (Phase 3 execution)' .planning/research/ARCHITECTURE.md` | exit 0 ✓ |
| 9a | Canary #5 (Layer A): `python3 simulate_stdout_stall.py` | **PASS** (5.1s) ✓ |
| 9b | Canary #6 PART A (Layer B): `bash simulate_step_transition.sh` | **SKIP** (no coreutils, per D-03) ✓ |
| 9c | Canary #6 PART B: `python3 simulate_step_transition_unit.py` | **PASS** (16 tests via class+alias) ✓ |
| 10 | `grep -nE 'heartbeat\.txt' skills/tas/SKILL.md` (MUST exit 1 — A2 info-hiding) | exit 1 ✓ |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] Canary #5 REPO_ROOT path off-by-one**
- **Found during:** Task 4(a) first run
- **Issue:** Research §3.8 sketch said `REPO_ROOT = Path(__file__).resolve().parents[3]`, which resolves to `/Users/hosoo/working/projects/tas/skills/` (the `skills/` dir, not the repo root). Result: `DIALECTIC_PY = .../skills/skills/tas/runtime/dialectic.py` → FileNotFoundError, canary failed with "FAIL: no stdout output".
- **Fix:** Changed to `parents[4]` with comment "(tests → runtime → tas → skills → REPO_ROOT)". Action text's description "4 levels up from skills/tas/runtime/tests" confirms the intended 4-edge traversal, which is `parents[4]` in Python (each edge increments the index, and `parents[0]` is already one edge up).
- **Files modified:** skills/tas/runtime/tests/simulate_stdout_stall.py (line 24)
- **Commit:** aac09a7 (bundled with Task 4)

**2. [Rule 1 — Bug] Canary #5 assertion `lines[-1]` mismatches dialectic.py main() emission pattern**
- **Found during:** Task 4(a) second run (after fix #1)
- **Issue:** Research §3.8 sketch asserted `last = json.loads(lines[-1])`, but dialectic.py's `main()` function (line 915-920, ISSUE-11 comment) intentionally emits two stdout lines on Layer A trip: (1) the halted JSON from `run_dialectic`'s TimeoutError except branch, then (2) a trailing `{"status":"error", "error":""}` from the outer `except Exception` handler after re-raise. Canary asserted status="halted" on line 2, saw status="error", failed.
- **Fix:** Scan the last 5 non-empty lines in reverse order for the first parseable JSON with `status == "halted"`. This mirrors how MetaAgent's CONTEXT D-05 classifier (row 4: "non-zero exit + valid JSON → propagate halt_reason") would correctly extract the halt_reason in production — the canary now reflects real-system behavior, not an idealized single-line emission.
- **Files modified:** skills/tas/runtime/tests/simulate_stdout_stall.py (lines 137-163)
- **Commit:** aac09a7 (bundled with Task 4)
- **Documentation updated:** canaries.md Canary #5 Pass criteria explicitly notes the trailing `{status:error}` line and the scan strategy.

### Intentional Plan Interpretations (not deviations)

- **Task 3 not git-committed.** `.planning/` is gitignored (`.gitignore:5`) — this is the established project convention (prior plans 03-01..03-06 all edit `.planning/` via disk-write only; `git log` shows no `.planning/` paths). The annotation is persisted on disk and will be used by downstream tools, but no git commit exists for Task 3. This matches the "standard single-repo" commit flow when there are no tracked files to stage.
- **Pre-existing `max_buffer_size` WIP untouched.** `_make_client` in dialectic.py had an uncommitted one-liner `max_buffer_size=10 * 1024 * 1024` (line 520 pre-cleanup) added in a prior uncommitted session. Used `git apply --cached` with a hand-built hunk-level patch to stage ONLY the import cleanup (lines 22-28) so the WIP remains unstaged. Future plan owns the max_buffer_size decision.

## Regression Guards Preserved

- **A1 (no cross-module coupling):** `grep -c 'from checkpoint' skills/tas/runtime/dialectic.py` returns 2, both are comment-only text (lines 351-352 explicitly document the "never `from checkpoint import ...`" anti-pattern); no actual import statements added.
- **A2 (info-hiding):** heartbeat.txt NOT in SKILL.md (check 10 above); Canary #4 regex extended to guard against future drift.
- **A3 (stdlib-only tests):** `grep -E '^(import|from) (pytest|async_timeout|psutil)' tests/*.py` exit 1 (no matches).
- **A5 (research snapshot):** ARCHITECTURE.md §6.4 body preserved; only a top-of-section blockquote added.
- **checkpoint.json schema unchanged:** no new fields; halt_reason remains open-string per Phase 1 D-03.
- **Phase 1 `--self-test`:** 45/45 green.

## Known Stubs

None. All Wave-0 SKIP-pending stubs replaced with real bodies. The 3 canary files now carry behavioral assertions, not grep-token placeholders.

## Threat Flags

None. No new network endpoints, auth paths, file access patterns, or schema changes introduced at trust boundaries. All edits are in-process (canaries subprocess into their own tmpdir, auto-cleaned via `trap rm -rf` + `shutil.rmtree`).

## Self-Check: PASSED

- [x] `skills/tas/SKILL.md` modified — 6 halt_reason rows present (`grep -cE 'sdk_session_hang|step_transition_hang|bash_wrapper_kill'` = 6)
- [x] `skills/tas/references/engine-invocation-protocol.md` modified — bash_wrapper_kill + step_transition_hang rows present
- [x] `.planning/research/ARCHITECTURE.md` modified on disk — "2026-04-21 update (Phase 3 execution)" grep found
- [x] `skills/tas-verify/canaries.md` modified — `## Canary #5` and `## Canary #6` headers found; Canary #4 regex extended with `heartbeat\.txt`
- [x] `skills/tas/runtime/tests/simulate_stdout_stall.py` modified — `PASS: canary #5` token present; canary exits 0 in 5.1s
- [x] `skills/tas/runtime/tests/simulate_step_transition.sh` modified — `TAS_WATCHDOG_TIMEOUT_SEC=5` export; coreutils preflight present; exits 0 (SKIP)
- [x] `skills/tas/runtime/tests/simulate_step_transition_unit.py` modified — `class StepTransitionHangTest` + `TestMetaAgentClassification = StepTransitionHangTest` alias; 16 tests pass
- [x] `skills/tas/runtime/dialectic.py` modified — unused `asynccontextmanager` + `AsyncIterator` imports removed; `--self-test` 45/45 green
- [x] Commit 56d3fba (Task 1) in `git log`
- [x] Commit c3b15e3 (Task 2) in `git log`
- [x] Commit aac09a7 (Task 4) in `git log`
- [x] Commit 90391c3 (import cleanup) in `git log`
- [x] Pre-existing `max_buffer_size` WIP NOT committed (still unstaged in working tree)
