#!/bin/bash
# tas Deliverable Integrity Guard — Stop hook
# Blocks session exit if /tas was invoked but DELIVERABLE.md is missing/empty.
# Uses REQUEST.md existence as the /tas session marker.
# Skips blocking while MetaAgent is still active (dialectic engine running
# or workspace recently modified) — prevents false-positive block during
# background Agent() execution before the final JSON result returns.
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

if [ -f "$DELIVERABLE" ] && [ -s "$DELIVERABLE" ]; then
  # DELIVERABLE present and non-empty — /tas completed, approve.
  exit 0
fi

# DELIVERABLE missing/empty. Before blocking, verify MetaAgent is truly idle —
# otherwise we'd block a session whose background Agent() is still producing
# the deliverable.

# Signal 1: dialectic engine process alive for THIS workspace. MetaAgent invokes
# `bash run-dialectic.sh {step-config.json}` which execs `python3 .../dialectic.py {config}`.
# The step-config.json path embeds the workspace path in argv. Match by workspace
# basename (timestamp dir) — unique enough and robust against macOS /var vs /private/var
# symlink resolution differences between `git rev-parse` and the process's actual argv.
WS_KEY="$(basename "${LATEST_WS%/}")"
if [ -n "$WS_KEY" ] \
  && ps -eo args 2>/dev/null | grep -v ' grep ' | grep -F "dialectic.py" | grep -qF "/$WS_KEY/"; then
  exit 0
fi

# Signal 2: workspace files recently modified (within 3 minutes).
# MetaAgent writes step-config.json, system prompts, and per-round logs
# throughout execution — so stale mtime means execution is truly stopped.
# Covers the gap between dialectic engine invocations (MetaAgent synthesis).
if find "$LATEST_WS" -type f -mmin -3 2>/dev/null | grep -q .; then
  exit 0
fi

# No active signals — DELIVERABLE is genuinely missing. Block.
REASON="[tas] DELIVERABLE.md is missing or empty.
Workspace: ${LATEST_WS}
A /tas run may not have completed.

To resolve:
  • Exit again to force close (override)
  • Re-run /tas to complete the task
  • Check workspace: cat ${LATEST_WS}REQUEST.md
  • Clean up workspace: /tas-workspace clean"
jq -n --arg reason "$REASON" '{"decision": "block", "reason": $reason}'
exit 0
