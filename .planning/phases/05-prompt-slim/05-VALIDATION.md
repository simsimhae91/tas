---
phase: 5
slug: prompt-slim
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-22
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | stdlib-only Python3 (mirrors Phase 3.1 / 4 precedent — no pytest, no psutil, no external test framework) |
| **Config file** | None — canary scripts are self-contained `python3` executables |
| **Quick run command** | `python3 skills/tas/runtime/tests/simulate_prompt_slim_diff.py` (default fast mode) |
| **Full suite command** | Manual sequential invocation of each canary (`/tas-verify` runner) + SSOT lint block |
| **Estimated runtime** | ~2s fast mode (each sub-canary ~0.5s) · ~15s full mode |
| **Measurement tool (dev-only)** | `python3 scripts/measure-prompt-tokens.py <file1> [<file2> ...]` |

---

## Sampling Rate

- **After every task commit:** Run `python3 skills/tas/runtime/tests/simulate_prompt_slim_diff.py` (fast mode, < 2s)
- **After every plan wave:** Full canary suite manual pass (all Canaries #4–#9 via `/tas-verify`, plus SSOT lint block) + `python3 scripts/measure-prompt-tokens.py skills/tas/agents/meta.md` (dev re-measurement to confirm ≤ 5,500 tokens)
- **Before `/gsd-verify-work`:** All 16 Per-Task rows green + human re-read of meta.md / meta-classify.md / meta-execute.md for semantic preservation
- **Max feedback latency:** < 2 seconds (fast mode) · < 15 seconds (full mode)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 5-01-01 | 01 | 0 | SLIM-01 | — | `scripts/measure-prompt-tokens.py` exists, imports `anthropic`, calls `count_tokens`, emits `{path}\t{tokens}\n` + TOTAL | integration (dev-only) | `python3 scripts/measure-prompt-tokens.py skills/tas/agents/meta.md` → exit 0, stdout has TOTAL line; `grep -v '^anthropic' skills/tas/runtime/requirements.txt` finds no anthropic (inverse assertion) | ❌ W0 | ⬜ pending |
| 5-01-02 | 01 | 0 | SLIM-01 | — | Script fails loudly on missing `anthropic` package | unit | `python3 -c "import sys; sys.modules['anthropic']=None; exec(open('scripts/measure-prompt-tokens.py').read())"` → exit 1 with stderr message | ❌ W0 | ⬜ pending |
| 5-01-03 | 01 | 0 | SLIM-01 | — | Script fails loudly on missing `ANTHROPIC_API_KEY` | unit | `unset ANTHROPIC_API_KEY && python3 scripts/measure-prompt-tokens.py skills/tas/agents/meta.md` → exit 1 with stderr message | ❌ W0 | ⬜ pending |
| 5-02-01 | 02 | 1 | SLIM-02 | — | Pre-slim baseline snapshots captured and committed | unit | `git log --oneline -- skills/tas-verify/fixtures/canary-9-baseline-a.json` returns ≥ 1 commit; same for b.json and c.json | ❌ W1 | ⬜ pending |
| 5-02-02 | 02 | 1 | SLIM-02 | — | `references/meta-classify.md` and `references/meta-execute.md` both exist and are non-empty | unit | `test -s skills/tas/references/meta-classify.md && test -s skills/tas/references/meta-execute.md` → exit 0 | ❌ W1 | ⬜ pending |
| 5-02-03 | 02 | 1 | SLIM-02 | — | meta.md token count ≤ 5,500 (threshold) — target ≤ 4,500 | integration | `python3 scripts/measure-prompt-tokens.py skills/tas/agents/meta.md` → parse output, assert `tokens ≤ 5500`; warn if > 4,500 | ❌ W1 | ⬜ pending |
| 5-03-01 | 03 | 2 | SLIM-02 | — | meta.md contains Mode-bound Reference Load dispatch block | unit (grep) | `grep -qE 'Read\(.*references/meta-(classify\|execute)\.md.*\)' skills/tas/agents/meta.md` → exit 0 | ❌ W2 | ⬜ pending |
| 5-03-02 | 03 | 2 | SLIM-02 | — | Final JSON schema contains `references_read` field definition | unit (grep) | `grep -qF '"references_read"' skills/tas/agents/meta.md` → exit 0 | ❌ W2 | ⬜ pending |
| 5-03-03 | 03 | 2 | SLIM-02 | — | SKILL.md Phase 3 warns (not halts) on empty / mismatched `references_read` | unit | Mock test: inject JSON `{"status":"completed","references_read":[]}` to SKILL.md Phase 3 parse path — assert NO halt emission, warning text present | ❌ W2 | ⬜ pending |
| 5-03-04 | 03 | 2 | SLIM-03 | — | SKILL.md information hiding / SCOPE PROHIBITION dedup'd from 3 mentions → ≤ 2 | unit (grep) | `[[ $(grep -cE "(information hiding\|SCOPE PROHIBITION)" skills/tas/SKILL.md) -le 2 ]]` | ❌ W2 | ⬜ pending |
| 5-04-01 | 04 | 3 | SLIM-03 | — | SSOT-1 lint: `engine_invocations` schema sentence in exactly 1 file | unit (grep) | `[[ $(grep -rFln -- '"engine_invocations" counts \`bash run-dialectic.sh\` calls' skills/ \| grep -v _workspace \| wc -l \| tr -d ' ') == "1" ]]` | ❌ W3 | ⬜ pending |
| 5-04-02 | 04 | 3 | SLIM-03 | — | SSOT-2 lint: convergence verdict normative in exactly 1 file | unit (grep) | `[[ $(grep -rn -- '^- \`검증\` uses \*\*inverted model\*\*' skills/ \| wc -l \| tr -d ' ') == "1" ]]` | ❌ W3 | ⬜ pending |
| 5-04-03 | 04 | 3 | SLIM-03 | — | SSOT-3 lint: `references_read` attestation schema in exactly 1 file | unit (grep) | `[[ $(grep -rFln -- 'references_read: ["${SKILL_DIR}/references/meta-' skills/ \| grep -v _workspace \| wc -l \| tr -d ' ') == "1" ]]` | ❌ W3 | ⬜ pending |
| 5-04-04 | 04 | 3 | SLIM-03 | — | thesis.md / antithesis.md minimal dedup (antithesis.md structural sections unchanged per Phase 4 D-07) | unit (grep) | `git diff HEAD~..HEAD -- skills/tas/agents/antithesis.md` shows no changes to lines matching `^## (Pre-ACCEPT\|Response Types\|Review Lenses)` headers | ❌ W3 | ⬜ pending |
| 5-05-01 | 05 | 4 | SLIM-04 | — | Canary #9 sub (a) trivial classify structural diff vs baseline-a.json PASSES | integration | `python3 skills/tas/runtime/tests/simulate_prompt_slim_diff.py` → exit 0; stdout includes `sub-canary a: PASS` | ❌ W4 | ⬜ pending |
| 5-05-02 | 05 | 4 | SLIM-04 | — | Canary #9 sub (b) chunked classify `implementation_chunks` structural diff PASSES | integration | same command; stdout includes `sub-canary b: PASS` | ❌ W4 | ⬜ pending |
| 5-05-03 | 05 | 4 | SLIM-04 | — | Canary #9 sub (c) full execute 5-field + `references_read` structural diff PASSES | integration | same command; stdout includes `sub-canary c: PASS` | ❌ W4 | ⬜ pending |
| 5-05-04 | 05 | 4 | SLIM-04 | — | Canary #9 fails loud on missing baseline | unit | `mv skills/tas-verify/fixtures/canary-9-baseline-a.json /tmp/; python3 ... → exit 1; mv back` | ❌ W4 | ⬜ pending |
| 5-05-05 | 05 | 4 | SLIM-04 | — | `skills/tas-verify/canaries.md` §Canary #9 PENDING markers replaced with concrete contract | unit (grep) | `grep -c "^## Canary #9" skills/tas-verify/canaries.md` == 1 AND `grep -c "PENDING" skills/tas-verify/canaries.md` unchanged from Canary #8 baseline (no new PENDING) | ❌ W4 | ⬜ pending |
| 5-06-01 | 06 | 5 | SLIM-01..04 | — | `scripts/measure-prompt-tokens.py` re-run shows meta.md ≤ 5,500 | integration | `python3 scripts/measure-prompt-tokens.py skills/tas/agents/meta.md skills/tas/references/meta-classify.md skills/tas/references/meta-execute.md` → parse + assert meta.md row ≤ 5500 | ❌ W5 | ⬜ pending |
| 5-06-02 | 06 | 5 | SLIM-03 | — | CLAUDE.md Common Mistakes section gets 1–2 Phase 5 bullets | unit (grep) | `grep -c "meta-classify.md\|meta-execute.md\|tiktoken\|measure-prompt-tokens" CLAUDE.md` ≥ 1 | ❌ W5 | ⬜ pending |
| 5-06-03 | 06 | 5 | — | — | ROADMAP Phase 5 [ ] → [x] and REQUIREMENTS SLIM-01..04 [ ] → [x] | unit | `grep -c "^\- \[x\] \*\*Phase 5" .planning/ROADMAP.md` == 1; `grep -c "^\- \[x\] \*\*SLIM-0" .planning/REQUIREMENTS.md` == 4 | ❌ W5 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `scripts/measure-prompt-tokens.py` — skeleton that imports `anthropic` + fails loud on missing package/API key (covers SLIM-01 basic shape)
- [x] `scripts/` directory (new parent) — unhides dev-only tooling from `skills/tas/runtime/`
- [x] `skills/tas-verify/fixtures/` directory (new) — parent for Canary #9 baseline JSON snapshots (a/b/c)
- [x] `skills/tas/runtime/tests/simulate_prompt_slim_diff.py` — PENDING stub (covers SLIM-04 Canary #9 entry point)
- [x] `skills/tas-verify/canaries.md` §Canary #9 PENDING placeholder — entry point appended to existing Canary #1–#8 list (Phase 4 Wave 0 precedent)
- [x] SSOT lint block PENDING stub in `skills/tas-verify/canaries.md` (or `skills/tas-verify/SKILL.md` — Plan step decides) — 3 unique-file invariants (SLIM-03)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Semantic preservation of MetaAgent behavior after split | SLIM-02 | Structural canary (D-05) diffs JSON fields but cannot detect prose-level meaning drift (e.g., "classify these 3 axes" → "classify these 2 axes" that still parses) | Human re-reads meta.md + references/meta-classify.md + references/meta-execute.md after Wave 1 split; verifies each Mode's procedure is complete and un-truncated. Sign-off on Phase 5 gate. |
| Token measurement empirical baseline (Wave 1) | SLIM-02 | `measure-prompt-tokens.py` requires operator to have `ANTHROPIC_API_KEY` env var + `pip install anthropic` (dev-only, NOT in requirements.txt per SLIM-01) — CI may not have this | Developer runs `pip install anthropic; export ANTHROPIC_API_KEY=sk-...; python3 scripts/measure-prompt-tokens.py skills/tas/agents/meta.md` before splitting; records pre-slim number in PR description / SUMMARY.md |
| Anthropic API reachability | SLIM-01 | count_tokens API is a live network call; rate limits / outages are environmental | Any SLIM-01 test run documents `ANTHROPIC_API_KEY` presence + `anthropic` package install; API failures → document + re-run later (exit 2 retry path) |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (scripts/, fixtures/, canary stub, lint stub)
- [x] No watch-mode flags
- [x] Feedback latency < 2s fast mode / < 15s full mode
- [x] `nyquist_compliant: true` set in frontmatter after Wave 0 complete and Per-Task map rows validated

**Approval:** approved 2026-04-22
