#!/bin/bash
# tas Deliverable Integrity Guard — Stop hook
# Blocks session exit if /tas was invoked but DELIVERABLE.md is missing/empty.
# Uses REQUEST.md existence as the /tas session marker.
# Protocol: stdin JSON input, stdout JSON output, always exit 0.

# jq is required for JSON parsing; exit cleanly if unavailable
command -v jq >/dev/null 2>&1 || exit 0

# Read hook input from stdin (JSON with stop_hook_active, etc.)
HOOK_INPUT=$(cat)

# Prevent recursion: if stop_hook_active is true, approve immediately
STOP_HOOK_ACTIVE=$(echo "$HOOK_INPUT" | jq -r '.stop_hook_active // "false"' 2>/dev/null)
if [ "$STOP_HOOK_ACTIVE" = "true" ]; then
  exit 0
fi

# Find project root
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
WORKSPACE_BASE="${PROJECT_ROOT}/_workspace/quick"

# No workspace at all — not a /tas session, approve
if [ ! -d "$WORKSPACE_BASE" ]; then
  exit 0
fi

# Find the most recent workspace (by timestamp directory name)
LATEST_WS="$(ls -1d "${WORKSPACE_BASE}/"*/ 2>/dev/null | sort -r | head -1)"

# No workspace directories — approve
if [ -z "$LATEST_WS" ]; then
  exit 0
fi

# Check if this workspace has a REQUEST.md (= /tas was invoked)
if [ ! -f "${LATEST_WS}REQUEST.md" ]; then
  exit 0
fi

# REQUEST.md exists — check for DELIVERABLE.md
DELIVERABLE="${LATEST_WS}DELIVERABLE.md"

if [ ! -f "$DELIVERABLE" ] || [ ! -s "$DELIVERABLE" ]; then
  REASON="[tas] DELIVERABLE.md가 없거나 비어 있습니다. 워크스페이스: ${LATEST_WS} — /tas 실행이 완료되지 않았을 수 있습니다. 무시하려면 다시 종료를 시도하세요."
  jq -n --arg reason "$REASON" '{"decision": "block", "reason": $reason}'
  exit 0
fi

exit 0
