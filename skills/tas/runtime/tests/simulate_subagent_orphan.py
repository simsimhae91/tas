#!/usr/bin/env python3
"""Canary #7 — Subagent-spawned orphan survival + real-chain integration guard.

Automates EXPERIMENT-2 / EXPERIMENT-3v2 (FINDINGS-nohup-bg-pattern.md §2.3, §7)
and adds a Phase 2 integration sub-assertion that invokes the REAL
run-dialectic.sh with a mock dialectic script, verifying the EXIT trap fires
and markers are written — a regression guard for Phase 3.1 Plan Review Issue #1
(the `exec` keyword suppresses EXIT trap firing).

Run via /tas-verify. stdlib-only. Default DURATION=120 (CI); override via
TAS_VERIFY_TOPO_DURATION_SEC=1800 for extended manual runs (nightly).

Usage:
    python3 simulate_subagent_orphan.py
    TAS_VERIFY_TOPO_DURATION_SEC=10 python3 simulate_subagent_orphan.py  # smoke

Exit codes: 0 = PASS (Phase 1 green; Phase 2 green or SKIP), 1 = FAIL.
"""
from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]  # tests → runtime → tas → skills → REPO
RUN_SCRIPT = REPO_ROOT / "skills" / "tas" / "runtime" / "run-dialectic.sh"

DURATION = int(os.environ.get("TAS_VERIFY_TOPO_DURATION_SEC", "120"))
SUBAGENT_RETURN_BUDGET_SEC = 10          # fire-and-forget must return in <10s
PPID_CHECK_DELAY_SEC = 2                  # init reparenting window
MARKER_POLL_INTERVAL_SEC = 2
MARKER_TIMEOUT_MARGIN_SEC = 15            # DURATION + margin before we give up


def _pid_alive(pid: int) -> bool:
    """True iff we can signal the PID (kill -0 equivalent)."""
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # EPERM → PID exists but we don't own it; treat as alive (matches Bash
        # `kill -0` convention used by MetaAgent polling).
        return True


def _pid_ppid(pid: int) -> int:
    """Return PPID via `ps -o ppid= -p <pid>`. Returns -1 if PID not found."""
    try:
        out = subprocess.check_output(
            ["ps", "-o", "ppid=", "-p", str(pid)],
            stderr=subprocess.DEVNULL,
        ).decode().strip()
        return int(out) if out else -1
    except (subprocess.CalledProcessError, ValueError):
        return -1


def _mock_subagent_spawn(marker_path: Path, log_path: Path, duration: int) -> tuple[int, float]:
    """Simulate a subagent that fires-and-forgets an orphan via nohup + &.

    Returns (pid, elapsed_seconds). Raises on spawn failure or missing PID.
    """
    cmd = (
        f"nohup bash -c 'sleep {duration}; echo survived > {marker_path}' "
        f"> {log_path} 2>&1 & echo $!"
    )
    t0 = time.monotonic()
    result = subprocess.run(
        ["bash", "-c", cmd],
        capture_output=True,
        text=True,
        timeout=SUBAGENT_RETURN_BUDGET_SEC + 5,
        check=False,
    )
    elapsed = time.monotonic() - t0

    if result.returncode != 0:
        raise RuntimeError(
            f"mock subagent spawn failed: rc={result.returncode}, stderr={result.stderr!r}"
        )
    pid_str = result.stdout.strip()
    try:
        pid = int(pid_str)
    except ValueError:
        raise RuntimeError(f"mock subagent did not emit integer PID: stdout={result.stdout!r}")
    return pid, elapsed


def _cleanup_pid(pid: int) -> None:
    """Best-effort kill of the orphan (no-op if already terminated)."""
    try:
        os.kill(pid, signal.SIGTERM)
        time.sleep(0.5)
        if _pid_alive(pid):
            os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except PermissionError:
        pass


def _phase_1_orphan_survival(tmpdir: Path) -> tuple[bool, int]:
    """Run Phase 1. Returns (passed, spawned_pid_for_cleanup).

    Prints FAIL messages if any assertion fails; returns (False, pid) in that case.
    On success returns (True, pid) with pid already dead (marker written).
    """
    marker = tmpdir / "marker.txt"
    log = tmpdir / "mock.log"
    try:
        pid, elapsed = _mock_subagent_spawn(marker, log, DURATION)
    except (RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"FAIL: Phase 1 mock subagent spawn error: {exc}")
        return (False, -1)

    if elapsed >= SUBAGENT_RETURN_BUDGET_SEC:
        print(
            f"FAIL: Phase 1 mock subagent duration {elapsed:.2f}s >= {SUBAGENT_RETURN_BUDGET_SEC}s "
            f"(fire-and-forget contract broken — nohup/& elements may be missing)"
        )
        return (False, pid)

    time.sleep(PPID_CHECK_DELAY_SEC)
    if not _pid_alive(pid):
        print(
            f"FAIL: Phase 1 PID {pid} died within {PPID_CHECK_DELAY_SEC}s of spawn "
            f"(orphan detach broken — harness reap or SIGHUP propagation regression)"
        )
        return (False, pid)
    ppid = _pid_ppid(pid)
    if ppid != 1:
        print(
            f"FAIL: Phase 1 PPID={ppid} for PID {pid}, expected 1 "
            f"(init reparenting broken — `nohup + &` orphaning regression)"
        )
        return (False, pid)

    deadline = time.monotonic() + DURATION + MARKER_TIMEOUT_MARGIN_SEC
    while time.monotonic() < deadline:
        if marker.exists():
            break
        if not _pid_alive(pid):
            break
        time.sleep(MARKER_POLL_INTERVAL_SEC)

    if not marker.exists():
        print(
            f"FAIL: Phase 1 PID {pid} did not produce marker within "
            f"{DURATION + MARKER_TIMEOUT_MARGIN_SEC}s "
            f"(orphan died or was killed prematurely)"
        )
        return (False, pid)

    content = marker.read_text().strip()
    if content != "survived":
        print(
            f"FAIL: Phase 1 marker content = {content!r}, expected 'survived' "
            f"(orphan ran but wrote wrong payload)"
        )
        return (False, pid)

    return (True, pid)


def _phase_2_real_chain_integration(tmpdir: Path) -> str:
    """Run Phase 2. Returns 'PASS' / 'SKIP (<reason>)' / 'FAIL (<detail>)'.

    Uses a sed-copied variant of run-dialectic.sh pointing at a mock dialectic
    script. Verifies engine.done + engine.exit markers appear — regression
    guard for Plan Review Issue #1 (`exec` keyword suppresses EXIT trap).
    """
    if not RUN_SCRIPT.is_file():
        return f"SKIP (run-dialectic.sh not found at {RUN_SCRIPT})"

    e_dir = tmpdir / "phase2"
    e_dir.mkdir(parents=True, exist_ok=True)
    mock = e_dir / "mock-dialectic.sh"
    mock.write_text(
        "#!/bin/bash\n"
        "# Mock dialectic — prints a single JSON line and exits 0.\n"
        "echo '{\"status\":\"completed\",\"verdict\":\"ACCEPT\"}'\n"
        "exit 0\n"
    )
    mock.chmod(0o755)

    mod_script = e_dir / "run-dialectic-mod.sh"
    try:
        original = RUN_SCRIPT.read_text()
    except OSError as exc:
        return f"SKIP (could not read run-dialectic.sh: {exc})"

    # sed-equivalent string replacement via Python:
    #   1) force find_python to succeed without requiring claude_agent_sdk
    #   2) swap "$PYTHON" "$SCRIPT_DIR/dialectic.py" "$@" with our mock
    modified = original
    modified = modified.replace(
        'if python3 -c "import claude_agent_sdk" 2>/dev/null; then',
        'if true; then',
    )
    modified = modified.replace(
        '    echo "python3"',
        '    echo "/bin/sh"',
    )
    modified = modified.replace(
        '"$PYTHON" "$SCRIPT_DIR/dialectic.py" "$@"',
        f'"{mock}"',
    )

    if modified == original:
        return "SKIP (sed-copy produced no change — run-dialectic.sh structure drifted)"

    mod_script.write_text(modified)
    mod_script.chmod(0o755)

    # sanity check: modified script must still parse
    parse = subprocess.run(
        ["bash", "-n", str(mod_script)],
        capture_output=True,
        text=True,
        check=False,
    )
    if parse.returncode != 0:
        return f"SKIP (modified script failed bash -n: {parse.stderr.strip()})"

    step_cfg = e_dir / "step-config.json"
    step_cfg.write_text("{}\n")
    engine_log = e_dir / "engine.log"

    try:
        run = subprocess.run(
            ["bash", str(mod_script), str(step_cfg)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return "FAIL (run-dialectic-mod.sh timed out after 30s — bash likely hung without reaching trap)"
    # mock stdout may have gone to the log redirect inside run-dialectic-mod.sh,
    # but since we rewrote the invocation without shell redirection, stdout
    # is captured here. Either way we check markers next.

    engine_done = e_dir / "engine.done"
    engine_exit = e_dir / "engine.exit"
    if not engine_done.exists():
        return (
            f"FAIL (engine.done missing after real-chain exit rc={run.returncode}; "
            f"possible `exec` reintroduced — Issue #1 regression. "
            f"stderr tail: {run.stderr.strip()[-200:]!r})"
        )
    exit_content = engine_exit.read_text().strip() if engine_exit.exists() else "<missing>"
    if exit_content != "0":
        return (
            f"FAIL (engine.exit = {exit_content!r}, expected '0'; "
            f"mock returned rc={run.returncode})"
        )

    # Optionally preserve run.stdout into engine.log for forensics (best-effort)
    if run.stdout and not engine_log.exists():
        try:
            engine_log.write_text(run.stdout)
        except OSError:
            pass

    return "PASS"


def main() -> int:
    tmpdir = Path(tempfile.mkdtemp(prefix="tas-canary-7-"))
    phase1_pid = -1
    try:
        # ---- Phase 1: subagent orphan survival
        phase1_dir = tmpdir / "phase1"
        phase1_dir.mkdir(parents=True, exist_ok=True)
        phase1_ok, phase1_pid = _phase_1_orphan_survival(phase1_dir)
        if not phase1_ok:
            return 1

        # ---- Phase 2: real exec chain integration (Issue #1 regression guard)
        phase2_result = _phase_2_real_chain_integration(tmpdir)
        if phase2_result.startswith("FAIL"):
            print(f"FAIL: Phase 2 {phase2_result[5:]}")
            return 1
        # PASS or SKIP both acceptable at the canary level; Plan 07 invariant 6
        # (static `grep -c '^[[:space:]]*exec '` == 0) covers the SKIP case.

        phase2_label = phase2_result  # 'PASS' or 'SKIP (<reason>)'
        print(
            f"PASS: canary #7 (subagent orphan survived {DURATION}s, PPID=1; "
            f"real-chain integration: {phase2_label})"
        )
        return 0

    finally:
        if phase1_pid > 0:
            _cleanup_pid(phase1_pid)
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
