# dial — Dialectic Workflow Plugin for Claude Code

A Claude Code plugin that executes user requests through a **thesis-antithesis-synthesis (정반합)** dialectical pattern using a 3-layer agent orchestration architecture. Supports both single requests and full SDLC/GameDev pipelines.

## Architecture

```
/dial {request}  →  MainOrchestrator (SKILL.md, depth 0)
                      │
                      ├── Simple request → single MetaAgent call
                      │
                      └── Project scope → per-step session pipeline
                            │
                            For each step (separate claude -p session):
                            └── MetaAgent (合, depth 0)
                                  ├── ThesisAgent (正, depth 1)
                                  └── AntithesisAgent (反, depth 1)
                                  │
                                  ┌────────────────────────────────────┐
                                  │  正 proposes → 反 responds          │
                                  │  (COUNTER / REFINE / ACCEPT)       │
                                  │  Dialogue until convergence or HALT │
                                  └────────────────────────────────────┘
                                  │
                                  Step output → next step
                            │
                            Phase DELIVERABLE.md → next phase
```

### Three Layers

| Layer | Agent | Role |
|-------|-------|------|
| **Layer 0** | MainOrchestrator (SKILL.md) | Thin scheduler — request parsing, PROGRESS.md, per-step invocation |
| **Layer 1** | MetaAgent (合) | Single-step executor — reads workflow file, runs 정반합, checkpoints |
| **Layer 2** | ThesisAgent (正) / AntithesisAgent (反) | Execution and review (leaf agents) |

### Key Design Decisions

- **Per-step sessions**: Each workflow step runs in its own `claude -p` process with fresh context, preventing context pollution and enabling resume
- **Workflow definition files**: Step details (goals, roles, criteria) are defined in markdown files under `workflows/`, not embedded in agent code
- **Required/Optional steps**: Each step is classified as Required or Optional. Optional steps can be skipped based on project scope, reducing overhead for simple projects
- **PROGRESS.md**: Tracks completion state across sessions. Re-running the pipeline resumes from the last incomplete step
- **Intra-step checkpointing**: Each round of thesis/antithesis dialogue is saved to the step output file for mid-step resume

### Execution Modes

- **Option B (Agent Teams)**: ThesisAgent and AntithesisAgent communicate directly via SendMessage
- **Option A (Fallback)**: Sequential subagent spawning with MetaAgent relay

## Installation

```bash
# Symlink into Claude Code skills
ln -s /path/to/dial/skills/dial ~/.claude/skills/dial
ln -s /path/to/dial/skills/dial-verify ~/.claude/skills/dial-verify
```

## Usage

```
/dial {your request}
```

### Examples

```
/dial TypeScript retry 함수 설계
/dial 이 코드의 에러 핸들링 리뷰
/dial 인증 모듈 리팩토링 계획
/dial Flutter 건강관리 앱 만들어줘       ← triggers SDLC pipeline
/dial Unity 로그라이크 게임 만들어줘     ← triggers Game Dev pipeline
```

### Single Request Flow

1. MainOrchestrator parses request, creates workspace, classifies type
2. MetaAgent invoked as `claude -p` process
3. MetaAgent designs workflow steps with pass criteria (uses `workflow-patterns.md`)
4. ThesisAgent proposes position → AntithesisAgent responds (COUNTER/REFINE/ACCEPT)
5. Dialogue continues until genuine convergence; synthesis report returned to user

### Pipeline Flow (Project Scope)

1. MainOrchestrator classifies pipeline (SDLC / Game Dev) and selects steps
2. User confirms step selection (optional steps can be included/skipped)
3. For each step: separate `claude -p` session, MetaAgent reads workflow definition
4. Step output saved with rounds for checkpoint/resume
5. Phase DELIVERABLE.md flows forward as context to next phase

## Pipeline Types

### Software Dev (SDLC) — 4 phases, 17 steps

| Phase | Goal | Steps (R=Required, O=Optional) |
|-------|------|------|
| 1. Analysis | Domain research, feasibility | S01 Enrichment(R), S02 Tech(O), S03 Domain(O), S04 Brief(R) |
| 2. Planning | Requirements, UX | S01 PRD(R), S02 UX Flows(O), S03 Validate(R) |
| 3. Solutioning | Architecture, stories | S01 Architecture(R), S02 Stories(R), S03 Readiness(O) |
| 4. Implementation | Sprint execution | 7 steps — see below |

### Game Dev — 4 phases, 24 steps

| Phase | Goal | Steps (R=Required, O=Optional) |
|-------|------|------|
| 1. Preproduction | Game concept, research | S01 Enrichment(R), S02 Brief(R), S03 Domain(O), S04 Market(O), S05 Tech(O), S06 Summary(R) |
| 2. Design | GDD, narrative, PRD, UX | S01 GDD(R), S02 Narrative(O), S03 PRD(R), S04 UX(O), S05 Validate(R) |
| 3. Technical | Architecture, stories, tests | S01 Architecture(R), S02 Stories(R), S03 Readiness(O), S04 Context(O), S05 Test Framework(O), S06 Test Design(O) |
| 4. Production | Sprint execution | 7 steps — same as SDLC Phase 4 |

### Phase 4: Implementation / Production (7 Steps)

Both pipelines share the same 7-step sprint pattern:

| Step | Role (Thesis / Antithesis) | Required |
|------|---------------------------|----------|
| S01 Sprint Planning | planner / plan-auditor | R |
| S02 Scaffold | builder / arch-verifier | O |
| S03 Create Story | spec-writer / spec-reviewer | R |
| S04 Dev Story | implementer / diff-reviewer | R |
| S05 QA Story | test-runner / — | O |
| **S06 Review Story** | **attacker / judge** (inverted) | R |
| S07 E2E QA | integration-tester / gap-finder | O |

S06 uses **inverted convergence**: thesis aggressively finds defects, antithesis judges whether each is a real blocker. FAIL → loop back to S04.

```
Per batch:
  Stories in parallel → S03 → S04 → S05 → S06
                                              ├─ PASS → merge
                                              └─ FAIL → S04 (retry)
After all batches → S07 E2E QA
```

## Workflow Types (Single Request)

| Type | Steps |
|------|-------|
| Implementation | Design → Implement → Verify |
| Architecture | Requirements → Design → Trade-off Review |
| Code Review | Analysis → Issues → Improvements |
| Refactoring | Current State → Plan → Execute → Regression Check |
| Analysis | Scope → Investigation → Conclusions |

## File Structure

```
dial/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   ├── dial/
│   │   ├── SKILL.md                    # MainOrchestrator — thin scheduler
│   │   ├── agents/
│   │   │   ├── meta.md                 # MetaAgent 合 — single-step executor
│   │   │   ├── thesis.md               # ThesisAgent 正 — first mover
│   │   │   ├── antithesis.md           # AntithesisAgent 反 — reactive reviewer
│   │   │   └── conflict-resolver.md    # Merge conflict resolution
│   │   ├── workflows/
│   │   │   ├── sdlc/                   # SDLC step definitions (4 files)
│   │   │   │   ├── P1-analysis.md
│   │   │   │   ├── P2-planning.md
│   │   │   │   ├── P3-solutioning.md
│   │   │   │   └── P4-implementation.md
│   │   │   └── gamedev/                # Game Dev step definitions (4 files)
│   │   │       ├── P1-preproduction.md
│   │   │       ├── P2-design.md
│   │   │       ├── P3-technical.md
│   │   │       └── P4-production.md
│   │   └── references/
│   │       ├── workspace-convention.md # Directory structure, output format, naming rules
│   │       ├── workflow-patterns.md    # Single-request workflow templates
│   │       ├── sdlc-phases.md          # SDLC inter-phase contracts
│   │       ├── gamedev-phases.md       # Game Dev inter-phase contracts
│   │       ├── story-spec-format.md    # Story spec standard format
│   │       ├── sprint-planning.md      # Sprint batching algorithm
│   │       └── recommended-hooks.md    # Hook recommendations
│   └── dial-verify/
│       └── SKILL.md                    # Independent post-synthesis verification
├── CLAUDE.md
└── README.md
```

## License

MIT
