#!/usr/bin/env python3
"""measure-prompt-tokens.py — Anthropic count_tokens API wrapper for prompt budget tracking.

DEV-ONLY. This tool is NOT a runtime dependency. The `anthropic` package
must NEVER be added to skills/tas/runtime/requirements.txt (SLIM-01 D-04).
End users do not need ANTHROPIC_API_KEY to run /tas.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    pip install anthropic  # dev machine only
    python3 scripts/measure-prompt-tokens.py skills/tas/agents/meta.md [<more-files>...]

Output (tab-separated, stdout):
    skills/tas/agents/meta.md\t<N>
    ...
    TOTAL\t<SUM>

Exit codes:
    0 — success
    1 — user error (missing package / missing API key / no args / file not found)
    2 — API error (invalid model ID / rate limit / network)

Per Phase 5 D-04 — no tiktoken fallback, no retry loop.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Updated 2026-04-22; verify at docs.claude.com/en/api/messages-count-tokens
# when updating. Must match MetaAgent's resolved opus alias for fidelity
# to the 5,500-token degradation threshold (Pitfall 3).
MODEL = "claude-opus-4-7"

# Per-file sanity cap — prevents accidental attempt to count very large logs.
MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB

try:
    from anthropic import Anthropic, NotFoundError, BadRequestError
except ImportError:
    print(
        "ERROR: anthropic package not installed. This is a dev-only tool.\n"
        "Install: pip install anthropic\n"
        "Note: do NOT add anthropic to skills/tas/runtime/requirements.txt.",
        file=sys.stderr,
    )
    sys.exit(1)


def _usage() -> None:
    print(
        "Usage: measure-prompt-tokens.py <file1> [<file2> ...]\n"
        "See scripts/README.md for dev-only installation notes.",
        file=sys.stderr,
    )


def _count_file(client: "Anthropic", path: Path) -> int:
    """Count tokens for one file via Anthropic count_tokens API.

    Uses `system=<file-content>` to match how meta.md / references are
    consumed at runtime (system prompt). Returns input_tokens (int).
    Raises anthropic exceptions on API failure; caller decides exit code.
    """
    content = path.read_text(encoding="utf-8")
    resp = client.messages.count_tokens(
        model=MODEL,
        system=content,
        messages=[{"role": "user", "content": "."}],
    )
    return int(resp.input_tokens)


def main(argv: list[str]) -> int:
    if not argv:
        _usage()
        return 1

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set.", file=sys.stderr)
        return 1

    # Validate all files exist + within sanity cap BEFORE any API call.
    paths: list[Path] = []
    for arg in argv:
        p = Path(arg).resolve()
        if not p.exists() or not p.is_file():
            print(f"ERROR: not a file: {arg}", file=sys.stderr)
            return 1
        if p.stat().st_size > MAX_FILE_BYTES:
            print(
                f"ERROR: file too large ({p.stat().st_size} bytes > {MAX_FILE_BYTES}): {arg}",
                file=sys.stderr,
            )
            return 1
        paths.append(p)

    # Anthropic() reads ANTHROPIC_API_KEY from env.
    client = Anthropic()

    total = 0
    try:
        for i, path in enumerate(paths):
            tokens = _count_file(client, path)
            # Print the arg as given (not the resolved absolute path) — preserves
            # the invocation's file-path presentation for diff-friendly output.
            print(f"{argv[i]}\t{tokens}")
            total += tokens
    except (NotFoundError, BadRequestError) as e:
        print(
            f"ERROR: Invalid model ID or request — update MODEL constant "
            f"(currently {MODEL!r}; verify at docs.claude.com/en/api/messages-count-tokens). "
            f"Underlying: {type(e).__name__}",
            file=sys.stderr,
        )
        return 2
    except Exception as e:  # noqa: BLE001 — dev-only surface
        # Never print the API key or any header content.
        print(f"ERROR: API call failed: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    print(f"TOTAL\t{total}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
