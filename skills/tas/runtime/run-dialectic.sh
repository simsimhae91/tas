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

exec "$PYTHON" "$SCRIPT_DIR/dialectic.py" "$@"
