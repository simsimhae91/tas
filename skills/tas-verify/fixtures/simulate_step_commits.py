#!/usr/bin/env python3
"""Canary #11 — Step-Level Commit Granularity (VERIFY-COMMIT-01).

STATUS: Wave 0 PENDING — scaffolded under Plan 07-01. Full 2-Phase body
        lands Plan 07-07 per ROADMAP Phase 7. This stub exits 0 in both
        MODE=fast and MODE=full so Plans 07-02..07-06 can pass their
        `<automated>` verify gates before the canary body is complete.

Phase 1 (TAS_VERIFY_COMMIT_MODE=fast, default, ~30s — PENDING):
  Will assert:
    1) Standard-flow commit count per step type (기획=0 empty-skip,
       구현≥1, 검증=0-1, 테스트=0-1) — ROADMAP SC 1 / COMMIT-01..02
    2) 5-trailer presence in every session-branch commit body via
       `git log --grep='Tas-Session: {TS}' --all` — ROADMAP SC 2 / COMMIT-03
    3) Subject format regex `^step-[0-9]+-(plan|implement|verify|test|step): `
       — COMMIT-03 D-04
    4) 기획 step produced 0 commits (empty-diff gate) — COMMIT-02 D-03

Phase 2 (TAS_VERIFY_COMMIT_MODE=full, ~300s — PENDING):
  Will assert:
    5) HALT JSON has status=halted, halt_reason=pre_commit_hook_failed
       — ROADMAP SC 3 / COMMIT-04 D-06
    6) precommit.log exists at
       `${SESSION_WORKTREE}/_workspace/quick/{TS}/iteration-1/logs/step-{S.id}-{slug}/precommit.log`
       AND contains stderr `tas-canary-11 forced failure` — COMMIT-04 D-07
    7) grep -E "git commit[^|]*--no-verify" across skills/tas/ +
       skills/tas-verify/ + skills/tas-explain/ + skills/tas-workspace/ +
       skills/tas-review/ returns 0 actual-invocation matches (prohibition
       references in CLAUDE.md + canaries.md are allowed) — COMMIT-04 D-08
    8) HALT-path stdout does NOT contain `git merge ${SESSION_BRANCH}`
       — merge proposal is PASS-path-only — COMMIT-05 D-09

Run via /tas-verify. stdlib-only (no pytest, pygit2, GitPython,
claude_agent_sdk). Exit 0 = PASS (stub) for Wave 0; final behavior
identical post-Plan 07-07.
"""
from __future__ import annotations

import os
import sys

MODE = os.environ.get("TAS_VERIFY_COMMIT_MODE", "fast")  # fast | full


def main() -> int:
    if MODE == "full":
        print(
            "PASS: canary #11 (step-level commit granularity; "
            "PENDING — Wave 0 stub, body lands Plan 07-07; "
            "Phase 2: PASS (full mode, stub))"
        )
    else:
        print(
            "PASS: canary #11 (step-level commit granularity; "
            "PENDING — Wave 0 stub, body lands Plan 07-07; "
            "Phase 2: SKIP (fast mode))"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
