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

# Only emit message if SDK is missing
if ! check_python_sdk; then
  cat <<'ADVICE'
[tas] claude-agent-sdk not detected. /tas will fail without it.
Install with one of:
  pip install claude-agent-sdk
  pipx install claude-agent-sdk
  uv tool install claude-agent-sdk
ADVICE
fi

exit 0
