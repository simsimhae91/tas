#!/bin/bash
# Locate a Python with claude_agent_sdk installed.
# Tries: 1) system python3  2) pipx venv  3) uv-managed
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

find_python() {
  # System / venv python
  if python3 -c "import claude_agent_sdk" 2>/dev/null; then
    echo "python3"
    return
  fi
  # pipx venv
  local pipx_py="$HOME/.local/pipx/venvs/claude-agent-sdk/bin/python3"
  if [ -x "$pipx_py" ]; then
    echo "$pipx_py"
    return
  fi
  # uv tool
  local uv_py="$HOME/.local/share/uv/tools/claude-agent-sdk/bin/python3"
  if [ -x "$uv_py" ]; then
    echo "$uv_py"
    return
  fi
  echo ""
}

PYTHON="$(find_python)"
if [ -z "$PYTHON" ]; then
  echo "ERROR: claude-agent-sdk not found. Install with one of:" >&2
  echo "  pip install claude-agent-sdk" >&2
  echo "  pipx install claude-agent-sdk" >&2
  exit 1
fi

# -- Phase 3.1 TOPO-01: EXIT trap writes atomic done + exit markers --
# Covers all exit paths: normal exit, Python raise, Layer A asyncio.timeout
# re-raise, Layer B SIGTERM (exit 124 from timeout(1) or 143 from bash
# receiving SIGTERM first — both observable; Plan 02 Test C accepts both).
# atomic via tempfile + mv -f (POSIX rename()), matching Phase 1
# checkpoint.py _atomic_write_json.
# LOG_DIR is the directory containing the step-config.json passed as $1.
# CRITICAL: bash MUST remain the parent process of the Python engine (no
# `exec` keyword on the final invocation lines) — `bash -c 'trap … EXIT;
# exec …'` does NOT fire the trap (Phase 3.1 Issue #1, empirically verified).
LOG_DIR="$(dirname "$1")"
trap 'rc=$?; echo "$rc" > "${LOG_DIR}/engine.exit.tmp" && mv -f "${LOG_DIR}/engine.exit.tmp" "${LOG_DIR}/engine.exit"; : > "${LOG_DIR}/engine.done.tmp" && mv -f "${LOG_DIR}/engine.done.tmp" "${LOG_DIR}/engine.done"' EXIT

# -- Phase 3 WATCH-03: Layer B watchdog (Bash timeout(1) wrapping) --
# Default watchdog budget — 20 min per step (CONTEXT D-03 §3.2).
# Override via environment (see 03-CONTEXT.md "user override path"):
#   TAS_WATCHDOG_TIMEOUT_SEC     total step budget before SIGTERM
#   TAS_WATCHDOG_KILL_GRACE_SEC  grace after SIGTERM before SIGKILL
WATCHDOG_TIMEOUT_SEC="${TAS_WATCHDOG_TIMEOUT_SEC:-1200}"
WATCHDOG_KILL_GRACE_SEC="${TAS_WATCHDOG_KILL_GRACE_SEC:-30}"

# Detect coreutils `timeout` (GNU default on Linux; `gtimeout` via Homebrew
# `brew install coreutils` on macOS). Absence → Layer B disabled (graceful
# degrade; Layer A asyncio.timeout remains active per Phase 3 Success
# Criterion 3).
if command -v timeout >/dev/null 2>&1; then
  TIMEOUT_BIN="timeout"
elif command -v gtimeout >/dev/null 2>&1; then
  TIMEOUT_BIN="gtimeout"
else
  TIMEOUT_BIN=""
fi

if [ -n "$TIMEOUT_BIN" ]; then
  # 2-stage kill: TIMEOUT_SEC → SIGTERM; KILL_GRACE_SEC later → SIGKILL.
  # Exit codes (coreutils §timeout-invocation): 124 SIGTERM, 137 SIGKILL.
  "$TIMEOUT_BIN" --kill-after="${WATCHDOG_KILL_GRACE_SEC}s" \
       "${WATCHDOG_TIMEOUT_SEC}s" \
       "$PYTHON" "$SCRIPT_DIR/dialectic.py" "$@"
else
  echo "⚠ tas watchdog: neither 'timeout' nor 'gtimeout' found — Layer B disabled." >&2
  echo "  Install via 'brew install coreutils' on macOS. Layer A (asyncio.timeout) remains active." >&2
  "$PYTHON" "$SCRIPT_DIR/dialectic.py" "$@"
fi
