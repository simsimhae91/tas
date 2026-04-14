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
tas 워크스페이스가 없습니다. /tas를 먼저 실행해주세요.
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
## tas 워크스페이스 목록

| # | 타임스탬프 | 상태 | 요청 요약 |
|---|-----------|------|----------|
| 1 | 20260414_102353 | completed | {first line of REQUEST.md, truncated to 60 chars} |
| 2 | 20260413_154200 | in-progress | {first line of REQUEST.md} |
| ... | | | |

총 {N}개 워크스페이스, {completed}개 완료, {in-progress}개 진행 중
```

**Status detection**:
- `DELIVERABLE.md` exists and non-empty → `completed`
- `REQUEST.md` exists but no `DELIVERABLE.md` → `in-progress`
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
최근 워크스페이스 ({timestamp})에 DELIVERABLE.md가 없습니다. 진행 중이거나 실패했을 수 있습니다.
```

---

## Subcommand: `show <timestamp>`

```bash
TARGET="${WS_BASE}/${timestamp}"
```

If directory doesn't exist:
```
워크스페이스 '{timestamp}'을 찾을 수 없습니다. /tas-workspace list로 확인해주세요.
```

Otherwise read and display `${TARGET}/DELIVERABLE.md`. If missing, show REQUEST.md
and available logs structure instead.

---

## Subcommand: `clean`

**Safety rule**: NEVER delete a workspace that has `REQUEST.md` but no `DELIVERABLE.md`
(in-progress run).

1. Scan all workspace directories
2. Identify candidates for deletion:
   - Has both REQUEST.md and DELIVERABLE.md (completed) — deletable
   - Has neither REQUEST.md nor DELIVERABLE.md (empty) — deletable
   - Has REQUEST.md but no DELIVERABLE.md (in-progress) — **SKIP**
3. Present the list to the user:

```
## 정리 대상 워크스페이스

삭제 가능:
- 20260412_091500 (completed)
- 20260411_143000 (completed)
- 20260410_080000 (empty)

보호됨 (진행 중):
- 20260414_102353

{N}개 삭제, {M}개 보호. 진행할까요?
```

4. On user confirmation, delete the listed directories:
```bash
rm -rf "${WS_BASE}/{timestamp}"
```

5. Report result:
```
{N}개 워크스페이스 정리 완료. 남은 워크스페이스: {remaining}개
```

---

## Subcommand: `stats`

Aggregate statistics across all workspaces:

```bash
# Count directories
TOTAL=$(ls -1d "${WS_BASE}/"*/ 2>/dev/null | wc -l)
```

For each completed workspace, read DELIVERABLE.md frontmatter for metadata
(iterations, rounds_total, status, request_type, complexity).

```
## tas 워크스페이스 통계

총 실행: {total}회
완료: {completed}회
중단(halted): {halted}회
진행 중: {in_progress}회

복잡도 분포: simple {N} / medium {N} / complex {N}
평균 라운드: {avg_rounds}
총 디스크 사용: {du -sh result}
```
