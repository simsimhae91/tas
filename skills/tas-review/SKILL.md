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
| Branch name (e.g., `main`, `feature/x`) | Not a SHA pattern, not a flag | `git diff $BRANCH...HEAD` |
| Commit SHA (7-40 hex chars) | `/^[0-9a-f]{7,40}$/` | `git diff $SHA HEAD` |
| `--staged` | Literal flag | `git diff --cached` |
| PR number (e.g., `#123`) | `/^#\d+$/` | `gh pr diff $NUMBER` |

Collect the diff:

```bash
DIFF="$(${diff_command} 2>&1)"
DIFF_STAT="$(${diff_command} --stat 2>&1)"
```

**Size guard**: If diff exceeds 800 lines, truncate and warn. Show which files are included vs excluded:

```bash
# Get per-file line counts from the diff
INCLUDED_FILES="$(echo "$DIFF" | head -800 | grep '^diff --git' | sed 's|diff --git a/||;s| b/.*||')"
EXCLUDED_FILES="$(echo "$DIFF" | tail -n +801 | grep '^diff --git' | sed 's|diff --git a/||;s| b/.*||')"
```

```
⚠ Diff exceeds 800 lines ({actual_lines} total). Reviewing first 800 lines only.

Included in review:
{INCLUDED_FILES, one per line with -)

Excluded (truncated):
{EXCLUDED_FILES, one per line with -)

To review specific files, narrow the scope: /tas-review --staged, or stage only the files you want reviewed.
```

If diff is empty:
```
No changes found. Specify a diff target:
  /tas-review main        — diff against main branch
  /tas-review --staged    — staged changes only
  /tas-review #42         — PR diff
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
REQUEST: Review the following diff. Change summary:\n${DIFF_STAT}\n\nFull diff:\n${DIFF}
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

REQUEST: Review the following diff. Change summary:\n${DIFF_STAT}\n\nFull diff:\n${DIFF}
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

Parse MetaAgent JSON. Check `status` field first.

**On HALT** (`status: "halted"`):
```
⚠ Review halted — {halt_reason}.
{summary}

Workspace: {workspace}
Dialogue: `/tas-explain {timestamp}`
```

**On success** (`status: "completed"`) — read and display the deliverable inline with size guard:

```bash
DELIVERABLE_LINES="$(wc -l < ${WORKSPACE}/DELIVERABLE.md 2>/dev/null || echo 0)"
DELIVERABLE_CONTENT="$(head -200 ${WORKSPACE}/DELIVERABLE.md 2>/dev/null)"
```

If 200 lines or fewer, display in full:
```
Review complete — {rounds_total} rounds.
{summary}

---
{DELIVERABLE_CONTENT}
---

Full review: {workspace}/DELIVERABLE.md
```

If over 200 lines, show preview:
```
Review complete — {rounds_total} rounds.
{summary}

---
{DELIVERABLE_CONTENT (first 200 lines)}

... ({DELIVERABLE_LINES - 200} more lines)
---

Full review: {workspace}/DELIVERABLE.md
```

If the deliverable file is missing or empty, fall back to showing just the path.

If the diff was truncated earlier (exceeded 800 lines), append to the result:

```
> **Note**: This review covers the first 800 of {actual_lines} diff lines. Files excluded from review are listed in the truncation warning above.
```

On error (MetaAgent JSON parse failure or non-zero exit):
```
⚠ Review encountered an error.
Workspace: {workspace}
Check: {workspace}/DELIVERABLE.md or logs/ for details.
```
