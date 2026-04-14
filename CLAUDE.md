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

No fixed iteration caps. Dialogue continues until ACCEPT or HALT. This is intentional — artificial caps produce premature consensus. If you're tempted to add a round limit, the real problem is probably unclear pass criteria or role ambiguity.

## Quality Standard

tas must catch what a human expert reviewer would catch. Four invariants:

1. **Semantic consistency** — same concept, same meaning everywhere
2. **Behavioral consistency** — same operation, same behavior under same contract
3. **Compositional integrity** — function A's output into function B is sound for ALL valid inputs
4. **Value flow soundness** — no intermediate NaN/Infinity/type-mismatch, even if downstream caps "fix" it

If review misses these, improve the review lenses — don't add defensive guards.

## Iteration Loop & Lessons Learned

MetaAgent's Execute Mode has two nested loops:

**Within-iteration retry** (automatic, unbounded until PASS or persistent failure):
- 검증 FAIL → 구현 재실행 → 검증 (repeat)
- 테스트 FAIL → 구현 재실행 → (검증) → 테스트 (repeat)
- HALT iteration if the same blocker set recurs `loop_policy.persistent_failure_halt_after`
  times consecutive (default 3)
- Within-iter retries create sibling log dirs (`step-{id}-{slug}-retry-{N}/`) inside the
  current iteration's directory — original logs are never overwritten

**Cross-iteration loop** (user-specified polish loop):
- `LOOP_COUNT` from classify plan (user can adjust at approval; default 1)
- Iteration 1: full baseline plan
- Iteration 2+: reenter from `loop_policy.reentry_point` (default 구현) with
  accumulated `lessons.md` context and a selected `focus_angle`
- Early exit allowed when agents agree further polish is fruitless

**lessons.md is append-only and load-bearing**: next iteration's thesis/antithesis
receive the full file as part of step_context. Never prune prior entries. The file
grows monotonically across iterations.

**Implication**: If you change the step set (e.g., add a new inverted check step), ensure:
- The within-iter retry loop handles which step FAIL jumps back to which upstream step
- The lessons extractor captures relevant fields for the new step type
- The focus_angle rotation table in `workflow-patterns.md` stays sensible

## Testing Strategy by Domain

The 테스트 step behavior changes based on `project_domain` detected in Classify Mode.
For web projects, dynamic testing via Playwright MCP (navigation + screenshots + UI/UX
evaluation) is **required**, not optional. For non-web domains, static + execution tests
suffice. See `references/workflow-patterns.md` → "Dynamic Testing by Domain".

**Implication**: When changing domain detection, update the testing strategy table in
`workflow-patterns.md` and the testing-specific context injection in `meta.md`.

## Common Mistakes When Editing This Repo

- **Adding implementation details to SKILL.md** — breaks information hiding
- **Reading agent files from SKILL.md** — breaks information hiding; Agent() prompt references meta.md by path only
- **Making convergence depend on round count** — produces shallow consensus
- **Bypassing dialectic.py** — MetaAgent must never spawn thesis/antithesis via `Agent()` directly; always use `Bash(bash runtime/run-dialectic.sh ...)`
- **Using Bash(claude -p) instead of Agent()** — causes timeout, JSON parsing, and empty output failures
- **Adding codebase-reading logic to SKILL.md** — breaks scope prohibition
- **Adding resume/pipeline mechanisms** — this repo is quick-only. Long-lived project context belongs elsewhere
- **Adding a fixed within-iteration retry cap** — within-iter retries are unbounded; HALT is governed by `persistent_failure_halt_after` (same-blocker recurrence), not a fixed count
- **Pruning lessons.md between iterations** — it must stay append-only; later iterations need the full history
- **Forgetting to preserve retry log directories** — never overwrite `step-{id}-{slug}-retry-{N}`; each retry gets a new sibling dir within the current iteration
- **Hardcoding loop_count** — it is user-specified; MetaAgent only proposes a default (usually 1)
