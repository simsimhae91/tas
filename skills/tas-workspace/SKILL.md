---
name: tas-workspace
description: >
  Workspace management for tas — list past deliverables, show stats, clean up
  old workspaces. Triggers on /tas-workspace. Use when: user wants to see past
  tas runs, clean up workspace, check latest deliverable, or says "tas-workspace".
---

# tas-workspace — Workspace Management

You manage the `_workspace/quick/` directory for the tas plugin. You list past runs,
show stats, display specific deliverables, and clean up old workspaces.

**SCOPE PROHIBITION** — identical to `/tas`:
- NEVER read project source code
- Only read files inside the resolved session worktree's `_workspace/quick/` directories (via LATEST symlink — Phase 6 ISO-04)
- Only delete workspace directories (never project files)

---

## Setup

Phase 6 ISO-04: companion commands resolve workspace via the `tas-sessions/LATEST` session-index symlink (replaces the former direct workspace scan).

```bash
# Resolve via tas-sessions/LATEST symlink (Phase 6 ISO-03 / D-04)
CACHE_ROOT="${XDG_CACHE_HOME:-${HOME}/.cache}/tas-sessions"
LATEST_LINK="${CACHE_ROOT}/LATEST"
if [ ! -L "${LATEST_LINK}" ]; then
  echo "No tas session found. Run /tas first to create one."
  exit 0
fi
SESSION_WORKTREE="$(readlink "${LATEST_LINK}")"
# Phase 6 D-10 chain-attack defense (T-V4-01) — bare 1-step readlink + cache-root prefix check
case "${SESSION_WORKTREE}" in
  "${CACHE_ROOT}/"*) ;;
  *) echo "LATEST symlink이 cache root 외부를 가리킵니다 (보안)."; exit 0 ;;
esac
WS_BASE="${SESSION_WORKTREE}/_workspace/quick"

# Retain user PROJECT_ROOT for the `clean` subcommand session-worktree extension below
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
```

If no workspaces exist yet inside the session worktree:
```
No tas workspace found. Run /tas first to create one.
```

---

## Subcommand Parsing

Parse `$ARGUMENTS` for the subcommand:

| Input | Subcommand | Description |
|-------|-----------|-------------|
| (empty) / `list` | `list` | List all past workspaces with summary |
| `latest` | `latest` | Show the most recent deliverable |
| `show <timestamp>` | `show` | Show a specific workspace's deliverable |
| `clean` | `clean` | Remove old workspaces (with safety check) |
| `stats` | `stats` | Show aggregate statistics |

---

## Subcommand: `list`

List all workspace directories sorted by timestamp (newest first):

```bash
ls -1d "${WS_BASE}/"*/ 2>/dev/null | sort -r
```

For each workspace directory, check for `DELIVERABLE.md` and `REQUEST.md`:

```
## tas Workspaces

| # | Timestamp | Status | Request |
|---|-----------|--------|---------|
| 1 | 20260414_102353 | ✓ completed | {first line of REQUEST.md, truncated to 60 chars} |
| 2 | 20260414_091500 | ⚠ halted | {first line of REQUEST.md} |
| 3 | 20260413_154200 | ⏳ in-progress | {first line of REQUEST.md} |
| ... | | | |

{N} workspaces — {completed} completed, {halted} halted, {in-progress} in progress
```

**Status detection**:
- `DELIVERABLE.md` exists and non-empty:
  - Read YAML frontmatter (between `---` markers) for `status` field
  - `status: completed` → `completed` (display: ✓)
  - `status: halted` or `status: blocked` → `halted` (display: ⚠)
  - No frontmatter or no `status` field → `completed` (display: ✓, legacy)
- `REQUEST.md` exists but no `DELIVERABLE.md` → `in-progress` (display: ⏳)
- Neither exists → `empty`

---

## Subcommand: `latest`

Find the most recent workspace (by directory name sort):

```bash
LATEST="$(ls -1d "${WS_BASE}/"*/ 2>/dev/null | sort -r | head -1)"
```

If no workspaces exist, say so. Otherwise read and display `${LATEST}/DELIVERABLE.md`.

If DELIVERABLE.md is missing:
```
Latest workspace ({timestamp}) has no DELIVERABLE.md. It may still be in progress or may have failed.
```

---

## Subcommand: `show <timestamp>`

```bash
TARGET="${WS_BASE}/${timestamp}"
```

If directory doesn't exist:
```
Workspace '{timestamp}' not found. Run /tas-workspace list to see available workspaces.
```

Otherwise read and display `${TARGET}/DELIVERABLE.md`. If missing, show REQUEST.md
and available logs structure instead.

---

## Subcommand: `clean`

**Safety rule**: NEVER delete a workspace that has `REQUEST.md` but no `DELIVERABLE.md`
(in-progress run).

1. Scan all workspace directories
2. Identify candidates for deletion using the same status detection as `list`:
   - Has DELIVERABLE.md with `status: completed` (or no frontmatter) → `completed` — deletable
   - Has DELIVERABLE.md with `status: halted` or `status: blocked` → `halted` — deletable (with warning)
   - Has neither REQUEST.md nor DELIVERABLE.md → `empty` — deletable
   - Has REQUEST.md but no DELIVERABLE.md → `in-progress` — **SKIP**
3. Present the list to the user:

```
## Workspaces to Clean

Deletable:
- 20260412_091500 (✓ completed)
- 20260411_143000 (✓ completed)
- 20260410_080000 (empty)

Deletable (halted — may contain diagnostic logs):
- 20260413_170000 (⚠ halted)

Protected (in progress):
- 20260414_102353

{N} to delete, {M} protected. Proceed?
```

4. On user confirmation, delete the listed directories:
```bash
rm -rf "${WS_BASE}/{timestamp}"
```

5. Report result:
```
{N} workspaces cleaned. {remaining} remaining.
```

### Phase 6 D-08 + Q-G extension: session-worktree pruning (after workspace cleanup)

After the workspace `_workspace/quick/{timestamp}/` cleanup completes, ALSO scan the user's git repo for stale `tas/session-*` worktrees (Phase 6 ISO-06 retention policy: tas does NOT auto-clean session worktrees; `/tas-workspace clean` is the user-explicit prune entry point).

```bash
# Discover tas/session-* worktrees registered in user's git repo
SESSION_WORKTREES="$(git -C "${PROJECT_ROOT}" worktree list --porcelain 2>/dev/null \
  | awk '/^worktree/{wt=$2} /^branch refs\/heads\/tas\/session-/{print wt}')"

if [ -n "${SESSION_WORKTREES}" ]; then
  COUNT=$(echo "${SESSION_WORKTREES}" | wc -l | tr -d ' ')
  echo ""
  echo "## tas/session-* Worktrees (Phase 6)"
  echo ""
  echo "Found ${COUNT} session worktree(s):"
  echo "${SESSION_WORKTREES}" | sed 's/^/  - /'
  echo ""
  echo "Remove all listed session worktrees + their tas/session-* branches? (y/n)"
fi
```

On user `y` confirmation, iterate the discovered list and remove each. The order matters: `git worktree remove` must run **before** `git branch -D` because git refuses to delete a branch that is still checked out by a worktree (Phase 6 Q-F).

```bash
echo "${SESSION_WORKTREES}" | while read -r wt_path; do
  [ -z "${wt_path}" ] && continue
  branch_name="$(git -C "${PROJECT_ROOT}" worktree list --porcelain 2>/dev/null \
    | awk -v wt="${wt_path}" '/^worktree/{cur=$2} cur==wt && /^branch refs\/heads\//{sub("refs/heads/","",$2); print $2}')"
  # Phase 6 Q-F order: worktree remove FIRST, then branch -D
  git -C "${PROJECT_ROOT}" worktree remove --force "${wt_path}" 2>/dev/null && \
    git -C "${PROJECT_ROOT}" branch -D "${branch_name}" 2>/dev/null
done
git -C "${PROJECT_ROOT}" worktree prune 2>/dev/null
echo "${COUNT} session worktree(s) pruned."
```

On `n` (or any non-`y`), skip session-worktree removal — the `_workspace` cleanup above remains complete. Session worktrees are preserved for forensics per D-08. This extension is the user-explicit prune entry point referenced by SKILL.md Phase 0 D-08 backlog guard; the `clean` subcommand extension was chosen over a new `--prune <ts>` sub-command (D-08 Discretion + Q-G recommendation: simpler UX, reuses the existing Y/N confirmation pattern).

---

## Subcommand: `stats`

Aggregate statistics across all workspaces:

```bash
# Count directories
TOTAL=$(ls -1d "${WS_BASE}/"*/ 2>/dev/null | wc -l)
```

For each workspace with DELIVERABLE.md, read YAML frontmatter for metadata
(iterations, rounds_total, status, request_type, complexity). Use the `status`
field to distinguish completed vs halted (see Status detection above).

```
## tas Workspace Stats

Total runs: {total}
  ✓ Completed: {completed}
  ⚠ Halted: {halted}
  ⏳ In progress: {in_progress}

Complexity: simple {N} / medium {N} / complex {N}
Avg rounds: {avg_rounds}
Disk usage: {du -sh result}
```
