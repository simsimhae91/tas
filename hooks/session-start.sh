#!/bin/bash
# tas Environment Preflight — SessionStart hook
# Checks Python + claude-agent-sdk availability at session start.
# Provides actionable guidance if missing. Read-only diagnostic.

check_python_sdk() {
  # 1) System / venv python
  if python3 -c "import claude_agent_sdk" 2>/dev/null; then
    return 0
  fi
  # 2) pipx venv
  local pipx_py="$HOME/.local/pipx/venvs/claude-agent-sdk/bin/python3"
  if [ -x "$pipx_py" ] && "$pipx_py" -c "import claude_agent_sdk" 2>/dev/null; then
    return 0
  fi
  # 3) uv tool
  local uv_py="$HOME/.local/share/uv/tools/claude-agent-sdk/bin/python3"
  if [ -x "$uv_py" ] && "$uv_py" -c "import claude_agent_sdk" 2>/dev/null; then
    return 0
  fi
  return 1
}

# Write SDK status marker for SKILL.md fail-fast check
TAS_MARKER_DIR="${TMPDIR:-/tmp}/tas-sdk-status"
mkdir -p "$TAS_MARKER_DIR"

if ! check_python_sdk; then
  echo "missing" > "$TAS_MARKER_DIR/sdk-status"
  cat <<'ADVICE'
⚠ claude-agent-sdk is not installed. /tas requires it to run.

Install with one of:
  pip install claude-agent-sdk
  pipx install claude-agent-sdk
  uv tool install claude-agent-sdk

Then start a new session and try again.
ADVICE
else
  echo "ok" > "$TAS_MARKER_DIR/sdk-status"
fi

exit 0
