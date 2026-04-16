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
- Only read files inside `_workspace/quick/` directories
- Only delete workspace directories (never project files)

---

## Setup

```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
WS_BASE="${PROJECT_ROOT}/_workspace/quick"
```

If `_workspace/quick/` does not exist:
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
