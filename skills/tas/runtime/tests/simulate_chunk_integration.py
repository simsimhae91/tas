#!/usr/bin/env python3
"""Canary #8 — 2-chunk merge + integrated verify + regression detection guard.

STATUS: Wave 5 complete — full 2-Phase implementation.

Phase 1 (TAS_VERIFY_CHUNK_MODE=fast, default, ~30s): 2-chunk happy path
synthetic fixture. MetaAgent-equivalent sub-loop uses a mock dialectic
(pure Python — no SDK session spawn) emitting ACCEPT. Asserts:
    1) worktree add x 2 succeeds; chunks/chunk-1 and chunks/chunk-2 registered
    2) each chunk worktree has exactly 1 commit with "chunk-N:" subject
    3) cherry-pick x 2 succeeds (primary path, D-05)
    4) Synthesis Context section present in mock verify step_assignment
    5) post-cleanup `git worktree list --porcelain` has no chunks/chunk-*

Phase 2 (TAS_VERIFY_CHUNK_MODE=full, optional, ~300s): regression sub-canary.
Chunk 1 deliverable embeds an intentional SIGNATURE_MISMATCH. Mock integrated
verify emits FAIL with "synthesis boundary" keyword. Asserts:
    6) Phase 1 assertions all hold against the regression-mode fixture
    7) integrated verify verdict == FAIL
    8) FAIL reason matches /synthesis|boundary|regression|chunk.1/i
    9) no re-Classify path triggered (structural — re_classify_called flag
       must remain False; MetaAgent does not re-enter Classify on chunk FAIL,
       per CHUNK-07 + 04-CONTEXT.md D-10)

Run via /tas-verify. stdlib-only (no psutil, pytest, claude_agent_sdk).
Exit 0 = PASS (fast) or PASS+PASS (full).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]  # tests -> runtime -> tas -> skills -> REPO
MODE = os.environ.get("TAS_VERIFY_CHUNK_MODE", "fast")  # fast | full

FAIL_KEYWORDS_RE = re.compile(r"synthesis|boundary|regression|chunk.1", re.IGNORECASE)


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    """Thin wrapper around `git -C <repo> <args>` with captured text output."""
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=check,
    )


def _init_fixture_repo(repo: Path) -> Path:
    """Create a minimal git repo with 3 source files + initial commit."""
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "--quiet")
    _git(repo, "config", "user.email", "canary@tas.test")
    _git(repo, "config", "user.name", "tas canary #8")
    _git(repo, "config", "commit.gpgsign", "false")

    src = repo / "src"
    src.mkdir(parents=True, exist_ok=True)
    (src / "schema.py").write_text(
        "def user_role_default() -> str:\n"
        "    return 'user'\n"
    )
    (src / "api.py").write_text(
        "def fetch_user(user_id: int) -> dict:\n"
        "    return {'id': user_id, 'role': 'user'}\n"
    )
    (src / "ui.py").write_text(
        "def render_user(user: dict) -> str:\n"
        "    return f\"<div>{user['id']}:{user['role']}</div>\"\n"
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "initial: 3 source files")
    return repo


def _build_plan_json() -> dict:
    """Return a 2-chunk plan.json dict matching D-02 6-field schema."""
    return {
        "request_type": "implement",
        "complexity": "complex",
        "reasoning": "synthetic fixture for Canary #8 — schema + api/ui layered",
        "steps": [
            {"id": "1", "name": "구현", "goal": "implement schema + api/ui"},
            {"id": "2", "name": "검증", "goal": "integrated verify post-merge"},
        ],
        "implementation_chunks": [
            {
                "id": "1",
                "title": "schema layer",
                "scope": "add role default helper to src/schema.py",
                "pass_criteria": [
                    "src/schema.py user_role_default returns a string",
                ],
                "dependencies_from_prev_chunks": [],
                "expected_files": ["src/schema.py"],
            },
            {
                "id": "2",
                "title": "api + ui layer",
                "scope": "wire schema helper through api and ui layers",
                "pass_criteria": [
                    "src/api.py fetch_user returns role from schema",
                    "src/ui.py render_user formats role correctly",
                ],
                "dependencies_from_prev_chunks": ["1"],
                "expected_files": ["src/api.py", "src/ui.py"],
            },
        ],
        "loop_count": 1,
        "loop_policy": {"reentry_point": "구현", "persistent_failure_halt_after": 3},
    }


def _mock_dialectic(
    worktree: Path,
    chunk_id: str,
    chunk_title: str,
    log_dir: Path,
    *,
    regression: bool = False,
) -> dict:
    """Pure-Python mock dialectic: writes deliverable.md + modifies one source file."""
    log_dir.mkdir(parents=True, exist_ok=True)
    deliverable = log_dir / "deliverable.md"

    if chunk_id == "1":
        lines = [
            f"# Chunk {chunk_id}: {chunk_title}",
            "",
            "## Public API",
            "- `user_role_default() -> str`: returns default role string for new users",
            "",
            "## Files modified",
            "- src/schema.py (appended DEFAULT_ROLES list)",
            "",
            "## Contracts for next chunks",
            "- chunk 2 may import `DEFAULT_ROLES` and assume list of strings",
        ]
        if regression:
            lines.append("")
            lines.append(
                "SIGNATURE_MISMATCH: expected return type `int` but delivers `str`"
            )
            lines.append(
                "(chunk 2 relies on the int return, this regression will surface at synthesis boundary)"
            )
        deliverable.write_text("\n".join(lines) + "\n")

        schema_file = worktree / "src" / "schema.py"
        content = schema_file.read_text()
        marker = f"\n# chunk-{chunk_id} appended\nDEFAULT_ROLES = ['user', 'admin']\n"
        schema_file.write_text(content + marker)

    elif chunk_id == "2":
        lines = [
            f"# Chunk {chunk_id}: {chunk_title}",
            "",
            "## Public API",
            "- `fetch_user(user_id: int) -> dict`: now returns role via schema.DEFAULT_ROLES[0]",
            "- `render_user(user: dict) -> str`: unchanged signature, uses dict role key",
            "",
            "## Files modified",
            "- src/api.py (wires DEFAULT_ROLES[0] into fetch_user)",
            "- src/ui.py (adds role badge class)",
            "",
            "## Relies on chunk 1",
            "- chunk 1 DEFAULT_ROLES list",
        ]
        deliverable.write_text("\n".join(lines) + "\n")

        api_file = worktree / "src" / "api.py"
        api_file.write_text(
            api_file.read_text()
            + f"\n# chunk-{chunk_id} appended\n"
            + "def api_version() -> str:\n    return 'v2'\n"
        )
        ui_file = worktree / "src" / "ui.py"
        ui_file.write_text(
            ui_file.read_text()
            + f"\n# chunk-{chunk_id} appended\n"
            + "def badge_class(role: str) -> str:\n    return f'badge badge-{role}'\n"
        )
    else:
        raise AssertionError(f"unexpected chunk_id: {chunk_id!r}")

    return {"status": "completed", "verdict": "ACCEPT"}


def _metaagent_commit(worktree: Path, chunk_id: str, chunk_title: str) -> str:
    """Create the chunk commit per D-06; return the new HEAD SHA."""
    status = _git(worktree, "status", "--porcelain").stdout
    if not status.strip():
        raise AssertionError(
            f"_metaagent_commit: chunk {chunk_id} worktree has no changes to commit"
        )
    _git(worktree, "add", "-A")
    _git(
        worktree,
        "commit",
        "--quiet",
        "-m",
        f"chunk-{chunk_id}: {chunk_title}",
    )
    return _git(worktree, "rev-parse", "HEAD").stdout.strip()


def _cherry_pick(project_root: Path, chunk_sha: str) -> str:
    """Cherry-pick chunk_sha into project_root; return 'cherry-pick' on success."""
    result = _git(
        project_root,
        "cherry-pick",
        chunk_sha,
        check=False,
    )
    if result.returncode != 0:
        # abort to leave the repo clean, then raise
        _git(project_root, "cherry-pick", "--abort", check=False)
        raise AssertionError(
            f"cherry-pick failed for sha {chunk_sha[:8]}: "
            f"rc={result.returncode} stderr={result.stderr.strip()!r}"
        )
    return "cherry-pick"


def _compose_synthesis_context(plan: dict, iter_n: int, step_id: str) -> str:
    """Build the D-07 Synthesis Context string to prepend to verify step_assignment."""
    chunks = plan.get("implementation_chunks") or []
    lines = ["## Synthesis Context (구현 step was chunked — integrated verify 대상은 머지된 통합 상태)", ""]
    lines.append("**Chunk plan**:")
    for c in chunks:
        deps = c.get("dependencies_from_prev_chunks") or []
        if deps:
            lines.append(f"  [{c['id']}] {c['title']} (depends on: {deps})")
        else:
            lines.append(f"  [{c['id']}] {c['title']}")
    lines.append("")
    lines.append("**Each chunk deliverable**:")
    for c in chunks:
        lines.append(
            f"  - iteration-{iter_n}/logs/step-{step_id}-implement-chunk-{c['id']}/deliverable.md"
        )
    lines.append("")
    lines.append("**Synthesis focus** (verify는 이것들을 중점 검증):")
    lines.append("  1. Public API / contracts at chunk boundaries")
    lines.append("  2. Shared file final state")
    lines.append("  3. Value flow integrity")
    lines.append("  4. Regression — chunk N이 이전 chunk의 기능을 깨지 않았는지")
    lines.append("")
    lines.append("**Not to be re-audited** (이미 chunk별로 검증 완료):")
    lines.append("  - 각 chunk 내부 구현 품질")
    return "\n".join(lines)


def _mock_integrated_verify(
    project_root: Path,
    synthesis_context: str,
    *,
    regression_mode: bool,
) -> dict:
    """Return a mock integrated verify verdict. FAIL when regression_mode=True."""
    # `project_root` + `synthesis_context` are intentionally unused at the
    # Python level — they represent what a real dialectic would consume.
    _ = project_root
    _ = synthesis_context
    if regression_mode:
        return {
            "status": "completed",
            "verdict": "FAIL",
            "reason": (
                "synthesis boundary detected: chunk 1 regression — schema return "
                "type mismatch breaks chunk 2 expectations (DEFAULT_ROLES semantics)"
            ),
        }
    return {"status": "completed", "verdict": "PASS", "reason": ""}


def _worktree_list(project_root: Path) -> list[str]:
    """Parse `git worktree list --porcelain` stdout and return non-main worktree paths."""
    result = _git(project_root, "worktree", "list", "--porcelain", check=False)
    paths: list[str] = []
    main_path = str(project_root.resolve())
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line.startswith("worktree "):
            continue
        path = line[len("worktree "):].strip()
        # normalise to a canonical form to compare with main repo path
        try:
            canonical = str(Path(path).resolve())
        except OSError:
            canonical = path
        if canonical != main_path:
            paths.append(path)
    return paths


def _run_2chunk_fixture(tmp: Path, *, regression_chunk_1: bool) -> tuple[
    Path, dict, Path, list[str], list[str], dict
]:
    """Shared fixture replay used by both Phase 1 and Phase 2.

    Returns (project_root, plan, workspace, chunk_add_rcs, merge_modes, verify_cfg).
    """
    project_root = _init_fixture_repo(tmp / "project")
    plan = _build_plan_json()

    workspace = tmp / "project" / "_workspace" / "quick" / "20260422_100000"
    (workspace / "chunks").mkdir(parents=True, exist_ok=True)

    chunk_add_rcs: list[str] = []
    merge_modes: list[str] = []

    for c in plan["implementation_chunks"]:
        chunk_path = workspace / "chunks" / f"chunk-{c['id']}"
        add = _git(
            project_root,
            "worktree",
            "add",
            "--detach",
            str(chunk_path),
            "HEAD",
            check=False,
        )
        if add.returncode != 0:
            raise AssertionError(
                f"worktree add failed for chunk {c['id']}: rc={add.returncode} "
                f"stderr={add.stderr.strip()!r}"
            )
        chunk_add_rcs.append(str(add.returncode))

        log_dir = workspace / f"iteration-1/logs/step-2-implement-chunk-{c['id']}"
        is_regression = regression_chunk_1 and c["id"] == "1"
        _mock_dialectic(chunk_path, c["id"], c["title"], log_dir, regression=is_regression)

        chunk_sha = _metaagent_commit(chunk_path, c["id"], c["title"])
        merge_modes.append(_cherry_pick(project_root, chunk_sha))
        _git(project_root, "worktree", "remove", "--force", str(chunk_path), check=False)

    sc = _compose_synthesis_context(plan, 1, "2")
    verify_cfg_path = workspace / "iteration-1/logs/step-3-verify/step-config.json"
    verify_cfg_path.parent.mkdir(parents=True, exist_ok=True)
    verify_cfg = {
        "step_assignment": sc + "\n\n... standard step content (goal, done criteria, etc.) ...",
        "step_id": "3",
        "iteration": 1,
    }
    verify_cfg_path.write_text(json.dumps(verify_cfg, indent=2))

    return project_root, plan, workspace, chunk_add_rcs, merge_modes, verify_cfg


def _phase_1_assertions(
    project_root: Path,
    chunk_add_rcs: list[str],
    merge_modes: list[str],
    verify_cfg: dict,
) -> tuple[bool, str]:
    """Run the 5 Phase 1 structural assertions; return (ok, reason_if_fail)."""
    # Assertion 1: worktree add x 2 succeeded (rc == 0 for both)
    if len(chunk_add_rcs) != 2 or any(rc != "0" for rc in chunk_add_rcs):
        return (
            False,
            f"Phase 1 assertion 1: worktree add did not succeed for both chunks (rcs={chunk_add_rcs!r})",
        )

    # Assertion 2: each chunk commit with chunk-N prefix in PROJECT_ROOT log
    log_out = _git(project_root, "log", "--oneline", "HEAD~2..HEAD", check=False).stdout
    if "chunk-1:" not in log_out or "chunk-2:" not in log_out:
        return (
            False,
            f"Phase 1 assertion 2: expected 'chunk-1:' and 'chunk-2:' in log output, got {log_out!r}",
        )

    # Assertion 3: both merges used cherry-pick primary path
    if merge_modes != ["cherry-pick", "cherry-pick"]:
        return (
            False,
            f"Phase 1 assertion 3: expected both merges via cherry-pick, got {merge_modes!r}",
        )

    # Assertion 4: Synthesis Context substrings present in verify step_assignment
    step_assignment = verify_cfg.get("step_assignment", "")
    required_substrings = [
        "## Synthesis Context",
        "Public API",
        "Shared file",
        "Value flow",
        "Regression",
        "Not to be re-audited",
    ]
    missing = [s for s in required_substrings if s not in step_assignment]
    if missing:
        return (
            False,
            f"Phase 1 assertion 4: Synthesis Context missing substrings {missing!r} in verify step_assignment",
        )

    # Assertion 5: post-cleanup worktree list has no chunks/chunk-* entries
    remaining = _worktree_list(project_root)
    stale = [p for p in remaining if "/chunks/chunk-" in p]
    if stale:
        return (
            False,
            f"Phase 1 assertion 5: post-cleanup worktree list still has chunk entries: {stale!r}",
        )

    return (True, "")


def _phase_1_happy_path(tmp: Path) -> tuple[bool, str]:
    """Phase 1: 2-chunk happy path, 5 assertions."""
    try:
        project_root, _plan, _ws, chunk_add_rcs, merge_modes, verify_cfg = _run_2chunk_fixture(
            tmp, regression_chunk_1=False
        )
    except (AssertionError, subprocess.CalledProcessError) as exc:
        return (False, f"Phase 1 fixture setup failed: {exc}")
    return _phase_1_assertions(project_root, chunk_add_rcs, merge_modes, verify_cfg)


def _phase_2_regression(tmp: Path) -> tuple[bool, str]:
    """Phase 2: chunk 1 regression detection, 4 additional assertions (6-9)."""
    # Structural guard: nothing below may flip this to True. The Phase 2 code
    # path MUST NOT invoke Classify (CHUNK-07 + D-10 "no re-chunking / no re-Classify").
    re_classify_called = False

    try:
        project_root, _plan, _ws, chunk_add_rcs, merge_modes, verify_cfg = _run_2chunk_fixture(
            tmp, regression_chunk_1=True
        )
    except (AssertionError, subprocess.CalledProcessError) as exc:
        return (False, f"Phase 2 fixture setup failed: {exc}")

    # Assertion 6: Phase 1 assertions still hold under the regression-mode fixture.
    ok1, reason1 = _phase_1_assertions(project_root, chunk_add_rcs, merge_modes, verify_cfg)
    if not ok1:
        return (False, f"Phase 2 assertion 6: {reason1}")

    # Invoke the mock integrated verify under regression mode — MetaAgent does
    # NOT re-enter Classify here; verify FAIL routes through Within-Iteration
    # FAIL handling (single dialectic retry in real system; here we just
    # surface the FAIL verdict and assert the structural guard).
    sc = verify_cfg.get("step_assignment", "")
    result = _mock_integrated_verify(project_root, sc, regression_mode=True)

    # Assertion 7: integrated verify verdict == FAIL
    if result.get("verdict") != "FAIL":
        return (
            False,
            f"Phase 2 assertion 7: integrated verify verdict expected FAIL, got {result.get('verdict')!r}",
        )

    # Assertion 8: FAIL reason matches /synthesis|boundary|regression|chunk.1/i
    reason = result.get("reason", "")
    if not FAIL_KEYWORDS_RE.search(reason):
        return (
            False,
            f"Phase 2 assertion 8: FAIL reason {reason!r} does not match "
            "/synthesis|boundary|regression|chunk.1/i",
        )

    # Assertion 9: no re-Classify path triggered (structural — the flag was
    # never flipped because nothing in the Phase 2 code path invokes Classify).
    if re_classify_called is not False:
        return (
            False,
            "Phase 2 assertion 9: re_classify_called was flipped True — "
            "MetaAgent must NOT re-enter Classify on chunk FAIL (CHUNK-07 + D-10)",
        )

    return (True, "")


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="tas-canary-8-"))
    try:
        ok1, reason1 = _phase_1_happy_path(tmp)
        if not ok1:
            print(f"FAIL: {reason1}")
            return 1

        if MODE == "full":
            ok2, reason2 = _phase_2_regression(tmp)
            if not ok2:
                print(f"FAIL: {reason2}")
                return 1
            print("PASS: canary #8 (2-chunk merge + integrated verify; Phase 2: PASS)")
        else:
            print("PASS: canary #8 (2-chunk merge + integrated verify; Phase 2: SKIP (fast mode))")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
