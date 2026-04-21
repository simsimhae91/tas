# Technology Stack

**Analysis Date:** 2026-04-21

## Languages

**Primary:**
- **Markdown** — The bulk of the codebase. Every agent, skill, and reference file is prompt instructions in Markdown with YAML frontmatter. See `skills/tas/SKILL.md`, `skills/tas/agents/*.md`, `skills/tas/references/*.md`, `skills/tas-*/SKILL.md`.
- **Python 3.10+** — Dialectic engine. Single file at `skills/tas/runtime/dialectic.py` (~830 lines). Uses modern typing (`from __future__ import annotations`, PEP 604 `X | None`).
- **Bash** — Hooks and a thin runtime wrapper: `hooks/session-start.sh`, `hooks/stop-check.sh`, `skills/tas/runtime/run-dialectic.sh`.
- **JSON** — Plugin/marketplace manifests and the MetaAgent ↔ dialectic engine wire contracts: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `hooks/hooks.json`, per-run `step-config.json`.

**Secondary:**
- None. There is no TypeScript/Go/Rust implementation in this repo. The `.gitignore` excludes `src/`, `package.json`, `tsconfig.json` — these may exist transiently from experimentation but are not part of the plugin.

## Runtime

**Environment:**
- **Claude Code ≥ 2.x** — Host runtime; plugin system support required. Surfaces the slash commands (`/tas`, `/tas-review`, `/tas-verify`, `/tas-explain`, `/tas-workspace`), runs `SessionStart` / `Stop` hooks, and exposes `${CLAUDE_PLUGIN_ROOT}` / `${CLAUDE_SKILL_DIR}` to hook commands and skill markdown.
- **Python 3.10+** — Runs the dialectic engine subprocess. `skills/tas/runtime/dialectic.py` imports `from __future__ import annotations` and uses `X | None` syntax, pinning the floor to 3.10.
- **Bash** — Required for `hooks/*.sh` and `skills/tas/runtime/run-dialectic.sh` (shebang `#!/bin/bash`).
- **git** — `hooks/stop-check.sh` and multiple SKILL.md files call `git rev-parse --show-toplevel`, `git status --porcelain`, `git diff`. The plugin assumes it runs inside a git repo (with graceful fallback to `pwd`).

**Package Manager:**
- **pip / pipx / uv** — Any of the three can install the sole Python dependency. `hooks/session-start.sh` and `skills/tas/runtime/run-dialectic.sh` probe all three in order: system/venv `python3` first, then `$HOME/.local/pipx/venvs/claude-agent-sdk/bin/python3`, then `$HOME/.local/share/uv/tools/claude-agent-sdk/bin/python3`.
- Lockfile: None. `skills/tas/runtime/requirements.txt` is a single unpinned-floor line (`claude-agent-sdk>=0.1.50`). There is no `pyproject.toml`, `Pipfile`, `poetry.lock`, or `uv.lock`.

## Frameworks

**Core:**
- **Claude Agent SDK (Python)** — `claude-agent-sdk>=0.1.50`, declared in `skills/tas/runtime/requirements.txt`. Used exclusively in `skills/tas/runtime/dialectic.py` for:
  - `ClaudeSDKClient` — stateful thesis/antithesis sessions (see `_make_client`, lines 314–351).
  - `ClaudeAgentOptions` — configures `model`, `system_prompt`, `permission_mode="bypassPermissions"`, `allowed_tools`, `disallowed_tools`, `cwd`, `max_turns=50`.
  - `SystemPromptPreset` with `preset="claude_code"` and an `append` string — keeps Claude Code's default system prompt and appends the step-specific instructions.
  - `AssistantMessage`, `ResultMessage`, `TextBlock` — streamed-response collection in `collect_response` (lines 94–121).
  - `claude_agent_sdk._errors.CLIConnectionError` — detected in `_is_cli_dead` to trigger one reconnect attempt in `query_with_reconnect`.
- **Claude Code Plugin System** — Host framework. Consumed via manifests and conventions, not a library import:
  - `.claude-plugin/plugin.json` (v0.2.0) — declares `name`, `hooks: ./hooks/hooks.json`.
  - `.claude-plugin/marketplace.json` — declares this repo as a single-plugin marketplace (`source: ./`).
  - `hooks/hooks.json` — registers `SessionStart` and `Stop` hook commands.
  - `skills/*/SKILL.md` — YAML frontmatter (`name`, `description`, optional `model`, `color`) registers each skill.

**Testing:**
- **No Python test framework.** `skills/tas/runtime/dialectic.py` defines its own `_self_test()` (lines 678–822) invoked via `python3 dialectic.py --self-test`. Covers `_strip_frontmatter`, `parse_verdict` (standard + inverted modes), and `_is_rate_limited` with hand-rolled assertion loops.
- **Playwright CLI** (`npx playwright test`, `npx playwright screenshot`) — referenced by `skills/tas/agents/meta.md` and `skills/tas/references/workflow-patterns.md` as the mandated dynamic-testing channel for `web-frontend` projects. NOT a dependency of this repo; invoked by dialectic agents inside the end user's project.

**Build/Dev:**
- None. There is no build step, no transpilation, no bundling. The plugin is distributed as source files.

## Key Dependencies

**Critical:**
- **`claude-agent-sdk>=0.1.50`** (Python) — `skills/tas/runtime/requirements.txt`. Sole Python dependency. Drives the entire dialectic loop. Absence is detected by `hooks/session-start.sh` (writes a marker to `${TMPDIR}/tas-sdk-status/sdk-status`) and by `skills/tas/SKILL.md` Phase 0 which reads the marker and aborts before invoking MetaAgent.

**Infrastructure:**
- **`jq`** (system binary) — Used by `hooks/stop-check.sh` for JSON parsing of the `Stop` hook stdin input and for producing the structured `{decision, reason}` block response. README calls it "optional, gracefully skipped if absent" — `command -v jq >/dev/null 2>&1 || exit 0` at line 11 of `hooks/stop-check.sh`.
- **`git`** (system binary) — Project-root detection and dirty-tree checks. Assumed present; scripts fall back to `pwd` if the repo check fails.

## Configuration

**Environment:**
- `CLAUDE_PLUGIN_ROOT` — Injected by the Claude Code runtime. Resolves to the plugin's root directory. Used in `hooks/hooks.json` command strings (`"${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh"`, `"${CLAUDE_PLUGIN_ROOT}/hooks/stop-check.sh"`). Guarded with `test -n "${CLAUDE_PLUGIN_ROOT:-}" && ... || true`.
- `CLAUDE_SKILL_DIR` — Injected by the runtime per-skill. Resolves to the specific skill directory (e.g., `.../skills/tas/` vs `.../skills/tas-review/`). Referenced in `skills/tas/SKILL.md` (`SKILL_DIR="${CLAUDE_SKILL_DIR}"`) and `skills/tas-review/SKILL.md` (`SKILL_DIR="${CLAUDE_SKILL_DIR}/../tas"` to reach the canonical meta.md).
- `TMPDIR` — Standard POSIX tmp dir. `hooks/session-start.sh` and `skills/tas/SKILL.md` use `${TMPDIR:-/tmp}/tas-sdk-status/sdk-status` as the preflight marker location.
- No `.env` or dotenv mechanism. No API keys live in this repo — authentication is delegated entirely to the host Claude Code CLI.

**Build:**
- No build config. No `tsconfig.json` (listed in `.gitignore`), no webpack/vite/rollup, no `pyproject.toml`. Runtime is direct-execute.

**Plugin Manifests:**
- `.claude-plugin/plugin.json` — `name`, `description`, `version: 0.2.0`, `author`, `homepage`, `repository`, `license: MIT`, `keywords`, `hooks: ./hooks/hooks.json`.
- `.claude-plugin/marketplace.json` — `name: tas`, single-plugin array with `source: ./` (the leading `./` is load-bearing per schema, per commit `4f3b9bd`).
- `hooks/hooks.json` — Two hook registrations (`SessionStart`, `Stop`), both with `timeout: 10` seconds, both wrapping their script in `test -n ... && test -f ... && bash ... || true` so missing files never fail the session.

**Skill Frontmatter (YAML at top of each `SKILL.md`):**
- `name` — Registers the slash command (`tas`, `tas-review`, `tas-verify`, `tas-explain`, `tas-workspace`).
- `description` — Trigger phrase surface for Claude Code's skill matcher; the `tas` skill lists `/tas`, `정반합`, "tas", and related phrases.
- Agent files (`agents/meta.md`, `agents/thesis.md`, `agents/antithesis.md`) carry `model: opus` in frontmatter; `thesis.md` / `antithesis.md` also carry `color: blue` / `color: red` for Claude Code UI.

**Runtime Model Selection:**
- MetaAgent always runs on `opus` — fixed. Invoked by `skills/tas/SKILL.md` with `model: "opus"` in every `Agent()` call.
- Dialectic agents (Thesis, Antithesis) run on `claude-sonnet-4-6` — set per-step in `step-config.json` via `skills/tas/agents/meta.md` (line 414: `"model": "claude-sonnet-4-6"`) with a fallback default in `skills/tas/runtime/dialectic.py` (line 384: `config.get("model", "claude-sonnet-4-6")`). Commit `897cffd` ("chore: route dialectic agents to sonnet-4-6, keep MetaAgent on opus") records this split.
- Thesis gets write tools: `["Read", "Write", "Edit", "Bash", "Grep", "Glob"]`. Antithesis is read-only: `["Read", "Grep", "Glob"]` with `disallowed_tools=["Write", "Edit", "NotebookEdit"]`. Both use `permission_mode="bypassPermissions"` (see `skills/tas/runtime/dialectic.py` lines 327–349).

## Platform Requirements

**Development:**
- macOS or Linux shell with Bash, git, Python 3.10+, and `claude-agent-sdk` installed via pip/pipx/uv.
- Claude Code installed and configured with the plugin either via marketplace (`/plugin marketplace add https://github.com/simsimhae91/tas.git`) or local clone (`claude --plugin-dir /path/to/tas`).
- `jq` recommended (but optional) for the Stop-hook deliverable guard.
- For end users whose projects target `web-frontend`: `npx` + a Playwright-capable Node environment so the dialectic agents can execute `npx playwright test` during the 테스트 step.

**Production:**
- Not applicable in the traditional sense — this is a developer tool that runs locally inside Claude Code. There is no server, no deployment target, no hosting platform. "Production" is the end user's Claude Code session on their own machine.

---

*Stack analysis: 2026-04-21*
