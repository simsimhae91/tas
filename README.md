# tas — Dialectic Workflow Plugin for Claude Code

A Claude Code plugin that runs user requests through **thesis-antithesis-synthesis (정반합)** using multi-agent orchestration. Adaptive 1-4 step workflows with user-controlled iteration loops and cumulative lessons learned.

## How It Works

```
/tas {request}
  │
  ├── Trivial? → respond directly
  │
  └── MetaAgent Classify (Agent subagent)
        │ returns plan JSON: {complexity, steps, loop_count, loop_policy}
        ▼
      User approval (can adjust loop_count, reentry_point)
        │
        ▼
      MetaAgent Execute (Agent subagent)
        │
        └── For iteration i in 1..loop_count:
              └── For each step (기획→구현→검증→테스트 or subset):
                    python3 dialectic.py
                    正 proposes → 反 responds → dialogue until convergence
                    │
                    └── On 검증/테스트 FAIL → retry 구현
                        (HALT if same blocker recurs 3× consecutive)
              └── Write iteration-{i}/DELIVERABLE.md
              └── Append lessons learned to lessons.md
              └── Next iteration receives all prior lessons + focus angle
```

Three layers, each with a strict context boundary:

| Layer | Agent | Boundary |
|-------|-------|----------|
| 0 | MainOrchestrator | Thin scheduler — never sees internal dialectic |
| 1 | MetaAgent (合) | Runs as an Agent() subagent; classifies then executes |
| 2 | ThesisAgent (正) / AntithesisAgent (反) | Claude SDK sessions managed by `dialectic.py` |

Context isolation prevents context exhaustion. MainOrchestrator provides inputs and parses JSON output. MetaAgent handles everything else.

## Installation

```bash
# Clone the repo
git clone <repo-url> /path/to/tas

# Install the dialectic engine dependency
pip install claude-agent-sdk

# Use as a plugin directory
claude --plugin-dir /path/to/tas
```

Registers two skills: `/tas` (dialectic orchestration) and `/tas-verify` (post-synthesis verification).

## Usage

```
/tas {request}
```

There is only one mode — **quick**. MetaAgent's classifier decides the step count (1-4) from the request's actual complexity.

### Examples

```
/tas TypeScript retry 함수 설계해줘              # simple — single step
/tas 이 코드의 에러 핸들링 리뷰                   # review — 2-3 steps
/tas 결제 버튼이 안 눌려요 고쳐주세요              # medium — 기획/구현/검증
/tas 대시보드에 실시간 알림 추가해줘               # complex — 기획/구현/검증/테스트
```

### Complexity Levels

| Level | Step Count | Example |
|-------|-----------|---------|
| `simple` | 1 | Single-function design, narrow question, tiny fix |
| `medium` | 2-3 | Multi-file change, new feature in existing module |
| `complex` | 4 | New user-facing behavior, wide integration |

Before execution, MetaAgent proposes the plan (steps + goals + pass criteria) and the user approves or adjusts.

### The Canonical 4-Step Flow

For complex implementation work:

| Step | Role | What happens |
|------|------|--------------|
| **1. 기획 (Plan)** | 正 proposes, 反 challenges | Approach, affected files, interfaces, constraints |
| **2. 구현 (Implement)** | 正 writes code, 反 reviews | Code lands on disk (via bypassPermissions) |
| **3. 검증 (Verify)** — *inverted* | 正 attacks, 反 judges | Static review; 0 blockers = PASS, ≥1 = FAIL → retry 구현 |
| **4. 테스트 (Test)** — *inverted* | 正 runs tests, 反 evaluates | Static + dynamic (Playwright for web); PASS or FAIL → retry 구현 |

Within an iteration, FAIL → 구현 retries are unbounded until PASS or persistent failure (same blockers 3× consecutive → HALT). No fixed retry cap — the dialectic handles resolution naturally.

### Iteration Loop (Ralph Pattern)

The user specifies `loop_count` at plan approval. Default is 1 (single pass, no polish loop). For polish-sensitive work, set higher:

```
Iteration 1: Baseline — full 기획→구현→검증→테스트
Iteration 2: Reentry from 구현 with "focus angle" + accumulated lessons
Iteration 3: Next focus angle + all prior lessons
...
```

Each iteration:
- Applies a **focus angle** (UX polish, accessibility, performance, edge cases, etc.)
- Builds on the previous iteration's output (not from scratch)
- Receives all accumulated `lessons.md` content as context
- Produces its own `iteration-{N}/DELIVERABLE.md`
- Appends an entry to `lessons.md` (what improved, blockers resolved, open observations, rejected alternatives)

Early exit: when both agents agree further polish would be fruitless, the loop terminates before reaching `loop_count`.

### Testing Strategy by Domain

The 테스트 step adapts to project domain (detected during classify):

| Domain | Strategy |
|--------|----------|
| `web-frontend` / `web-backend-with-ui` | Unit tests + Playwright navigation + screenshots + UI/UX evaluation |
| `web-backend` / `api` | Unit tests + integration tests against real endpoints |
| `cli` | Unit tests + subprocess execution with real args |
| `library` | Unit tests + usage-example verification |

### Workspace

```
_workspace/
  quick/
    {YYYYmmdd_HHMMSS}/
      REQUEST.md
      DELIVERABLE.md                 # final cross-iteration synthesis
      lessons.md                     # cumulative lessons learned
      iteration-1/
        DELIVERABLE.md               # this iteration's output
        logs/
          step-1-plan/
            round-1-thesis.md, round-1-antithesis.md, ...
            deliverable.md
          step-2-implement/
          step-3-verify/
          step-3-verify-retry-1/     # within-iter FAIL retry
          step-4-test/
      iteration-2/                   # only if loop_count > 1
        ...
```

Every run is timestamped and isolated. No resume mechanism — each `/tas` invocation is a fresh session.

### Post-Synthesis Verification

```
/tas-verify                     # verify last tas output (latest _workspace/quick/*)
/tas-verify path/to/file.ts     # verify specific file
```

tas's 검증 step performs static review during the dialectic. `/tas-verify` adds **concrete-value boundary tracing** — catching defects that text-based review misses.

## File Structure

```
tas/
├── .claude-plugin/
│   └── plugin.json                 # Plugin metadata
├── skills/
│   ├── tas/
│   │   ├── SKILL.md                # MainOrchestrator (thin scheduler)
│   │   ├── agents/
│   │   │   ├── meta.md             # MetaAgent (合) — classify + execute
│   │   │   ├── thesis.md           # ThesisAgent (正)
│   │   │   └── antithesis.md       # AntithesisAgent (反)
│   │   ├── runtime/
│   │   │   ├── dialectic.py        # PingPong dialectic engine
│   │   │   ├── run-dialectic.sh    # Shell wrapper
│   │   │   └── requirements.txt    # claude-agent-sdk dependency
│   │   └── references/
│   │       ├── workflow-patterns.md   # 4-step canonical + adaptive templates
│   │       ├── workspace-convention.md
│   │       └── recommended-hooks.md
│   └── tas-verify/
│       └── SKILL.md                # Post-synthesis boundary tracing
├── CLAUDE.md                       # Development meta-guide
└── README.md
```

## License

MIT
