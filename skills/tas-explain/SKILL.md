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
No tas workspace found. Run /tas first to create one.
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

Produce a structured summary. Use the **same language as the user's request** found in REQUEST.md. Default to English if unclear.

```
## Dialectic Dialogue Summary

### Overview
- Workspace: {timestamp}
- Request: {first line of REQUEST.md}
- Iterations: {iterations executed}
- Total rounds: {rounds_total from DELIVERABLE.md frontmatter}
- Status: {completed / halted}

### Key Contentions
Points where Thesis and Antithesis diverged:

1. **{contention topic}**
   - Thesis: {thesis position, 1-2 sentences}
   - Antithesis: {antithesis position, 1-2 sentences}
   - Resolution: {how resolved — accepted / refined / conceded}

2. **{contention topic}**
   ...

### Agreements
Key decisions both sides agreed on:
- {agreement 1}
- {agreement 2}
- ...

### Rejected Alternatives
Approaches considered but not adopted:
- **{alternative}** — Reason: {reason}
- ...

### Final Decision
{Summary of the final deliverable — what was built/designed/reviewed and key conclusions}

### Lessons Learned
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
### Iteration Summary

| # | Focus | Key Improvements | Status |
|---|-------|-----------------|--------|
| 1 | baseline | {summary} | completed |
| 2 | {focus_angle} | {summary} | completed |
```

Then combine contentions, agreements, and rejected alternatives across all iterations
into the unified sections above.
