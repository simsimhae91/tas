---
name: tas-review
description: >
  Lightweight dialectic code review — triggers on /tas-review.
  Automatically extracts git diff, accepts PR branch/SHA, and invokes
  MetaAgent with request_type=review for structured review output.
  Use when: user wants code review, PR review, diff review, or says "tas-review".
---

# tas-review — Lightweight Dialectic Code Review

You are the orchestrator for `/tas-review`. You collect diff context, then delegate
to MetaAgent for dialectic review. You do NOT perform the review yourself.

**SCOPE PROHIBITION** — identical to `/tas`:
- NEVER read project source code to make review judgments yourself
- NEVER analyze diff content to decide whether review is needed
- Collect diff mechanically, pass to MetaAgent, present results

---

## Step 1: Collect Diff Context

```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
SKILL_DIR="${CLAUDE_SKILL_DIR}/../tas"
```

Parse `$ARGUMENTS` for review target:

| Input | Detection | Diff Command |
|-------|-----------|-------------|
| No arguments | Default | `git diff HEAD` (unstaged + staged) |
| Branch name (e.g., `main`, `feature/x`) | No `/`, no SHA pattern | `git diff $BRANCH...HEAD` |
| Commit SHA (7-40 hex chars) | `/^[0-9a-f]{7,40}$/` | `git diff $SHA HEAD` |
| `--staged` | Literal flag | `git diff --cached` |
| PR number (e.g., `#123`) | `/^#\d+$/` | `gh pr diff $NUMBER` |

Collect the diff:

```bash
DIFF="$(${diff_command} 2>&1)"
DIFF_STAT="$(${diff_command} --stat 2>&1)"
```

**Size guard**: If diff exceeds 800 lines, truncate and warn:
```
⚠ Diff가 800줄을 초과합니다 ({actual_lines}줄). 처음 800줄만 리뷰합니다.
전체 리뷰가 필요하면 범위를 좁혀주세요 (예: /tas-review --staged)
```

If diff is empty:
```
변경사항이 없습니다. 리뷰할 diff를 지정해주세요.
예: /tas-review main, /tas-review --staged, /tas-review #42
```

---

## Step 2: Classify + Execute

Create workspace and invoke MetaAgent with review-specific context:

```bash
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
WORKSPACE="${PROJECT_ROOT}/_workspace/quick/${TIMESTAMP}/"
mkdir -p "$WORKSPACE"
```

Write `$WORKSPACE/REQUEST.md` with the review request.

Single classify+execute invocation (review is always single-step):

```
META_OUTPUT = Agent({
  description: "tas review: code review",
  prompt: "Read ${SKILL_DIR}/agents/meta.md and follow its instructions exactly.

COMMAND: classify
REQUEST: 다음 diff를 리뷰해주세요. 변경 요약:\n${DIFF_STAT}\n\n전체 diff:\n${DIFF}
PROJECT_ROOT: ${PROJECT_ROOT}
SKILL_DIR: ${SKILL_DIR}

Return ONLY the JSON result line.",
  mode: "bypassPermissions",
  model: "opus"
})
```

If classify returns `mode: "quick"`, proceed to execute:

```
RESULT = Agent({
  description: "tas review: execute review",
  prompt: "Read ${SKILL_DIR}/agents/meta.md and follow its instructions exactly.

REQUEST: 다음 diff를 리뷰해주세요. 변경 요약:\n${DIFF_STAT}\n\n전체 diff:\n${DIFF}
WORKSPACE: ${WORKSPACE}
PROJECT_ROOT: ${PROJECT_ROOT}
SKILL_DIR: ${SKILL_DIR}
REQUEST_TYPE: review
COMPLEXITY: ${complexity from classify}
PLAN: ${steps from classify}
LOOP_COUNT: ${loop_count from classify}
LOOP_POLICY: ${loop_policy from classify}

Return ONLY the JSON result line.",
  mode: "bypassPermissions",
  model: "opus"
})
```

---

## Step 3: Present Results

On success:
```
정반합 리뷰 완료 — {rounds_total}라운드.
{summary}

결과물: {workspace}/DELIVERABLE.md
```

On error (MetaAgent JSON parse failure or non-zero exit):
```
⚠ 리뷰 중 오류가 발생했습니다.
워크스페이스: {workspace}
수동 확인: {workspace}/DELIVERABLE.md 또는 logs/ 참조
```
