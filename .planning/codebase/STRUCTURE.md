# Codebase Structure

**Analysis Date:** 2026-04-21

## Directory Layout

```
tas/                                        # Project root (a Claude Code plugin)
├── .claude-plugin/                         # Plugin + marketplace manifest (what Claude Code reads on install)
│   ├── plugin.json                         # Plugin manifest — name, version, hooks pointer
│   └── marketplace.json                    # Marketplace manifest — single-entry catalog for this repo
├── hooks/                                  # Plugin-level shell hooks (project lifecycle)
│   ├── hooks.json                          # Hook registration (SessionStart → session-start.sh, Stop → stop-check.sh)
│   ├── session-start.sh                    # SDK preflight — writes ok/missing marker to ${TMPDIR}/tas-sdk-status/sdk-status
│   └── stop-check.sh                       # Deliverable integrity guard — blocks exit if REQUEST.md exists but DELIVERABLE.md is missing
├── skills/                                 # All skills exposed by this plugin
│   ├── tas/                                # Primary orchestration skill (slash command /tas)
│   │   ├── SKILL.md                        # MainOrchestrator — request parsing, trivial gate, classify/execute invocation, result display
│   │   ├── agents/                         # Agent instruction files (read by each agent's Claude instance)
│   │   │   ├── meta.md                     # MetaAgent — classify + execute (Agent subagent)
│   │   │   ├── thesis.md                   # ThesisAgent (正) template — prepended by engine to step-specific prompt
│   │   │   └── antithesis.md               # AntithesisAgent (反) template — prepended by engine
│   │   ├── runtime/                        # Python dialectic engine (subprocess)
│   │   │   ├── dialectic.py                # PingPong loop, verdict parser, SDK session management, degeneration detection
│   │   │   ├── run-dialectic.sh            # Python resolver (system → pipx → uv), invokes dialectic.py
│   │   │   ├── requirements.txt            # claude-agent-sdk>=0.1.50
│   │   │   └── __pycache__/                # Python bytecode cache (gitignored via __pycache__ entry)
│   │   └── references/                     # Load-on-demand reference docs (read by MetaAgent; end-users for recommended-hooks)
│   │       ├── workflow-patterns.md        # Request-type classification, complexity mapping, 4-step canonical flow, testing-by-domain
│   │       ├── workspace-convention.md     # Directory layout, DELIVERABLE.md / lessons.md formats, retry conventions
│   │       ├── failure-patterns.md         # Injected into antithesis prompt during 기획 steps only (asymmetric)
│   │       └── recommended-hooks.md        # Example PostToolUse hooks for consumer projects (TS / Python / Go)
│   ├── tas-review/                         # /tas-review — lightweight dialectic code review
│   │   └── SKILL.md                        # Collects git diff (branch/SHA/--staged/#PR), invokes MetaAgent with request_type=review
│   ├── tas-verify/                         # /tas-verify — independent post-synthesis boundary-value tracing
│   │   └── SKILL.md                        # Auto-detects latest workspace, traces numeric values through call chains
│   ├── tas-explain/                        # /tas-explain — summarize past dialectic dialogues in plain language
│   │   └── SKILL.md                        # Reads dialogue.md / DELIVERABLE.md / lessons.md, produces structured summary
│   └── tas-workspace/                      # /tas-workspace — list / latest / show / clean / stats
│       └── SKILL.md                        # Workspace management (read-only listing + targeted rm)
├── _workspace/                             # Runtime output root (gitignored)
│   └── quick/                              # All /tas runs land here
│       ├── {YYYYmmdd_HHMMSS}/              # One timestamped directory per run (no "resume" across runs)
│       │   ├── REQUEST.md                  # Original user request (verbatim)
│       │   ├── DELIVERABLE.md              # Final cross-iteration synthesis (MetaAgent Phase 3)
│       │   ├── lessons.md                  # Append-only lessons log across iterations
│       │   └── iteration-{N}/              # One per loop_count iteration (1-indexed)
│       │       ├── DELIVERABLE.md          # This iteration's synthesized output
│       │       └── logs/                   # Per-step dialectic artifacts
│       │           ├── step-{id}-{slug}/   # Primary step run (slug: plan/implement/verify/test)
│       │           │   ├── step-config.json                 # Engine input (MetaAgent-written)
│       │           │   ├── thesis-system-prompt.md          # Step-specific injection (MetaAgent)
│       │           │   ├── antithesis-system-prompt.md      # Step-specific injection (MetaAgent)
│       │           │   ├── round-1-thesis.md                # Engine-written per round
│       │           │   ├── round-1-antithesis.md
│       │           │   ├── round-N-thesis.md / antithesis.md / final.md / halt.md
│       │           │   ├── dialogue.md                      # Unified transcript (engine)
│       │           │   └── deliverable.md                   # Converged per-step output (engine)
│       │           └── step-{id}-{slug}-retry-{K}/          # Sibling dir per within-iteration retry (never overwrites)
│       └── classify-{YYYYmmdd_HHMMSS}/     # Plan-validation workspace for complex requests only
│           └── logs/validation/            # Lightweight dialectic to pressure-test the plan
├── .planning/                              # Planning docs (this directory)
│   └── codebase/                           # Codebase analysis docs (ARCHITECTURE.md, STRUCTURE.md, ...)
├── CLAUDE.md                               # Project meta-cognitive guide — paradox, information-hiding rules, edit checklist, file roles
├── README.md                               # Public-facing install + usage docs
├── .gitignore                              # Excludes node_modules/, _workspace/, __pycache__/, .claude/, etc.
├── .worktrees/                             # Git worktree directory (usually empty)
├── .openchrome/                            # Chrome profile for /browse skill (gstack unrelated to tas)
├── .claude/                                # Per-project Claude Code settings (gitignored)
└── .git/                                   # Git metadata
```

## Directory Purposes

**`.claude-plugin/`:**
- Purpose: Plugin manifest + marketplace listing. Read by Claude Code when the plugin is installed via `--plugin-dir`.
- Contains: `plugin.json` (name, version 0.2.0, author, hooks pointer `./hooks/hooks.json`), `marketplace.json` (single-plugin catalog with source `./`).
- Key files: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`.

**`hooks/`:**
- Purpose: Plugin-level shell hooks registered via `hooks.json`. Triggered by Claude Code lifecycle events, not by skill invocation.
- Contains: Hook registration manifest + executable `.sh` scripts. All scripts exit 0 to avoid blocking sessions unexpectedly (except `stop-check.sh` which explicitly blocks when integrity is violated).
- Key files: `hooks/hooks.json` (registers SessionStart + Stop), `hooks/session-start.sh` (SDK preflight — writes `${TMPDIR}/tas-sdk-status/sdk-status` marker), `hooks/stop-check.sh` (Deliverable Integrity Guard — JSON input/output on stdin/stdout, emits `{"decision":"block","reason":...}` when needed).

**`skills/`:**
- Purpose: One subdirectory per slash command. Each contains `SKILL.md` with YAML frontmatter (`name`, `description`) that Claude Code indexes for skill triggering.
- Contains: Five sibling skill directories — `tas/` (main), `tas-review/`, `tas-verify/`, `tas-explain/`, `tas-workspace/`.
- Key files: `skills/tas/SKILL.md` is the user entry point for `/tas`; the others invoke `skills/tas/agents/meta.md` via `Agent()` with pre-configured `request_type`.

**`skills/tas/`:**
- Purpose: The primary dialectic skill. Contains the MainOrchestrator, both agent templates, the Python engine, and load-on-demand reference docs.
- Contains: `SKILL.md` (MainOrchestrator), `agents/` (three agent files), `runtime/` (Python engine + launcher), `references/` (four reference docs).
- Key files: `skills/tas/SKILL.md`, `skills/tas/agents/meta.md`, `skills/tas/runtime/dialectic.py`.

**`skills/tas/agents/`:**
- Purpose: Agent instruction files. Each is executed by a different Claude instance under a different invocation mechanism (see `CLAUDE.md` §File Roles).
- Contains: `meta.md` (MetaAgent — Agent() subagent, `model: opus`), `thesis.md` (ThesisAgent — SDK stateful session, sonnet-4-6), `antithesis.md` (AntithesisAgent — SDK stateful session, sonnet-4-6).
- Key files: `skills/tas/agents/meta.md` (564 lines — classify + execute modes + iteration loop orchestration), `skills/tas/agents/thesis.md` (186 lines), `skills/tas/agents/antithesis.md` (280 lines — review lenses, Pre-ACCEPT Quality Invariant Check).

**`skills/tas/runtime/`:**
- Purpose: Python subprocess layer. The sole authorized producer of dialectic content.
- Contains: `dialectic.py` (engine, 828 lines), `run-dialectic.sh` (Python resolver), `requirements.txt` (single dependency).
- Key files: `skills/tas/runtime/dialectic.py` `run_dialectic()` async function is the PingPong loop; `_make_client()` creates asymmetric-permission clients (thesis writable, antithesis read-only).

**`skills/tas/references/`:**
- Purpose: Load-on-demand documentation. Kept out of agent system prompts to reduce base context; agents read these on request.
- Contains: Four markdown docs (workflow-patterns, workspace-convention, failure-patterns, recommended-hooks). All read by MetaAgent except `recommended-hooks.md` which targets end users of the plugin.
- Key files: `skills/tas/references/workflow-patterns.md` (canonical flows + domain testing table), `skills/tas/references/workspace-convention.md` (naming rules + file formats).

**`skills/tas-review/`, `skills/tas-verify/`, `skills/tas-explain/`, `skills/tas-workspace/`:**
- Purpose: Thin companion skills — each provides a focused user experience built on top of (or adjacent to) the main dialectic.
- Contains: One `SKILL.md` per directory, no agents or runtime of their own. `tas-review` delegates to MetaAgent with preconfigured `request_type=review`. `tas-verify` runs standalone (not part of the dialectic loop). `tas-explain` and `tas-workspace` are read-only workspace tools.
- Key files: `skills/tas-review/SKILL.md`, `skills/tas-verify/SKILL.md`, `skills/tas-explain/SKILL.md`, `skills/tas-workspace/SKILL.md`.

**`_workspace/`:**
- Purpose: Runtime output location for all `/tas` runs. Gitignored. Created by MainOrchestrator; populated by MetaAgent + engine.
- Contains: Only `quick/` subdirectory in the current design (no `deep/` or other modes).
- Key files: Per-run `REQUEST.md`, `DELIVERABLE.md`, `lessons.md` at `_workspace/quick/{timestamp}/`. Per-step artifacts in nested `iteration-{N}/logs/step-{id}-{slug}/`.

**`_workspace/quick/`:**
- Purpose: Timestamp-isolated run directories. One per `/tas` invocation; no cross-run state.
- Contains: `{YYYYmmdd_HHMMSS}/` directories (e.g., `20260417_084513/`), plus `classify-{YYYYmmdd_HHMMSS}/` dirs for plan-validation runs on complex requests.
- Key files: Every run directory contains `REQUEST.md` (always) + `DELIVERABLE.md` (on completion) + `lessons.md` (append-only) + one or more `iteration-{N}/` subdirs.

**`.planning/codebase/`:**
- Purpose: Out-of-tree codebase analysis documents (produced by `/gsd-map-codebase` and similar). Not consumed by the tas runtime.
- Contains: This file, `ARCHITECTURE.md`, and any other maps generated on demand.

## Key File Locations

**Entry Points:**
- `skills/tas/SKILL.md`: `/tas` user entry — MainOrchestrator, thin scheduler.
- `skills/tas/agents/meta.md`: MetaAgent entry — Classify + Execute modes, iteration loop.
- `skills/tas/runtime/dialectic.py` (line 644 `main()`): Python engine entry — PingPong loop runner.
- `skills/tas/runtime/run-dialectic.sh`: Launcher that resolves a Python with `claude-agent-sdk` installed and execs `dialectic.py`.
- `skills/tas-review/SKILL.md`: `/tas-review` entry — diff collection + MetaAgent invocation with `request_type=review`.
- `skills/tas-verify/SKILL.md`: `/tas-verify` entry — standalone boundary-value tracer.
- `skills/tas-explain/SKILL.md`: `/tas-explain` entry — dialogue summarizer.
- `skills/tas-workspace/SKILL.md`: `/tas-workspace` entry — workspace management subcommands.
- `hooks/session-start.sh`: Fires on SessionStart event (per `hooks/hooks.json`).
- `hooks/stop-check.sh`: Fires on Stop event.

**Configuration:**
- `.claude-plugin/plugin.json`: Plugin manifest (name, version, hooks pointer).
- `.claude-plugin/marketplace.json`: Marketplace catalog (single entry, source `./`).
- `hooks/hooks.json`: Hook registration (SessionStart, Stop).
- `skills/tas/runtime/requirements.txt`: Sole Python dependency (`claude-agent-sdk>=0.1.50`).
- `.gitignore`: Excludes `_workspace/`, `node_modules/`, `__pycache__/`, `.claude/`, `.openchrome/`, `src/`, `package*.json`, `tsconfig.json`.

**Core Logic:**
- `skills/tas/SKILL.md`: Request routing, trivial gate, SDK preflight, workspace setup, MetaAgent invocation, result display, HALT handling.
- `skills/tas/agents/meta.md`: Classify Mode (Phases 1-4), Execute Mode (Phases 1-5, iteration loop, within-iteration retry), Pre-Output Self-Check, JSON response contract.
- `skills/tas/agents/thesis.md`: Position proposal + defense + concession protocol + inverted-mode attacker role.
- `skills/tas/agents/antithesis.md`: Counter-position + review lenses + convergence-seeking + inverted-mode judge role + Pre-ACCEPT Quality Invariant Check.
- `skills/tas/runtime/dialectic.py`: `run_dialectic()` PingPong loop, `parse_verdict()`, `_make_client()` (asymmetric tool permissions), degeneration detectors (`_is_rate_limited`, consecutive UNKNOWN/degenerate counters), `_strip_frontmatter()` (for template prepending), `query_with_reconnect()` (CLI death recovery).

**Reference Docs (load-on-demand):**
- `skills/tas/references/workflow-patterns.md`: Request-type classification, complexity→step-count table, 4-step canonical flow (기획→구현→검증→테스트), per-domain dynamic-testing requirements.
- `skills/tas/references/workspace-convention.md`: Directory structure, naming rules, DELIVERABLE.md / lessons.md formats, iteration & retry flow.
- `skills/tas/references/failure-patterns.md`: Architectural / design / compositional failure patterns — injected into antithesis prompt during 기획 steps ONLY (asymmetric to reduce confirmation bias).
- `skills/tas/references/recommended-hooks.md`: Example `PostToolUse` hooks for consumer projects (TS/Python/Go type-check or lint on Write/Edit).

**Testing:**
- Dialectic engine self-test: `python3 skills/tas/runtime/dialectic.py --self-test` (verdict parser, frontmatter stripper, rate-limit detector regression tests).
- No separate test directory; the engine's self-test covers its pure functions. Prompt behavior is not unit-testable (see `CLAUDE.md` §The Core Paradox — "you can't test prompt changes").

## Naming Conventions

**Files:**
- Agent instruction files: lowercase `{role}.md` in `skills/tas/agents/` (e.g., `meta.md`, `thesis.md`, `antithesis.md`).
- Reference docs: lowercase-kebab-case `{topic}.md` in `skills/tas/references/` (e.g., `workflow-patterns.md`, `workspace-convention.md`).
- Skill entry files: `SKILL.md` (uppercase, literal — required by Claude Code skill discovery).
- Hook scripts: lowercase-kebab-case `.sh` (e.g., `session-start.sh`, `stop-check.sh`). Executable bit set.
- Workspace markers (always exact these names): `REQUEST.md`, `DELIVERABLE.md` (uppercase), `lessons.md` (lowercase).
- Per-step engine artifacts (always exact): `step-config.json`, `thesis-system-prompt.md`, `antithesis-system-prompt.md`, `dialogue.md`, `deliverable.md` (lowercase).
- Per-round logs (engine-written): `round-{N}-thesis.md`, `round-{N}-antithesis.md`, `round-{N}-final.md` (on ACCEPT), `round-{N}-halt.md` (on HALT).

**Directories:**
- Run workspaces: `_workspace/quick/{YYYYmmdd_HHMMSS}/` (e.g., `_workspace/quick/20260417_084513/`). Timestamp format is `date +%Y%m%d_%H%M%S`.
- Classify-validation workspaces (complex-complexity only): `_workspace/quick/classify-{YYYYmmdd_HHMMSS}/`.
- Iterations: `iteration-{N}/` where N is 1-indexed per `loop_count`.
- Step log dirs: `iteration-{N}/logs/step-{id}-{slug}/` — `id` is 1-indexed from the classify plan, `slug` is kebab-case English translation of the Korean step name (`기획` → `plan`, `구현` → `implement`, `검증` → `verify`, `테스트` → `test`).
- Retry dirs: `step-{id}-{slug}-retry-{K}/` — sibling of the primary step dir; `K` is 1-indexed. Never overwrites the original; `-retry-2`, `-retry-3` append sequentially.

**Step Names (enforced enum):**
- `steps[].name` in classify plans MUST be one of `기획`, `구현`, `검증`, `테스트` (per `skills/tas/agents/meta.md` §Step name enum).
- English translations surface only as `slug` in directory names, never as step names themselves.
- 1-step plans: use the single most applicable canonical name.
- 2-step: typically `기획` + `구현`.
- 3-step: adds `검증`.
- 4-step: adds `테스트`.

**Verdict Strings (engine-parsed):**
- Standard mode: `ACCEPT`, `REFINE`, `COUNTER`, `HALT` — from `## Response: X` / `**Response**: X` / `Response: X` / `판정: X` / `**X**` patterns in antithesis responses.
- Inverted mode (검증/테스트): `PASS` / `FAIL` — from `## Judgment: X` / `**Judgment**: X` / `판정: X` patterns. In standard mode, PASS→ACCEPT and FAIL→REFINE aliases are applied; in inverted mode, PASS/FAIL are terminal.

## Where to Add New Code

**New agent-facing instruction (classify behavior, new step type, new convergence rule):**
- Edit: `skills/tas/agents/meta.md` (MetaAgent — classify + execute logic).
- Often also: `skills/tas/references/workflow-patterns.md` (if adding a step type or complexity level) and `skills/tas/references/workspace-convention.md` (if changing file/dir conventions).
- Consider: `CLAUDE.md` §Common Mistakes When Editing This Repo before adding any cross-layer mechanism.

**New thesis/antithesis behavior (review lens, defense protocol, role override):**
- Edit: `skills/tas/agents/thesis.md` or `skills/tas/agents/antithesis.md`.
- These are prepended in full by `skills/tas/runtime/dialectic.py` `_strip_frontmatter()` + template concatenation at step startup — no MetaAgent involvement required.

**New engine behavior (verdict format, degeneration signal, reconnect logic):**
- Edit: `skills/tas/runtime/dialectic.py`.
- Add regression cases to `_self_test()` (line 678) and run `python3 skills/tas/runtime/dialectic.py --self-test`.
- Preserve the structural thesis→antithesis turn order in the main loop (`CLAUDE.md` §Turn Order Is Enforced by Python, Not Prompts).

**New orchestrator capability (new gate, new input shape, new result display):**
- Edit: `skills/tas/SKILL.md`.
- Verify it does NOT create a path where MainOrchestrator reads project source or agent files (`CLAUDE.md` §Scope Prohibition Is a Behavioral Guardrail, §Information Hiding Is Load-Bearing).

**New companion skill (`/tas-<something>`):**
- Create: `skills/tas-{name}/SKILL.md` with YAML frontmatter (`name`, `description`).
- If it invokes the dialectic, delegate to MetaAgent via `Agent(prompt="Read ${SKILL_DIR}/../tas/agents/meta.md ...")` — do NOT read project source directly in the new skill.
- Register in `README.md` command list. No changes needed in `hooks/hooks.json` (hooks are project-wide, not per-skill).

**New plugin hook (PreToolUse, PostToolUse, UserPromptSubmit, Notification):**
- Edit: `hooks/hooks.json` to add a new event key.
- Create: `hooks/{event-name}.sh` (executable, idempotent, bounded timeout — current pattern is 10s).
- All hook commands are wrapped in `test -n "${CLAUDE_PLUGIN_ROOT:-}" && test -f "..." && bash "..." || true` to fail open.

**New reference doc (load-on-demand):**
- Create: `skills/tas/references/{topic}.md`.
- Reference it from the agent that should load it (typically `skills/tas/agents/meta.md`).
- Do NOT embed it in a system prompt — the point of `references/` is that it stays out of base context.

**Workspace layout changes:**
- Edit: `skills/tas/references/workspace-convention.md` (the single source of truth).
- Then propagate: `skills/tas/SKILL.md` (if orchestrator reads/writes root-level files), `skills/tas/agents/meta.md` (Phase 1 Initialize, Phase 2 iteration loop, Phase 4 self-check glob), `skills/tas/runtime/dialectic.py` `_make_client()` / `log_dir` handling if step dir structure changes.

## Special Directories

**`_workspace/`:**
- Purpose: Runtime output root.
- Generated: Yes — by MainOrchestrator (`mkdir -p _workspace/quick`) and MetaAgent (`mkdir -p $WORKSPACE`, `mkdir -p $ITER_DIR/logs`).
- Committed: No (gitignored via `.gitignore` entry `_workspace/`).
- Lifecycle: Appended per run; never compacted automatically. User clears via `/tas-workspace clean`.

**`.claude/`:**
- Purpose: Per-project Claude Code settings.
- Generated: Yes (by Claude Code).
- Committed: No (gitignored).

**`.openchrome/`:**
- Purpose: Chrome profile for `/browse` skill (provided by gstack; orthogonal to tas).
- Generated: Yes.
- Committed: No (gitignored).

**`.planning/`:**
- Purpose: Out-of-tree planning + analysis documents (produced by `/gsd-map-codebase`, etc.).
- Generated: On demand by planning skills.
- Committed: Depends on user — not excluded by `.gitignore`.

**`.worktrees/`:**
- Purpose: Git worktree checkouts for parallel branch work.
- Generated: Yes (by `git worktree add`).
- Committed: No.

**`skills/tas/runtime/__pycache__/`:**
- Purpose: Python bytecode cache.
- Generated: Yes (by Python runtime).
- Committed: No (`__pycache__/` in `.gitignore`).

---

*Structure analysis: 2026-04-21*
