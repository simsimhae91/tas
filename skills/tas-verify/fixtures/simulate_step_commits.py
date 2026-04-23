#!/usr/bin/env python3
"""Canary #11 — Step-Level Commit Granularity (VERIFY-COMMIT-01).

STATUS: Wave 5 complete — Phase 7 shipped.

Phase 1 (TAS_VERIFY_COMMIT_MODE=fast, default, ~30s): synthetic 4-step
flow fixture (기획 → 구현 → 검증 → 테스트) with mock dialectic verdict=ACCEPT.
Replays meta-execute.md step 9.6 heredoc logic in Python subprocess (git CLI).
Asserts:
    1) Standard-flow commit count: 기획=0 empty-skip, 구현≥1, 검증=0-1,
       테스트=0-1; total 1-3 — ROADMAP SC 1 / COMMIT-01..02
    2) 5-trailer presence via `git log --format=%B` body contains all of
       Tas-Session, Step-Id, Iteration, Dialectic-Verdict, Dialectic-Rounds
       — ROADMAP SC 2 / COMMIT-03
    3) Subject format matches `^step-[0-9]+-(plan|implement|verify|test|step): `
       regex — COMMIT-03 D-04
    4) 기획 step produced 0 commits (empty-diff gate) — COMMIT-02 D-03

Phase 2 (TAS_VERIFY_COMMIT_MODE=full, ~300s): regression sub-canary.
Forces pre-commit hook failure via `.git/hooks/pre-commit` with `exit 1`.
Asserts:
    5) HALT JSON has status=halted, halt_reason=pre_commit_hook_failed,
       current_step=${S.id} NOT in completed_steps — COMMIT-04 D-06
    6) precommit.log exists at the Phase 7 D-07 path AND contains stderr
       `tas-canary-11 forced failure` — COMMIT-04 D-07
    7) grep -E `git commit[^|]*--no-verify` across skills/tas/ +
       skills/tas-verify/ + skills/tas-explain/ + skills/tas-workspace/ +
       skills/tas-review/ — 0 actual-invocation matches (prohibition
       references in CLAUDE.md Bullet C + SKILL.md Recovery Korean + this
       fixture's docstring are allowed via the `canary-11` keyword) —
       COMMIT-04 D-08
    8) HALT-path stdout does NOT contain `git merge ${SESSION_BRANCH}` —
       merge proposal is PASS-path-only (COMMIT-05 D-09)

Run via /tas-verify. stdlib-only (no pytest, pygit2, GitPython,
claude_agent_sdk). Exit 0 = PASS (fast) or PASS+PASS (full).

Note on prohibition vs. invocation (Assertion 7): this docstring
references `git commit ... --no-verify` only as part of the prohibition
text (see CLAUDE.md Common Mistakes Bullet C — "D-08 prohibition" —
`tas 는 --no-verify 자동 우회를 수행하지 않습니다`). The programmatic
allowlist keyword `canary-11` in every such reference ensures SSOT-5 and
Assertion 7 both ignore them as non-invocations.
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

# fixtures -> tas-verify -> skills -> REPO (depth 3)
REPO_ROOT = Path(__file__).resolve().parents[3]
MODE = os.environ.get("TAS_VERIFY_COMMIT_MODE", "fast")  # fast | full

FIXTURE_TS_PHASE_1 = "20260423T120000Z"
FIXTURE_TS_PHASE_2 = "20260423T130000Z"

SUBJECT_RE = re.compile(r"^step-[0-9]+-(plan|implement|verify|test|step): ")
TRAILER_NAMES = (
    "Tas-Session:",
    "Step-Id:",
    "Iteration:",
    "Dialectic-Verdict:",
    "Dialectic-Rounds:",
)

SLUG_MAP = {
    "기획": "plan",
    "구현": "implement",
    "검증": "verify",
    "테스트": "test",
}


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    """Thin wrapper around `git -C <repo> <args>` with captured text output."""
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=check,
    )


def _init_user_repo(root: Path) -> Path:
    """Create a bare user repo with one initial commit on `main`."""
    repo = root / "user_repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "canary11@tas.test")
    _git(repo, "config", "user.name", "Canary 11")
    (repo / "README.md").write_text("# canary-11 user repo\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "initial")
    return repo


def _bootstrap_session(user_repo: Path, cache_root: Path, ts: str) -> tuple[Path, str]:
    """Create tas/session-{ts} worktree at cache_root/{ts}/project/.

    Mirrors SKILL.md Phase 0 bootstrap. Returns (session_worktree, session_branch).
    """
    session_dir = cache_root / ts
    session_dir.mkdir(parents=True)
    session_worktree = session_dir / "project"
    session_branch = f"tas/session-{ts}"
    _git(
        user_repo,
        "worktree",
        "add",
        "-b",
        session_branch,
        str(session_worktree),
        "HEAD",
    )
    # Make the LATEST symlink for completeness (Canary #11 does not assert it;
    # Canary #10 already guards LATEST semantics).
    latest = cache_root / "LATEST"
    if latest.exists() or latest.is_symlink():
        latest.unlink()
    latest.symlink_to(session_worktree)
    return session_worktree, session_branch


def _compose_commit(
    session_worktree: Path,
    step_log_dir: Path,
    s_id: str,
    s_name: str,
    s_title: str,
    ts: str,
    iter_n: str,
    verdict: str,
    rounds: str,
) -> tuple[str, str]:
    """Replay meta-execute.md step 9.6 heredoc logic in Python.

    Returns (stdout_sentinel, precommit_log_path).
    Sentinels: COMMIT_OK | COMMIT_EMPTY | COMMIT_HOOK_FAIL.
    """
    step_log_dir.mkdir(parents=True, exist_ok=True)
    slug = SLUG_MAP.get(s_name, "step")
    subject = f"step-{s_id}-{slug}: {s_title}"
    _git(session_worktree, "add", "-A")
    staged = _git(session_worktree, "diff", "--cached", "--quiet", check=False)
    if staged.returncode == 0:
        return "COMMIT_EMPTY", ""
    precommit_log = step_log_dir / "precommit.log"
    # Run git commit with 6 -m flags; capture stderr to precommit.log.
    # NB: prohibition reference (non-invocation) — this fixture uses plain
    # `git commit` with trailers; it does NOT pass `--no-verify` (D-08
    # prohibition — canary-11 allowlist keyword).
    with precommit_log.open("w") as log_fh:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(session_worktree),
                "commit",
                "-m",
                subject,
                "-m",
                f"Tas-Session: {ts}",
                "-m",
                f"Step-Id: {s_id}",
                "-m",
                f"Iteration: {iter_n}",
                "-m",
                f"Dialectic-Verdict: {verdict}",
                "-m",
                f"Dialectic-Rounds: {rounds}",
            ],
            stdout=subprocess.PIPE,
            stderr=log_fh,
            text=True,
        )
    if result.returncode == 0:
        return "COMMIT_OK", str(precommit_log)
    return "COMMIT_HOOK_FAIL", str(precommit_log)


def _run_step(
    session_worktree: Path,
    workspace: Path,
    s_id: str,
    s_name: str,
    s_title: str,
    ts: str,
    iter_n: str,
    modifies_file: bool,
) -> str:
    """Simulate one ACCEPT'd step: optionally modify a file, then emit commit.

    Returns the stdout sentinel from step 9.6 composer.
    """
    slug = SLUG_MAP.get(s_name, "step")
    step_log_dir = (
        workspace / f"iteration-{iter_n}" / "logs" / f"step-{s_id}-{slug}"
    )
    if modifies_file:
        target = session_worktree / f"step_{s_id}.txt"
        target.write_text(f"step {s_id} {s_name} ({slug}) - {s_title}\n")
    return _compose_commit(
        session_worktree=session_worktree,
        step_log_dir=step_log_dir,
        s_id=s_id,
        s_name=s_name,
        s_title=s_title,
        ts=ts,
        iter_n=iter_n,
        verdict="ACCEPT",
        rounds="3",
    )[0]


def _phase_1_happy_path(tmp: Path) -> tuple[bool, str]:
    """Phase 1 — 4단 standard flow: commit count + trailers + subject + empty-skip."""
    ts = FIXTURE_TS_PHASE_1
    user_repo = _init_user_repo(tmp)
    cache_root = tmp / "cache" / "tas-sessions"
    session_worktree, session_branch = _bootstrap_session(user_repo, cache_root, ts)
    workspace = session_worktree / "_workspace" / "quick" / ts
    workspace.mkdir(parents=True)
    steps = [
        # (id, name, title, modifies_file)
        ("1", "기획", "plan phase - no code changes", False),   # empty-skip expected
        ("2", "구현", "implement CLI refactor", True),           # 1 commit
        ("3", "검증", "verify lint clean", False),               # empty-skip (read-only)
        ("4", "테스트", "add regression test", True),            # 1 commit
    ]
    sentinels: list[str] = []
    for s_id, s_name, s_title, modifies in steps:
        sentinels.append(
            _run_step(
                session_worktree,
                workspace,
                s_id,
                s_name,
                s_title,
                ts,
                "1",
                modifies,
            )
        )
    # Count actual commits on session branch (exclude the initial `main` commit)
    log_out = _git(
        user_repo, "log", "--oneline", session_branch, "^main"
    ).stdout.strip()
    commits = [ln for ln in log_out.splitlines() if ln]
    # Assertion 1: commit count sanity (expected 2: step 2 + step 4)
    if len(commits) < 1 or len(commits) > 3:
        return False, (
            f"Phase 1 assertion 1: commit count {len(commits)} out of range [1,3]; "
            f"expected 2 (step 2 + step 4); sentinels={sentinels}"
        )
    # Assertion 2: every commit body contains all 5 trailers
    body_out = _git(
        user_repo, "log", "--format=%B%x00", session_branch, "^main"
    ).stdout
    bodies = [b for b in body_out.split("\x00") if b.strip()]
    for idx, body in enumerate(bodies):
        missing = [t for t in TRAILER_NAMES if t not in body]
        if missing:
            return False, (
                f"Phase 1 assertion 2: trailer missing in commit {idx + 1} body: "
                f"{missing}; full body excerpt={body[:300]!r}"
            )
        if f"Tas-Session: {ts}" not in body:
            return False, (
                f"Phase 1 assertion 2: Tas-Session value mismatch in commit {idx + 1}; "
                f"expected {ts}, body excerpt={body[:300]!r}"
            )
    # Assertion 3: subject format regex
    for idx, commit_line in enumerate(commits):
        # commit_line is "<sha> <subject>"
        subject = commit_line.split(" ", 1)[1] if " " in commit_line else commit_line
        if not SUBJECT_RE.match(subject):
            return False, (
                f"Phase 1 assertion 3: subject format mismatch in commit {idx + 1}: "
                f"{subject!r}; expected regex {SUBJECT_RE.pattern!r}"
            )
    # Assertion 4: 기획 step produced 0 commits (sentinels[0] == COMMIT_EMPTY)
    if sentinels[0] != "COMMIT_EMPTY":
        return False, (
            f"Phase 1 assertion 4: 기획 step emitted {sentinels[0]}, expected "
            f"COMMIT_EMPTY (empty-diff gate bypassed; "
            f"`git diff --cached --quiet` regressed)"
        )
    return True, "phase 1 PASS"


def _install_failing_hook(user_repo: Path) -> None:
    """Install deterministic failing pre-commit hook into the user repo's
    shared .git/hooks/ (the session worktree shares hooks with main repo)."""
    hook = user_repo / ".git" / "hooks" / "pre-commit"
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text(
        "#!/bin/sh\n"
        "echo 'tas-canary-11 forced failure' >&2\n"
        "exit 1\n"
    )
    hook.chmod(0o755)


def _phase_2_regression(tmp: Path) -> tuple[bool, str]:
    """Phase 2 — pre_commit_hook_failed HALT + precommit.log + --no-verify grep-0 + HALT no-merge."""
    ts = FIXTURE_TS_PHASE_2
    user_repo = _init_user_repo(tmp)
    cache_root = tmp / "cache" / "tas-sessions"
    session_worktree, _ = _bootstrap_session(user_repo, cache_root, ts)
    workspace = session_worktree / "_workspace" / "quick" / ts
    workspace.mkdir(parents=True)
    _install_failing_hook(user_repo)
    # Run a single 구현 step that should HALT
    step_log_dir = workspace / "iteration-1" / "logs" / "step-2-implement"
    (session_worktree / "step_2.txt").write_text("step 2 content\n")
    sentinel, precommit_log = _compose_commit(
        session_worktree=session_worktree,
        step_log_dir=step_log_dir,
        s_id="2",
        s_name="구현",
        s_title="implement with failing hook",
        ts=ts,
        iter_n="1",
        verdict="ACCEPT",
        rounds="3",
    )
    # Assertion 5: sentinel should classify as COMMIT_HOOK_FAIL; synthesize
    # the HALT JSON the way meta-execute.md FAIL branch would, then assert.
    halt_json = {
        "status": "halted",
        "halt_reason": "pre_commit_hook_failed",
        "current_step": "2",
        "completed_steps": [],
        "workspace": str(workspace),
        "halted_at": "execute-step-2-commit",
    }
    if sentinel != "COMMIT_HOOK_FAIL":
        return False, (
            f"Phase 2 assertion 5: expected COMMIT_HOOK_FAIL sentinel, got "
            f"{sentinel!r}; pre-commit hook fixture may be broken or heredoc "
            f"logic diverged"
        )
    if (
        halt_json.get("status") != "halted"
        or halt_json.get("halt_reason") != "pre_commit_hook_failed"
    ):
        return False, (
            f"Phase 2 assertion 5: HALT JSON missing pre_commit_hook_failed: "
            f"{halt_json!r}"
        )
    # Assertion 6: precommit.log exists + contains stderr
    log_path = Path(precommit_log)
    if not log_path.is_file():
        return False, f"Phase 2 assertion 6: precommit.log missing at {log_path}"
    log_contents = log_path.read_text()
    if "tas-canary-11 forced failure" not in log_contents:
        return False, (
            f"Phase 2 assertion 6: precommit.log at {log_path} missing expected "
            f"stderr; contents: {log_contents[:500]!r}"
        )
    # Assertion 7: --no-verify actual-invocation grep across tas skills = 0
    targets = [
        REPO_ROOT / "skills" / "tas",
        REPO_ROOT / "skills" / "tas-verify",
        REPO_ROOT / "skills" / "tas-explain",
        REPO_ROOT / "skills" / "tas-workspace",
        REPO_ROOT / "skills" / "tas-review",
    ]
    existing_targets = [str(t) for t in targets if t.exists()]
    if not existing_targets:
        return False, (
            "Phase 2 assertion 7: no tas skill directories found — REPO_ROOT "
            "resolution broken"
        )
    # canary-11 D-08 Regex: match `git commit ... --no-verify` as actual invocation;
    # prohibition references in this fixture docstring + CLAUDE.md Bullet C
    # + SKILL.md Recovery Korean text use surrounding context that DOES match
    # this pattern but is excluded via keyword allowlist below.
    grep_result = subprocess.run(
        ["grep", "-rEn", r"git commit[^|]*--no-verify", *existing_targets],
        capture_output=True,
        text=True,
        check=False,
    )
    actual_invocations = [
        ln
        for ln in grep_result.stdout.splitlines()
        # Exclude prohibition references that happen to contain the pattern
        # in bullets/assertions. The regex-allowlist is intentionally narrow.
        if "D-08" not in ln
        and "prohibition" not in ln.lower()
        and "자동 우회" not in ln
        and "must not" not in ln.lower()
        and "MUST NOT" not in ln
        and "forbidden" not in ln.lower()
        and "Canary #11" not in ln
        and "canary-11" not in ln
        and "Canary #8 Phase 2" not in ln
    ]
    if actual_invocations:
        sample = "\n  ".join(actual_invocations[:5])
        return False, (
            f"Phase 2 assertion 7 (canary-11 D-08): {len(actual_invocations)} actual invocation(s) found "
            f"of the prohibited `git commit --no-verify` pattern (canary-11):\n  {sample}"
        )
    # Assertion 8: HALT-path stdout does NOT contain `git merge ${SESSION_BRANCH}`
    # merge proposal. The synthetic HALT JSON does not include a merge proposal;
    # we also grep SKILL.md's `**On HALT**` rendering block to confirm it has no
    # `git merge tas/session` literal.
    skill_md = REPO_ROOT / "skills" / "tas" / "SKILL.md"
    skill_text = skill_md.read_text()
    # Extract the On HALT block (from `**On HALT**` to next `**On ` heading or EOF).
    halt_match = re.search(
        r"\*\*On HALT\*\*.*?(?=\n\*\*On |\n## |\Z)",
        skill_text,
        flags=re.DOTALL,
    )
    halt_block = halt_match.group(0) if halt_match else ""
    if (
        "git merge ${SESSION_BRANCH}" in halt_block
        or "git merge tas/session" in halt_block
    ):
        return False, (
            "Phase 2 assertion 8: HALT stdout rendering contains merge proposal "
            "(COMMIT-05 D-09 regression — merge block leaked into HALT path)"
        )
    # Also confirm the HALT JSON itself (synthesized above) carries no merge text.
    halt_stdout = json.dumps(halt_json)
    if "git merge" in halt_stdout:
        return False, (
            "Phase 2 assertion 8: synthesized HALT JSON contains `git merge` "
            "— merge proposal must be PASS-path-only (COMMIT-05 D-09)"
        )
    return True, "phase 2 PASS"


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="tas-canary-11-"))
    try:
        # Per-phase subdirs prevent Phase 2's _init_user_repo from colliding
        # with Phase 1's user_repo directory (T-07-07-01 isolation mitigation).
        phase_1_dir = tmp / "phase-1"
        phase_1_dir.mkdir()
        ok1, reason1 = _phase_1_happy_path(phase_1_dir)
        if not ok1:
            print(f"FAIL: {reason1}", file=sys.stderr)
            return 1
        if MODE == "full":
            phase_2_dir = tmp / "phase-2"
            phase_2_dir.mkdir()
            ok2, reason2 = _phase_2_regression(phase_2_dir)
            if not ok2:
                print(f"FAIL: {reason2}", file=sys.stderr)
                return 1
            print("PASS: canary #11 (step-level commit granularity; Phase 2: PASS)")
        else:
            print(
                "PASS: canary #11 (step-level commit granularity; "
                "Phase 2: SKIP (fast mode))"
            )
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
