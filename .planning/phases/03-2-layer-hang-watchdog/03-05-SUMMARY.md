---
phase: 03-2-layer-hang-watchdog
plan: 05
subsystem: runtime
tags: [watchdog, layer-b, bash-timeout, coreutils, graceful-degrade, d-03, watch-03, run-dialectic]

# Dependency graph
requires:
  - phase: 03-2-layer-hang-watchdog / 03-02
    provides: Layer A asyncio.timeout wrapper — Layer B operates above Layer A on the process tree so the graceful-degrade branch can credibly claim "Layer A remains active"
  - phase: 03-2-layer-hang-watchdog / 03-04
    provides: run_dialectic outer try/except + halt JSON stdout contract — when Layer B SIGTERM fires, the engine's finally fallback still emits halt_reason=engine_crash (engine-level halt JSON + wrapper exit 124/137 together disambiguate bash_wrapper_kill)
provides:
  - run-dialectic.sh Layer B wrapper block — coreutils timeout/gtimeout detection + 2-stage kill (SIGTERM → --kill-after → SIGKILL)
  - TAS_WATCHDOG_TIMEOUT_SEC / TAS_WATCHDOG_KILL_GRACE_SEC env var override path (defaults 1200s / 30s)
  - Graceful-degrade branch — stderr 2-line warning + unwrapped exec when neither `timeout` nor `gtimeout` is on PATH
  - Preserved find_python preflight (lines 1-33 byte-identical to HEAD before this plan)
affects:
  - 03-06-PLAN.md (meta.md classifier — consumes exit codes 124/137 as bash_wrapper_kill signal; this plan ships the coreutils contract the classifier reads)
  - 03-07-PLAN.md (Wave 3 canary #6 — exports TAS_WATCHDOG_TIMEOUT_SEC=5 to trip Layer B once coreutils is installed in the test env)

# Tech tracking
tech-stack:
  added:
    - "coreutils `timeout(1)` / `gtimeout` (optional external; graceful degrade when absent)"
  patterns:
    - "CLI capability probe via `command -v <bin> >/dev/null 2>&1` — same POSIX idiom as find_python's `python3 -c ...` probe; no bashism escalation"
    - "Parallel detection of GNU (Linux default `timeout`) + Homebrew macOS (`gtimeout` from `brew install coreutils`) — TIMEOUT_BIN empty-string sentinel drives the degrade branch"
    - "2-stage kill via `--kill-after=<grace>s <budget>s` — SIGTERM after budget, SIGKILL <grace>s later; exit codes 124/137 signal bash_wrapper_kill to Plan 06's classifier"
    - "Env-var override via `${TAS_WATCHDOG_TIMEOUT_SEC:-1200}` parameter expansion — zero schema drift in step-config.json (M1 minimal surface-area principle, D-03 Rejected alternative)"
    - "Graceful degrade: stderr 2-line warning + unwrapped `exec \"$PYTHON\" ...` — byte-identical to the legacy line-35 exec on degrade path (Layer A still covers hangs)"
    - "User-input validation delegated to coreutils (exit 125 on bad duration syntax) — P3-05 scope creep avoidance"
    - "Explicit `s` suffix on duration arguments (`\"${VAR}s\"`) — defense against future edits that might pass bare integers (coreutils accepts bare = seconds, but explicit is safer)"

key-files:
  created: []
  modified:
    - skills/tas/runtime/run-dialectic.sh

key-decisions:
  - "Env-var override path (TAS_WATCHDOG_TIMEOUT_SEC / TAS_WATCHDOG_KILL_GRACE_SEC) chosen over step-config.json schema field — STATE.md Open Question (정상 step 실측 분포 미수집) settled with default + user-adjustable override; schema change cost > runtime benefit in M1."
  - "Graceful degrade (stderr warn + unwrapped exec) chosen over HARD FAIL on coreutils absence — D-03 Rejected alternative; macOS without Homebrew coreutils is a realistic dev configuration and Layer A already covers asyncio-level hangs."
  - "No user-input validation for TAS_WATCHDOG_TIMEOUT_SEC (abc/0/-5) — delegated to coreutils exit 125, which Plan 06's classifier will route as engine_crash (P3-05 + T-3-01 threat-register disposition)."
  - "Explicit `s` suffix on both duration args even though coreutils accepts bare integers as seconds — defense against future refactors that might pass minutes/hours via env override (forward-compat without extra code)."
  - "No `set -u` / `set -e` added — existing preflight uses `[ -z \"$PYTHON\" ]` check which relies on unset=empty semantics; adding `set -u` would regress the error path."
  - "Comment-only annotation of coreutils exit codes (124/137) inside the wrapped branch — audit trail for Plan 06 classifier (readers can trace exit-code → halt_reason without opening CONTEXT D-03)."
  - "Human-verify checkpoint (Task 2) auto-approved under auto-mode policy; replaced by automated dry-smoke (`bash run-dialectic.sh /nonexistent.json`) which confirmed exact 2-line stderr warning + Python JSON error path + exit 1 (not 124/137 — wrapper correctly degraded)."

patterns-established:
  - "Surgical bash edit anchor: find_python preflight byte-identical (lines 1-33); only the final exec line is replaced — PATTERNS M2 compliance"
  - "Parameter-expansion default pattern (`${VAR:-DEFAULT}`) for all tunables — no POSIX-shell math, no arithmetic expansion, no regression risk"

requirements-completed: [WATCH-03]

# Metrics
duration: 1m52s
completed: 2026-04-21
---

# Phase 3 Plan 05: Layer B Bash `timeout(1)` Watchdog Wrapper Summary

**`run-dialectic.sh` now wraps `dialectic.py` in a coreutils `timeout` / `gtimeout` 2-stage-kill watchdog (TAS_WATCHDOG_TIMEOUT_SEC=1200s default → SIGTERM → 30s grace → SIGKILL) with POSIX `command -v` detection, environment-variable overrides, and a graceful-degrade stderr warning + unwrapped exec path for hosts (like the current macOS dev machine) without coreutils — Layer A `asyncio.timeout` still active on the degrade path per Success Criterion 3.**

## Performance

- **Duration:** 1m52s
- **Started:** 2026-04-21T09:14:59Z
- **Completed:** 2026-04-21T09:16:51Z
- **Tasks:** 1 code task (Task 1) + 1 auto-approved checkpoint (Task 2, automated-verify)
- **Files modified:** 1 (skills/tas/runtime/run-dialectic.sh: 35 → 65 lines, +31/-1)

## Accomplishments

- Layer B Bash `timeout(1)` wrapper installed in `run-dialectic.sh` — exit codes 124/137 will signal `bash_wrapper_kill` to Plan 06's MetaAgent classifier
- Coreutils probe via POSIX `command -v timeout` / `command -v gtimeout` — same idiom style as the preserved `find_python` preflight
- Two environment-variable override hooks (`TAS_WATCHDOG_TIMEOUT_SEC`, `TAS_WATCHDOG_KILL_GRACE_SEC`) with sensible defaults (1200s / 30s)
- Graceful-degrade branch verified by live dry-smoke on Darwin 26.3.1 without coreutils: exact 2-line stderr warning copy emitted, unwrapped `exec "$PYTHON" ...` runs `dialectic.py` which surfaces its own JSON error for the missing config (exit 1, NOT 124/137 — confirms wrapper did not wrap)
- `find_python` preflight (lines 1-33) preserved byte-identically — `diff` against `git show HEAD:...` returns empty on post-edit verification
- `bash -n` clean; `dialectic.py --self-test` still green (45/45) — this plan had zero Python touchpoints, confirming scope discipline

## Task Commits

1. **Task 1: Replace exec line with Layer B watchdog wrapper block** — `a61fd8e` (feat)
2. **Task 2: Human-verify graceful-degrade warning on macOS** — no commit (auto-approved checkpoint, zero file modifications; automated dry-smoke performed in lieu of manual user verification per auto-mode policy)

**Plan metadata (SUMMARY + STATE + ROADMAP):** forthcoming (`docs(03-05)` commit after this SUMMARY writes through)

## Files Created/Modified

- `skills/tas/runtime/run-dialectic.sh` — Layer B wrapper: replaces the single line-35 `exec` with a ~30-line block (env var defaults + coreutils detection + wrapped/unwrapped branch). Lines 1-33 (find_python + PYTHON preflight) byte-identical to pre-change HEAD.

## Decisions Made

See `key-decisions:` frontmatter above. Summary:

- **Env-var override, not schema field** — STATE.md's Open Question (watchdog thresholds, 실측 분포 미수집) resolved with env var + default rather than step-config.json schema drift (M1 minimal surface-area, D-03 §Rejected alternative).
- **Graceful degrade, not HARD FAIL** — macOS without brew coreutils is a realistic dev configuration; Layer A already covers asyncio-level hangs so Layer B absence is a graceful capability reduction, not a runtime error.
- **No user-input validation** — malformed `TAS_WATCHDOG_TIMEOUT_SEC` (e.g., `abc`, `-5`) falls through to coreutils exit 125, which Plan 06's classifier will route as `engine_crash` (P3-05 + T-3-01 accept disposition in the threat register).
- **Explicit `s` duration suffix** — defense against future edits that might interpret tunables in minutes/hours.
- **Comment-only exit-code annotation (124/137/125)** — readable audit trail for Plan 06's classifier implementation; no executable change.

## Deviations from Plan

None — plan executed exactly as written.

All 10 acceptance greps passed on first edit; no auto-fixes, no Rule 1/2/3 triggers. Task 1's `<action>` block was copied verbatim (with a single whitespace-level fidelity edit — the plan's wrapper block was inserted directly below line 33's blank line per the `exec` line replacement rule).

## Issues Encountered

None.

## Verification Results

### Automated (all passing)

| Check | Command | Result |
|-------|---------|--------|
| Syntax | `bash -n skills/tas/runtime/run-dialectic.sh` | exit 0 |
| Byte-identity (preflight) | `diff <(sed -n '1,33p' ...) <(git show HEAD:... \| sed -n '1,33p')` | no output (identical) |
| Env var default (timeout) | `grep -c 'TAS_WATCHDOG_TIMEOUT_SEC:-1200' ...` | 1 |
| Env var default (grace) | `grep -c 'TAS_WATCHDOG_KILL_GRACE_SEC:-30' ...` | 1 |
| Both CLIs probed | `grep -cE 'command -v (timeout\|gtimeout) >/dev/null 2>&1' ...` | 2 |
| 2-stage kill flag | `grep -c -- '--kill-after=' ...` | 1 |
| Degrade warning line | `grep -c '⚠ tas watchdog: neither' ...` | 1 |
| Install instruction | `grep -c 'brew install coreutils' ...` | 2 (comment + stderr warn) |
| Unwrapped exec (degrade) | `grep -c 'exec "\$PYTHON" "\$SCRIPT_DIR/dialectic.py" "\$@"' ...` | 1 |
| Wrapped exec | `grep -c 'exec "\$TIMEOUT_BIN" --kill-after' ...` | 1 |
| find_python preserved | `grep -c 'find_python' ...` | 2 (function def + call site) |
| Python regression | `python3 dialectic.py --self-test` | 45/45 PASS |

### Live dry-smoke (automated in lieu of Task 2 human-verify, auto-mode policy)

**Host profile:** Darwin 26.3.1 (macOS 26.3.1), `command -v timeout` → exit 1, `command -v gtimeout` → exit 1 (coreutils NOT installed; graceful-degrade branch is the expected code path).

**Command:** `bash skills/tas/runtime/run-dialectic.sh /nonexistent-step-config.json`

**Result:**
- **stderr:** Exact 2-line warning emitted as specified:
  1. `⚠ tas watchdog: neither 'timeout' nor 'gtimeout' found — Layer B disabled.`
  2. `  Install via 'brew install coreutils' on macOS. Layer A (asyncio.timeout) remains active.`
- **stdout:** `{"status": "error", "error": "Config load failed: [Errno 2] No such file or directory: '/nonexistent-step-config.json'"}` (emitted by dialectic.py — proves the unwrapped exec succeeded and dialectic.py ran normally under the degrade branch)
- **Exit code:** `1` (from dialectic.py's Config load failure; NOT 124/137 — wrapper correctly skipped the `timeout` wrap on this host)

**Env-var override probe:** `TAS_WATCHDOG_TIMEOUT_SEC=2 bash run-dialectic.sh /nonexistent.json` → same degrade branch (coreutils absent), same stderr/stdout/exit — confirms `${TAS_WATCHDOG_TIMEOUT_SEC:-1200}` parameter expansion parses user override without shell error. (Wrapped-branch env-var override exercise deferred to a coreutils-equipped CI host.)

### Human verification deferred

**Deferred to Plan 07 / coreutils-equipped CI host:**

1. **Wrapped-branch live exercise** — install coreutils (`brew install coreutils` on a test macOS box OR any Linux host with GNU coreutils), then run `TAS_WATCHDOG_TIMEOUT_SEC=5 bash run-dialectic.sh <path-to-real-step-config>`. Expectations: when a long-running dialectic exceeds 5s, SIGTERM delivered at t=5s and (if dialectic does not cooperatively exit within 30s) SIGKILL at t=35s. Exit code 124 (SIGTERM honored) or 137 (SIGKILL) should appear, matching the Plan 06 classifier contract.
2. **Layer A + Layer B interplay in a real hang** — deferred to Plan 07 Wave 3 canary #6 per the plan's `<success_criteria>`: "Plan 07 canary #6 can now trip Layer B by exporting `TAS_WATCHDOG_TIMEOUT_SEC=5` (once coreutils is installed in CI / test environments)".
3. **Malformed-input exit-125 route** — verify `TAS_WATCHDOG_TIMEOUT_SEC=abc bash run-dialectic.sh ...` yields exit 125 on a coreutils-equipped host (threat T-3-01 accept disposition confidence gate).

These deferred items do NOT block Phase 3 plan closure. The graceful-degrade branch is live-verified on the current dev machine, and the wrapped branch is syntactically correct + `bash -n` clean; coreutils exit-code semantics are documented (Research §4.3) and not amenable to local test on a coreutils-free host without scope creep.

## Next Phase Readiness

- Plan 06 (MetaAgent classifier, D-05 implementation) — READY. The exit-code ↔ halt_reason mapping Plan 06 will read is now backed by a live Layer B wrapper + graceful-degrade fallback. Plan 06 can safely assume: `124|137` ⇒ `bash_wrapper_kill`; `0` + valid halt JSON ⇒ `sdk_session_hang`; `0` + missing halt JSON ⇒ `step_transition_hang`; other non-zero ⇒ `engine_crash`.
- Plan 07 (Wave 3 canaries) — READY. Canary #6 can export `TAS_WATCHDOG_TIMEOUT_SEC=5` on a coreutils-equipped CI host to exercise the wrapped branch.
- Current dev machine (Darwin, no coreutils) — UNCHANGED operational behavior. Every invocation will now emit the 2-line stderr warning once (intended UX; see D-03 Graceful degrade policy).

## Self-Check: PASSED

- `skills/tas/runtime/run-dialectic.sh` — FOUND
- `.planning/phases/03-2-layer-hang-watchdog/03-05-SUMMARY.md` — FOUND
- Commit `a61fd8e` — FOUND in git log

---
*Phase: 03-2-layer-hang-watchdog*
*Plan: 05*
*Completed: 2026-04-21*
