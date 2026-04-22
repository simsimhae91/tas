---
phase: 05-prompt-slim
plan: 01
subsystem: testing
tags: [prompt-slim, scaffolding, canary, anthropic-count-tokens, dev-only]

# Dependency graph
requires:
  - phase: 04-chunk-decomposition
    provides: "Canary #8 Wave 0 PENDING stub precedent (simulate_chunk_integration.py + canaries.md placeholder pattern)"
  - phase: 04-chunk-decomposition
    provides: "D-07 antithesis.md UNCHANGED protection line — Phase 5 inherits"
  - phase: 03-2-layer-hang-watchdog
    provides: "halt_reason enum freeze (Phase 5 creates no new enums)"
provides:
  - "scripts/ directory physical boundary (NOT under skills/tas/runtime/ — enforces dev-only isolation per D-04 + Pitfall 2)"
  - "measure-prompt-tokens.py skeleton with fail-loud ImportError + ANTHROPIC_API_KEY guards + MODEL=\"claude-opus-4-7\" constant + count_tokens(system=...) per-file loop + TOTAL line"
  - "Canary #9 PENDING harness entry point at skills/tas/runtime/tests/simulate_prompt_slim_diff.py (stdlib-only stub, exits 0 in default/fast/full modes)"
  - "canaries.md §Canary #9 PENDING section + §SSOT Invariants PENDING section (append between Canary #8 and 'When to add a new canary')"
  - "skills/tas-verify/fixtures/ directory committable via .gitkeep (Canary #9 baseline JSON home — populated in Plan 05-02 Wave 1)"
  - "05-VALIDATION.md Wave 0 Requirements — all 6 boxes flipped [ ] → [x] (nyquist_compliant stays false until Plan 05-06)"
affects: [05-02, 05-03, 05-04, 05-05, 05-06]

# Tech tracking
tech-stack:
  added: ["anthropic Python SDK (dev-only — NOT in runtime/requirements.txt)"]
  patterns:
    - "Wave 0 scaffolding pattern (Phase 4 Plan 04-01 precedent inherited): PENDING stubs + canaries.md placeholders + .gitkeep for empty dirs + VALIDATION Wave 0 boxes flipped at Wave 0 close"
    - "Dev-only boundary via physical directory (scripts/ at repo root, NOT under runtime/) — enforces import isolation without code guards"
    - "Fail-loud-first CLI design: ImportError → exit 1 (missing package), usage → exit 1 (no args), ANTHROPIC_API_KEY missing → exit 1, API error → exit 2"

key-files:
  created:
    - "scripts/measure-prompt-tokens.py (128 lines — count_tokens wrapper, MODEL=claude-opus-4-7, MAX_FILE_BYTES=10MB sanity cap)"
    - "scripts/README.md (27 lines — dev-only boundary doc, pip install anthropic note, NEVER-add-to-runtime rule)"
    - "skills/tas/runtime/tests/simulate_prompt_slim_diff.py (46 lines — stdlib-only Wave 0 stub, TAS_VERIFY_SLIM_MODE=fast|full, TAS_VERIFY_SLIM_REGENERATE flag, REPO_ROOT.parents[4], FIXTURES path)"
    - "skills/tas-verify/fixtures/.gitkeep (1 line — placeholder comment pointing to Plan 05-02 for baselines)"
  modified:
    - "skills/tas-verify/canaries.md (+33 lines — Canary #9 PENDING section + SSOT Invariants PENDING section appended after Canary #8 and before 'When to add a new canary')"
    - ".planning/phases/05-prompt-slim/05-VALIDATION.md (6 Wave 0 Requirement checkboxes flipped [ ] → [x])"

key-decisions:
  - "anthropic ImportError guard fires BEFORE ANTHROPIC_API_KEY guard (module load order) — both are fail-loud exit 1 paths per D-04; in environments without anthropic installed (e.g., this worktree), the ImportError path executes first — this is correct per <behavior> spec (either fail-loud path satisfies the contract)"
  - "Canary #9 stub uses `REPO_ROOT.parents[4]` (tests→runtime→tas→skills→REPO) — same depth as Phase 4 Canary #8 (simulate_chunk_integration.py) so file can be safely moved/edited without repo-root relocation"
  - ".gitkeep in fixtures/ carries a comment line pointing to Plan 05-02 Wave 1 (rather than being empty) — future readers get direct breadcrumb to where baseline JSONs land"
  - "05-VALIDATION.md force-added via `git add -f` because `.planning/` is gitignored (inherited from pre-Phase 3 gitignore rule); otherwise the Wave 0 box flips would be lost on worktree merge"
  - "nyquist_compliant stays false (per plan Step Final instruction) — Plan 05-06 owns the flip after full-phase verification"

patterns-established:
  - "Phase 5 Wave 0 scaffolding: new files ONLY (no existing-file rewrites), PENDING stubs + placeholders + .gitkeep directories — subsequent waves edit existing scaffolds without mkdir"
  - "Dev-only script placement at repo root scripts/ (sibling to skills/) — physical filesystem enforcement of the runtime-dep isolation rule"
  - "Canary section order invariant in canaries.md: #1 < #2 < ... < #8 < #9 < SSOT Invariants < 'When to add a new canary' — verified via awk line-number comparison"

requirements-completed: []  # SLIM-01 + SLIM-04 are Wave 0 scaffolding covered here but remain [ ] in REQUIREMENTS.md until Plan 05-06 (full implementation lands in Waves 1-5)

# Metrics
duration: 5min
completed: 2026-04-22
---

# Phase 05 Plan 01: Wave 0 Scaffolding Summary

**Dev-only token-measurement CLI skeleton (`scripts/measure-prompt-tokens.py`) + Canary #9 PENDING harness stub + canaries.md Canary #9 / SSOT Invariants placeholder sections + `skills/tas-verify/fixtures/` home — all 6 Wave 0 Requirements flipped to `[x]`.**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-04-22T08:59:14Z
- **Completed:** 2026-04-22T09:04:13Z
- **Tasks:** 2
- **Files created:** 4 (measure-prompt-tokens.py, scripts/README.md, simulate_prompt_slim_diff.py, fixtures/.gitkeep)
- **Files modified:** 2 (canaries.md, 05-VALIDATION.md)
- **Lines added total:** 334

## Accomplishments

- Created `scripts/` directory at repo root (physical enforcement of dev-only boundary per D-04 + Pitfall 2 — NOT under `skills/tas/runtime/`).
- `scripts/measure-prompt-tokens.py` skeleton (128 lines): fail-loud `ImportError` guard → exit 1, `ANTHROPIC_API_KEY` guard → exit 1, `MODEL = "claude-opus-4-7"` constant, `MAX_FILE_BYTES = 10 * 1024 * 1024` DoS cap (T-05-03), per-file `count_tokens(system=content)` loop printing `{path}\t{tokens}` + final `TOTAL\t{sum}`, `NotFoundError`/`BadRequestError` branch → exit 2 with model-ID update hint. Made executable (`chmod +x`).
- `scripts/README.md` (27 lines): dev-only boundary doc; explicit "NEVER add anthropic to runtime/requirements.txt" note.
- `skills/tas/runtime/tests/simulate_prompt_slim_diff.py` (46 lines) — Wave 0 PENDING stub mirroring Phase 4 `simulate_chunk_integration.py` precedent. Stdlib-only, `TAS_VERIFY_SLIM_MODE=fast|full` env var, `TAS_VERIFY_SLIM_REGENERATE=1` opt-in flag, `REPO_ROOT = Path(__file__).resolve().parents[4]`, `FIXTURES = REPO_ROOT / "skills" / "tas-verify" / "fixtures"`. Exits 0 in all 3 invocation modes with `"PASS: canary #9 (Wave 0 stub; …)"` message.
- `skills/tas-verify/canaries.md` — appended `## Canary #9 — Prompt Slim Behavioral Diff (SLIM-04)` and `## SSOT Invariants (SLIM-03)` sections between Canary #8 (line 297) and `## When to add a new canary` (now line 394). All existing sections Canary #1-#8 byte-identical.
- `skills/tas-verify/fixtures/.gitkeep` — placeholder so empty fixtures/ directory is committable; contains a single comment pointing to Plan 05-02 Wave 1 for baseline JSON arrival.
- `05-VALIDATION.md` — all 6 Wave 0 Requirements checkboxes flipped `[ ]` → `[x]`; `nyquist_compliant: false` intentionally preserved (Plan 05-06 flips).

## Task Commits

Each task was committed atomically with `--no-verify` (parallel worktree mode):

1. **Task 1: scripts/ directory + measure-prompt-tokens.py + README** — `5838085` (feat)
2. **Task 2: Canary #9 PENDING stub + canaries.md sections + fixtures/.gitkeep + 05-VALIDATION.md Wave 0 boxes** — `8edf750` (feat)

_No plan metadata commit — worktree mode skips STATE.md/ROADMAP.md writes (orchestrator owns them)._

## Verification Results

### Task 1 automated verify (all pass)

| Check | Command | Result |
|-------|---------|--------|
| File exists + executable | `test -x scripts/measure-prompt-tokens.py` | PASS |
| README non-empty | `test -s scripts/README.md` | PASS |
| Python syntactic validity | `python3 -c "import ast; ast.parse(...)"` | PASS |
| MODEL constant | `grep -q '^MODEL = "claude-opus-4-7"'` | PASS |
| anthropic import in try block | `grep -q "from anthropic import Anthropic"` + `except ImportError` | PASS |
| API key guard | `grep -q "ANTHROPIC_API_KEY"` | PASS |
| system=content param | `grep -q "system=content"` | PASS |
| TOTAL line | `grep -q "TOTAL"` | PASS |
| Runtime dep isolation | `! grep -qE "^anthropic" skills/tas/runtime/requirements.txt` | PASS |
| Fail-loud path (API key unset) | `ANTHROPIC_API_KEY= python3 scripts/measure-prompt-tokens.py /tmp/file` | PASS (exit 1 with stderr — see Deviations §1 for path taken) |

### Task 2 automated verify (all pass)

| Check | Command | Result |
|-------|---------|--------|
| Stub file exists | `test -f skills/tas/runtime/tests/simulate_prompt_slim_diff.py` | PASS |
| .gitkeep exists | `test -f skills/tas-verify/fixtures/.gitkeep` | PASS |
| Python syntactic validity | `python3 -c "import ast; ast.parse(...)"` | PASS |
| Default mode exit 0 | `python3 skills/tas/runtime/tests/simulate_prompt_slim_diff.py` | exit 0 — `MODE=fast` |
| Fast mode exit 0 | `TAS_VERIFY_SLIM_MODE=fast …` | exit 0 — `MODE=fast` |
| Full mode exit 0 | `TAS_VERIFY_SLIM_MODE=full …` | exit 0 — `MODE=full` |
| No forbidden imports | `! grep -qE "^(import\|from) (claude_agent_sdk\|pytest\|psutil\|anthropic)"` | PASS |
| Canary #9 count=1 | `grep -c "^## Canary #9" canaries.md` | 1 |
| SSOT Invariants count=1 | `grep -c "^## SSOT Invariants" canaries.md` | 1 |
| Canary #8 preserved | `grep -c "^## Canary #8" canaries.md` | 1 |
| Canaries #1-#7 preserved | individual `grep -c "^## Canary #N "` | all == 1 |
| Order invariant | awk `c8 < c9 < ss < wa` | PASS |
| Wave 0 Requirements 6 boxes [x] | 6 × `grep -cE "^- \[x\]"` | all == 1 |
| nyquist_compliant stays false | `grep -q "^nyquist_compliant: false"` | PASS |

### canaries.md diff stats

- **Before:** 367 lines, 8 `## Canary #N` sections + `## When to add a new canary`
- **After:** 400 lines, 9 `## Canary #N` sections + `## SSOT Invariants` section + `## When to add a new canary` (unchanged)
- **Diff:** +33 lines, 0 deletions, 1 file modified
- **Placement order (line numbers after change):** Canary #8 → 297, Canary #9 → 361, SSOT Invariants → 384, When to add → 394

### D-08 no-change invariants (all held)

| File | Pre-change sha256 | Post-change sha256 | Result |
|------|-------------------|--------------------|--------|
| `skills/tas/runtime/requirements.txt` | `53baec93…a543892` | `53baec93…a543892` | BYTE-IDENTICAL |
| `.claude-plugin/plugin.json` | `e666673f…8c28dcc` | `e666673f…8c28dcc` | BYTE-IDENTICAL |
| `.claude-plugin/marketplace.json` | `6ddba729…b918386` | `6ddba729…b918386` | BYTE-IDENTICAL |

Also unchanged (verified via `git diff --stat eb3361b..HEAD --`):
- `skills/tas/runtime/*.py` (checkpoint.py, dialectic.py)
- `skills/tas/runtime/run-dialectic.sh`
- `skills/tas/agents/antithesis.md` (D-07 protection held)
- `skills/tas/agents/thesis.md`
- `skills/tas/SKILL.md`
- `skills/tas/references/*.md` (workspace-convention, engine-invocation-protocol, workflow-patterns, failure-patterns, planning-antithesis-directive, recommended-hooks)
- `skills/tas/agents/meta.md`
- `hooks/`, `skills/tas-review/`, `skills/tas-explain/`, `skills/tas-workspace/`

### Runtime-dep isolation

Inverse assertion `! grep -qE "^anthropic" skills/tas/runtime/requirements.txt` — PASS. `requirements.txt` content unchanged:
```
claude-agent-sdk>=0.1.50
```

## Decisions Made

See `key-decisions:` frontmatter block. Notable:

1. **anthropic ImportError guard fires before API key guard.** On this worktree, anthropic is NOT installed, so `ANTHROPIC_API_KEY= python3 scripts/measure-prompt-tokens.py …` hits the ImportError branch first (exit 1 with "ERROR: anthropic package not installed" stderr). This is correct per D-04 `<behavior>` — either fail-loud path satisfies the "script fails loud on missing precondition, exit 1" contract. The API-key guard is reachable on a dev machine that has `pip install anthropic`.

2. **05-VALIDATION.md force-added.** `.planning/` is gitignored (gitignore line 5). Without `git add -f`, the Wave 0 checkbox flips would be untracked and lost on worktree merge. Precedent: Phase 3 SUMMARY.md files were tracked pre-gitignore; Phase 4 files live outside git. For Phase 5, force-add is the only path that preserves Wave 0 state across worktree merge.

3. **.gitkeep carries a comment** (`# Baseline fixtures for Canary #9 land in Plan 05-02 (Wave 1).`) rather than being empty — gives future readers a direct breadcrumb.

## Deviations from Plan

### Rule 3 Inline — Verify Block Path Divergence (Environment, not a bug)

**1. [Rule 3 - Blocking / Environmental] anthropic package not installed on this worktree**
- **Found during:** Task 1 automated verify block (final line)
- **Issue:** Plan's verify block line `ANTHROPIC_API_KEY= python3 scripts/measure-prompt-tokens.py "$TMPFILE" 2>&1 | grep -qE "ANTHROPIC_API_KEY not set"` expects the script to reach the API-key guard. Because `anthropic` is NOT installed in this environment (nor intended to be — SLIM-01 explicitly makes it dev-only), the script exits at the ImportError guard first with `ERROR: anthropic package not installed.` stderr instead.
- **Analysis:** This is NOT a script bug. Both guards implement the D-04 `<behavior>` spec ("fail loudly without anthropic package installed (exit 1)" AND "fail loudly without ANTHROPIC_API_KEY (exit 1)"). The plan `<automated>` verify block assumed anthropic was installed on the dev machine running the executor; in a worktree / CI environment without anthropic, the ImportError path is hit first. The script still delivers the "fail loud with exit 1 and clear stderr" contract.
- **Fix:** No code change. Both fail-loud paths are specified in D-04 `<behavior>`; the ImportError path is hit first here by module-load order (import happens at module top, before `main()` runs). Source inspection confirms the API-key guard is also in place (line 81 of measure-prompt-tokens.py) and would fire in an environment with anthropic installed but `ANTHROPIC_API_KEY` unset. All grep-level structural assertions for the API-key guard pass (`grep -q "ANTHROPIC_API_KEY"` = PASS, `grep -q "ERROR: ANTHROPIC_API_KEY not set"` in source = PASS).
- **Files modified:** None
- **Verification:** `grep -n "ImportError\|ANTHROPIC_API_KEY not set\|_usage()\|not argv" scripts/measure-prompt-tokens.py` shows guards at lines 41 / 51 / 76-77 / 81 in the documented fail-loud order.
- **Committed in:** N/A (no code change)

### Rule 3 Inline — 05-VALIDATION.md gitignored

**2. [Rule 3 - Blocking] `.planning/phases/` is gitignored — 05-VALIDATION.md checkbox flips would be lost without force-add**
- **Found during:** Task 2 Step Final (Wave 0 boxes flip)
- **Issue:** `git status` did not show 05-VALIDATION.md after edit because `.gitignore` line 5 (`.planning/`) ignores the file. `git check-ignore -v` confirmed. Without explicit action, the Wave 0 state (6 boxes flipped) would be preserved only on disk and lost when the worktree is merged back.
- **Fix:** `git add -f .planning/phases/05-prompt-slim/05-VALIDATION.md` in Task 2 staging step — force-adds past the gitignore rule. Committed in `8edf750` alongside the rest of Task 2.
- **Files modified:** `.planning/phases/05-prompt-slim/05-VALIDATION.md` (now tracked)
- **Verification:** `git log --oneline HEAD~1..HEAD -- .planning/phases/05-prompt-slim/05-VALIDATION.md` shows the commit; `git ls-files .planning/phases/05-prompt-slim/05-VALIDATION.md` returns the path.
- **Committed in:** `8edf750` (Task 2 commit)

---

**Total deviations:** 2 Rule 3 (both environmental / workflow — no code defect)
**Impact on plan:** Zero functional impact. Deviation 1 validates the plan's `<behavior>` spec correctness (both fail-loud guards in place); Deviation 2 preserves Wave 0 state across worktree merge (otherwise invisible state loss risk).

## Issues Encountered

- **Worktree branch base mismatch on first `git merge-base` check** — ACTUAL_BASE returned `438db67…` (current worktree HEAD) instead of the expected feature-branch tip `eb3361b…`. Resolved via the mandatory `git reset --hard eb3361b…` from the `<worktree_branch_check>` protocol at agent startup. Verified post-reset HEAD matches.

## User Setup Required

None — Phase 5 is entirely dev/plugin-internal. End users do not need to install `anthropic` or set `ANTHROPIC_API_KEY` to run `/tas`.

## Threat Flags

No new security-relevant surface introduced beyond what the plan's `<threat_model>` already enumerated (T-05-01..T-05-06 all mitigated or accepted as documented). No new endpoints, auth paths, schema changes at trust boundaries. The `scripts/` directory is strictly dev-only; `fixtures/` is a git-committed artifact location (baselines land in Wave 1).

## Known Stubs

Two intentional PENDING stubs — expected Wave 0 transient state per D-09, to be filled by later plans:

1. `skills/tas/runtime/tests/simulate_prompt_slim_diff.py` — always exits 0 with a "Wave 0 stub" PASS line. Full 3-sub-canary diff logic lands in **Plan 05-05 (Wave 4)**. Stub docstring explicitly states this.
2. `skills/tas-verify/canaries.md` §Canary #9 — Guards / Exercise detail / Pass criteria / Fail signals all marked `[PENDING Wave 4]`. Replaced with concrete contract in **Plan 05-05 (Wave 4)**.
3. `skills/tas-verify/canaries.md` §SSOT Invariants — Exercise / Pass criteria marked `[PENDING Wave 3]`. Replaced with concrete grep invariants in **Plan 05-04 (Wave 3)**.
4. `skills/tas-verify/fixtures/.gitkeep` — directory placeholder. Baseline JSONs (`canary-9-baseline-{a,b,c}.json`) arrive in **Plan 05-02 (Wave 1)**.

These are all Wave 0 scaffolding by design (Phase 4 Plan 04-01 precedent); each stub's docstring / placeholder text points to the exact plan that resolves it.

## Next Phase Readiness

Ready for **Plan 05-02 (Wave 1 — Measurement & Split)**:
- `scripts/measure-prompt-tokens.py` skeleton in place — Plan 05-02 invokes it to capture pre-slim baseline token counts on current `meta.md`.
- `skills/tas-verify/fixtures/` exists — Plan 05-02 drops `canary-9-baseline-{a,b,c}.json` here.
- Canary #9 stub + canaries.md placeholder — Plan 05-05 (Wave 4) replaces stub body + placeholder markers.
- SSOT Invariants placeholder — Plan 05-04 (Wave 3) replaces PENDING markers with real invariants.
- No further mkdir / new-directory needs across Waves 1-5 (all parent directories now exist).

No blockers. D-08 protected files untouched. nyquist_compliant stays false per plan (Plan 05-06 owns the flip).

## Self-Check: PASSED

**Created files verified:**
- `scripts/measure-prompt-tokens.py` — FOUND
- `scripts/README.md` — FOUND
- `skills/tas/runtime/tests/simulate_prompt_slim_diff.py` — FOUND
- `skills/tas-verify/fixtures/.gitkeep` — FOUND

**Modified files verified:**
- `skills/tas-verify/canaries.md` — diff +33 lines vs eb3361b
- `.planning/phases/05-prompt-slim/05-VALIDATION.md` — 6 boxes flipped, force-added via `git add -f`

**Commits verified:**
- `5838085` (Task 1) — `git log --oneline HEAD~2..HEAD | grep -q 5838085` → FOUND
- `8edf750` (Task 2) — `git log --oneline HEAD~2..HEAD | grep -q 8edf750` → FOUND

---
*Phase: 05-prompt-slim*
*Completed: 2026-04-22*
