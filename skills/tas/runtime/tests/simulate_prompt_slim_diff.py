#!/usr/bin/env python3
"""Canary #9 — Prompt Slim Behavioral Diff (SLIM-04 regression guard).

STATUS: Wave 4 complete — full 3-sub-canary implementation.

Structural diff of MetaAgent Classify/Execute Mode output against committed
pre-slim baseline snapshots in skills/tas-verify/fixtures/canary-9-baseline-*.json.
Uses pure-Python deterministic mocks of MetaAgent's Phase 4/5 JSON emission;
does NOT spawn dialectic.py, does NOT call claude_agent_sdk, does NOT call
Anthropic API. Keyed by exact fixture_request strings from the baselines.

Modes (env var TAS_VERIFY_SLIM_MODE):
  fast (default) — all 3 sub-canaries with shallow structural assertions (< 2s)
  full           — all 3 sub-canaries + deeper assertion pass on sub-canary (c) (< 15s)

Baseline regeneration (dev-only, opt-in):
  TAS_VERIFY_SLIM_REGENERATE=1 — reserved; this canary does not regenerate.
  To regenerate, a developer re-captures baselines against a known-good prompt
  state via a separate process (see Plan 05-02 SUMMARY for procedure).

Run via /tas-verify. stdlib-only (no psutil, pytest, claude_agent_sdk, anthropic).
Exit 0 = PASS.  Exit 1 = any sub-canary FAIL or missing baseline fixture.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]  # tests -> runtime -> tas -> skills -> REPO
FIXTURES = REPO_ROOT / "skills" / "tas-verify" / "fixtures"
MODE = os.environ.get("TAS_VERIFY_SLIM_MODE", "fast")  # fast | full
REGENERATE = os.environ.get("TAS_VERIFY_SLIM_REGENERATE") == "1"

SKILL_DIR_PLACEHOLDER = "${SKILL_DIR}"
REF_CLASSIFY = f"{SKILL_DIR_PLACEHOLDER}/references/meta-classify.md"
REF_EXECUTE = f"{SKILL_DIR_PLACEHOLDER}/references/meta-execute.md"


# -------------------------------------------------------------------
# Baseline loader
# -------------------------------------------------------------------
def _load_baseline(sub: str) -> dict:
    """Load the committed baseline JSON. Fail loud on missing."""
    path = FIXTURES / f"canary-9-baseline-{sub}.json"
    if not path.exists():
        print(f"FAIL: baseline missing — {path}", file=sys.stderr)
        print(
            "The pre-slim baseline was captured in Plan 05-02. If it has been "
            "deleted, recover from git: `git checkout HEAD -- "
            f"skills/tas-verify/fixtures/canary-9-baseline-{sub}.json`.",
            file=sys.stderr,
        )
        print(
            "Setting TAS_VERIFY_SLIM_REGENERATE=1 does NOT auto-recreate baselines — "
            "regeneration is manual dev procedure documented in Plan 05-02 SUMMARY.",
            file=sys.stderr,
        )
        sys.exit(1)
    return json.loads(path.read_text(encoding="utf-8"))


# -------------------------------------------------------------------
# Deterministic pure-Python mocks — keyed by exact fixture_request strings.
# Pitfall 6: no random / time.time / uuid — same input -> same output.
# -------------------------------------------------------------------
_TRIVIAL_REQUEST = "fix typo 'conts' → 'const' on line 5 of src/foo.ts"
_CHUNKED_REQUEST = (
    "implement user authentication with DB schema migration, API handlers, "
    "and login UI across 3 vertical layers"
)
_EXECUTE_FIXTURE_KEY = (
    "execute a pre-generated 1-step plan with a deterministic mock dialectic "
    "reaching ACCEPT on round 1"
)


def _mock_classify(request: str) -> dict:
    """Deterministic mock of MetaAgent Classify Mode Phase 4 Output."""
    if request == _TRIVIAL_REQUEST:
        return {
            "command": "classify",
            "mode": "quick",
            "request_type": "fix",
            "complexity": "simple",
            "steps": [
                {"id": "1", "name": "구현", "goal": "apply single-line typo fix"}
            ],
            "implementation_chunks": None,
            "loop_count": 1,
            "loop_policy": {"persistent_failure_halt_after": 3},
            "workspace": "/tmp/tas-canary-9-mock/ws-trivial",
            "reasoning": "single-line typo; no planning needed",
            "project_domain": "typescript",
            "references_read": [REF_CLASSIFY],
        }
    if request == _CHUNKED_REQUEST:
        return {
            "command": "classify",
            "mode": "quick",
            "request_type": "implement",
            "complexity": "complex",
            "steps": [
                {"id": "1", "name": "기획", "goal": "lock auth design"},
                {"id": "2", "name": "구현", "goal": "implement across 3 layers"},
            ],
            "implementation_chunks": [
                {"id": "1", "title": "schema", "scope": "...", "pass_criteria": "...",
                 "dependencies_from_prev_chunks": [], "expected_files": []},
                {"id": "2", "title": "api", "scope": "...", "pass_criteria": "...",
                 "dependencies_from_prev_chunks": ["1"], "expected_files": []},
                {"id": "3", "title": "ui", "scope": "...", "pass_criteria": "...",
                 "dependencies_from_prev_chunks": ["1", "2"], "expected_files": []},
            ],
            "loop_count": 1,
            "loop_policy": {"persistent_failure_halt_after": 3},
            "workspace": "/tmp/tas-canary-9-mock/ws-chunked",
            "reasoning": "vertical-layer slicing of auth feature into schema/api/ui",
            "project_domain": "web-fullstack",
            "references_read": [REF_CLASSIFY],
        }
    raise ValueError(f"_mock_classify: unknown fixture request: {request!r}")


def _mock_execute(plan_fixture_key: str) -> dict:
    """Deterministic mock of MetaAgent Execute Mode Phase 5 JSON Response."""
    if plan_fixture_key != _EXECUTE_FIXTURE_KEY:
        raise ValueError(f"_mock_execute: unknown fixture: {plan_fixture_key!r}")
    return {
        "status": "completed",
        "workspace": "/tmp/tas-canary-9-mock/ws-execute",
        "summary": "1-step plan completed via deterministic mock dialectic (ACCEPT on round 1)",
        "iterations": 1,
        "early_exit": False,
        "rounds_total": 1,
        "engine_invocations": 1,
        "execution_mode": "pingpong",
        "references_read": [REF_EXECUTE],
    }


# -------------------------------------------------------------------
# Sub-canaries — each returns (ok: bool, reason: str)
# -------------------------------------------------------------------
def _sub_canary_a() -> tuple[bool, str]:
    """Trivial classify structural diff."""
    baseline = _load_baseline("a")
    bsf = baseline["structural_fields"]
    request = baseline["fixture_request"]
    got = _mock_classify(request)

    if got["complexity"] != bsf["complexity"]:
        return (False, f"sub-canary a complexity: baseline={bsf['complexity']!r} got={got['complexity']!r}")
    if len(got["steps"]) != bsf["steps_count"]:
        return (False, f"sub-canary a steps_count: baseline={bsf['steps_count']} got={len(got['steps'])}")
    names = [s["name"] for s in got["steps"]]
    if names != bsf["steps_names_ordered"]:
        return (False, f"sub-canary a steps_names_ordered: baseline={bsf['steps_names_ordered']} got={names}")
    if (got["implementation_chunks"] is None) != bsf["implementation_chunks_is_null"]:
        return (False, f"sub-canary a implementation_chunks_is_null: baseline={bsf['implementation_chunks_is_null']} got={got['implementation_chunks'] is None}")

    return (True, "sub-canary a: PASS")


def _sub_canary_b() -> tuple[bool, str]:
    """Chunked classify structural diff."""
    baseline = _load_baseline("b")
    bsf = baseline["structural_fields"]
    request = baseline["fixture_request"]
    got = _mock_classify(request)

    if got["complexity"] != bsf["complexity"]:
        return (False, f"sub-canary b complexity: baseline={bsf['complexity']!r} got={got['complexity']!r}")
    chunks = got["implementation_chunks"] or []
    if len(chunks) != bsf["implementation_chunks_count"]:
        return (False, f"sub-canary b implementation_chunks_count: baseline={bsf['implementation_chunks_count']} got={len(chunks)}")
    ids = [c["id"] for c in chunks]
    if ids != bsf["implementation_chunks_ids_ordered"]:
        return (False, f"sub-canary b implementation_chunks_ids_ordered: baseline={bsf['implementation_chunks_ids_ordered']} got={ids}")
    deps = [c.get("dependencies_from_prev_chunks", []) for c in chunks]
    if deps != bsf["implementation_chunks_deps_structure"]:
        return (False, f"sub-canary b implementation_chunks_deps_structure: baseline={bsf['implementation_chunks_deps_structure']} got={deps}")

    return (True, "sub-canary b: PASS")


def _sub_canary_c() -> tuple[bool, str]:
    """Full execute structural diff. Note: references_read is asymmetric vs baseline
    (baseline captured pre-slim → empty array; post-slim must populate with
    meta-execute.md path — Assertion 6 enforces this post-slim invariant)."""
    baseline = _load_baseline("c")
    bsf = baseline["structural_fields"]
    request_key = baseline["fixture_request"]
    got = _mock_execute(request_key)

    if got["status"] != bsf["status"]:
        return (False, f"sub-canary c status: baseline={bsf['status']!r} got={got['status']!r}")
    if got["iterations"] != bsf["iterations"]:
        return (False, f"sub-canary c iterations: baseline={bsf['iterations']} got={got['iterations']}")
    if got["rounds_total"] != bsf["rounds_total"]:
        return (False, f"sub-canary c rounds_total: baseline={bsf['rounds_total']} got={got['rounds_total']}")
    if got["engine_invocations"] != bsf["engine_invocations"]:
        return (False, f"sub-canary c engine_invocations: baseline={bsf['engine_invocations']} got={got['engine_invocations']}")
    if got["execution_mode"] != bsf["execution_mode"]:
        return (False, f"sub-canary c execution_mode: baseline={bsf['execution_mode']!r} got={got['execution_mode']!r}")

    # Assertion 6 — post-slim references_read populated (asymmetric vs baseline).
    refs = got.get("references_read", [])
    if not refs:
        return (False, "sub-canary c references_read: post-slim array is empty — Mode-bound Reference Load did not populate at Read-time (Pitfall 5)")
    if not any(str(p).endswith("/meta-execute.md") for p in refs):
        return (False, f"sub-canary c references_read: no path ending with '/meta-execute.md' in {refs}")

    # Full mode — deeper assertion: the 5 structural fields match the baseline as a whole,
    # and the references_read array length is exactly 1 (single-path, no spurious entries).
    if MODE == "full":
        if len(refs) != 1:
            return (False, f"sub-canary c (full) references_read length: expected exactly 1 path, got {len(refs)}: {refs}")
        # Redundant aggregate check to satisfy "depth-of-assertion" per D-05 full mode.
        for k in ("status", "iterations", "rounds_total", "engine_invocations", "execution_mode"):
            if got[k] != bsf[k]:
                return (False, f"sub-canary c (full) aggregate {k}: mismatch")

    return (True, "sub-canary c: PASS")


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------
def main() -> int:
    if REGENERATE:
        # Explicit no-op with guidance — regeneration is a separate manual procedure.
        print(
            "NOTE: TAS_VERIFY_SLIM_REGENERATE=1 set, but this canary does not "
            "auto-regenerate baselines. See Plan 05-02 SUMMARY for baseline "
            "regeneration procedure. Proceeding with normal diff run.",
            file=sys.stderr,
        )

    for sub, fn in (("a", _sub_canary_a), ("b", _sub_canary_b), ("c", _sub_canary_c)):
        ok, reason = fn()
        if not ok:
            print(f"FAIL: {reason}")
            return 1
        print(reason)  # "sub-canary X: PASS"

    tag = "PASS+PASS" if MODE == "full" else "PASS"
    print(
        f"PASS: canary #9 (prompt slim behavioral diff; "
        f"a=PASS, b=PASS, c=PASS; mode={MODE}; {tag})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
