# Workspace Convention

This document defines the directory structure, file formats, naming rules, and state management
conventions used by tas's per-step session architecture. All workflow files, MetaAgent, and
MainOrchestrator reference this document as the single source of truth for workspace layout.

---

## Directory Structure

```
_workspace/
  REQUEST.md                                    ← original user request
  PROGRESS.md                                   ← main-level progress log
  P1-{phase-slug}/
    S01-{step-slug}.md                          ← step output (rounds + final output)
    S02-{step-slug}.md
    ...
    DELIVERABLE.md                              ← phase exit contract
  P2-{phase-slug}/
    ...
  P4-{phase-slug}/
    S01-sprint-planning.md
    S02-scaffold.md
    batch-1/
      {story-id}/
        S03-create-story.md
        S04-dev-story.md
        S05-qa-story.md
        S06-review-story.md
      {story-id}/
        ...
    batch-2/
      ...
    S07-e2e-qa.md
    DELIVERABLE.md
```

### Naming Rules

| Element | Pattern | Example |
|---------|---------|---------|
| Phase directory | `P{N}-{slug}` | `P1-analysis`, `P3-solutioning` |
| Step output file | `S{NN}-{slug}.md` | `S01-idea-enrichment.md` |
| Phase deliverable | `DELIVERABLE.md` | (always this exact name) |
| Progress log | `PROGRESS.md` | (always this exact name) |
| Original request | `REQUEST.md` | (always this exact name) |
| Batch directory | `batch-{N}` | `batch-1`, `batch-2` |
| Story directory | `{story-id}` | `AUTH-001`, `DATA-002` |

- Phase `N`: 1-indexed, matches pipeline phase order
- Step `NN`: 01-padded, unique within phase
- Slugs: English kebab-case, 1:1 match with step names in workflow files
- Story IDs: match story spec filenames (e.g., `AUTH-001` from `stories/AUTH-001-login-flow.md`)

---

## Step Output File Format

Each step produces exactly one output file at its designated path. This file serves dual purpose:
checkpoint during execution (tracks rounds) and final deliverable after convergence.

### During Execution (IN_PROGRESS)

```markdown
---
phase: P{N}-{slug}
step: S{NN}-{slug}
status: IN_PROGRESS
rounds_completed: {N}
---

# Round 1

## Thesis
{thesis full output — position, reasoning, self-assessment}

## Antithesis
{antithesis full response — evaluation, response type, contentions}

## Round Result: {COUNTER | REFINE | ACCEPT}

---

# Round 2

## Thesis
{revised thesis output}

## Antithesis
{antithesis re-evaluation}

## Round Result: {COUNTER | REFINE | ACCEPT}

---
```

Round content is saved in full during execution to enable session resume.
`rounds_completed` is incremented after each complete round (both thesis and antithesis).

### After Convergence (DONE)

```markdown
---
phase: P{N}-{slug}
step: S{NN}-{slug}
status: DONE
rounds_completed: {N}
convergence_reason: "{one-line summary of why convergence was reached}"
---

# Rounds

## Round 1: {COUNTER | REFINE}
Thesis: {1-2 sentence summary}
Antithesis: {1-2 sentence summary of response}

## Round 2: {ACCEPT}
Thesis: {1-2 sentence summary}
Antithesis: {1-2 sentence summary}

---

# Output

{final deliverable content — the primary artifact of this step}

---

## Next Step Input

{structured summary of what the next step must consume —
 extracted key information, not the full output}
```

After convergence, round content is **compressed to summaries**. The full content is no longer
needed (it served its checkpoint purpose). The `# Output` section contains the complete deliverable.

### On HALT

```markdown
---
phase: P{N}-{slug}
step: S{NN}-{slug}
status: HALTED
rounds_completed: {N}
halt_reason: "{circular_argumentation | external_contradiction | missing_information | scope_escalation}"
---

# Rounds
{round summaries as above}

---

# Partial Output

{best available output at time of halt}

---

# Halt Report

## Reason
{detailed explanation of why convergence was not reached}

## Final Positions
- **Thesis**: {final thesis position summary}
- **Antithesis**: {final antithesis position summary}

## MetaAgent Assessment
{which position is stronger and why, recommended resolution}
```

---

## PROGRESS.md Format

The progress log tracks overall project state. MainOrchestrator reads this on startup to
determine resume point.

```markdown
---
pipeline: {sdlc | gamedev}
request_file: _workspace/REQUEST.md
created: {ISO 8601 timestamp}
updated: {ISO 8601 timestamp}
current: {P{N}-{slug}/S{NN}-{slug}}
---

# P1-{phase-slug}

| Step | Status | Output | Updated |
|------|--------|--------|---------|
| S01-{slug} | DONE | P1-{slug}/S01-{slug}.md | {timestamp} |
| S02-{slug} | DONE | P1-{slug}/S02-{slug}.md | {timestamp} |
| S03-{slug} | RUNNING | | {timestamp} |
| S04-{slug} | PENDING | | |

# P2-{phase-slug}

| Step | Status | Output | Updated |
|------|--------|--------|---------|
| S01-{slug} | PENDING | | |
| ... | | | |
```

### Phase 4 with Story Pipelines

```markdown
# P4-implementation

| Step | Status | Output | Updated |
|------|--------|--------|---------|
| S01-sprint-planning | DONE | P4-.../S01-sprint-planning.md | ... |
| S02-scaffold | DONE | P4-.../S02-scaffold.md | ... |
| batch-1/AUTH-001/S03-create-story | DONE | ... | ... |
| batch-1/AUTH-001/S04-dev-story | DONE | ... | ... |
| batch-1/AUTH-001/S05-qa-story | SKIPPED | | |
| batch-1/AUTH-001/S06-review-story | DONE | ... | ... |
| batch-1/DATA-001/S03-create-story | RUNNING | | ... |
| S07-e2e-qa | PENDING | | |
```

### Status Values

| Status | Meaning | Transition |
|--------|---------|------------|
| `PENDING` | Not started | → RUNNING |
| `RUNNING` | Session in progress | → DONE, HALTED |
| `DONE` | Converged successfully | Terminal |
| `HALTED` | Stopped, needs intervention | → RUNNING (retry) |
| `SKIPPED` | Conditionally skipped | Terminal |

### Resume Logic (MainOrchestrator)

```
1. Read PROGRESS.md
2. Find first non-terminal step (not DONE, not SKIPPED):
   a. RUNNING → check step output file:
      - output exists with status: DONE → mark DONE in PROGRESS, move to next
      - output exists with status: IN_PROGRESS → re-invoke step (Meta resumes from checkpoint)
      - output missing → reset to PENDING, start fresh
   b. PENDING → start this step
   c. HALTED → report to user, offer retry or skip
3. Update PROGRESS.md before and after each step invocation
```

---

## DELIVERABLE.md Format

Written by MetaAgent at the last step of each phase. Contains the phase exit contract —
the structured handoff for the next phase.

```markdown
---
phase: P{N}-{slug}
pipeline: {sdlc | gamedev}
next_phase: P{N+1}-{slug}
created: {ISO 8601 timestamp}
---

# Phase {N} Deliverable: {Phase Name}

## Summary
{2-3 sentence summary of what this phase produced}

## {Exit Contract Field 1}
{content — as defined in sdlc-phases.md or gamedev-phases.md inter-phase contracts}

## {Exit Contract Field 2}
{content}

...

## Key Decisions
- {Decision 1}: {rationale}
- {Decision 2}: {rationale}

## Deferred Items
- {items explicitly deferred to later phases}
```

The exact fields under the exit contract vary by phase and pipeline type. See:
- `references/sdlc-phases.md` → Inter-Phase Deliverable Contracts
- `references/gamedev-phases.md` → Inter-Phase Deliverable Contracts

### Cross-Phase Reference Rule

**Next phase's steps may ONLY read the previous phase's `DELIVERABLE.md`.**
They must NOT directly reference individual step output files from the previous phase.
This enforces clean phase boundaries and prevents context leakage.

---

## Step Required/Optional Semantics

Each workflow step is classified as **Required** or **Optional**:

- **Required**: Always executed. Cannot be skipped.
- **Optional**: May be skipped based on project scope. Has a `Skip Condition`
  describing when to skip.

### Consistency Rules

1. Required step's output → downstream may reference as `required:` or `optional:`
2. Optional step's output → downstream must reference as **`optional:` only**
3. Required steps must function correctly with only `required:` inputs
4. DELIVERABLE.md exit contract fields sourced from optional steps may be marked
   "Deferred" or "Not analyzed" when those steps were skipped

### PROGRESS.md Handling

Optional steps excluded by the user are initialized as `SKIPPED` in PROGRESS.md:

```
| S02-tech-research | SKIPPED | | {timestamp} |
```

MainOrchestrator skips `SKIPPED` steps and proceeds to the next step.
MetaAgent handles missing optional inputs by notifying agents that the
corresponding research was not performed.

---

## Read Scope Rules

Each workflow step defines its Read Scope — the explicit list of files MetaAgent may load
and pass to thesis/antithesis agents.

### Rules

1. **Cross-phase**: Only `DELIVERABLE.md` from the immediately preceding phase
2. **Within-phase**: Only step output files explicitly listed in the workflow's `Read Scope` section
3. **Original request**: `REQUEST.md` is available to Phase 1 steps only
4. **Phase 4 stories**: Each story pipeline step reads only files within its own story directory
   (plus architecture/scaffold artifacts shared across all stories)

### Enforcement

MetaAgent enforces Read Scope by only loading listed files into thesis/antithesis context.
This is a process-level enforcement (MetaAgent follows the rule), not filesystem-level.

---

## Workflow File Reference

Step definitions live in workflow files under `skills/tas/workflows/`:

```
workflows/
  sdlc/
    P1-analysis.md
    P2-planning.md
    P3-solutioning.md
    P4-implementation.md
  gamedev/
    P1-preproduction.md
    P2-design.md
    P3-technical.md
    P4-production.md
```

Each workflow file defines all steps within a phase. MainOrchestrator reads the step list
from the workflow file. MetaAgent reads the step details (goal, roles, criteria) from the
workflow file at session start.

See individual workflow files for step-level definitions.
