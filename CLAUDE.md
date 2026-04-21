# tas — Meta-Cognitive Development Guide

This project is a **Claude Code plugin**. The files you edit here are prompts and instructions that other Claude instances will execute. A "code change" in this repo is a **behavior change** in a running agent system.

## The Core Paradox

You (Claude) are editing instructions for yourself (Claude). This creates unique failure modes that don't exist in normal software:

1. **You can't test prompt changes** — there's no compiler, no unit test. You must reason about how a receiving Claude will interpret your edits under diverse user inputs.
2. **Your intuitions are miscalibrated** — you know what you *meant* to write. The receiving Claude only sees what you *actually* wrote, without your conversational context.
3. **You're tempted to optimize for yourself** — the instructions that feel clearest to you right now may be ambiguous to a fresh instance with a different conversation history.

## What You Must Be Aware Of

### Information Hiding Is Load-Bearing

SKILL.md (MainOrchestrator) intentionally does not know MetaAgent internals — thesis/antithesis roles, convergence model, review lenses. This is not an oversight.

**Why**: If the MainOrchestrator Claude learns how 정반합 works internally, it develops a behavioral bias to skip the Agent() call and run the dialectic itself directly. Information hiding is preserved because the Agent() prompt says "Read meta.md and follow it" — MainOrchestrator never sees meta.md's content.

**Implication**: When editing SKILL.md, never add references to agent internals. Never read agent files (meta.md, thesis.md, antithesis.md) from SKILL.md. When editing agent files, don't worry about what SKILL.md knows — they run in separate contexts.

### Turn Order Is Enforced by Python, Not Prompts

The dialectic engine (`runtime/dialectic.py`) controls turn order deterministically:
Thesis always goes first, Antithesis always responds. This is enforced by the Python
PingPong loop — not by agent prompts. The previous SendMessage-based architecture
required prompt-level "FIRST MOVER" / "REACTIVE" discipline to prevent deadlock;
the Python loop makes this structurally impossible.

**Implication**: If you're modifying `dialectic.py`, preserve the strict
thesis-then-antithesis ordering in the main loop. Agent prompts no longer need
turn-order instructions.

### Context Isolation Is the Context Strategy

MainOrchestrator invokes MetaAgent twice per run (classify, then execute) as Agent()
subagents. Within the execute call, the dialectic runs via `python3 dialectic.py` which
manages two `ClaudeSDKClient` sessions per step.

```
MainOrchestrator → MetaAgent: Agent() subagent (context boundary)
MetaAgent → Dialectic: python3 dialectic.py subprocess (process boundary)
Dialectic → Thesis/Antithesis: ClaudeSDKClient stateful sessions (SDK boundary)
```

Each boundary prevents context window contamination. MetaAgent returns ONLY a JSON
summary to MainOrchestrator — no dialectic content flows back. Thesis and Antithesis
maintain their own conversation history within a step (stateful sessions), but sessions
are scoped per-step — state dies between steps.

**Implication**: Don't add mechanisms that share state across steps except through explicit files (per-step `deliverable.md` under `logs/`, final `DELIVERABLE.md`). MetaAgent appends prior step outputs to `cumulative_context` in-memory, but that lives only within the single Execute Mode invocation.

### Scope Prohibition Is a Behavioral Guardrail

MainOrchestrator must never read project source code. Trivial Gate judges from request text alone. These rules exist because Claude has a strong drive to be helpful — without explicit prohibition, it will read the codebase "to better understand the request" and then skip MetaAgent entirely.

**Implication**: If you add any new capability to SKILL.md, verify it doesn't create a path where MainOrchestrator reads project files and decides to handle the request directly.

## Edit Checklist

Before finalizing any edit to an agent file:

- [ ] **Who executes this?** Identify which Claude instance (MainOrchestrator, MetaAgent, ThesisAgent, AntithesisAgent) will read this text.
- [ ] **What context does it have?** That instance has only its system prompt + the input parameters passed to it. Not your current conversation. Not the other agent files.
- [ ] **Does this leak across boundaries?** SKILL.md shouldn't reference agent internals. Agent files shouldn't assume MainOrchestrator behavior.
- [ ] **Is the instruction falsifiable?** "Be thorough" is noise. "Trace the return value of function A through every call site" is actionable.
- [ ] **Would a fresh Claude misread this?** Read your edit as if you had zero context about what it's supposed to do.

## File Roles

| File | Executed By | Edits Affect |
|------|-------------|--------------|
| `SKILL.md` | MainOrchestrator (user's Claude) | Request routing, trivial gate, classify invocation, execute invocation, result presentation |
| `agents/meta.md` | MetaAgent (Agent subagent) | Classify mode (complexity + plan), Execute mode (step loop + Ralph retry), convergence logic |
| `agents/thesis.md` | ThesisAgent (ClaudeSDKClient session) | Position proposal, defense, concession protocol; inverted-mode attacker role |
| `agents/antithesis.md` | AntithesisAgent (ClaudeSDKClient session) | Counter-position, review lenses, convergence seeking; inverted-mode judge role |
| `runtime/dialectic.py` | Python subprocess (invoked by MetaAgent) | PingPong dialogue loop, SDK session management |
| `references/workflow-patterns.md` | MetaAgent only | Request type classification, complexity mapping, 4-step canonical flow, testing strategy by domain |
| `references/workspace-convention.md` | MetaAgent only | Directory structure, DELIVERABLE.md format, retry log conventions |
| `references/recommended-hooks.md` | End users | Optional hook examples for projects that use tas |

## Convergence Model

No fixed iteration caps — artificial caps produce premature consensus. See `agents/meta.md` Convergence Model + `runtime/dialectic.py` degeneration HALTs (rate-limit detection, unparseable verdicts, dialogue degeneration).

**System Prompt Assembly**: Agent templates (thesis.md, antithesis.md) are prepended by `dialectic.py` directly — NOT by MetaAgent. MetaAgent writes ONLY step-specific context (role/goal/criteria) to `system prompt files`. The engine reads template paths from step-config.json.

## Quality Standard

tas must catch what a human expert reviewer would catch. See `agents/antithesis.md` Pre-ACCEPT Quality Invariant Check for the four invariants (semantic consistency, behavioral consistency, compositional integrity, value flow soundness). If review misses these, improve the review lenses — don't add defensive guards.

## Iteration Loop & Lessons Learned

MetaAgent's Execute Mode has two nested loops:

**Within-iteration retry** (unbounded until PASS or persistent failure):
- 검증 FAIL → 구현 재실행 → 검증; 테스트 FAIL → 구현 재실행 → 검증 → 테스트
- HALT if same blocker recurs `loop_policy.persistent_failure_halt_after` times (default 3)
- Retries create sibling dirs (`step-{id}-{slug}-retry-{N}/`) — never overwrite originals

**Cross-iteration loop** (user-specified):
- `LOOP_COUNT` from classify plan (default 1, user can adjust)
- Iteration 2+ reenters from `loop_policy.reentry_point` (default 구현) with accumulated `lessons.md` and a selected `focus_angle`
- Early exit when agents agree further polish is fruitless

**lessons.md is append-only and load-bearing**: never prune prior entries; next iteration's agents receive the full file.

**Implication**: When adding new step types, ensure the retry-loop FAIL routing, lessons extractor, and `workflow-patterns.md` focus_angle table all stay consistent.

## Testing Strategy by Domain

Web projects require dynamic testing via Playwright CLI (`npx playwright test` + screenshots); Playwright MCP tools are NOT available in dialectic sessions. Non-web domains use static + execution tests. See `references/workflow-patterns.md` → "Dynamic Testing by Domain".

**Implication**: When changing domain detection, update both `workflow-patterns.md` testing table and `meta.md` testing-context injection.

## Common Mistakes When Editing This Repo

- **Adding implementation details or codebase-reading logic to SKILL.md** — breaks information hiding and scope prohibition
- **Reading agent files from SKILL.md** — breaks information hiding; Agent() prompt references meta.md by path only
- **Making convergence depend on round count** — produces shallow consensus
- **Bypassing dialectic.py** — MetaAgent must never spawn thesis/antithesis via `Agent()` directly; always use `Bash(bash runtime/run-dialectic.sh ...)` per `references/engine-invocation-protocol.md`
- **Invoking `run-dialectic.sh` in the foreground** — a single dialectic round takes 8–12 minutes; multi-round steps exceed the Bash tool's 10-minute cap (600000ms). ALWAYS use `run_in_background: true` and await the harness completion notification. `timeout: 900000` or any value above 600000 is silently ignored — do not use it as a workaround
- **Using Bash(`claude -p`) instead of Agent()** — causes timeout, JSON parsing, and empty output failures
- **Copying agent instructions into `system prompt files`** — MetaAgent writes ONLY step-specific context to system prompt files; agent templates are prepended by `dialectic.py` via step-config.json paths. MetaAgent must NOT copy or summarize agent instructions
- **Pruning lessons.md between iterations** — it must stay append-only; later iterations need the full history
- **Adding auto-resume daemons, background retry loops, or hardcoding `loop_count`** — `loop_count` is user-specified; MetaAgent only proposes a default. Manual `/tas --resume` is the single permitted opt-in resume path (Phase 2); auto-retry pipelines, background daemons, `--force-resume` flags, and round/iteration-boundary checkpoints remain forbidden.
- **Adding a fixed retry cap or overwriting retry log dirs** — within-iter retries are unbounded (HALT by `persistent_failure_halt_after`); each retry gets its own `step-{id}-{slug}-retry-{N}/` dir
