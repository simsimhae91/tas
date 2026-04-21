#!/usr/bin/env python3
"""
tas checkpoint — crash-safe checkpoint.json / plan.json writer.

stdlib-only. Called by MetaAgent via CLI (Bash heredoc is NOT used — see
meta.md Phase 2d step 9.5). Provides:
  write_checkpoint(workspace, **fields)  — atomic write of checkpoint.json
  read_checkpoint(workspace)             — returns dict or None
  compute_plan_hash(plan)                — canonical JSON SHA-256 hex

Atomic write invariant: the target file either reflects the pre-call state
or the full new payload. No reader ever observes a partial write.

Usage (CLI, invoked by MetaAgent):
  python3 checkpoint.py write      <workspace> --json '<payload>'
  python3 checkpoint.py write-plan <workspace> --json '<payload>'
  python3 checkpoint.py read       <workspace>
  python3 checkpoint.py hash       <plan_json_path>
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Schema constants
# ---------------------------------------------------------------------------

# Integer schema version — Phase 1 writes only `1`; future values trigger
# HALT `checkpoint_schema_unsupported` in Phase 2 Resume Gate.
SCHEMA_VERSION = 1
CHECKPOINT_FILENAME = "checkpoint.json"
PLAN_FILENAME = "plan.json"


# ---------------------------------------------------------------------------
# Atomic JSON writer
# ---------------------------------------------------------------------------

def _atomic_write_json(path: Path, payload: dict[str, Any], *, canonical: bool = False) -> None:
    """Write payload as JSON to `path` atomically.

    Crash invariant: after return (or exception), `path` either contains the
    previous content or the full new content. Never a torn write.

    - `canonical=True` uses canonical JSON (for plan.json, so plan_hash is stable).
    - `canonical=False` uses indent=2 for developer-readable checkpoint.json.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if canonical:
        data = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    else:
        data = json.dumps(payload, indent=2, ensure_ascii=False)

    # tempfile.NamedTemporaryFile with delete=False lets us close + fsync + replace.
    # dir=path.parent ensures rename is on the same filesystem (required for atomicity).
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    )
    try:
        tmp.write(data)
        tmp.flush()
        os.fsync(tmp.fileno())  # force page cache → disk before rename
        tmp.close()
        os.replace(tmp.name, path)  # POSIX: atomic rename within same fs
    except BaseException:
        # On any failure, best-effort cleanup. The original `path` is untouched.
        try:
            os.unlink(tmp.name)
        except FileNotFoundError:
            pass
        raise


def write_checkpoint(workspace: Path, /, **fields: Any) -> None:
    """Atomically write checkpoint.json at workspace/checkpoint.json.

    Caller provides all schema fields as kwargs. This function does NOT
    merge with the existing file — MetaAgent is expected to pass the full
    intended state. (Rationale: file-mediated state only; no hidden merging.)

    `workspace` is positional-only so that a caller may still pass the
    schema field `workspace` inside `**fields` (e.g., `**payload` from CLI)
    without a name-collision TypeError.
    """
    path = Path(workspace) / CHECKPOINT_FILENAME
    _atomic_write_json(path, dict(fields), canonical=False)


def read_checkpoint(workspace: Path) -> dict[str, Any] | None:
    """Read checkpoint.json; return None if absent. Raise on corrupt JSON."""
    path = Path(workspace) / CHECKPOINT_FILENAME
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def compute_plan_hash(plan: dict[str, Any]) -> str:
    """Canonical JSON SHA-256 hex digest of a plan dict.

    Uses sort_keys=True, separators=(",", ":"), ensure_ascii=False so that
    whitespace/ordering re-formatting (e.g., a reviewer running `jq`) does
    not trip the hash, but any semantic change does.
    """
    canonical = json.dumps(plan, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# CLI (called by MetaAgent via Bash)
# ---------------------------------------------------------------------------

def _main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: checkpoint.py {write|write-plan|read|hash} <args>", file=sys.stderr)
        return 2
    cmd = argv[1]
    if cmd == "write":
        # checkpoint.py write <workspace_dir> --json '<json-payload>'
        if len(argv) != 5 or argv[3] != "--json":
            print("Usage: checkpoint.py write <workspace> --json '<payload>'", file=sys.stderr)
            return 2
        workspace = Path(argv[2])
        payload = json.loads(argv[4])
        write_checkpoint(workspace, **payload)
        return 0
    if cmd == "write-plan":
        # checkpoint.py write-plan <workspace_dir> --json '<json-payload>'
        if len(argv) != 5 or argv[3] != "--json":
            print("Usage: checkpoint.py write-plan <workspace> --json '<payload>'", file=sys.stderr)
            return 2
        workspace = Path(argv[2])
        plan_path = workspace / PLAN_FILENAME
        if plan_path.exists():
            print(
                "plan.json already exists; plan.json is immutable after Classify approval",
                file=sys.stderr,
            )
            return 3
        payload = json.loads(argv[4])
        # canonical=True so plan.json is byte-stable → subsequent `hash` calls agree.
        _atomic_write_json(plan_path, payload, canonical=True)
        return 0
    if cmd == "read":
        if len(argv) != 3:
            print("Usage: checkpoint.py read <workspace>", file=sys.stderr)
            return 2
        workspace = Path(argv[2])
        ck = read_checkpoint(workspace)
        print(json.dumps(ck if ck is not None else None))
        return 0
    if cmd == "hash":
        if len(argv) != 3:
            print("Usage: checkpoint.py hash <plan_json_path>", file=sys.stderr)
            return 2
        plan_path = Path(argv[2])
        with plan_path.open("r", encoding="utf-8") as f:
            plan = json.load(f)
        print(compute_plan_hash(plan))
        return 0
    print(f"Unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
