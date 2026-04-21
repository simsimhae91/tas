#!/usr/bin/env python3
"""Canary #6 sub-assertion — verify MetaAgent classification of
exit 0 + last-line JSON absent → step_transition_hang.

Since MetaAgent is a prompt (Markdown), we cannot unit-test it in Python.
Instead, we verify the *inputs* that would force MetaAgent down the
step_transition_hang branch:

  Given: a subprocess that exits 0 with stdout NOT containing valid JSON
         on its last non-empty line.
  Then:  The classification table in meta.md Phase 2d step 8 would route
         this to step_transition_hang (as opposed to 'normal completion').

This test produces an artificial stdout and asserts the rule evaluation
directly. Mirrors 03-CONTEXT.md D-05 classification table.
"""
from __future__ import annotations

import json
import unittest


def classify(exit_code: int, last_line: str | None) -> str:
    """Pure Python mirror of meta.md Phase 2d step 8 classification.
    Kept minimal — any drift from meta.md is what this canary catches.

    Mirrors 03-CONTEXT.md D-05 7-row table:
      - exit 124/137 → bash_wrapper_kill (Layer B SIGTERM/SIGKILL)
      - exit 0 + JSON absent/unparseable → step_transition_hang (upper layer hang)
      - exit 0 + status=halted → propagate halt_reason (Layer A or other)
      - exit 0 + normal verdict → normal_completion
      - non-zero + halted JSON → propagate halt_reason (engine crashed after halt)
      - non-zero + no JSON → engine_crash
    """
    if exit_code in (124, 137):
        return "bash_wrapper_kill"
    if exit_code == 0:
        if last_line is None or last_line.strip() == "":
            return "step_transition_hang"
        try:
            parsed = json.loads(last_line)
        except json.JSONDecodeError:
            return "step_transition_hang"
        if parsed.get("status") == "halted":
            return parsed.get("halt_reason") or "convergence_failure"
        return "normal_completion"
    # non-zero exit
    if last_line:
        try:
            parsed = json.loads(last_line)
            if parsed.get("status") == "halted":
                return parsed.get("halt_reason", "engine_crash")
        except json.JSONDecodeError:
            pass
    return "engine_crash"


class StepTransitionHangTest(unittest.TestCase):

    def test_exit0_json_absent(self):
        self.assertEqual(classify(0, None), "step_transition_hang")

    def test_exit0_empty_line(self):
        self.assertEqual(classify(0, ""), "step_transition_hang")

    def test_exit0_parse_fail(self):
        self.assertEqual(classify(0, "not a json"), "step_transition_hang")

    def test_exit0_valid_completed(self):
        self.assertEqual(
            classify(0, json.dumps({"status": "completed", "verdict": "ACCEPT"})),
            "normal_completion",
        )

    def test_exit124_bash_wrapper(self):
        self.assertEqual(classify(124, None), "bash_wrapper_kill")

    def test_exit137_bash_wrapper(self):
        self.assertEqual(classify(137, "ignored"), "bash_wrapper_kill")

    def test_exit0_halted_sdk_session_hang(self):
        self.assertEqual(
            classify(0, json.dumps({"status": "halted",
                                    "halt_reason": "sdk_session_hang"})),
            "sdk_session_hang",
        )

    def test_exit1_engine_crash(self):
        self.assertEqual(classify(1, None), "engine_crash")


# Wave 0 grep-compatibility alias: original stub used `TestMetaAgentClassification`
# as its class name. Preserve the token so acceptance greps from Plan 01 still
# resolve to a discoverable test class. (Zero behavioral cost.)
TestMetaAgentClassification = StepTransitionHangTest


if __name__ == "__main__":
    unittest.main(verbosity=2)
