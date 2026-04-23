#!/usr/bin/env python3
"""Canary #10 — Session Worktree Isolation (VERIFY-ISO-01).

STATUS: Wave 0 PENDING stub — full 2-Phase body lands in Plan 06-07.

Phase 1 (TAS_VERIFY_ISO_MODE=fast, default, ~30s — Plan 06-07): dirty fixture
+ session bootstrap simulation + sentinel write + delta=0 + branch+symlink
existence (4 assertions per .planning/phases/06-session-worktree-isolation/
06-CONTEXT.md D-09).

Phase 2 (TAS_VERIFY_ISO_MODE=full, optional, ~300s — Plan 06-07): HALT-path
session worktree retention (ISO-06) + Canary #8 PASS on session worktree
(ISO-05 retarget regression guard) + manual merge stdout placeholder
(Phase 7 prep) + companion-command grep-0-matches (ISO-04).

This Wave 0 stub deliberately exits 0 in both modes — it is a placeholder
so plans 06-02..06-06 can ship while Plan 06-07 implements the full body.
Run via /tas-verify. stdlib-only (no psutil, pytest, claude_agent_sdk).
"""
from __future__ import annotations

import os
import sys

MODE = os.environ.get("TAS_VERIFY_ISO_MODE", "fast")  # fast | full


def main() -> int:
    # PENDING: Wave 0 stub. Full body in Plan 06-07.
    if MODE == "full":
        print("PASS: canary #10 (PENDING — Wave 0 stub; full body Plan 06-07; mode=full SKIP)")
    else:
        print("PASS: canary #10 (PENDING — Wave 0 stub; full body Plan 06-07; mode=fast SKIP)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
