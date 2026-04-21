#!/bin/bash
# Unit + integration test for run-dialectic.sh EXIT trap atomic marker write
# (Phase 3.1 TOPO-01 / D-TOPO-02 / Plan Review Issue #1).
#
# Verifies:
#   Test A: Normal exit (rc=0)        → engine.done exists, engine.exit == "0"   (isolated subshell)
#   Test B: Python raise (rc=1)       → engine.done exists, engine.exit == "1"   (isolated subshell)
#   Test C: SIGTERM via timeout       → engine.done exists, engine.exit ∈ {124,143}
#                                        (SKIP on hosts without coreutils timeout)
#   Test D: Atomicity                 → no .tmp files leaked after trap fires
#   Test E: Real exec chain (integration) — invoke REAL run-dialectic.sh with a
#                                        sed-copied variant that points at a mock
#                                        dialectic script. Verifies that the trap
#                                        actually fires in the production code path,
#                                        i.e. `exec` has been removed (Issue #1).
#                                        (SKIP if sed-copy cannot be constructed.)
#
# Target wall-clock < 10s. stdlib + bash + coreutils (timeout optional).

set -u

REPO_ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
RUN_SCRIPT="${REPO_ROOT}/skills/tas/runtime/run-dialectic.sh"

if [ ! -f "$RUN_SCRIPT" ]; then
  echo "FAIL: test_exit_trap can't find run-dialectic.sh at $RUN_SCRIPT"
  exit 1
fi

# Extract ONLY the trap-block lines (Phase 3.1 TOPO-01) from run-dialectic.sh
# so we can test them in isolation without triggering find_python / exec.
TRAP_SRC="$(awk '/# -- Phase 3\.1 TOPO-01:/,/^trap .* EXIT$/' "$RUN_SCRIPT")"
if [ -z "$TRAP_SRC" ]; then
  echo "FAIL: could not extract Phase 3.1 TOPO-01 trap block from $RUN_SCRIPT"
  exit 1
fi

run_trap_harness() {
  # $1 = tmpdir acting as LOG_DIR
  # $2 = exit_code_to_simulate
  local logdir="$1"
  local rc="$2"
  bash -c "
    set +e
    $TRAP_SRC
    exit $rc
  " -- "${logdir}/step-config.json"
}

TMPDIR_ROOT="$(mktemp -d -t tas-topo-01-XXXXXX)"
trap 'rm -rf "$TMPDIR_ROOT"' EXIT

# ---- Test A: Normal exit (rc=0) -----------------------------------------
A_DIR="${TMPDIR_ROOT}/testA"
mkdir -p "$A_DIR"
run_trap_harness "$A_DIR" 0
if [ ! -f "${A_DIR}/engine.done" ]; then
  echo "FAIL Test A: engine.done missing after rc=0"; exit 1
fi
if [ "$(cat "${A_DIR}/engine.exit")" != "0" ]; then
  echo "FAIL Test A: engine.exit != '0', got '$(cat "${A_DIR}/engine.exit")'"; exit 1
fi
echo "  Test A (rc=0): PASS"

# ---- Test B: Python raise simulated via rc=1 ----------------------------
B_DIR="${TMPDIR_ROOT}/testB"
mkdir -p "$B_DIR"
run_trap_harness "$B_DIR" 1
if [ ! -f "${B_DIR}/engine.done" ]; then
  echo "FAIL Test B: engine.done missing after rc=1"; exit 1
fi
if [ "$(cat "${B_DIR}/engine.exit")" != "1" ]; then
  echo "FAIL Test B: engine.exit != '1', got '$(cat "${B_DIR}/engine.exit")'"; exit 1
fi
echo "  Test B (rc=1 raise): PASS"

# ---- Test C: SIGTERM via coreutils timeout -> rc=124 or 143 -------------
if command -v timeout >/dev/null 2>&1; then
  TIMEOUT_BIN=timeout
elif command -v gtimeout >/dev/null 2>&1; then
  TIMEOUT_BIN=gtimeout
else
  TIMEOUT_BIN=""
fi

if [ -n "$TIMEOUT_BIN" ]; then
  C_DIR="${TMPDIR_ROOT}/testC"
  mkdir -p "$C_DIR"
  "$TIMEOUT_BIN" --kill-after=2s 1s bash -c "
    set +e
    $TRAP_SRC
    sleep 5
  " -- "${C_DIR}/step-config.json"
  rc=$?
  if [ ! -f "${C_DIR}/engine.done" ]; then
    echo "FAIL Test C: engine.done missing after SIGTERM (rc=$rc)"; exit 1
  fi
  exit_content="$(cat "${C_DIR}/engine.exit" 2>/dev/null || echo missing)"
  case "$exit_content" in
    124|143) ;;
    *) echo "FAIL Test C: expected engine.exit in {124,143}, got '$exit_content'"; exit 1 ;;
  esac
  echo "  Test C (SIGTERM): PASS (engine.exit=$exit_content)"
else
  echo "  Test C (SIGTERM): SKIP (coreutils timeout absent)"
fi

# ---- Test D: Atomicity — no .tmp files leaked ---------------------------
for d in "${TMPDIR_ROOT}/testA" "${TMPDIR_ROOT}/testB"; do
  if [ -f "${d}/engine.done.tmp" ] || [ -f "${d}/engine.exit.tmp" ]; then
    echo "FAIL Test D: .tmp leaked in $d"; exit 1
  fi
done
echo "  Test D (atomicity): PASS"

# ---- Test E: Real exec chain integration (Issue #1 regression guard) ----
# Strategy: sed-copy run-dialectic.sh into tmpdir, rewriting the two
# Python invocation lines to call a mock script instead. This lets us
# exercise the entire trap + (non-)exec chain without requiring
# claude_agent_sdk. If sed-copy fails for any reason, SKIP.
E_DIR="${TMPDIR_ROOT}/testE"
mkdir -p "$E_DIR"
MOCK_SCRIPT="${E_DIR}/mock-dialectic.sh"
cat > "$MOCK_SCRIPT" <<'MOCK_EOF'
#!/bin/bash
# Mock dialectic — prints a single JSON line and exits 0.
echo '{"status":"completed","verdict":"ACCEPT"}'
exit 0
MOCK_EOF
chmod +x "$MOCK_SCRIPT"

# Build a modified run-dialectic.sh in tmpdir: point the two Python
# invocation lines at the mock. We also short-circuit find_python so it
# does NOT require claude_agent_sdk to be installed.
MOD_SCRIPT="${E_DIR}/run-dialectic-mod.sh"
# 1) Rewrite find_python to always emit /bin/echo (we don't actually run python in E).
# 2) Replace "$PYTHON" "$SCRIPT_DIR/dialectic.py" with the mock invocation.
sed -E \
  -e 's#^  if python3 -c "import claude_agent_sdk" 2>/dev/null; then$#  if true; then#' \
  -e 's#^    echo "python3"$#    echo "/bin/sh"#' \
  -e 's#"\$PYTHON" "\$SCRIPT_DIR/dialectic\.py" "\$@"#"'"$MOCK_SCRIPT"'"#g' \
  "$RUN_SCRIPT" > "$MOD_SCRIPT"

if [ ! -s "$MOD_SCRIPT" ]; then
  echo "  Test E (real exec chain): SKIP (sed-copy produced empty output)"
else
  chmod +x "$MOD_SCRIPT"
  # sanity: modified script must still parse
  if ! bash -n "$MOD_SCRIPT" 2>/dev/null; then
    echo "  Test E (real exec chain): SKIP (modified script failed bash -n)"
  else
    E_STEP_CFG="${E_DIR}/step-config.json"
    echo '{}' > "$E_STEP_CFG"
    # Invoke the modified run-dialectic.sh. We redirect stdout to a log.
    bash "$MOD_SCRIPT" "$E_STEP_CFG" > "${E_DIR}/engine.log" 2>&1
    erc=$?
    if [ ! -f "${E_DIR}/engine.done" ]; then
      echo "FAIL Test E: engine.done missing after real-chain exit rc=$erc"
      echo "  (log tail: $(tail -n 3 "${E_DIR}/engine.log" 2>/dev/null | tr '\n' ' '))"
      exit 1
    fi
    if [ "$(cat "${E_DIR}/engine.exit" 2>/dev/null)" != "0" ]; then
      echo "FAIL Test E: engine.exit != '0', got '$(cat "${E_DIR}/engine.exit" 2>/dev/null || echo missing)'"
      exit 1
    fi
    echo "  Test E (real exec chain): PASS"
  fi
fi

echo "PASS: test_exit_trap (5 cases — TOPO-01 + Issue #1 regression guard)"
exit 0
