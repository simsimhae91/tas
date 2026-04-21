#!/bin/bash
# tas Phase 2 Resume Entry — Per-task Quick Check
# Run after each commit in Phase 2 to verify prompt-edit invariants.
# Exits 0 on all-PASS, 1 on any-FAIL. Stdlib-only (bash + grep + wc + awk).
# Usage: bash .planning/phases/02-resume-entry/quick-check.sh
# Expected runtime: ~10 seconds.

set -u
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$PROJECT_ROOT"
overall_failed=0

# ---------------------------------------------------------------------------
# Check 1: SKILL.md Phase 0b section + SCOPE comment + Agent() count
# ---------------------------------------------------------------------------
check_skill_md_phase_0b() {
  local f="skills/tas/SKILL.md"
  if ! grep -q '^## Phase 0b: Resume Gate' "$f"; then
    echo "FAIL: skill_md_phase_0b: missing '## Phase 0b: Resume Gate' header" >&2
    return 1
  fi
  if ! grep -q 'SCOPE: SKILL.md may ONLY Read checkpoint.json / plan.json / REQUEST.md' "$f"; then
    echo "FAIL: skill_md_phase_0b: SCOPE comment not present" >&2
    return 1
  fi
  local agent_count
  agent_count=$(grep -cE 'Agent\(\{' "$f")
  if [ "$agent_count" != "3" ]; then
    echo "FAIL: skill_md_phase_0b: expected 3 Agent({ invocation blocks, got $agent_count" >&2
    return 1
  fi
  echo "PASS: skill_md_phase_0b (header + SCOPE + 3 Agent({ blocks)"
  return 0
}

# ---------------------------------------------------------------------------
# Check 2: SKILL.md contains 7 halt_reason enums each >=2 occurrences
# ---------------------------------------------------------------------------
check_skill_md_halt_reasons() {
  local f="skills/tas/SKILL.md"
  local hr count
  for hr in no_checkpoint plan_missing checkpoint_corrupt plan_hash_mismatch checkpoint_schema_unsupported workspace_missing already_completed; do
    count=$(grep -c "$hr" "$f")
    if [ "$count" -lt 2 ]; then
      echo "FAIL: skill_md_halt_reasons: '$hr' count=$count (expected >=2)" >&2
      return 1
    fi
  done
  echo "PASS: skill_md_halt_reasons (all 7 halt reasons >=2x)"
  return 0
}

# ---------------------------------------------------------------------------
# Check 3: meta.md MODE:resume branch + 4 Input Contract rows + Phase 2d
# ---------------------------------------------------------------------------
check_meta_md_mode_resume() {
  local f="skills/tas/agents/meta.md"
  local token
  for token in 'MODE' 'RESUME_FROM' 'COMPLETED_STEPS' 'PLAN_HASH'; do
    if ! grep -qE "^\| \`${token}\`" "$f"; then
      echo "FAIL: meta_md_mode_resume: Input Contract row '| \`${token}\`' missing" >&2
      return 1
    fi
  done
  if ! grep -qE 'MODE:\s*resume' "$f"; then
    echo "FAIL: meta_md_mode_resume: 'MODE: resume' not found" >&2
    return 1
  fi
  if ! grep -q 'Resume cursor application' "$f"; then
    echo "FAIL: meta_md_mode_resume: '#### Resume cursor application' sub-header missing" >&2
    return 1
  fi
  if ! grep -q 'ALREADY DONE: step' "$f"; then
    echo "FAIL: meta_md_mode_resume: 'ALREADY DONE: step' stderr log missing" >&2
    return 1
  fi
  if ! grep -q 'Re-verify plan_hash on resume' "$f"; then
    echo "FAIL: meta_md_mode_resume: 'Re-verify plan_hash on resume' Bash description missing" >&2
    return 1
  fi
  if ! grep -q 'chunk_resume_not_supported_in_m1' "$f"; then
    echo "FAIL: meta_md_mode_resume: chunk guard halt reason missing" >&2
    return 1
  fi
  if ! grep -q 'Do NOT cache the payload in memory across steps' "$f"; then
    echo "FAIL: meta_md_mode_resume: Pitfall 4 invariant line not preserved" >&2
    return 1
  fi
  echo "PASS: meta_md_mode_resume (4 rows + MODE:resume + Phase 2d + preservation)"
  return 0
}

# ---------------------------------------------------------------------------
# Check 4: CLAUDE.md line count 129 + new bullet present + ordering
# ---------------------------------------------------------------------------
check_claude_md_bullet() {
  local f="CLAUDE.md"
  local lines
  lines=$(wc -l < "$f" | tr -d ' ')
  if [ "$lines" != "129" ]; then
    echo "FAIL: claude_md_bullet: line count = $lines (expected 129)" >&2
    return 1
  fi
  if ! grep -q 'Reading dialectic artifacts from SKILL.md during resume' "$f"; then
    echo "FAIL: claude_md_bullet: new D-07 Layer 3 bullet missing" >&2
    return 1
  fi
  if ! grep -q 'Adding auto-resume daemons, background retry loops' "$f"; then
    echo "FAIL: claude_md_bullet: Phase 1 D-04 bullet (prerequisite) missing" >&2
    return 1
  fi
  # Ordering: new bullet must appear IMMEDIATELY after D-04 bullet
  local next_line
  next_line=$(awk '/Adding auto-resume daemons/{f=1;next} f{print; exit}' "$f")
  if ! echo "$next_line" | grep -q 'Reading dialectic artifacts from SKILL'; then
    echo "FAIL: claude_md_bullet: new bullet not immediately after D-04 bullet" >&2
    echo "  line after D-04: $next_line" >&2
    return 1
  fi
  echo "PASS: claude_md_bullet (129 lines + bullet present + ordering correct)"
  return 0
}

# ---------------------------------------------------------------------------
# Check 5: tas-verify Canary #4 registered with correct grep pattern
# ---------------------------------------------------------------------------
check_canaries_md_canary_4() {
  local f="skills/tas-verify/canaries.md"
  if ! grep -q '^## Canary #4 — Resume info-hiding (I-1 regression guard)' "$f"; then
    echo "FAIL: canaries_md_canary_4: Canary #4 header missing" >&2
    return 1
  fi
  if ! grep -q 'RESUME-02' "$f"; then
    echo "FAIL: canaries_md_canary_4: RESUME-02 guard reference missing" >&2
    return 1
  fi
  # Full D-07 Layer 2 grep regex pattern must appear
  if ! grep -qE "dialogue\\\\.md\\|round-\\[0-9\\]\\+-\\(thesis\\|antithesis\\)\\\\.md\\|deliverable\\\\.md\\|lessons\\\\.md" "$f"; then
    echo "FAIL: canaries_md_canary_4: full D-07 Layer 2 grep pattern not present" >&2
    return 1
  fi
  # Canary #1/#2/#3 preserved
  local c
  for c in 'Canary #1 — Background-transition' 'Canary #2 — Dialectic engine monopoly' 'Canary #3 — Retry-dir preservation'; do
    if ! grep -q "^## $c" "$f"; then
      echo "FAIL: canaries_md_canary_4: existing $c not preserved" >&2
      return 1
    fi
  done
  echo "PASS: canaries_md_canary_4 (header + RESUME-02 + regex + prior canaries preserved)"
  return 0
}

# ---------------------------------------------------------------------------
# Check 6: I-1 static lint — exact D-07 Layer 2 regex against SKILL.md,
# tolerating intentional SCOPE / anti-feature warning comments.
# ---------------------------------------------------------------------------
check_i1_canary() {
  local matches violations
  matches=$(grep -nE 'dialogue\.md|round-[0-9]+-(thesis|antithesis)\.md|deliverable\.md|lessons\.md' skills/tas/SKILL.md || true)
  if [ -z "$matches" ]; then
    echo "PASS: i1_canary (zero matches — strictest interpretation)"
    return 0
  fi
  # Heuristic: exclude lines that are intentional warning documentation or
  # pre-Phase-2 Phase 3 user-facing display strings (NOT Read() operations):
  #   - `# SCOPE:` lines (Phase 0b scope rule)
  #   - `Phase 0b does NOT` / `Read dialectic artifacts` (anti-feature HTML block)
  #   - `I-1 regression` lines (narrative forbidden-list documentation)
  #   - `Reading dialectic artifacts` (this very rule, if cited)
  #   - `Lessons:` — Phase 3 summary display rendering
  #   - `Blockers (from lessons.md)` / `for blockers` — Phase 3 HALT rendering
  #   - `Check lessons.md for details` — Phase 3 Recovery Guidance fallback
  violations=$(echo "$matches" | grep -vE '# SCOPE:|Phase 0b does NOT|I-1 regression|Reading dialectic artifacts|Lessons:|for blockers|Blockers \(from lessons\.md\)|Check lessons\.md for details|Read dialectic artifacts')
  if [ -z "$violations" ]; then
    echo "PASS: i1_canary (matches only inside intentional warning / display strings)"
    return 0
  fi
  echo "FAIL: i1_canary — SKILL.md contains dialectic artifact references OUTSIDE warning comments:" >&2
  echo "$violations" >&2
  return 1
}

# ---------------------------------------------------------------------------
# Main block
# ---------------------------------------------------------------------------
for check in check_skill_md_phase_0b check_skill_md_halt_reasons check_meta_md_mode_resume check_claude_md_bullet check_canaries_md_canary_4 check_i1_canary; do
  if ! "$check"; then
    overall_failed=1
  fi
done

if [ "$overall_failed" = "1" ]; then
  echo ""
  echo "===== OVERALL: FAIL ====="
  exit 1
fi

echo ""
echo "===== OVERALL: ALL CHECKS PASSED ====="
exit 0
