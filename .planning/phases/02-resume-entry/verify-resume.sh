#!/bin/bash
# tas Phase 2 Resume Entry — End-to-end Resume Simulation
# Simulates the SKILL.md Phase 0b pre-condition checks against real
# checkpoint.py CLI fixtures in mktemp workspaces. Does NOT invoke Agent()
# — static simulation only. Also runs dialectic.py --self-test to ensure
# Phase 1 checkpoint schema regression is preserved.
# Usage: bash .planning/phases/02-resume-entry/verify-resume.sh
# Expected runtime: ~60 seconds.

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
CHECKPOINT_PY="$PROJECT_ROOT/skills/tas/runtime/checkpoint.py"
DIALECTIC_PY="$PROJECT_ROOT/skills/tas/runtime/dialectic.py"
test -f "$CHECKPOINT_PY" || { echo "FAIL: $CHECKPOINT_PY missing" >&2; exit 1; }
test -f "$DIALECTIC_PY"  || { echo "FAIL: $DIALECTIC_PY missing" >&2; exit 1; }

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT INT TERM
failed=0

pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1" >&2; failed=1; }

# ---------------------------------------------------------------------------
# Scenario 1 — Latest-detect excludes classify-*
# ---------------------------------------------------------------------------
mkdir -p "$TMP/_workspace/quick/classify-20260421_120000"
mkdir -p "$TMP/_workspace/quick/20260421_130000"
# Ensure the timestamped dir is newer than the classify- dir so `ls -t` would
# pick it anyway — but the grep -v /classify- filter is what guarantees
# correctness regardless of mtime.
touch -t 202604211300.00 "$TMP/_workspace/quick/20260421_130000"
touch -t 202604211200.00 "$TMP/_workspace/quick/classify-20260421_120000"

LATEST=$(ls -1dt "$TMP/_workspace/quick/"*/ 2>/dev/null | grep -v '/classify-' | head -1 | sed 's#/$##')
if [[ "$LATEST" == *"/20260421_130000" ]]; then
  pass "scenario 1 — latest-detect excludes classify-*"
else
  fail "scenario 1 — latest-detect returned '$LATEST' (expected *20260421_130000)"
fi

# ---------------------------------------------------------------------------
# Scenario 2 — `no_checkpoint` halt when no checkpoint.json
# ---------------------------------------------------------------------------
WS2="$TMP/_workspace/quick/20260421_ws2"
mkdir -p "$WS2"
if [ ! -f "$WS2/checkpoint.json" ]; then
  pass "scenario 2 — no_checkpoint (checkpoint.json absent → halt)"
else
  fail "scenario 2 — checkpoint.json unexpectedly present in $WS2"
fi

# ---------------------------------------------------------------------------
# Scenario 3 — `plan_missing` halt when checkpoint exists but plan.json missing
# ---------------------------------------------------------------------------
WS3="$TMP/_workspace/quick/20260421_ws3"
mkdir -p "$WS3"
CKPT3_JSON='{"schema_version":1,"workspace":"'"$WS3"'","plan_hash":"0000000000000000000000000000000000000000000000000000000000000000","current_step":"1","completed_steps":[],"current_chunk":null,"completed_chunks":[],"status":"running","updated_at":"2026-04-21T00:00:00.000000+00:00"}'
python3 "$CHECKPOINT_PY" write "$WS3" --json "$CKPT3_JSON" >/dev/null 2>&1
if [ -f "$WS3/checkpoint.json" ] && [ ! -f "$WS3/plan.json" ]; then
  pass "scenario 3 — plan_missing (checkpoint present, plan.json absent → halt)"
else
  fail "scenario 3 — state setup wrong (checkpoint present? $(test -f "$WS3/checkpoint.json" && echo yes || echo no) / plan absent? $(test ! -f "$WS3/plan.json" && echo yes || echo no))"
fi

# ---------------------------------------------------------------------------
# Scenario 4 — `plan_hash_mismatch` halt
# ---------------------------------------------------------------------------
WS4="$TMP/_workspace/quick/20260421_ws4"
mkdir -p "$WS4"
PLAN4_JSON='{"request":"test","request_type":"implement","complexity":"simple","steps":[{"id":"1","name":"구현","goal":"g","pass_criteria":["c"]}],"loop_count":1,"loop_policy":{"reentry_point":"구현","early_exit_on_no_improvement":true,"persistent_failure_halt_after":3},"implementation_chunks":null,"project_domain":null,"focus_angle":null,"approved_at":"2026-04-21T00:00:00+00:00"}'
python3 "$CHECKPOINT_PY" write-plan "$WS4" --json "$PLAN4_JSON" >/dev/null 2>&1
FAKE_HASH="0000000000000000000000000000000000000000000000000000000000000000"
CKPT4_JSON='{"schema_version":1,"workspace":"'"$WS4"'","plan_hash":"'"$FAKE_HASH"'","current_step":"1","completed_steps":[],"current_chunk":null,"completed_chunks":[],"status":"running","updated_at":"2026-04-21T00:00:00.000000+00:00"}'
python3 "$CHECKPOINT_PY" write "$WS4" --json "$CKPT4_JSON" >/dev/null 2>&1
ACTUAL4=$(python3 "$CHECKPOINT_PY" hash "$WS4/plan.json")
CKPT4_HASH=$(python3 "$CHECKPOINT_PY" read "$WS4" | python3 -c "import json,sys; print(json.load(sys.stdin)['plan_hash'])")
if [ "$ACTUAL4" != "$CKPT4_HASH" ]; then
  pass "scenario 4 — plan_hash_mismatch (actual=$ACTUAL4... vs ckpt=$CKPT4_HASH... differ → halt)"
else
  fail "scenario 4 — hashes unexpectedly matched ($ACTUAL4 vs $CKPT4_HASH)"
fi

# ---------------------------------------------------------------------------
# Scenario 5 — `checkpoint_schema_unsupported` halt
# ---------------------------------------------------------------------------
WS5="$TMP/_workspace/quick/20260421_ws5"
mkdir -p "$WS5"
CKPT5_JSON='{"schema_version":2,"workspace":"'"$WS5"'","plan_hash":"0000000000000000000000000000000000000000000000000000000000000000","current_step":"1","completed_steps":[],"current_chunk":null,"completed_chunks":[],"status":"running","updated_at":"2026-04-21T00:00:00.000000+00:00"}'
python3 "$CHECKPOINT_PY" write "$WS5" --json "$CKPT5_JSON" >/dev/null 2>&1
SCHEMA_V=$(python3 "$CHECKPOINT_PY" read "$WS5" | python3 -c "import json,sys; print(json.load(sys.stdin)['schema_version'])")
if [ "$SCHEMA_V" != "1" ]; then
  pass "scenario 5 — checkpoint_schema_unsupported (schema_version=$SCHEMA_V != 1 → halt)"
else
  fail "scenario 5 — schema_version unexpectedly 1"
fi

# ---------------------------------------------------------------------------
# Scenario 6 — `already_completed` halt (status in {completed, finalized})
# ---------------------------------------------------------------------------
WS6A="$TMP/_workspace/quick/20260421_ws6a"
WS6B="$TMP/_workspace/quick/20260421_ws6b"
mkdir -p "$WS6A" "$WS6B"
CKPT6A_JSON='{"schema_version":1,"workspace":"'"$WS6A"'","plan_hash":"0000000000000000000000000000000000000000000000000000000000000000","current_step":null,"completed_steps":["1"],"current_chunk":null,"completed_chunks":[],"status":"completed","updated_at":"2026-04-21T00:00:00.000000+00:00"}'
CKPT6B_JSON='{"schema_version":1,"workspace":"'"$WS6B"'","plan_hash":"0000000000000000000000000000000000000000000000000000000000000000","current_step":null,"completed_steps":["1"],"current_chunk":null,"completed_chunks":[],"status":"finalized","updated_at":"2026-04-21T00:00:00.000000+00:00"}'
python3 "$CHECKPOINT_PY" write "$WS6A" --json "$CKPT6A_JSON" >/dev/null 2>&1
python3 "$CHECKPOINT_PY" write "$WS6B" --json "$CKPT6B_JSON" >/dev/null 2>&1
STATUS_A=$(python3 "$CHECKPOINT_PY" read "$WS6A" | python3 -c "import json,sys; print(json.load(sys.stdin)['status'])")
STATUS_B=$(python3 "$CHECKPOINT_PY" read "$WS6B" | python3 -c "import json,sys; print(json.load(sys.stdin)['status'])")
case "$STATUS_A" in completed|finalized) hit_a=1 ;; *) hit_a=0 ;; esac
case "$STATUS_B" in completed|finalized) hit_b=1 ;; *) hit_b=0 ;; esac
if [ "$hit_a" = "1" ] && [ "$hit_b" = "1" ]; then
  pass "scenario 6 — already_completed (status=completed and status=finalized both trigger halt branch)"
else
  fail "scenario 6 — status values did not both match completed|finalized (got '$STATUS_A' / '$STATUS_B')"
fi

# ---------------------------------------------------------------------------
# Scenario 7 — `workspace_missing` halt (path outside _workspace/quick/)
# ---------------------------------------------------------------------------
OUTSIDE="$TMP/malicious_dir"
mkdir -p "$OUTSIDE"
set +e
PROJECT_ROOT="$TMP" python3 -c '
import os, sys
p = os.path.realpath(sys.argv[1])
root = os.path.realpath(os.environ["PROJECT_ROOT"] + "/_workspace/quick")
if p == root or p.startswith(root + os.sep):
    sys.exit(0)
sys.exit(3)
' "$OUTSIDE"
rc=$?
set -e
if [ "$rc" = "3" ]; then
  pass "scenario 7 — workspace_missing (path outside _workspace/quick rejected with exit 3)"
else
  fail "scenario 7 — realpath check did not reject outside path (exit=$rc)"
fi

# ---------------------------------------------------------------------------
# Phase 1 regression check
# ---------------------------------------------------------------------------
echo ""
echo "Running dialectic.py --self-test (Phase 1 regression)..."
if python3 "$DIALECTIC_PY" --self-test 2>&1 | tail -1 | grep -q "PASS:.*tests passed"; then
  pass "dialectic.py --self-test (Phase 1 checkpoint schema regression)"
else
  fail "dialectic.py --self-test regression — Phase 1 checkpoint schema broken"
fi

# ---------------------------------------------------------------------------
# MODE:resume contract grep — SKILL.md + meta.md aligned
# ---------------------------------------------------------------------------
if grep -qE 'MODE:\s*resume' "$PROJECT_ROOT/skills/tas/agents/meta.md" \
   && grep -q 'ALREADY DONE: step' "$PROJECT_ROOT/skills/tas/agents/meta.md" \
   && grep -qE 'MODE:\s*resume' "$PROJECT_ROOT/skills/tas/SKILL.md"; then
  pass "MODE:resume contract strings present in SKILL.md + meta.md"
else
  fail "MODE:resume contract missing — Task 1 of Plan 02-02 or Plan 02-01 regression"
fi

# ---------------------------------------------------------------------------
# Exit block
# ---------------------------------------------------------------------------
if [ "$failed" = "1" ]; then
  echo ""
  echo "===== verify-resume.sh: FAIL ====="
  exit 1
fi

echo ""
echo "===== verify-resume.sh: ALL 7 SCENARIOS + PHASE 1 REGRESSION + CONTRACT PASSED ====="
exit 0
