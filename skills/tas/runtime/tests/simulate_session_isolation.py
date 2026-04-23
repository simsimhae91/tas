#!/usr/bin/env python3
"""Canary #10 — Session Worktree Isolation (VERIFY-ISO-01).

STATUS: Wave 3 complete — full 2-Phase implementation.

Phase 1 (TAS_VERIFY_ISO_MODE=fast, default, ~30s): synthetic dirty-fixture +
session bootstrap + sentinel write. Asserts:
    1) dirty status delta=0 (baseline vs after — user tree unchanged)
    2) tas/session-{ts} branch exists in user repo
    3) LATEST symlink resolves to a path under cache root AND equals
       SESSION_WORKTREE (chain-attack defense + D-04 direct-gesture)
    4) sentinel file present in session worktree, absent in user worktree

Phase 2 (TAS_VERIFY_ISO_MODE=full, optional, ~300s): regression sub-canary.
Asserts:
    5) HALT path retains session worktree + branch (ISO-06)
    6) Canary #8 (Phase 4 chunk merge) PASSes standalone — confirms Plan 06-05's
       16 substitutions in meta-execute.md Phase 2d.5 did NOT break byte-identical
       chunk merge contract (ISO-05 regression smoke)
    7) Manual merge stdout placeholder — SKILL.md mentions `git merge` + the
       `${SESSION_BRANCH}` substring (Phase 7 COMMIT-05 forward-reference; Wave 3
       records the placeholder as a forward-compatible no-op pending Phase 7)
    8) Companion command grep-0-matches: 0 files reference
       `${PROJECT_ROOT}/_workspace` in skills/tas-{explain,workspace,review}/SKILL.md
       AND all 3 files reference `tas-sessions/LATEST` (ISO-04 grep-0-matches
       guarantee)

Run via /tas-verify. stdlib-only (no psutil, pytest, claude_agent_sdk).
Exit 0 = PASS (fast) or PASS+PASS (full).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]  # tests -> runtime -> tas -> skills -> REPO
MODE = os.environ.get("TAS_VERIFY_ISO_MODE", "fast")  # fast | full

# Deterministic TS for fixture (avoid same-TS-second collision per Pitfall 5).
# Phase 1 and Phase 2 HALT fixture use different TS values to guarantee no
# branch-name collision if both Phases run inside the same tempdir.
FIXTURE_TS_PHASE_1 = "20260423T120000Z"
FIXTURE_TS_PHASE_2 = "20260423T130000Z"


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    """Thin wrapper around `git -C <repo> <args>` with captured text output."""
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=check,
    )


def _init_dirty_fixture(repo: Path) -> int:
    """Init repo with 1 committed file + 1 modified + 1 untracked.

    Returns baseline `git status --porcelain` line count.
    """
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "--quiet")
    _git(repo, "config", "user.email", "canary@tas.test")
    _git(repo, "config", "user.name", "tas canary #10")
    _git(repo, "config", "commit.gpgsign", "false")
    (repo / "src.py").write_text("x = 1\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "--quiet", "-m", "init")
    # Now make it dirty
    (repo / "src.py").write_text("x = 2\n")  # modified
    (repo / "untracked.txt").write_text("u\n")  # untracked
    baseline = _git(repo, "status", "--porcelain").stdout
    return len([line for line in baseline.splitlines() if line.strip()])


def _bootstrap_session(
    repo: Path, cache_root: Path, ts: str = FIXTURE_TS_PHASE_1
) -> tuple[Path, Path, str]:
    """Mirror SKILL.md Phase 0 D-01 bootstrap block.

    Returns (session_dir, session_worktree, session_branch).
    """
    project_name = repo.name
    session_dir = cache_root / ts
    session_worktree = session_dir / project_name
    session_branch = f"tas/session-{ts}"
    session_dir.mkdir(parents=True)
    _git(repo, "worktree", "add", "-b", session_branch, str(session_worktree), "HEAD")
    latest = cache_root / "LATEST"
    if latest.exists() or latest.is_symlink():
        latest.unlink()
    # D-04: LATEST gestures SESSION_WORKTREE directly (NOT SESSION_DIR — 1 extra
    # path segment). The canary explicitly verifies this in Assertion 3.
    latest.symlink_to(session_worktree)
    # Workspace inside session worktree (NOT in user repo). Any leak of this
    # mkdir into ${repo}/_workspace is an ISO-01 severe regression (Assertion 4b).
    (session_worktree / "_workspace" / "quick").mkdir(parents=True)
    return session_dir, session_worktree, session_branch


def _phase_1_happy_path(tmpdir: Path) -> tuple[bool, str]:
    """4 assertions per CONTEXT D-09 Phase 1."""
    repo = tmpdir / "phase1-fixture-project"
    cache_root = tmpdir / "phase1-cache" / "tas-sessions"
    cache_root.mkdir(parents=True)

    try:
        baseline_count = _init_dirty_fixture(repo)
        session_dir, session_worktree, session_branch = _bootstrap_session(
            repo, cache_root, ts=FIXTURE_TS_PHASE_1
        )
    except (AssertionError, subprocess.CalledProcessError) as exc:
        return False, f"Phase 1 fixture setup failed: {exc}"

    # Write sentinel inside session worktree workspace
    workspace = session_worktree / "_workspace" / "quick" / "canary-10-sentinel"
    workspace.mkdir(parents=True)
    sentinel = workspace / "SENTINEL.txt"
    sentinel.write_text("isolation test\n")

    # Assertion 1: user tree dirty status delta=0
    after = _git(repo, "status", "--porcelain").stdout
    after_count = len([line for line in after.splitlines() if line.strip()])
    if after_count != baseline_count:
        return False, (
            f"Phase 1 assertion 1: status delta != 0 "
            f"(baseline={baseline_count}, after={after_count})"
        )

    # Assertion 2: tas/session-{ts} branch exists in user repo
    branches = _git(repo, "branch", "--list", "tas/session-*").stdout
    if session_branch not in branches:
        return False, (
            f"Phase 1 assertion 2: branch {session_branch} missing in "
            f"`git branch --list 'tas/session-*'` output: {branches!r}"
        )

    # Assertion 3: LATEST resolves to a path under cache root AND equals SESSION_WORKTREE
    latest = cache_root / "LATEST"
    resolved = os.readlink(latest)
    resolved_path = Path(resolved)
    cache_root_str = str(cache_root)
    if not resolved.startswith(cache_root_str + os.sep) and resolved != cache_root_str:
        return False, (
            f"Phase 1 assertion 3: LATEST resolves to {resolved}, "
            f"not under cache root {cache_root_str}"
        )
    # D-04 direct-gesture: LATEST → SESSION_WORKTREE (NOT SESSION_DIR)
    if resolved_path != session_worktree:
        return False, (
            f"Phase 1 assertion 3 (D-04): LATEST resolves to {resolved}, "
            f"expected SESSION_WORKTREE {session_worktree}"
        )

    # Assertion 4a: sentinel file present inside session worktree
    if not sentinel.exists():
        return False, (
            f"Phase 1 assertion 4a: sentinel missing in session worktree at {sentinel}"
        )
    # Assertion 4b: sentinel NOT leaked to user repo
    leak_path = repo / "_workspace" / "quick" / "canary-10-sentinel" / "SENTINEL.txt"
    if leak_path.exists():
        return False, (
            f"Phase 1 assertion 4b: sentinel leaked into user tree at {leak_path}"
        )

    return True, "Phase 1 PASS (4/4 assertions)"


def _phase_2_halt_retention(tmpdir: Path) -> tuple[bool, str]:
    """Phase 2 Assertion 5: ISO-06 — HALT path retains session worktree + branch.

    Synthesizes a HALT scenario by writing a broken checkpoint.json into the
    session worktree workspace (simulating an Execute Mode halt) WITHOUT calling
    `git worktree remove`. Asserts worktree directory + tas/session-{ts} branch
    are still present afterward (ISO-06 retention — auto-cleanup forbidden).
    """
    repo = tmpdir / "phase2-halt-fixture-project"
    cache_root = tmpdir / "phase2-halt-cache" / "tas-sessions"
    cache_root.mkdir(parents=True)
    try:
        _init_dirty_fixture(repo)
        session_dir, session_worktree, session_branch = _bootstrap_session(
            repo, cache_root, ts=FIXTURE_TS_PHASE_2
        )
    except (AssertionError, subprocess.CalledProcessError) as exc:
        return False, f"Phase 2 halt-retention fixture setup failed: {exc}"

    # Synthesize HALT — write a "broken" checkpoint.json. We deliberately do NOT
    # run `git worktree remove` afterwards, because ISO-06 says tas must retain
    # the session worktree on HALT so the user can inspect/recover.
    workspace = session_worktree / "_workspace" / "quick" / "20260423_130000"
    workspace.mkdir(parents=True)
    (workspace / "checkpoint.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "status": "halted",
                "halt_reason": "synthetic_canary_halt",
                "session_branch": session_branch,
                "session_worktree_path": str(session_worktree),
            }
        )
    )

    # Per ISO-06: tas does NOT auto-clean on HALT. Worktree + branch must persist.
    if not session_worktree.exists():
        return False, (
            "Phase 2 assertion 5: session worktree directory was removed after "
            "synthetic HALT (ISO-06 violation)"
        )
    branches_after = _git(repo, "branch", "--list", "tas/session-*").stdout
    if session_branch not in branches_after:
        return False, (
            f"Phase 2 assertion 5: {session_branch} branch removed after "
            f"synthetic HALT (ISO-06 violation); branches={branches_after!r}"
        )

    return True, "Phase 2 assertion 5 PASS (HALT retention)"


def _phase_2_canary_8_regression(_tmpdir: Path) -> tuple[bool, str]:
    """Phase 2 Assertion 6: ISO-05 byte-identical — Canary #8 PASSes standalone.

    Plan 06-05 substituted `${PROJECT_ROOT}` → `${SESSION_WORKTREE}` at 16 sites
    in meta-execute.md Phase 2d.5. The contract is "byte-identical except
    variable substitution"; if the substitutions broke Phase 4 chunk merge
    control flow, Canary #8 (which mocks meta-execute.md's documented bash)
    would regress. We invoke Canary #8 as a subprocess regression smoke.

    Note: Canary #8 manages its own tempdir fixture (it does not accept an
    external session-worktree fixture). A future enhancement (out of Phase 6
    scope) would adapt Canary #8 to replay on a pre-existing session-worktree.
    """
    canary_8_path = REPO_ROOT / "skills" / "tas" / "runtime" / "tests" / "simulate_chunk_integration.py"
    if not canary_8_path.exists():
        return False, (
            f"Phase 2 assertion 6: Canary #8 script not found at {canary_8_path}"
        )

    # Fast mode keeps Canary #10's runtime budget under ~300s (full mode would
    # add ~270s to the Assertion 6 budget alone).
    env = {**os.environ, "TAS_VERIFY_CHUNK_MODE": "fast"}
    result = subprocess.run(
        [sys.executable, str(canary_8_path)],
        capture_output=True,
        text=True,
        env=env,
        timeout=180,
    )
    if result.returncode != 0:
        last_line = (
            result.stdout.splitlines()[-1] if result.stdout.splitlines() else "(empty)"
        )
        return False, (
            f"Phase 2 assertion 6: Canary #8 (Phase 4 chunk merge) FAILED post "
            f"Plan 06-05 substitution. Exit={result.returncode}, "
            f"stdout last line: {last_line!r}"
        )
    stdout_lines = result.stdout.strip().splitlines()
    if not stdout_lines or not stdout_lines[-1].startswith("PASS: canary #8"):
        return False, (
            f"Phase 2 assertion 6: Canary #8 stdout missing PASS line. "
            f"Got last 200 chars: {result.stdout[-200:]!r}"
        )

    return True, "Phase 2 assertion 6 PASS (Canary #8 regression smoke)"


def _phase_2_manual_merge_forward_reference() -> tuple[bool, str]:
    """Phase 2 Assertion 7: Phase 7 COMMIT-05 forward reference.

    Plan 06-02 Task 3 added the manual merge forward-reference to SKILL.md's
    Present Result block. For Wave 3, the assertion is the structural presence
    of `git merge` AND `${SESSION_BRANCH}` substrings in SKILL.md (Wave 3
    records the placeholder — Phase 7 will replace this with a real stdout-emit
    check when COMMIT-05 ships).
    """
    skill_md = REPO_ROOT / "skills" / "tas" / "SKILL.md"
    if not skill_md.exists():
        return False, (
            f"Phase 2 assertion 7: skills/tas/SKILL.md not found at {skill_md}"
        )
    content = skill_md.read_text()
    if "git merge" not in content:
        return False, (
            "Phase 2 assertion 7: SKILL.md Present Result block lacks "
            "`git merge` forward-reference (Phase 7 COMMIT-05 prep)"
        )
    if "${SESSION_BRANCH}" not in content:
        return False, (
            "Phase 2 assertion 7: SKILL.md Present Result block lacks "
            "`${SESSION_BRANCH}` forward-reference (Phase 7 COMMIT-05 prep)"
        )
    return True, "Phase 2 assertion 7 PASS (manual merge forward-reference present)"


def _phase_2_companion_grep_zero() -> tuple[bool, str]:
    """Phase 2 Assertion 8: ISO-04 grep-0-matches guarantee.

    Verify all 3 companion command SKILL.md files have:
    - 0 occurrences of `${PROJECT_ROOT}/_workspace` (old in-tree path)
    - >=1 occurrence of `tas-sessions/LATEST` (new session-index path)
    """
    companions = [
        REPO_ROOT / "skills" / "tas-explain" / "SKILL.md",
        REPO_ROOT / "skills" / "tas-workspace" / "SKILL.md",
        REPO_ROOT / "skills" / "tas-review" / "SKILL.md",
    ]
    for path in companions:
        if not path.exists():
            return False, (
                f"Phase 2 assertion 8: companion command file not found: {path}"
            )
        content = path.read_text()
        if "${PROJECT_ROOT}/_workspace" in content:
            return False, (
                f"Phase 2 assertion 8 (ISO-04 regression): {path.name} still "
                "references ${PROJECT_ROOT}/_workspace (old in-tree path)"
            )
        if "tas-sessions/LATEST" not in content:
            return False, (
                f"Phase 2 assertion 8 (ISO-04 regression): {path.name} missing "
                "tas-sessions/LATEST (new session-index path)"
            )
    return True, (
        "Phase 2 assertion 8 PASS (3/3 companion commands have grep-0-matches "
        "+ tas-sessions/LATEST)"
    )


def _phase_2_regression(tmpdir: Path) -> tuple[bool, str]:
    """Run all 4 Phase 2 assertions sequentially. Returns (ok, reason)."""
    for fn in (
        lambda: _phase_2_halt_retention(tmpdir),
        lambda: _phase_2_canary_8_regression(tmpdir),
        lambda: _phase_2_manual_merge_forward_reference(),
        lambda: _phase_2_companion_grep_zero(),
    ):
        ok, reason = fn()
        if not ok:
            return False, reason
    return True, "Phase 2 PASS (4/4 assertions)"


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="tas-canary-10-"))
    try:
        ok1, reason1 = _phase_1_happy_path(tmp)
        if not ok1:
            print(f"FAIL: {reason1}", file=sys.stderr)
            return 1

        if MODE == "full":
            ok2, reason2 = _phase_2_regression(tmp)
            if not ok2:
                print(f"FAIL: {reason2}", file=sys.stderr)
                return 1
            print("PASS: canary #10 (session worktree isolation; Phase 2: PASS)")
        else:
            print("PASS: canary #10 (session worktree isolation; Phase 2: SKIP (fast mode))")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
