#!/bin/bash
# Canary #7 — Subagent-spawned orphan survival + real-chain integration guard.
# Guards: Phase 3.1 D-VERIFY-TOPO-01 + TOPO-01..TOPO-06 topology + Plan Review Issue #1.
# Delegates to the Python harness (simulate_subagent_orphan.py) which does
# the real work across two Phases:
#   Phase 1 — orphan survival (PPID=1, $MARKER=survived, duration<10s)
#   Phase 2 — real run-dialectic.sh chain with mock dialectic injection
#             (engine.done/engine.exit markers; SKIPs if env constraints)
# Preserved as a wrapper for parity with Canary #6 bash entry.
# Env overrides: TAS_VERIFY_TOPO_DURATION_SEC (default 120s, smoke: 10s).

set -u
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_HARNESS="${SCRIPT_DIR}/simulate_subagent_orphan.py"

if [ ! -f "$PYTHON_HARNESS" ]; then
  echo "FAIL: canary #7 python harness missing at $PYTHON_HARNESS"
  exit 1
fi

# Delegate to Python harness (implements the 2-Phase PASS contract)
exec python3 "$PYTHON_HARNESS" "$@"
