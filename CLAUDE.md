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

**Why**: If the MainOrchestrator Claude learns how 정반합 works internally, it develops a behavioral bias to skip the subprocess call and run the dialectic itself via `Agent()`. This has been observed and is the reason for the strict `claude -p` boundary.

**Implication**: When editing SKILL.md, never add references to agent internals. When editing agent files (meta.md, thesis.md, antithesis.md), don't worry about what SKILL.md knows — they run in separate processes.

### Role Separation Prevents Deadlock

ThesisAgent is always FIRST MOVER. AntithesisAgent is always REACTIVE. This asymmetry was established to resolve a deadlock (commit e38ec8d) where both agents waited for the other to speak first.

**Implication**: Any edit that blurs who speaks first reintroduces the deadlock. If you're changing agent roles, trace the turn-taking protocol through the full dialogue sequence.

### Process Isolation Is the Context Strategy

Each workflow step runs in its own `claude -p` process. This is not an implementation detail — it's the mechanism that prevents context window exhaustion during long pipelines. One step = one process = one context window.

**Implication**: Don't add mechanisms that share state between steps except through explicit files (DELIVERABLE.md, PROGRESS.md, step output files). In-memory state dies with each process.

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
| `SKILL.md` | MainOrchestrator (user's Claude) | Request routing, workspace management, MetaAgent invocation |
| `agents/meta.md` | MetaAgent (subprocess) | Step execution, 정반합 orchestration, convergence logic |
| `agents/thesis.md` | ThesisAgent (sub-subprocess) | Position proposal, defense, concession protocol |
| `agents/antithesis.md` | AntithesisAgent (sub-subprocess) | Counter-position, review lenses, convergence seeking |
| `agents/conflict-resolver.md` | ConflictResolver (subprocess) | Merge conflict resolution during sprint |
| `workflows/*/manifest.md` | MainOrchestrator | Step listing, required/optional classification |
| `workflows/*/P{N}-*.md` | MetaAgent only | Step details, goals, roles, pass criteria |
| `references/*.md` | MetaAgent or agents | Shared conventions, formats, patterns |

## Convergence Model

No fixed iteration caps. Dialogue continues until ACCEPT or HALT. This is intentional — artificial caps produce premature consensus. If you're tempted to add a round limit, the real problem is probably unclear pass criteria or role ambiguity.

## Quality Standard

tas must catch what a human expert reviewer would catch. Four invariants:

1. **Semantic consistency** — same concept, same meaning everywhere
2. **Behavioral consistency** — same operation, same behavior under same contract
3. **Compositional integrity** — function A's output into function B is sound for ALL valid inputs
4. **Value flow soundness** — no intermediate NaN/Infinity/type-mismatch, even if downstream caps "fix" it

If review misses these, improve the review lenses — don't add defensive guards.

## Common Mistakes When Editing This Repo

- **Adding implementation details to SKILL.md** — breaks information hiding
- **Making convergence depend on round count** — produces shallow consensus
- **Adding `Agent()` calls** — defeats process isolation; always use `Bash(claude -p ...)`
- **Editing workflow files without updating manifest.md** — MainOrchestrator sees only the manifest
- **Adding codebase-reading logic to SKILL.md** — breaks scope prohibition
- **Writing instructions that assume shared context between steps** — each step is a fresh process
