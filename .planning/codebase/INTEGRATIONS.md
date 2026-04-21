# External Integrations

**Analysis Date:** 2026-04-21

## APIs & External Services

**Anthropic / Claude (primary and only LLM provider):**
- **Claude Agent SDK (Python)** — `claude-agent-sdk>=0.1.50`. The single integration that makes the plugin work. Used at exactly one site: `skills/tas/runtime/dialectic.py`. Imports:
  - `ClaudeSDKClient` — one instance per agent per step (thesis + antithesis); stateful across rounds within a step, disposed between steps.
  - `ClaudeAgentOptions` — per-client config (`model`, `system_prompt`, `permission_mode`, `allowed_tools`, `disallowed_tools`, `cwd`, `max_turns`).
  - `SystemPromptPreset(type="preset", preset="claude_code", append=...)` — inherits Claude Code's default system prompt and appends role-specific instructions.
  - Message types: `AssistantMessage`, `ResultMessage`, `TextBlock` (streaming response collection).
  - `claude_agent_sdk._errors.CLIConnectionError` — exception taxonomy for the reconnect-once logic in `query_with_reconnect`.
  - Auth: inherited from the host environment — the SDK spawns the Claude CLI subprocess which reads whatever credentials the user has configured for Claude Code (OAuth session, API key, etc.). This repo never reads, stores, or references any auth env var.

- **Claude Code CLI** — Indirect dependency. The `claude-agent-sdk` package internally spawns the `claude` CLI subprocess to talk to the model. The SDK abstracts this away; this repo never shells out to `claude` directly (and explicitly forbids it — `skills/tas/SKILL.md` warns "NEVER use `Bash(claude -p ...)`" and CLAUDE.md lists "Using Bash(`claude -p`) instead of Agent()" as a common mistake). The preflight hooks (`hooks/session-start.sh`, `skills/tas/runtime/run-dialectic.sh`) only probe Python + the SDK import; they do not verify the `claude` binary itself — that check is implicit in the SDK's own runtime.

- **Host Claude Code runtime (Agent tool)** — `skills/tas/SKILL.md` (MainOrchestrator) invokes MetaAgent via the built-in `Agent()` tool (Phase 1 Classify, Phase 2 Execute). `skills/tas-review/SKILL.md` does the same. This is a first-class Claude Code capability, not an external API.

**No other LLM providers, no OpenAI, no Azure, no local-model backends.**

## Data Storage

**Databases:**
- None. No SQL, no NoSQL, no ORM, no connection strings. The plugin has no persistent state.

**File Storage:**
- Local filesystem only. The workspace at `{PROJECT_ROOT}/_workspace/quick/{YYYYmmdd_HHMMSS}/` is the sole state store. Structure (see `skills/tas/references/workspace-convention.md`):
  - `REQUEST.md` — original user request.
  - `DELIVERABLE.md` — final cross-iteration synthesis.
  - `lessons.md` — append-only cumulative lessons across iterations.
  - `iteration-{N}/DELIVERABLE.md` — per-iteration output.
  - `iteration-{N}/logs/step-{id}-{slug}/` — per-step round logs (`round-{N}-thesis.md`, `round-{N}-antithesis.md`, `dialogue.md`, `deliverable.md`), plus optional `-retry-{N}` sibling dirs.
  - `iteration-{N}/logs/step-{id}-{slug}/step-config.json` — the wire format between MetaAgent and `dialectic.py` (contains prompt paths, step assignment, model, convergence_model, timeouts).
  - `iteration-{N}/logs/step-{id}-{slug}/{thesis,antithesis}-system-prompt.md` — step-specific prompts written by MetaAgent; the engine prepends the full agent template before sending to the SDK.
- Each `/tas` invocation creates a fresh timestamped directory. There is no resume mechanism; `.gitignore` excludes `_workspace/` so nothing is committed.

**Caching:**
- None. No Redis, no memcached, no in-memory caches that survive a process. MetaAgent builds a `cumulative_context` string in memory within a single Execute-mode invocation, but it is discarded when the MetaAgent subagent returns.

## Authentication & Identity

**Auth Provider:**
- None owned by this plugin. All authentication to Anthropic's API is handled by the Claude Code CLI that the Agent SDK spawns under the hood. This repo has no login flow, no token handling, no OAuth, no API-key management.
- No env vars like `ANTHROPIC_API_KEY` are read anywhere in the codebase (verified via grep for `ANTHROPIC|API_KEY|TOKEN|SECRET` — no matches).

## Monitoring & Observability

**Error Tracking:**
- None. No Sentry, Datadog, Rollbar, or equivalent.

**Logs:**
- Filesystem-only logs in `_workspace/quick/{timestamp}/iteration-{N}/logs/`. Each dialectic round writes `round-{N}-{thesis|antithesis|final|halt}.md`, and a unified `dialogue.md` is appended turn-by-turn (`append_dialogue` in `skills/tas/runtime/dialectic.py` lines 284–307).
- Python logging at `WARNING` level to stderr (`logging.basicConfig(level=logging.WARNING, stream=sys.stderr)` in `main()`) for engine-level diagnostics (CLI death + reconnect, rate-limit detection, degenerate-round HALTs).
- `/tas-explain` and `/tas-workspace` skills read these logs for post-hoc inspection. There is no external log aggregator.

## CI/CD & Deployment

**Hosting:**
- **GitHub** — Repo at `https://github.com/simsimhae91/tas` (declared in `.claude-plugin/plugin.json` `homepage` and `repository`, and referenced in `README.md` install instructions).
- Distribution vectors (from `README.md` "Installation"):
  - **Public marketplace (recommended)**: `/plugin marketplace add https://github.com/simsimhae91/tas.git` followed by `/plugin install tas@tas`. Marketplace name and plugin name happen to both be `tas`.
  - **Local development (ephemeral)**: `claude --plugin-dir /path/to/tas` — loads from a clone for a single session, not persistent. This is the primary mode for plugin contributors (and the mode noted in the project's own memory index: "Plugin distributed via --plugin-dir with local clone, not registry").
  - **Local marketplace (persistent clone)**: `/plugin marketplace add /path/to/tas` followed by `/plugin install tas@tas`.

**CI Pipeline:**
- None. No `.github/workflows/`, no Travis/Circle/GitLab CI config. Quality is enforced by the dialectic process itself ("there's no compiler, no unit test" — CLAUDE.md) and by `python3 dialectic.py --self-test` run manually.

## Environment Configuration

**Required env vars:**
- `CLAUDE_PLUGIN_ROOT` — supplied by Claude Code runtime for hook commands. Required by `hooks/hooks.json`.
- `CLAUDE_SKILL_DIR` — supplied by Claude Code runtime per-skill. Required by `skills/tas/SKILL.md` (Phase 0) and `skills/tas-review/SKILL.md`.
- `TMPDIR` — standard POSIX; falls back to `/tmp`. Used for the SDK-status marker.

**Optional:**
- None. No feature flags, no toggle env vars.

**Secrets location:**
- Out of scope. All secrets live in the user's Claude Code configuration, managed by the host CLI. This repo contains no `.env`, no secret store, no vault integration.

## Webhooks & Callbacks

**Incoming:**
- None. There is no HTTP server, no listener, no Stripe-style webhook handler.

**Outgoing:**
- None. The plugin makes no outbound HTTP calls of its own. All network traffic to Anthropic is initiated by `claude-agent-sdk` → Claude Code CLI.

## MCP (Model Context Protocol) Servers

- **No MCP server is required, configured, or referenced by this plugin.**
- Relevant policy: `skills/tas/agents/meta.md` line 393, `skills/tas/agents/thesis.md` line 166, `skills/tas/references/workflow-patterns.md` line 70, and CLAUDE.md line 113 all explicitly note that **Playwright MCP tools are NOT available inside dialectic agent sessions** — the dialectic SDK clients run with a fixed `allowed_tools` list (`Read`, `Write`, `Edit`, `Bash`, `Grep`, `Glob` for thesis; `Read`, `Grep`, `Glob` for antithesis — see `skills/tas/runtime/dialectic.py` lines 327–332). Agents must use `Bash(npx playwright ...)` instead.
- The host Claude Code instance that runs MainOrchestrator may have MCP servers attached (e.g., the user's global `context7` per their environment), but they are not invoked by the plugin's own code paths.

## Claude Code Hook Integrations

**Plugin-level hooks** (this repo, registered in `hooks/hooks.json`):
- `SessionStart` → `hooks/session-start.sh` — probes `python3 -c "import claude_agent_sdk"` across system/pipx/uv Python installs; writes `ok`/`missing` to `${TMPDIR}/tas-sdk-status/sdk-status`; prints install guidance if missing. 10s timeout.
- `Stop` → `hooks/stop-check.sh` — blocks session exit if `/tas` was invoked (`REQUEST.md` present) but `DELIVERABLE.md` is missing or empty, AND no dialectic subprocess is alive, AND no workspace file has been modified in the last 3 minutes. Returns JSON `{"decision": "block", "reason": ...}` via `jq`. Respects `stop_hook_active` to prevent recursion. 10s timeout.

**Project-level hook propagation** (from `skills/tas/references/recommended-hooks.md`):
- When the dialectic engine creates a `ClaudeSDKClient` with `cwd=project_root`, the spawned CLI subprocess automatically discovers and loads hooks from the end user's project `.claude/settings.local.json`. Thus `PostToolUse` lint/type-check hooks (TypeScript, Python, Go examples documented) fire inside Thesis and Antithesis sessions without any explicit pass-through.
- Plugin-level hooks (`hooks/hooks.json`) only fire at the MainOrchestrator boundary — they do NOT propagate into dialectic subprocess sessions. This is by design.

## Distribution Mechanism Summary

The plugin is a self-contained source tree distributed via Claude Code's plugin system:

| Mechanism | Persistent | Use case |
|-----------|-----------|----------|
| `/plugin marketplace add <git-url>` + `/plugin install tas@tas` | Yes | End users on a stable version |
| `claude --plugin-dir /path/to/clone` | No (session-scoped) | Contributors editing `SKILL.md` / agent prompts |
| `/plugin marketplace add /path/to/clone` + `/plugin install tas@tas` | Yes | Running your own clone persistently |

The marketplace manifest at `.claude-plugin/marketplace.json` makes the same repo function as a single-plugin marketplace (`source: "./"` — the leading `./` is required by schema per commit `4f3b9bd`). There is no package registry (no PyPI, no npm); the git repo IS the distribution.

---

*Integration audit: 2026-04-21*
