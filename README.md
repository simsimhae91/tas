# tas — Dialectic Workflow Plugin for Claude Code

**English** · [한국어](./README.ko.md)

A Claude Code plugin that runs user requests through **thesis–antithesis–synthesis (정반합)** using multi-agent orchestration. Adaptive 1–4 step workflows, user-controlled iteration loops, and cumulative lessons learned between passes.

> Why use it? Most AI coding agents produce a single-pass answer. `tas` forces two agents to argue — one proposes, one attacks — until they converge. For ambiguous or high-stakes work, this surfaces failures a single pass would miss.

---

## Requirements

- **Claude Code** ≥ 2.x (plugin system support)
- **Python 3.10+** (runs the dialectic engine)
- **`claude-agent-sdk`** Python package — install with any of:
  ```bash
  pip install claude-agent-sdk
  # or
  pipx install claude-agent-sdk
  # or
  uv tool install claude-agent-sdk
  ```
- **`jq`** (for the `Stop` hook's deliverable-integrity guard — optional, gracefully skipped if absent)

The `SessionStart` hook checks Python + SDK availability and prints install guidance if missing, so you'll know on first launch.

---

## Installation

Three options depending on your use case.

### Option A — Install from the public marketplace (recommended)

```
/plugin marketplace add https://github.com/simsimhae91/tas.git
/plugin install tas@tas
```

Persistent across sessions. First `tas` is the plugin name, second is the marketplace name (both happen to be `tas`).

Remove with:
```
/plugin uninstall tas@tas
/plugin marketplace remove tas
```

### Option B — Local development (not persistent)

If you've cloned the repo for hacking:

```bash
git clone https://github.com/simsimhae91/tas.git /path/to/tas
claude --plugin-dir /path/to/tas
```

Loads for that session only. Useful while editing `SKILL.md` / agent prompts.

### Option C — Local marketplace (persistent from a clone)

```bash
git clone https://github.com/simsimhae91/tas.git /path/to/tas
```
Then in Claude Code:
```
/plugin marketplace add /path/to/tas
/plugin install tas@tas
```

---

## Skills

Installing the plugin registers five skills:

| Command | Purpose |
|---------|---------|
| `/tas {request}` | Main dialectic workflow — classify, plan approval, execute |
| `/tas-review [ref\|diff]` | Lightweight dialectic code review against a git ref or PR |
| `/tas-verify [file]` | Post-synthesis boundary-value tracing on produced code |
| `/tas-explain [run-id]` | Plain-language summary of a past dialectic dialogue |
| `/tas-workspace [list\|show\|clean]` | Inspect or clean up `_workspace/quick/` |

All five share the same scope prohibition: they never read your project source code except where a specific task requires it (e.g., `/tas-review` reads the diff it's reviewing). The dialectic engine is what reads and edits code, not the orchestrator.

---

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
| 1 | MetaAgent (合) | Runs as an `Agent()` subagent; classifies then executes |
| 2 | ThesisAgent (正) / AntithesisAgent (反) | Claude SDK sessions managed by `dialectic.py` |

Context isolation prevents context-window exhaustion. MainOrchestrator provides inputs and parses JSON output. MetaAgent handles everything else.

---

## Usage

```
/tas {request}
```

There is only one mode — **quick**. MetaAgent's classifier decides the step count (1–4) from the request's actual complexity.

### Examples

```
/tas TypeScript retry 함수 설계해줘              # simple — single step
/tas 이 코드의 에러 핸들링 리뷰                   # review — 2–3 steps
/tas 결제 버튼이 안 눌려요 고쳐주세요              # medium — 기획/구현/검증
/tas 대시보드에 실시간 알림 추가해줘               # complex — 기획/구현/검증/테스트
```

### Complexity levels

| Level | Step count | Example |
|-------|-----------|---------|
| `simple` | 1 | Single-function design, narrow question, tiny fix |
| `medium` | 2–3 | Multi-file change, new feature in existing module |
| `complex` | 4 | New user-facing behavior, wide integration |

Before execution, MetaAgent proposes the plan (steps + goals + pass criteria) and the user approves or adjusts.

### The canonical 4-step flow

For complex implementation work:

| Step | Role | What happens |
|------|------|--------------|
| **1. 기획 (Plan)** | 正 proposes, 反 challenges | Approach, affected files, interfaces, constraints |
| **2. 구현 (Implement)** | 正 writes code, 反 reviews | Code lands on disk (via `bypassPermissions`) |
| **3. 검증 (Verify)** — *inverted* | 正 attacks, 反 judges | Static review; 0 blockers = PASS, ≥1 = FAIL → retry 구현 |
| **4. 테스트 (Test)** — *inverted* | 正 runs tests, 反 evaluates | Static + dynamic (Playwright for web); PASS or FAIL → retry 구현 |

Within an iteration, FAIL → 구현 retries are unbounded until PASS or persistent failure (same blockers 3× consecutive → HALT). No fixed retry cap — the dialectic handles resolution naturally.

### Iteration loop (Ralph pattern)

The user specifies `loop_count` at plan approval. Default is 1 (single pass, no polish loop). For polish-sensitive work, raise it:

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

**Early exit**: when both agents agree further polish would be fruitless, the loop terminates before reaching `loop_count`.

### Testing strategy by domain

The 테스트 step adapts to project domain (detected during classify):

| Domain | Strategy |
|--------|----------|
| `web-frontend` | Unit tests + Playwright navigation + screenshots + UI/UX evaluation |
| `web-backend` / `api` | Unit tests + integration tests against real endpoints |
| `cli` | Unit tests + subprocess execution with real args |
| `library` | Unit tests + usage-example verification |

### Workspace layout

Since **0.2.5**, every `/tas` run lands in a **session-isolated git worktree** under the XDG cache — your project tree is never modified directly by the dialectic engine.

```
~/.cache/tas-sessions/
  LATEST → 20260423T060506Z/myproject/           # symlink to the most recent session
  20260423T060506Z/
    myproject/                                   # git worktree on branch tas/session-20260423T060506Z
      _workspace/
        quick/
          {YYYYmmdd_HHMMSS}/
            REQUEST.md
            DELIVERABLE.md                       # final cross-iteration synthesis
            lessons.md                           # cumulative lessons learned
            checkpoint.json                      # resume state (11-field schema)
            plan.json                            # classified plan
            iteration-1/
              DELIVERABLE.md                     # this iteration's output
              logs/
                step-1-plan/
                  round-1-thesis.md, round-1-antithesis.md, ...
                  deliverable.md
                step-2-implement/
                step-3-verify/
                step-3-verify-retry-1/           # within-iter FAIL retry
                step-4-test/
            iteration-2/                         # only if loop_count > 1
              ...
```

Each session lives on a named branch (`tas/session-{ts}`) so the work is reviewable and mergeable as a single unit: `git merge tas/session-{ts}`. The `LATEST` symlink is the single entry point for `/tas --resume` and the companion commands (`/tas-explain`, `/tas-workspace`, `/tas-review`). Sessions are retained after PASS or HALT for forensics — use `/tas-workspace clean` to prune old ones.

If `/tas` is interrupted (context reset, HALT, network hiccup), re-run with `/tas --resume` to pick up from the last step checkpoint.

---

## Hooks

The plugin ships two hooks, registered via `hooks/hooks.json`:

| Hook | Event | Behavior |
|------|-------|----------|
| `session-start.sh` | `SessionStart` | Read-only preflight — checks Python + `claude-agent-sdk`, prints install hint if missing |
| `stop-check.sh` | `Stop` | Blocks session exit if `/tas` ran but `DELIVERABLE.md` is missing/empty. Skips while dialectic is still active (process detection + mtime check) |

Both hooks no-op in non-`tas` sessions and respect `stop_hook_active` to prevent recursion.

---

## Configuration

| Setting | Default | Adjustable By |
|---------|---------|---------------|
| MetaAgent model | `opus` | Fixed — classify/execute run on the most capable model |
| Dialectic model (Thesis/Antithesis) | `claude-sonnet-4-6` | `agents/meta.md` step-config `model` field + `runtime/dialectic.py` fallback |
| Workspace | `~/.cache/tas-sessions/{ts}/<project>/_workspace/quick/{timestamp}/` | Session worktree per run (0.2.5+); `LATEST` symlink resolves the most recent |
| Loop count | 1 | User at plan approval (`loop_count`) |
| Reentry point | `구현` | User at plan approval (`loop_policy.reentry_point`) |
| Persistent-fail HALT | after 3 consecutive same-blocker FAILs | `loop_policy.persistent_failure_halt_after` |
| Early exit | allowed when agents agree no further polish | `loop_policy.early_exit_on_no_improvement` |
| Output language | English (unless user explicitly requests another language) | detected at classify time |

To change the dialectic model (e.g., back to opus for higher quality, or haiku for speed), edit both:
- `skills/tas/agents/meta.md` — the `model` field in the step-config JSON template
- `skills/tas/runtime/dialectic.py` — the `config.get("model", ...)` fallback

---

## File structure

```
tas/
├── .claude-plugin/
│   ├── plugin.json                 # Plugin manifest (registers hooks)
│   └── marketplace.json            # Marketplace catalog (single-plugin)
├── hooks/
│   ├── hooks.json                  # SessionStart + Stop hook registration
│   ├── session-start.sh            # Python/SDK preflight
│   └── stop-check.sh               # DELIVERABLE.md integrity guard
├── skills/
│   ├── tas/                        # Main dialectic workflow
│   │   ├── SKILL.md                # MainOrchestrator (thin scheduler)
│   │   ├── agents/
│   │   │   ├── meta.md             # MetaAgent (合) — classify + execute
│   │   │   ├── thesis.md           # ThesisAgent (正)
│   │   │   └── antithesis.md       # AntithesisAgent (反)
│   │   ├── runtime/
│   │   │   ├── dialectic.py        # PingPong dialectic engine
│   │   │   ├── run-dialectic.sh    # Shell wrapper
│   │   │   └── requirements.txt    # claude-agent-sdk dependency pin
│   │   └── references/
│   │       ├── workflow-patterns.md   # 4-step canonical + adaptive templates
│   │       ├── workspace-convention.md
│   │       └── recommended-hooks.md
│   ├── tas-review/SKILL.md         # Dialectic code review
│   ├── tas-verify/SKILL.md         # Post-synthesis boundary tracing
│   ├── tas-explain/SKILL.md        # Dialogue summarizer
│   └── tas-workspace/SKILL.md      # Workspace management
├── CLAUDE.md                       # Development meta-guide (for contributors)
└── README.md
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `claude-agent-sdk is not installed` at session start | Python SDK missing | `pip install claude-agent-sdk` (or `pipx` / `uv`), then restart session |
| `/tas` does nothing / hangs | Dialectic engine subprocess died | Check `_workspace/quick/{latest}/logs/step-*/` for errors |
| Session blocked on exit with "DELIVERABLE.md is missing" | `/tas` ran but didn't finish | Re-run `/tas`, or exit again to override, or `/tas-workspace clean` |
| Hooks don't fire | `plugin.json` missing `"hooks"` key | Verify `.claude-plugin/plugin.json` has `"hooks": "./hooks/hooks.json"` |
| "Plugin not found" after `/plugin install` | Marketplace added without `marketplace.json` | Repo must contain `.claude-plugin/marketplace.json` — pull latest |

---

## License

MIT
