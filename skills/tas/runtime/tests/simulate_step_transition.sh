#!/bin/bash
# Canary #6 — Layer B watchdog (bash_wrapper_kill + step_transition_hang)
# regression guard.
#
# PART A: induce Layer B SIGTERM/SIGKILL via short TAS_WATCHDOG_TIMEOUT_SEC
#         + mock client that sleeps longer than Layer A would tolerate.
#         Assert exit 124 or 137.
#
# PART B: (Research §3.10) verify MetaAgent classification of
#         "exit 0 + JSON absent" → step_transition_hang.
#         This is a stdlib unittest at tests/simulate_step_transition_unit.py.
#
# stdlib-only. Target wall-clock < 17s (timeout 5s + grace 2s + startup).

set -u
REPO_ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
RUN_SCRIPT="${REPO_ROOT}/skills/tas/runtime/run-dialectic.sh"
DIALECTIC="${REPO_ROOT}/skills/tas/runtime/dialectic.py"

# Pre-flight: Layer B requires timeout or gtimeout; skip with PASS-SKIP if absent.
if ! command -v timeout >/dev/null 2>&1 && ! command -v gtimeout >/dev/null 2>&1; then
  echo "SKIP: canary #6 requires coreutils 'timeout' or 'gtimeout' (Layer B disabled)."
  echo "      Install via 'brew install coreutils' on macOS. This is not a regression."
  exit 0  # skipped, not failed — matches D-03 graceful degrade policy
fi

TMPDIR="$(mktemp -d -t tas-canary6-XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

LOGDIR="${TMPDIR}/logs/step-canary6"
mkdir -p "$LOGDIR"
cat > "${TMPDIR}/thesis.md" <<'EOF'
# mock thesis
EOF
cat > "${TMPDIR}/antithesis.md" <<'EOF'
# mock antithesis
EOF
cat > "${TMPDIR}/step-config.json" <<EOF
{
  "log_dir": "${LOGDIR}",
  "step_id": "canary6",
  "step_goal": "Layer B regression guard",
  "project_root": "${TMPDIR}",
  "thesis_prompt_path": "${TMPDIR}/thesis.md",
  "antithesis_prompt_path": "${TMPDIR}/antithesis.md",
  "step_assignment": "mock",
  "antithesis_briefing": "mock",
  "query_timeout": 3600
}
EOF

# Mock SDK that sleeps 30s — longer than Layer B timeout (5s) but also longer
# than Layer A query_timeout (3600 → effectively off). Ensures Layer B trips
# FIRST.
mkdir -p "${TMPDIR}/mock/claude_agent_sdk"
cat > "${TMPDIR}/mock/claude_agent_sdk/__init__.py" <<'EOF'
from ._shim import *
from .types import SystemPromptPreset
EOF
cat > "${TMPDIR}/mock/claude_agent_sdk/_shim.py" <<'EOF'
import asyncio
class _MockClient:
    async def connect(self): return None
    async def disconnect(self): return None
    async def query(self, p): return None
    async def receive_response(self):
        await asyncio.sleep(30)
        if False: yield
class ClaudeSDKClient(_MockClient):
    def __init__(self, options=None): self.options = options
class ClaudeAgentOptions(dict):
    def __init__(self, **kw): super().__init__(**kw)
class AssistantMessage: pass
class ResultMessage: pass
class TextBlock: pass
EOF
cat > "${TMPDIR}/mock/claude_agent_sdk/types.py" <<'EOF'
class SystemPromptPreset(dict):
    def __init__(self, **kw): super().__init__(**kw)
EOF
cat > "${TMPDIR}/mock/claude_agent_sdk/_errors.py" <<'EOF'
class CLIConnectionError(Exception): pass
EOF

# Invoke run-dialectic.sh with 5s watchdog budget + 2s kill grace.
export TAS_WATCHDOG_TIMEOUT_SEC=5
export TAS_WATCHDOG_KILL_GRACE_SEC=2
export PYTHONPATH="${TMPDIR}/mock:${PYTHONPATH:-}"

start=$(date +%s)
"$RUN_SCRIPT" "${TMPDIR}/step-config.json" >"${TMPDIR}/stdout" 2>"${TMPDIR}/stderr"
ec=$?
end=$(date +%s)
elapsed=$((end - start))

# Expected: exit 124 (SIGTERM) or 137 (SIGKILL). Anything else fails.
if [ "$ec" -ne 124 ] && [ "$ec" -ne 137 ]; then
  echo "FAIL: canary #6 expected exit 124 or 137, got $ec (elapsed ${elapsed}s)"
  echo "--- stdout ---"; tail -c 500 "${TMPDIR}/stdout"
  echo "--- stderr ---"; tail -c 500 "${TMPDIR}/stderr"
  exit 1
fi

# Additional sanity: the kill must fire within TIMEOUT + GRACE + small startup.
# Upper bound = 5 + 2 + 10 = 17s.
if [ "$elapsed" -gt 17 ]; then
  echo "FAIL: canary #6 took ${elapsed}s (> 17s upper bound)"
  exit 1
fi

echo "PASS: canary #6 Layer B bash_wrapper_kill (exit $ec, elapsed ${elapsed}s)"
exit 0
