---
phase: 05-prompt-slim
plan: 02
subsystem: prompt-engineering
tags: [prompt-slim, split, baseline, meta-md, ssot, canary-9]

# Dependency graph
requires:
  - phase: 05-prompt-slim
    plan: 01
    provides: "Wave 0 scaffolding — scripts/measure-prompt-tokens.py skeleton, Canary #9 PENDING stub, skills/tas-verify/fixtures/ home, canaries.md placeholder sections"
  - phase: 04-chunk-decomposition
    provides: "D-07 antithesis.md UNCHANGED protection line — Phase 5 D-08 scope inherits"
  - phase: 03.1-engine-invocation-topology-refactor
    provides: "halt_reason enum freeze (Phase 5 creates no new enums); Phase 3.1 TOPO-02..05 load-bearing Bash patterns preserved byte-identically in meta-execute.md"
provides:
  - "skills/tas-verify/fixtures/canary-9-baseline-{a,b,c}.json — 3 committed pre-slim baseline snapshots with _meta.captured_from recording pre-split meta.md SHA 2f3ad87e"
  - "skills/tas/references/meta-classify.md (155 lines) — Classify Mode procedural body (Phase 1/2/2c/3/4), promoted from meta.md L98-240 H2 → H1 top heading + H3 Phase sections → H2"
  - "skills/tas/references/meta-execute.md (856 lines) — Execute Mode procedural body (Phase 1 Initialize / Phase 2 Iteration Loop incl. Phase 2a-2g + Phase 2d.5 chunk sub-loop / Phase 3 Final Aggregate / Phase 4 Pre-Output Self-Check / Phase 5 JSON Response), promoted from meta.md L241-1085"
  - "skills/tas/agents/meta.md reduced 1123 → 135 lines (~88% smaller) — retains only SSOT dispatcher shell (Architecture Position / Self-Bootstrap / Input Contract / Mode Detection / Convergence Model / Quality Invariants / Edge Cases)"
  - "SSOT-1 pointer substitution — pre-existing backticked `engine_invocations` counts `bash run-dialectic.sh` calls sentence in meta.md L1074 replaced with forward-reference pointer in meta-execute.md Phase 5; canonical sentence insertion deferred to Plan 05-03 Wave 2 at meta.md §Final JSON Contract"
  - "Pitfall 1 mitigation — git ancestor ordering: baseline commit 4fb388f precedes split commit 5087156 (verified via git merge-base --is-ancestor)"
affects: [05-03, 05-04, 05-05, 05-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Mechanical split pattern: extract body-range → promote one heading level → inject opening preamble (who reads this + forward-refs to SSOT sections) → delete body-range from source → preserve frontmatter + all non-moved sections byte-identically"
    - "Pre-split baseline snapshot pattern (Pitfall 1): git SHA recorded in _meta.captured_from field, baselines committed in ancestor commit of split commit — provides immutable reference for Canary #9 behavioral-diff in Plan 05-05"
    - "SSOT pointer substitution during split: normative prose sentence (SSOT-1 engine_invocations definition) replaced in references/ with forward-reference pointer, canonical text migrated to meta.md §Final JSON Contract (Plan 05-03 inserts the section)"

key-files:
  created:
    - "skills/tas-verify/fixtures/canary-9-baseline-a.json (14 lines — trivial classify baseline: complexity=simple, steps=[구현], chunks=null)"
    - "skills/tas-verify/fixtures/canary-9-baseline-b.json (14 lines — chunked classify baseline: complexity=complex, 3 chunks with [[], ['1'], ['1','2']] dep structure)"
    - "skills/tas-verify/fixtures/canary-9-baseline-c.json (16 lines — full execute baseline: status=completed, iterations=1, rounds=1, engine_invocations=1, references_read_structure=[])"
    - "skills/tas/references/meta-classify.md (155 lines — # Classify Mode H1, Phase 1/2/2c/3/4 H2 sub-sections, forward-refs to meta.md §Final JSON Contract)"
    - "skills/tas/references/meta-execute.md (856 lines — # Execute Mode H1, Phase 1-5 H2 sub-sections, Phase 2d.5 chunk sub-loop preserved byte-identically, SSOT-1 pointer substitution applied)"
  modified:
    - "skills/tas/agents/meta.md (1123 → 135 lines; Classify Mode body L98-240 deleted, Execute Mode body L241-1085 deleted, frontmatter + 7 SSOT dispatcher sections preserved byte-identically)"

key-decisions:
  - "Promote all heading levels uniformly when transplanting bodies — top H2 → H1, inner ### Phase sub-headings → ## (plan action mock-up + verify grep patterns both specify H2 for Phase headings, overriding the conflicting 'keep internal levels' comment)"
  - "Drop `(COMMAND: classify)` / `(COMMAND absent, PLAN provided)` parenthetical from top H1 headers in reference files — plan's example mock-up shows clean form; opening preamble paragraph carries the semantic (MODE == classify/execute)"
  - "SSOT-1 replacement spans 4 lines in source meta.md (L1074-1077 backticked form) → single forward-reference pointer line in meta-execute.md §Phase 5 — preserves the 4-line sentence's semantic while routing canonical definition to meta.md §Final JSON Contract (Plan 05-03 owns insertion)"
  - "Preserve blank lines adjacent to promoted headings — regex `^(#+)(\\s)(.*?)(\\n?)$` with `re.DOTALL` captures trailing newline group, preventing collapse of heading-body separator that initially broke Phase 5 markdown spacing"
  - "Task 3 checkpoint auto-approved provisionally with char÷4 heuristic (1,681 tokens for meta.md) — anthropic package not installed in this worktree, which D-04 classifies as environmentally expected; authoritative count_tokens() measurement deferred to Plan 05-06 Wave 5 per plan's <how-to-verify> fallback clause"

patterns-established:
  - "Phase 5 split pattern: preserve body verbatim → promote top heading → insert 'who reads this' preamble + forward-refs → delete source body range → retain frontmatter + non-moved sections byte-identically"
  - "Pitfall 1 Pre-split Baseline Capture: distinct atomic commits — baseline-capture commit MUST precede split commit, verified via `git merge-base --is-ancestor`"
  - "SSOT-1 pointer substitution during split: replace 4-line backticked definition sentence in references/ with single forward-ref pointer line → defer canonical sentence insertion to later plan in planning wave"

requirements-completed: []  # SLIM-02 + SLIM-04 are addressed in-progress across Waves 1-5; Plan 05-06 owns the final flips in REQUIREMENTS.md

# Metrics
duration: 12min
completed: 2026-04-22
---

# Phase 05 Plan 02: Wave 1 — Pre-slim Baselines + meta.md Split Summary

**Captured 3 immutable Canary #9 pre-slim baseline fixtures against meta.md @2f3ad87e, then mechanically split meta.md (1123 → 135 lines) into dispatcher + references/meta-classify.md (155 lines) + references/meta-execute.md (856 lines), applying SSOT-1 pointer substitution; char÷4 provisional measurement shows meta.md ≈ 1,681 tokens ≪ 5,500 SLIM-02 threshold.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-04-22T10:40:00Z (approximate — worktree-branch-reset)
- **Completed:** 2026-04-22T10:52:00Z
- **Tasks:** 3 (2 atomic + 1 auto-approved checkpoint)
- **Files created:** 5 (3 baseline JSONs + 2 reference files)
- **Files modified:** 1 (skills/tas/agents/meta.md — 988-line deletion)

## Accomplishments

- **Task 1 (4fb388f):** Captured 3 pre-slim baseline snapshots (`canary-9-baseline-{a,b,c}.json`) with `_meta.captured_from = "skills/tas/agents/meta.md @2f3ad87e46deeecb29ec240b4bdad7eaacc4e235"`. Each baseline contains only deterministic structural fields (complexity/steps/chunks for a+b; status/iterations/rounds/engine_invocations/execution_mode/references_read_structure for c) — stochastic fields (reasoning/summary/uuid/timestamp/workspace) explicitly excluded per RESEARCH L607.
- **Task 2 (5087156):** Mechanically split meta.md per D-01 locked boundary. Classify Mode body (pre-split L98-240, 142 source lines) transplanted into `skills/tas/references/meta-classify.md` (155 lines with preamble). Execute Mode body (pre-split L241-1085, 844 source lines) transplanted into `skills/tas/references/meta-execute.md` (856 lines with preamble). meta.md reduced to 135 lines, retaining only frontmatter + # MetaAgent header + 7 SSOT dispatcher sections.
- **SSOT-1 pointer substitution applied:** The pre-existing backticked `engine_invocations` counts `bash run-dialectic.sh` calls sentence (formerly meta.md L1074 area, spanning 4 lines) is replaced in meta-execute.md §Phase 5 with a single forward-reference pointer line (`(See \`${SKILL_DIR}/agents/meta.md\` §Final JSON Contract for the canonical definition of \`engine_invocations\` — added in Plan 05-03 Wave 2.)`). Both the backticked variant AND the double-quoted variant now return grep count 0 across `skills/` — canonical sentence insertion deferred to Plan 05-03 Wave 2 per plan spec.
- **Pitfall 1 mitigated:** Commit ordering is baseline (4fb388f) → split (5087156); `git merge-base --is-ancestor 4fb388f 5087156` returns 0. Git history explicitly records baselines-before-split invariant.
- **Task 3 checkpoint auto-approved under auto-chain:** `anthropic` package not installed in this worktree (environmental — D-04 fallback clause applies). Provisional char÷4 heuristic: meta.md ≈ 1,681 tokens (char-count 6,726). Well under both D-06 stretch target (≤ 4,500) and SLIM-02 hard threshold (≤ 5,500). Plan 05-06 Wave 5 will perform the authoritative `count_tokens()` measurement.

## Task Commits

Each task was committed atomically via `git commit --no-verify` (parallel worktree mode):

1. **Task 1: Pre-slim Canary #9 baselines a/b/c** — `4fb388f` (feat)
2. **Task 2: meta.md split → references/meta-{classify,execute}.md** — `5087156` (feat)
3. **Task 3: Developer-verify token measurement checkpoint** — auto-approved provisionally under auto-chain (no commit — verification gate only)

_No plan metadata commit at this stage — worktree mode skips STATE.md/ROADMAP.md writes (orchestrator owns them after wave completion). SUMMARY.md commit lands separately via `git add -f` below._

## Files Created/Modified

### Created

- `skills/tas-verify/fixtures/canary-9-baseline-a.json` — Trivial classify baseline (fixture: "fix typo 'conts' → 'const'"; complexity=simple, steps_count=1, steps_names_ordered=["구현"], implementation_chunks_is_null=true)
- `skills/tas-verify/fixtures/canary-9-baseline-b.json` — Chunked classify baseline (fixture: "implement user authentication ... 3 vertical layers"; complexity=complex, implementation_chunks_count=3, ids=["1","2","3"], deps=[[],["1"],["1","2"]])
- `skills/tas-verify/fixtures/canary-9-baseline-c.json` — Full execute baseline (fixture: "execute a pre-generated 1-step plan ... deterministic mock ... ACCEPT on round 1"; status=completed, iterations=1, rounds_total=1, engine_invocations=1, execution_mode=pingpong, references_read_structure=[])
- `skills/tas/references/meta-classify.md` — Classify Mode procedural body, H1 + 5 H2 Phase sub-sections (Phase 1 Project Context Scan / Phase 2 Classification / Phase 2c Chunk Sizing / Phase 3 Plan Validation / Phase 4 Output), preamble specifies MODE==classify caller context + forward-ref to meta.md §Final JSON Contract
- `skills/tas/references/meta-execute.md` — Execute Mode procedural body, H1 + 5 H2 Phase sub-sections (Phase 1 Initialize / Phase 2 Iteration Loop / Phase 3 Final Aggregate / Phase 4 Pre-Output Self-Check / Phase 5 JSON Response), all Phase 3.1 TOPO load-bearing Bash patterns (`nohup bash`, `echo $!`, `engine.done`, `run_in_background: false`, 19×30s polling) + Phase 4 CHUNK patterns (Phase 2d.5 worktree prune, cherry-pick, PRE_MERGE_SHA, chunk_merge_conflict + worktree_backlog enums) preserved byte-identically, Synthesis Context injection block + antithesis.md UNCHANGED note preserved

### Modified

- `skills/tas/agents/meta.md` — Reduced from 1123 lines to 135 lines (988-line deletion). Lines 1-97 (frontmatter + # MetaAgent header + Architecture Position + Self-Bootstrap + Input Contract + ### Mode Detection + separator) retained byte-identically. Lines 1086-1123 (Convergence Model + Quality Invariants + Edge Cases & Error Handling) retained byte-identically. Lines 98-1085 (Classify Mode body + Execute Mode body) deleted.

## Decisions Made

1. **Heading-level promotion uniform (not "keep internal levels")** — Plan action comment said "H2 → H1 only for the top section header. All internal ### sub-headings keep their levels." But the same plan's action mock-up text AND the verify grep pattern both specify H2 for Phase headings (`grep -q "^## Phase 1: Project Context Scan"`). The verify block is the gating contract — all headings promoted one level uniformly (H2 → H1 top, H3 Phase sections → H2, H4 sub-sections → H3). This is the only internally-consistent interpretation.
2. **Clean top H1 heading in reference files** — Drop the `(COMMAND: classify)` / `(COMMAND absent, PLAN provided)` parenthetical from top headers (the plan's example mock-up shows clean form). The opening preamble paragraph explicitly states "MODE == classify" / "MODE == execute" which carries the semantic. Verbatim preservation applies to inner content (tables, code blocks, specific phrases) per the plan's byte-identical discipline; the top header is the explicit transformation target.
3. **SSOT-1 pointer substitution spans 4 source lines** — The pre-split sentence spanned lines 1074-1077 (backticked form): `` `engine_invocations` counts `bash run-dialectic.sh` calls made during this run\n(plan validation + per-step execution + within-iter retries). For an M-step plan\nover K iterations with no retries, the minimum value is M×K. A report with\n`engine_invocations: 0` signals a protocol violation. `` — replaced as a single unit with the forward-reference pointer in meta-execute.md. Semantic content (attestation / protocol-violation meaning) is preserved via the pointer route to Plan 05-03's §Final JSON Contract insertion.
4. **Blank-line preservation around promoted headings (Rule 1 inline bug fix)** — First Python pass used regex `^(#+)(\s.*)$` which dropped trailing `\n`, collapsing the blank separator between `## Phase 5: JSON Response` and `Your entire response must be ONLY the JSON line:`. Fixed by switching to `^(#+)(\s)(.*?)(\n?)$` with `re.DOTALL` to explicitly capture and re-emit the trailing newline. Applied before commit (no remediation commit needed).
5. **Task 3 checkpoint auto-approved as `approved-provisional`** — `anthropic` package not installed in this worktree (environmentally expected per D-04 / RESEARCH §Manual-Only Verifications / plan `<how-to-verify>` fallback). Provisional char÷4 heuristic: meta.md ≈ 1,681 tokens (well under 4,500 stretch, comfortably under 5,500 hard threshold). Auto-chain objective explicitly authorizes this path. Plan 05-06 Wave 5 owns the authoritative measurement gate.

## Deviations from Plan

### Rule 1 Inline — Heading-Promotion Blank-Line Collapse (fixed before commit)

**1. [Rule 1 - Bug] Python regex `^(#+)(\\s.*)$` stripped trailing \\n on promoted headings, collapsing blank separator lines**
- **Found during:** Task 2 post-write manual inspection of `## Phase 5: JSON Response` section formatting (noticed heading adjacent to body with no blank between them)
- **Issue:** My initial `promote_heading(line)` used `re.match(r'^(#+)(\\s.*)$', line)` which — by default — does not capture the trailing `\\n` (since `.*` doesn't match `\\n` under the default flag). Returned value was `hashes[1:] + rest` where `rest` had no newline, producing e.g. `'## Phase 5: JSON Response'` (no `\\n`). When concatenated with the next list element (the blank `'\\n'` line), `writelines()` produced `## Phase 5: JSON Response\\nYour entire response...\\n` — which renders without a blank line between heading and body.
- **Fix:** Switched regex to `^(#+)(\\s)(.*?)(\\n?)$` with `re.DOTALL` so the trailing newline group is captured and re-emitted. Applied before any commit — regenerated both reference files with correct spacing, re-ran all Task 2 verify checks (ALL PASS).
- **Files modified:** N/A (fix applied in memory; final committed files have correct spacing)
- **Verification:** `awk 'NR>=820 && NR<=825' skills/tas/references/meta-execute.md` confirms `## Phase 5: JSON Response\\n\\nYour entire response...\\n` with proper blank separator.
- **Committed in:** `5087156` (Task 2 final commit — the fix landed before commit)

### Rule 3 Inline — anthropic Package Not Installed (environmental, per D-04)

**2. [Rule 3 - Environmental] Task 3 checkpoint measurement uses char÷4 fallback because anthropic package is not installed in this worktree**
- **Found during:** Task 3 attempted invocation of `scripts/measure-prompt-tokens.py` — fail-loud ImportError exit 1 (matches D-04 `<behavior>` spec)
- **Analysis:** This is environmentally expected per D-04 ("fallback none — tiktoken approximation etc. are dev-only"), RESEARCH §Manual-Only Verifications ("authoritative measurement deferred to Plan 05-06"), and the plan's explicit `<how-to-verify>` fallback clause ("provisional; to be confirmed with count_tokens in Plan 05-06 Wave 5"). Per the objective, under auto-chain this checkpoint auto-approves with provisional char÷4 estimate.
- **Fix:** No code change. Auto-approved with `approved-provisional` semantics; recorded char÷4 measurement: meta.md ≈ 1,681 tokens (6,726 chars ÷ 4). Even with a conservative 1.5× multiplier (char÷4 typically underestimates BPE token count), the upper-bound estimate ~2,520 tokens is still well under the 5,500 threshold.
- **Files modified:** None
- **Verification:** `wc -c skills/tas/agents/meta.md` = 6,726; 6,726 ÷ 4 = 1,681. `scripts/measure-prompt-tokens.py` exits 1 with fail-loud stderr (matches D-04 fail-loud contract).
- **Committed in:** N/A (no code change — provisional approval only)

---

**Total deviations:** 2 (1 Rule 1 bug fixed before commit, 1 Rule 3 environmental)
**Impact on plan:** Zero functional impact. Deviation 1 caught pre-commit via visual inspection; fix applied before Task 2 commit landed. Deviation 2 is an authorized fallback path per the plan's explicit auto-approve clause under auto-chain.

## Issues Encountered

- **Worktree branch base mismatch at agent startup** — ACTUAL_BASE returned `438db671…` instead of expected `a7f3e33…`. Resolved via mandatory `git reset --hard a7f3e339…` per `<worktree_branch_check>` protocol. Post-reset HEAD verified against expected base.
- **Read tool stale view** — After writing the new meta.md via Python, the `Read` tool briefly showed the pre-split content (likely in-memory cache from earlier reads). Directly verified via `sed -n` and `grep` on the actual filesystem — file content was correct.

## User Setup Required

None — Phase 5 is entirely dev/plugin-internal. Wave 1 split operation does not touch any user-facing surface. End users do not need to install `anthropic` or set `ANTHROPIC_API_KEY` to run `/tas`; the token-measurement tool is strictly a dev-only Phase 5 validation utility per D-04.

## Threat Flags

No new security-relevant surface introduced. The 3 baseline JSONs + 2 reference files contain no secrets, no auth paths, no network endpoints, no schema changes at trust boundaries. Threat-model entries T-05-07..T-05-12 all addressed:
- T-05-07 (baseline-after-split tampering): mitigated by git ancestor ordering + grep `^## Classify Mode` passing in Task 1 end
- T-05-08 (load-bearing Bash sketches dropped): mitigated by Task 2 verify greps (nohup / engine.done / cherry-pick / worktree / implementation_chunks all PASS)
- T-05-09 (Self-Bootstrap whitelist modified): mitigated by byte-identical retention — `grep -q "Permitted Write targets"` + `grep -q "Forbidden patterns"` + `grep -q "Never Write dialectic content"` all PASS in meta.md
- T-05-10 (API key leaked during checkpoint): accepted (mitigated upstream in Plan 05-01 — `measure-prompt-tokens.py` never prints key)
- T-05-11 (human checkpoint approver lies): accepted (trust-based; Plan 05-06 re-runs)
- T-05-12 (Mode Detection leaked to references): mitigated by inverse assertions — `! grep -q "^### Mode Detection"` passes for both references

## Known Stubs

No new stubs introduced in this plan. Existing Wave 0 stubs (simulate_prompt_slim_diff.py PENDING body, canaries.md §Canary #9 PENDING sections, §SSOT Invariants PENDING) remain in place per D-09 plan schedule (Plan 05-04 resolves SSOT Invariants; Plan 05-05 resolves Canary #9 full implementation).

Forward-reference pointers in meta-classify.md + meta-execute.md to "§Final JSON Contract" — these are intentional forward references that will resolve when Plan 05-03 Wave 2 inserts the §Final JSON Contract section into meta.md. This is a deliberate stub-like pattern documented in the plan action as "the pointer text above acknowledges the forward reference."

## Next Phase Readiness

Ready for **Plan 05-03 (Wave 2 — Attestation wiring)**:
- meta.md dispatcher shell at 135 lines with ~1,681 char÷4 estimated tokens — ample budget for Plan 05-03's Mode-bound Reference Load block + Final JSON Contract section (~80-120 line addition projected, still well under 5,500 threshold).
- meta-classify.md + meta-execute.md forward-references to `§Final JSON Contract` waiting to resolve — Plan 05-03 owns the insertion.
- Both reference files have opening preamble paragraphs mentioning `MODE == classify` / `MODE == execute` — Plan 05-03's Mode-bound Reference Load block wires the `Read(...)` dispatch into these files.
- SSOT-1 pointer substitution applied in meta-execute.md. Plan 05-03 Task 1 will insert the canonical double-quoted form `"engine_invocations" counts \`bash run-dialectic.sh\` calls` in meta.md §Final JSON Contract, yielding total count == 1 across `skills/` (the SSOT-1 grep lint invariant).
- Canary #9 baselines (a/b/c) immutable and committed — Plan 05-05 (Wave 4) implements the full behavioral-diff canary against these fossils.
- D-08 untouched scope verified: `git diff --stat a7f3e33..HEAD` on protected files (runtime/*.py, runtime/run-dialectic.sh, runtime/requirements.txt, agents/antithesis.md, agents/thesis.md, SKILL.md, .claude-plugin/*.json) returns empty — all byte-identical.
- nyquist_compliant stays false (Plan 05-06 flips).

No blockers. Wave 1 commit ordering invariant intact (git ancestor verification passes).

## Self-Check: PASSED

**Created files verified:**
- `skills/tas-verify/fixtures/canary-9-baseline-a.json` — FOUND (14 lines, valid JSON, captured_from=2f3ad87e SHA)
- `skills/tas-verify/fixtures/canary-9-baseline-b.json` — FOUND (14 lines, valid JSON)
- `skills/tas-verify/fixtures/canary-9-baseline-c.json` — FOUND (16 lines, valid JSON)
- `skills/tas/references/meta-classify.md` — FOUND (155 lines, H1 + 5 H2 Phase sub-sections)
- `skills/tas/references/meta-execute.md` — FOUND (856 lines, H1 + 5 H2 Phase sub-sections)

**Modified files verified:**
- `skills/tas/agents/meta.md` — 135 lines (from 1123), 7 SSOT headers retained, frontmatter `model: opus` intact, Classify/Execute Mode body headers absent

**Commits verified:**
- `4fb388f` (Task 1) — `git log --oneline | grep -q 4fb388f` → FOUND
- `5087156` (Task 2) — `git log --oneline | grep -q 5087156` → FOUND
- Ancestry: `git merge-base --is-ancestor 4fb388f 5087156` → exit 0 (ORDER OK)

**Invariants verified:**
- SSOT-1 backticked form: 0 matches across `skills/` (was 1 pre-split)
- SSOT-1 double-quoted form: 0 matches (Plan 05-03 will insert == 1)
- Mode Detection uniqueness: 1 match in meta.md, 0 in either reference
- D-08 protected files: 0 lines changed vs a7f3e33 baseline
- Canary #9 stub: exits 0 (Wave 0 artifact preserved)

---
*Phase: 05-prompt-slim*
*Completed: 2026-04-22*
