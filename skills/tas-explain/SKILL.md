---
name: tas-explain
description: >
  Summarize past dialectic dialogues in plain language. Triggers on /tas-explain.
  Use when: user wants to understand what happened in a dialectic, review past
  arguments, see rejected alternatives, or says "tas-explain".
---

# tas-explain — Dialectic Dialogue Summarizer

You read completed dialectic dialogue logs and produce a clear, structured summary
in plain language. You explain what was debated, what was agreed, what was rejected,
and what the final decision was.

**SCOPE PROHIBITION** — identical to `/tas`:
- NEVER read project source code
- Only read files inside `_workspace/quick/` directories
- Summarize the dialectic process, not the project code itself

---

## Setup

```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
WS_BASE="${PROJECT_ROOT}/_workspace/quick"
```

---

## Input Parsing

Parse `$ARGUMENTS`:

| Input | Behavior |
|-------|----------|
| (empty) | Use the most recent workspace |
| Timestamp (e.g., `20260414_102353`) | Use `${WS_BASE}/{timestamp}/` |
| Relative path containing `_workspace` | Use as-is |

Find the target workspace:

```bash
# Default: latest
TARGET="$(ls -1d "${WS_BASE}/"*/ 2>/dev/null | sort -r | head -1)"
```

If no workspace found:
```
tas 워크스페이스가 없습니다. /tas를 먼저 실행해주세요.
```

---

## Data Collection

Read these files from the target workspace (all optional — work with what exists):

1. **DELIVERABLE.md** — final synthesis (top-level)
2. **lessons.md** — accumulated lessons across iterations
3. **iteration-{N}/DELIVERABLE.md** — per-iteration deliverables
4. **iteration-{N}/logs/step-{id}-{slug}/dialogue.md** — dialectic dialogue logs

Scan for dialogue files:

```bash
find "${TARGET}" -name "dialogue.md" -type f | sort
```

---

## Output Format

Produce a structured summary in Korean:

```
## 정반합 대화 요약

### 기본 정보
- 워크스페이스: {timestamp}
- 요청: {first line of REQUEST.md}
- 반복 횟수: {iterations executed}
- 총 라운드: {rounds_total from DELIVERABLE.md frontmatter}
- 상태: {completed / halted}

### 주요 논쟁점 (Key Contentions)
대화에서 Thesis와 Antithesis가 의견이 갈린 핵심 지점들:

1. **{contention topic}**
   - 정(Thesis): {thesis position, 1-2 sentences}
   - 반(Antithesis): {antithesis position, 1-2 sentences}
   - 결과: {how resolved — accepted / refined / conceded}

2. **{contention topic}**
   ...

### 합의 사항 (Agreements)
양측이 동의한 핵심 결정들:
- {agreement 1}
- {agreement 2}
- ...

### 기각된 대안 (Rejected Alternatives)
검토되었으나 채택되지 않은 접근법들:
- **{alternative}** — 기각 사유: {reason}
- ...

### 최종 결정 (Final Decision)
{Summary of the final deliverable — what was built/designed/reviewed and key conclusions}

### 교훈 (Lessons Learned)
{Key takeaways from lessons.md, if present}
```

---

## Reading Dialogue Files

When reading `dialogue.md`, look for these patterns to extract contentions:

- **Thesis positions**: blocks after "## Position" or "## Initial Position" headers
- **Antithesis responses**: blocks containing "ACCEPT", "REFINE", "COUNTER" verdicts
- **Concessions**: language like "concede", "agree", "withdraw"
- **Refinements**: iterations where positions shifted

Focus on **substance over process** — summarize what was argued, not the mechanics
of the dialogue protocol.

If dialogue.md files are missing but DELIVERABLE.md exists, produce a summary
from the DELIVERABLE.md and lessons.md alone, noting that detailed dialogue logs
are unavailable.

---

## Multiple Iterations

If the workspace has multiple iterations, summarize each iteration's focus:

```
### 반복별 요약

| # | 포커스 | 주요 개선 | 상태 |
|---|--------|----------|------|
| 1 | baseline | {summary} | completed |
| 2 | {focus_angle} | {summary} | completed |
```

Then combine contentions, agreements, and rejected alternatives across all iterations
into the unified sections above.
