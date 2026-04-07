# tas — Development Guide

## What is tas?

tas is a Claude Code plugin that applies thesis-antithesis-synthesis (정반합) to produce higher-quality outputs through multi-agent dialectical review. It uses a 3-layer orchestration architecture and supports both single requests and full SDLC/GameDev pipelines.

## Architecture

```
MainOrchestrator (SKILL.md, depth 0)
  └── For each step in workflow file:
        claude -p (separate process, per step)
          └── MetaAgent (合, depth 0 in own process)
                ├── ThesisAgent (正, depth 1, leaf)
                ├── AntithesisAgent (反, depth 1, leaf)
                └── ConflictResolver (depth 1, leaf, sprint only)
```

### Architecture Invariants

- **MainOrchestrator** (SKILL.md) is a thin scheduler — parses request, manages PROGRESS.md, invokes MetaAgent per step, presents results
- **MetaAgent** (合) is the per-step workflow executor — reads workflow definition file, runs single-step 정반합, manages checkpoints
- **ThesisAgent** (正) is always **FIRST MOVER** — proposes position with reasoning, defends or concedes through dialogue
- **AntithesisAgent** (反) is always **REACTIVE** — responds with COUNTER, REFINE, or ACCEPT; proposes alternatives, not just critique
- MetaAgent runs in its own process (`CLAUDECODE=0 claude -p`) with its own context window
- **One step per session**: Each workflow step gets its own MetaAgent process with fresh context
- These roles prevent the deadlock resolved in commit e38ec8d
- **Convergence model**: No fixed iteration caps — dialogue continues until genuine agreement (ACCEPT) or irrecoverable HALT (circular argumentation, external contradiction, missing information)
- Multi-phase projects: each **step** gets its own MetaAgent process with `WORKFLOW_FILE` + `STEP_ID`

### Execution Modes

| Mode | Trigger | Session Granularity |
|------|---------|---------------------|
| Single-request | Non-project scope | 1 session, MetaAgent handles multi-step internally |
| Pipeline | Project scope | 1 session per step, MainOrchestrator iterates |

### Phase 4 Implementation Pattern (7 Steps)

Both SDLC and GameDev use the same 7-step sprint pattern:

| Step | 정반합 Role | Convergence |
|------|------------|-------------|
| S01 Sprint Planning | planner / plan-auditor | plan-validity (light) |
| S02 Scaffold | builder / arch-verifier | arch-conformance (light) |
| S03 Create Story | spec-writer / spec-reviewer | spec-quality (medium) |
| S04 Dev Story | implementer / diff-reviewer | ac-fulfillment (heavy) |
| S05 QA Story | test-runner / - | automated (minimal, conditional) |
| S06 Review Story | **attacker / judge** | **issue-verdict (heavy, inverted)** |
| S07 E2E QA | integration-tester / gap-finder | integration-quality (medium) |

S06 uses **inverted convergence**: thesis attacks (finds defects), antithesis judges (filters false positives). FAIL → loop to S04.

## Quality Invariants

The tas process must catch issues that a human expert reviewer would catch. The following are **not edge cases** — they are design defects when violated:

1. **Semantic consistency** — the same concept means the same thing in every appearance (parameters, callbacks, errors, docs)
2. **Behavioral consistency** — all code paths for the same operation behave identically under the same contract
3. **Compositional integrity** — when function A's output feeds into function B, the composition is sound for ALL valid inputs
4. **Value flow soundness** — no intermediate computation in the call chain produces NaN, Infinity, or an unexpected type, even if a downstream cap would "fix" it

If a tas session produces code that violates any of these, the gap is in the **review process**, not in the produced code. The remedy is improving the lenses, not adding edge-case guards.

## Defensive Measure Rule

A cap, clamp, or guard is correctly placed only when it is applied **before** the value is consumed by further computation. If `computeDelay` returns Infinity and the caller caps it afterward, any intermediate use (like `Math.random() * Infinity`) is already corrupted. This is a **composition order** defect.

## Key Files

| File | Role |
|------|------|
| `skills/tas/SKILL.md` | MainOrchestrator — thin scheduler, PROGRESS.md management, per-step invocation |
| `skills/tas/agents/meta.md` | MetaAgent (合) — single-step executor, workflow file reader, checkpoint management |
| `skills/tas/agents/thesis.md` | ThesisAgent (正) — position holder with reasoning, defense/concession through dialogue |
| `skills/tas/agents/antithesis.md` | AntithesisAgent (反) — counter-position with alternatives, 4 review lenses, convergence-seeking |
| `skills/tas/agents/conflict-resolver.md` | Merge conflict resolution for sprint execution |
| `skills/tas/references/workspace-convention.md` | Workspace directory structure, output format, PROGRESS.md format, Read Scope rules |
| `skills/tas/references/workflow-patterns.md` | Workflow templates for single-request mode |
| `skills/tas/references/sdlc-phases.md` | SDLC inter-phase deliverable contracts |
| `skills/tas/references/gamedev-phases.md` | Game Dev inter-phase deliverable contracts |
| `skills/tas/references/story-spec-format.md` | Standard format for implementation stories |
| `skills/tas/references/sprint-planning.md` | Sprint batching algorithm for parallel implementation |
| `skills/tas/references/recommended-hooks.md` | Hook recommendations for target projects |
| `skills/tas/workflows/sdlc/P{1-4}-*.md` | SDLC step-by-step workflow definitions (4 files) |
| `skills/tas/workflows/gamedev/P{1-4}-*.md` | Game Dev step-by-step workflow definitions (4 files) |
| `skills/tas-verify/SKILL.md` | Post-synthesis independent verification |

## Development Conventions

- All agent definitions are markdown — no build step required
- Lenses in antithesis.md are **perspectives**, not checklists — apply them by reading the deliverable through each perspective
- Pass criteria: verifiable, specific, relevant, countable (3-6 per step)
- Workspace audit trails in `_workspace/` are the source of truth for session history
- Review lenses must require **concrete value tracing**, not just semantic assertion
- MetaAgent's last stdout line is always a JSON output contract
- Inter-phase context flows via `DELIVERABLE.md` → `PHASE_CONTEXT` parameter
- Implementation phase uses worktree isolation (`isolation: "worktree"`) for parallel stories

### Per-Step Session Conventions

- Workflow step definitions live in `workflows/` directory, not in agent code
- MainOrchestrator reads step lists from workflow files; MetaAgent reads step details
- **Read Scope enforcement**: cross-phase only DELIVERABLE.md, within-phase only explicit step outputs
- **PROGRESS.md** is the resume mechanism — MainOrchestrator reads it on startup to find resume point
- **Checkpoint**: each step's output file has frontmatter with `status` and `rounds_completed`
- Each round's thesis/antithesis output is saved to the step file for intra-step resume
- After convergence, round content is compressed to summaries; `# Output` section holds the final deliverable
- `Next Step Input` section in each step output provides structured context for the following step

### Step Selection (Required/Optional)

- Each workflow step is classified as **Required** or **Optional** (defined in workflow files with `### Required` field)
- Optional steps have a `### Skip Condition` describing when to skip
- MainOrchestrator recommends step inclusion/exclusion based on project scope during Phase 0.5
- Optional step outputs are always referenced as `optional:` in downstream Read Scopes
- Required steps must function correctly with only `required:` inputs — optional inputs enrich but are not necessary
- When optional inputs are absent, MetaAgent notifies agents so they adapt expectations
