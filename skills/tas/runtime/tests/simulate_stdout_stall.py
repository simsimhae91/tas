#!/usr/bin/env python3
"""Canary #5 — Layer A watchdog (sdk_session_hang) regression guard.

Executes dialectic.run_dialectic() with a mock ClaudeSDKClient whose
`receive_response` stream stalls for 60s. With query_timeout=5, Layer A
must trip and emit a halted JSON with:
  - halt_reason == "sdk_session_hang"
  - watchdog_layer == "A"
  - last_heartbeat object (4 fields, non-null)

Run via /tas-verify. stdlib-only. Target wall-clock < 10s.
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]  # tas/ repo root (tests → runtime → tas → skills → REPO_ROOT)
DIALECTIC_PY = REPO_ROOT / "skills" / "tas" / "runtime" / "dialectic.py"


def _write_prompt(p: Path, name: str) -> Path:
    f = p / f"{name}.md"
    f.write_text(f"# {name}\nYou are a mock. Respond briefly.\n", encoding="utf-8")
    return f


_MOCK_SHIM = '''
import asyncio

class _MockClient:
    async def connect(self): return None
    async def disconnect(self): return None
    async def query(self, prompt): return None
    async def receive_response(self):
        await asyncio.sleep(60)
        if False:
            yield

class ClaudeSDKClient(_MockClient):
    def __init__(self, options=None): self.options = options

class ClaudeAgentOptions(dict):
    def __init__(self, *a, **kw): super().__init__(**kw)

class AssistantMessage: pass
class ResultMessage: pass
class TextBlock: pass
'''


def _patch_dialectic_with_mock():
    """Spawn dialectic.py as a subprocess with PYTHONPATH injection that
    replaces claude_agent_sdk with a mock module."""
    tmpdir = Path(tempfile.mkdtemp(prefix="tas-canary5-"))
    try:
        # Write a fake claude_agent_sdk package into tmpdir so `import
        # claude_agent_sdk` picks up our mock first.
        pkg = tmpdir / "claude_agent_sdk"
        pkg.mkdir()
        (pkg / "__init__.py").write_text(
            "from ._shim import ClaudeSDKClient, ClaudeAgentOptions, "
            "AssistantMessage, ResultMessage, TextBlock\n"
            "from .types import SystemPromptPreset\n",
            encoding="utf-8",
        )
        (pkg / "_shim.py").write_text(_MOCK_SHIM, encoding="utf-8")
        (pkg / "types.py").write_text(
            "class SystemPromptPreset(dict):\n"
            "    def __init__(self, *a, **kw): super().__init__(**kw)\n",
            encoding="utf-8",
        )
        (pkg / "_errors.py").write_text(
            "class CLIConnectionError(Exception): pass\n",
            encoding="utf-8",
        )

        # Build step-config.json in tmpdir
        log_dir = tmpdir / "logs" / "step-canary5"
        log_dir.mkdir(parents=True)
        thesis_p = _write_prompt(tmpdir, "thesis")
        anti_p = _write_prompt(tmpdir, "antithesis")
        cfg = {
            "log_dir": str(log_dir),
            "step_id": "canary5",
            "step_goal": "Layer A regression guard",
            "project_root": str(tmpdir),
            "thesis_prompt_path": str(thesis_p),
            "antithesis_prompt_path": str(anti_p),
            "step_assignment": "mock prompt",
            "antithesis_briefing": "mock briefing",
            "query_timeout": 5,  # short → Layer A trips fast
        }
        cfg_path = tmpdir / "step-config.json"
        cfg_path.write_text(json.dumps(cfg), encoding="utf-8")

        env = os.environ.copy()
        env["PYTHONPATH"] = str(tmpdir) + os.pathsep + env.get("PYTHONPATH", "")
        # Force Layer B off (no TAS_WATCHDOG_TIMEOUT_SEC, plus run dialectic.py
        # directly to bypass run-dialectic.sh wrapper)
        proc = subprocess.Popen(
            [sys.executable, str(DIALECTIC_PY), str(cfg_path)],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(tmpdir),
        )
        return proc, tmpdir
    except Exception:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise


def main() -> int:
    proc, tmpdir = _patch_dialectic_with_mock()
    try:
        stdout, stderr = proc.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        print("FAIL: canary #5 exceeded 30s wall-clock (Layer A may be broken)")
        return 1
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    # Assertions per D-07 (a):
    if proc.returncode == 0:
        print(f"FAIL: expected non-zero exit (TimeoutError re-raise), got {proc.returncode}")
        return 1

    lines = stdout.decode("utf-8", errors="replace").strip().splitlines()
    if not lines:
        print("FAIL: no stdout output")
        print("--- stderr ---")
        print(stderr.decode("utf-8", errors="replace"))
        return 1

    # Layer A contract: run_dialectic() emits the halted JSON, then re-raises
    # TimeoutError, which main()'s outer try/except catches and prints a
    # trailing {"status":"error"} line (dialectic.py line 919, ISSUE-11).
    # MetaAgent's classifier (CONTEXT D-05) would reconcile this via "non-zero
    # exit + valid JSON → propagate halt_reason". Canary #5 scans last-N
    # lines for the first parseable JSON with status=halted.
    halted = None
    last_line_raw = lines[-1]
    for line in reversed(lines[-5:]):  # scan last 5 lines (halted JSON is line -2)
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("status") == "halted":
            halted = obj
            break
    if halted is None:
        print(f"FAIL: no halted JSON found in last 5 stdout lines. last line: {last_line_raw!r}")
        print("--- stderr ---")
        print(stderr.decode("utf-8", errors="replace"))
        return 1

    required = {"status": "halted", "halt_reason": "sdk_session_hang", "watchdog_layer": "A"}
    for k, v in required.items():
        if halted.get(k) != v:
            print(f"FAIL: expected {k}={v!r}, got {halted.get(k)!r}")
            return 1
    hb = halted.get("last_heartbeat")
    if not isinstance(hb, dict) or not {"timestamp", "round_n", "speaker", "phase"}.issubset(hb):
        print(f"FAIL: last_heartbeat missing/incomplete: {hb!r}")
        return 1

    print("PASS: canary #5 (Layer A sdk_session_hang)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
