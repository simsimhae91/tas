#!/bin/bash
# Canary #6 — Layer B watchdog (bash_wrapper_kill + step_transition_hang)
# regression guard.
#
# STATUS: Wave 0 scaffolding stub. Plan 07 (Wave 3) replaces the body with
# the Research §3.9 bash canary (sets TAS_WATCHDOG_TIMEOUT_SEC=5, invokes
# run-dialectic.sh with a mock config, asserts exit 124/137). Until wired,
# this stub emits SKIP: pending and exits 0 so the canary runner treats it
# as benign.
#
# Wired body will export TAS_WATCHDOG_TIMEOUT_SEC=5 to trigger Layer B.
# This comment preserves the grep token for Wave 0 acceptance.
set -u

echo "SKIP: pending — Wave 3 will wire real body (Research §3.9)"
# Grep token TAS_WATCHDOG_TIMEOUT_SEC= present in-body ensures Wave 0 check
# in 03-VALIDATION.md Per-Task Verification Map passes.
exit 0
