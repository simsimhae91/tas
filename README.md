# tas — Dialectic Workflow Plugin for Claude Code

A Claude Code plugin that runs user requests through **thesis-antithesis-synthesis (정반합)** using multi-agent orchestration. Supports single requests (quick mode) and full project pipelines (SDLC / GameDev).

## How It Works

```
/tas {request}  →  MainOrchestrator
                     │
                     ├── Trivial? → respond directly
                     └── Non-trivial → MetaAgent (separate process)
                                         │
                                         正 proposes → 反 responds
                                         Dialogue until convergence
                                         │
                                         Synthesized output
```

Three layers, each with a strict boundary:

| Layer | Agent | Boundary |
|-------|-------|----------|
| 0 | MainOrchestrator | Thin scheduler — never sees internal dialectic |
| 1 | MetaAgent (合) | Runs in its own `claude -p` process per step |
| 2 | ThesisAgent (正) / AntithesisAgent (反) | Leaf agents, internal to MetaAgent |

**Process isolation** prevents context exhaustion. MainOrchestrator provides inputs, parses JSON output, manages PROGRESS.md. MetaAgent handles everything else.

## Installation

```bash
# Clone and register as a plugin
git clone <repo-url> /path/to/tas
claude plugins add /path/to/tas
```

Registers two skills: `/tas` (dialectic orchestration) and `/tas-verify` (post-synthesis verification).

## Usage

```
/tas {request}                  # quick mode — single dialectic
/tas sdlc {request}             # full SDLC pipeline
/tas game {request}             # game development pipeline
```

### Examples

```
/tas TypeScript retry 함수 설계해줘              # quick — design review
/tas 이 코드의 에러 핸들링 리뷰                   # quick — code review
/tas sdlc Flutter 건강관리 앱 만들어줘            # SDLC pipeline
/tas game Unity 로그라이크 게임 만들어줘          # GameDev pipeline
```

### Quick Mode

Single MetaAgent session. Classifies the request type (implementation, architecture, code review, refactoring, analysis), designs internal workflow steps, runs dialectic until convergence. Output: synthesis report.

### Pipeline Mode

Multi-phase project execution. Each phase produces a `DELIVERABLE.md` that flows to the next. Each step runs in its own `claude -p` process. PROGRESS.md enables resume across sessions.

**SDLC** — 4 phases, 14 steps (+ optional):

| Phase | Steps |
|-------|-------|
| P1 Analysis | Idea Enrichment, Tech Research*, Domain Analysis*, Create Brief |
| P2 Planning | Create PRD, UX Flows*, Validate PRD |
| P3 Solutioning | Architecture, Epic & Story Breakdown, Readiness Check* |
| P4 Implementation | Sprint Planning, Scaffold*, Create/Dev/QA*/Review Story (per-story), E2E QA* |

**GameDev** — 4 phases, 24 steps (+ optional):

| Phase | Steps |
|-------|-------|
| P1 Preproduction | Game Concept Enrichment, Game Brief, Domain Research*, Market Research*, Tech Research*, Create Summary |
| P2 Design | GDD, Narrative Design*, Create PRD, Create UX*, Validate PRD |
| P3 Technical | Game Architecture, Create Stories, Check Readiness*, Project Context*, Test Framework*, Test Design* |
| P4 Production | Same sprint pattern as SDLC P4 |

Steps marked with * are optional — skippable based on project scope.

### Phase 4: Sprint Pattern (Shared)

Both pipelines use the same 7-step sprint execution:

```
S01 Sprint Planning → S02 Scaffold*
  │
  For each batch (stories in parallel):
    S03 Create Story → S04 Dev Story → S05 QA Story* → S06 Review Story
                                                           ├─ PASS → merge
                                                           └─ FAIL → S04 retry (max 2)
  │
  S07 E2E QA*
```

S06 uses **inverted convergence**: thesis finds defects, antithesis judges whether each is a real blocker.

### Workspace

```
_workspace/
  sdlc/            # active SDLC pipeline (stable path, resumable)
  gamedev/         # active GameDev pipeline (stable path, resumable)
  quick/           # quick mode runs (timestamped, independent)
    20260408_140000/
  archive/         # completed/abandoned pipelines
```

Pipeline workspaces use stable paths — re-running `/tas sdlc` resumes from the last incomplete step. Starting a new pipeline archives the previous one.

### Post-Synthesis Verification

```
/tas-verify                     # verify last tas output
/tas-verify path/to/file.ts     # verify specific file
/tas-verify sdlc                # verify pipeline output
```

Traces concrete values through computation chains. Independent from the dialectic — runs after synthesis to catch compositional defects that text-based review misses.

## File Structure

```
tas/
├── .claude-plugin/
│   └── plugin.json                 # Plugin metadata (v0.2.0)
├── skills/
│   ├── tas/
│   │   ├── SKILL.md                # MainOrchestrator
│   │   ├── agents/
│   │   │   ├── meta.md             # MetaAgent (合)
│   │   │   ├── thesis.md           # ThesisAgent (正)
│   │   │   ├── antithesis.md       # AntithesisAgent (反)
│   │   │   └── conflict-resolver.md
│   │   ├── workflows/
│   │   │   ├── sdlc/
│   │   │   │   ├── manifest.md     # Step metadata (MainOrchestrator reads this)
│   │   │   │   └── P{1-4}-*.md     # Step definitions (MetaAgent reads these)
│   │   │   └── gamedev/
│   │   │       ├── manifest.md
│   │   │       └── P{1-4}-*.md
│   │   └── references/
│   │       ├── workspace-convention.md
│   │       ├── workflow-patterns.md
│   │       ├── sdlc-phases.md
│   │       ├── gamedev-phases.md
│   │       ├── story-spec-format.md
│   │       ├── sprint-planning.md
│   │       └── recommended-hooks.md
│   └── tas-verify/
│       └── SKILL.md                # Post-synthesis verification
├── CLAUDE.md                       # Development meta-guide
└── README.md
```

## License

MIT
