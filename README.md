# dial — Dialectic Workflow Plugin for Claude Code

A Claude Code plugin that executes user requests through a **thesis-antithesis-synthesis (정반합)** dialectical pattern.

## Architecture

```
/dial {request}  →  MetaAgent (合)
                      │
                      ├── Phase 0: Parse request, detect mode
                      ├── Phase 1: Design workflow steps
                      │
                      │   For each step:
                      │   ┌─────────────────────────────────┐
                      │   │  ThesisAgent (正) executes goal  │
                      │   │         ↕ direct dialogue        │
                      │   │  AntithesisAgent (反) reviews    │
                      │   │         ↓                        │
                      │   │  MetaAgent (合) judges verdict   │
                      │   │  PASS → next / FAIL → retry     │
                      │   └─────────────────────────────────┘
                      │
                      └── Phase 3: Synthesis report
```

### Three Agents

| Agent | Role | Behavior |
|-------|------|----------|
| **MetaAgent (合)** | Orchestrator | Designs workflow, judges convergence, delivers synthesis |
| **ThesisAgent (正)** | Executor | Produces deliverables, incorporates feedback on retries |
| **AntithesisAgent (反)** | Supervisor | Strict review against pass criteria, no leniency |

### Two Execution Modes

- **Option B (Agent Teams)**: ThesisAgent and AntithesisAgent communicate directly via SendMessage. Philosophically faithful to dialectics. Used when `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` is set.
- **Option A (Fallback)**: Sequential subagent spawning. MetaAgent relays between agents. Used when Agent Teams is unavailable.

## Installation

```bash
# From local directory
claude --plugin-dir /path/to/dial

# Or symlink into Claude Code skills
ln -s /path/to/dial/skills/dial ~/.claude/skills/dial
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
/dial analyze why the build is failing on CI
```

### What Happens

1. MetaAgent analyzes your request and designs a workflow (1-4 steps)
2. For each step, ThesisAgent produces a deliverable
3. AntithesisAgent reviews against specific pass criteria
4. If any criteria fail, ThesisAgent revises (up to 3 iterations)
5. Final synthesis report with all results

## Workflow Types

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
│   └── plugin.json                  # Plugin manifest
├── skills/
│   └── dial/
│       ├── SKILL.md                 # MetaAgent orchestrator
│       ├── agents/
│       │   ├── thesis.md            # ThesisAgent role definition
│       │   └── antithesis.md        # AntithesisAgent role definition
│       └── references/
│           └── workflow-patterns.md  # Workflow templates
└── README.md
```

## License

MIT
