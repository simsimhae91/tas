# Coding Conventions

**Analysis Date:** 2026-04-21

This project is unusual: most "code" is markdown — prompts and instructions that other Claude instances execute at runtime. Prompt-authoring conventions are first-class code conventions here, on par with the Python runtime. Conventions are enforced by reasoning (reviewer + author applying the edit checklist), not by a compiler.

Two code "kinds" live here:
1. **Prompt/markdown code** — `skills/**/SKILL.md`, `skills/tas/agents/*.md`, `skills/tas/references/*.md`. Read by Claude at runtime.
2. **Python code** — `skills/tas/runtime/dialectic.py` (sole module), `skills/tas/runtime/run-dialectic.sh`. Invoked as a subprocess.

---

## Part 1 — Prompt/Markdown Conventions

These rules are documented and motivated in `CLAUDE.md` (Core Paradox, Edit Checklist, Common Mistakes). Violating any of them is a behavior bug in the running agent system, even if the markdown renders fine.

### Information Hiding Is Load-Bearing

SKILL.md (MainOrchestrator context) **intentionally does not know MetaAgent internals** — no mention of thesis/antithesis roles, convergence model, review lenses, or Pre-ACCEPT invariants.

| File | Must NOT reference | Why |
|------|-------------------|-----|
| `skills/tas/SKILL.md` | `meta.md`, `thesis.md`, `antithesis.md` contents; 正/反 role semantics; convergence model; review lenses | If MainOrchestrator learns the dialectic internals, it develops a bias to skip `Agent()` and run the dialectic itself |
| `skills/tas/agents/meta.md` | MainOrchestrator's internal decision flow, trivial-gate logic | MetaAgent runs in its own context — assumptions about the caller leak across the boundary |
| `skills/tas/agents/thesis.md`, `antithesis.md` | Each other's instructions, MetaAgent's retry logic | Agents run as separate SDK sessions; cross-assumptions produce deadlock or circular argumentation |

The `Agent()` prompt for MetaAgent says "Read `${SKILL_DIR}/agents/meta.md` and follow it" — MainOrchestrator never inlines or summarizes meta.md's content. Prompts reference each other by path, not by copied content.

### Scope Prohibition (MainOrchestrator)

`skills/tas/SKILL.md` lines 40-48 enumerate what MainOrchestrator must NEVER do:

- Read, edit, or create project source code files
- Read agent definition files (meta.md, thesis.md, antithesis.md)
- Analyze code to decide whether to handle the request itself
- Design solutions, plan implementations, make architectural decisions
- Fall back to direct implementation when MetaAgent invocation fails

The same prohibition applies to `skills/tas-review/SKILL.md`, `skills/tas-explain/SKILL.md`, `skills/tas-workspace/SKILL.md`, and `skills/tas-verify/SKILL.md` (with narrow scoped exceptions — e.g., `/tas-review` reads the diff it was explicitly asked to review; `/tas-verify` traces the code it was explicitly asked to verify). The Trivial Gate in SKILL.md (lines 97-111) judges from **request text alone** — no project file reads.

**When adding any new capability to SKILL.md, verify it doesn't create a path where MainOrchestrator reads project files and decides to handle the request directly.** Claude has a strong helpfulness drive; without explicit prohibition, it will read the codebase "to better understand the request" and then skip MetaAgent entirely.

### Boundary Discipline — Know Which Claude Executes What

Every edit to a prompt file must first answer "Who executes this?" The authoritative table lives in `CLAUDE.md` (File Roles). Do not generalize across rows.

| File | Executed By | Context Available to That Instance |
|------|-------------|-----------------------------------|
| `skills/tas/SKILL.md` | MainOrchestrator (user's Claude) | User request, `$ARGUMENTS`, shell env. No other agent files. |
| `skills/tas/agents/meta.md` | MetaAgent (Agent subagent) | Only its bootstrap prompt + whatever it reads via Read tool |
| `skills/tas/agents/thesis.md` | ThesisAgent (ClaudeSDKClient session) | Prepended template (this file, frontmatter stripped) + step-specific system prompt written by MetaAgent. Fresh stateful session per step. |
| `skills/tas/agents/antithesis.md` | AntithesisAgent (ClaudeSDKClient session) | Same shape as thesis.md, but appended with historical failure patterns during 기획 steps (asymmetric) |
| `skills/tas/runtime/dialectic.py` | Python subprocess (spawned by MetaAgent via `run-dialectic.sh`) | `step-config.json` passed as argv[1] |
| `skills/tas/references/*.md` | MetaAgent only | Read on demand during classify / execute |
| `skills/tas/references/recommended-hooks.md` | End users (not Claude) | Plain documentation |

**Implication**: "That instance has only its system prompt + the input parameters passed to it. Not your current conversation. Not the other agent files." (`CLAUDE.md` Edit Checklist)

### Falsifiable Instruction Rule

Every directive in a prompt must be **falsifiable** — a receiving Claude must be able to tell whether it complied. See `CLAUDE.md` Edit Checklist item 4.

| Non-falsifiable (reject) | Falsifiable (accept) |
|--------------------------|----------------------|
| "Be thorough" | "Trace the return value of function A through every call site" |
| "Review carefully" | "For each function in the target code, produce a Function Inventory row with signature, numeric params, callees, defensive measures" (pattern from `skills/tas-verify/SKILL.md`) |
| "Handle errors gracefully" | "On non-zero exit, print `{\"status\":\"error\",\"error\":str(exc)}` and `sys.exit(1)`" (pattern from `dialectic.py:671`) |

When adding a rule, ask: what concrete observable would prove non-compliance? If the answer is "I'd just feel it was wrong," the instruction is noise.

### Convergence Model — No Fixed Iteration Caps

- Dialectic rounds per step: **uncapped** until ACCEPT / PASS / FAIL / HALT. Implemented in `dialectic.py` `run_dialectic()` main loop (line 449: `while True`).
- Within-iteration retries (검증 FAIL → 구현 재실행): **uncapped** until PASS or persistent failure. `persistent_failure_halt_after` defaults to 3 consecutive **same-blocker** FAILs. Enforced by MetaAgent in `agents/meta.md` Phase 2d.
- Cross-iteration loop count: **user-specified** (default 1) at plan approval; MetaAgent only proposes a default in classify output.

**Why**: "Artificial caps produce premature consensus." (`CLAUDE.md` Convergence Model). HALT must come from structural degeneration (rate-limit, unparseable verdicts, dialogue degeneration, circular argumentation, external contradiction, missing information, scope escalation) — not from hitting a round counter.

**Do NOT** add round-count conditionals like "after 5 rounds, force ACCEPT" to any agent prompt.

### Append-Only `lessons.md`

`{workspace}/lessons.md` is load-bearing across iterations. Rules:

- Every iteration appends a new section using the schema in `skills/tas/references/workspace-convention.md` §lessons.md Format (Iteration N header, Focus Angle, Concrete Improvements, Blockers Resolved, Patterns Observed, Open Observations, Rejected Alternatives).
- **Never prune prior iterations' entries.** Iteration `i+1`'s thesis and antithesis receive the full cumulative file as part of their step context.
- Do not deduplicate, summarize-and-replace, or rewrite historical entries. The next iteration's agents need the full history to avoid re-litigating settled questions.

Enforced in `agents/meta.md` Phase 2f (Lessons Learned Extraction) and documented as a "Common Mistake" in `CLAUDE.md`.

### Asymmetric Prompt Injection (Deliberate)

During **기획 (planning) steps only**, MetaAgent injects additional content into the **antithesis** system prompt (not thesis):

1. The Planning-Phase Directive (alternative framework, assumption challenge, scope tension) — `agents/meta.md` lines 319-334.
2. The full content of `skills/tas/references/failure-patterns.md` — `agents/meta.md` lines 336-347.

This asymmetry reduces confirmation bias. **Do not append these to `thesis-system-prompt.md`.** See `references/failure-patterns.md` header — it is explicitly intended for antithesis only.

### Permitted Write Targets (MetaAgent Whitelist)

`agents/meta.md` lines 51-57 specify the complete whitelist of files MetaAgent may `Write`:

- `{WORKSPACE}/REQUEST.md`, `DELIVERABLE.md`, `lessons.md` (lessons append-only)
- `{WORKSPACE}/iteration-{N}/DELIVERABLE.md`
- `{LOG_DIR}/step-config.json`, `thesis-system-prompt.md`, `antithesis-system-prompt.md`

**Forbidden** MetaAgent writes (proof of protocol violation → HALT):

- Round logs (`round-*-thesis.md`, `round-*-antithesis.md`) — produced ONLY by the engine
- `dialogue.md` or per-step `deliverable.md` — produced ONLY by the engine
- Any `01_*.md`, `NN_*.md`, `*dialectic_log*`, `*research_note*`, `*ideation*` at workspace root
- 正/反 role-play content simulating dialectic output

### Output Contracts Are Machine-Parsed

Some prompt outputs are parsed by Python regex (`dialectic.py` `_VERDICT_PATTERNS` at lines 174-192). Authors of agent prompts must produce exactly these headers:

- Standard mode: `## Response: ACCEPT|REFINE|COUNTER|HALT` on its own line
- Inverted mode: `## Judgment: PASS|FAIL` on its own line
- Korean alias: `판정: ACCEPT|PASS|...` accepted
- Standalone bold verdict accepted: `**ACCEPT**`

The AntithesisAgent output format section (`skills/tas/agents/antithesis.md` lines 74-78) states: "The `## Response: {VERDICT}` line ... is parsed by the dialectic engine (`dialectic.py`) to determine dialogue flow. Always include this exact format on its own line — the engine matches these headers via regex." Reformatting breaks the engine — 5 consecutive UNKNOWN verdicts → HALT.

### Step Name Enum (Canonical Korean)

`steps[].name` in classify plans MUST be one of: `기획`, `구현`, `검증`, `테스트`. Enforced in `agents/meta.md` line 159-163. English or ad-hoc names (e.g., `research`, `ideation`, `dialectic`, `finalize`) break the inverted-step logic (검증/테스트 use the inverted convergence model) and the slug mapping for log directories (기획→plan, 구현→implement, 검증→verify, 테스트→test, per `references/workspace-convention.md`).

### Prompt File Frontmatter

Agent templates (`agents/thesis.md`, `agents/antithesis.md`, `agents/meta.md`) begin with YAML frontmatter (`name`, `description`, `model`, optional `color`). `dialectic.py` `_strip_frontmatter()` removes this before prepending the template to the step-specific system prompt — the frontmatter is metadata for the plugin loader, not content for the receiving Claude.

When editing these files, preserve the `---` frontmatter delimiters and the expected keys. Adding freeform content before the closing `---` will be stripped silently.

### Invocation Discipline (SKILL.md)

- **Always** invoke MetaAgent via `Agent()` tool. Never `Bash(claude -p ...)` — per `SKILL.md` line 28-30: "it causes timeout management bugs, JSON parsing failures, and empty output from background execution."
- **Never** narrate waits ("still processing", "waiting for output"). Agent() blocks synchronously and returns when done.
- **Never** fall back to direct implementation on MetaAgent failure. Report error and offer retry / abort (SKILL.md line 450).

### Common Prompt-Editing Mistakes

Documented in `CLAUDE.md` "Common Mistakes When Editing This Repo":

- Adding implementation details or codebase-reading logic to `SKILL.md`
- Reading agent files from `SKILL.md`
- Making convergence depend on round count
- Bypassing `dialectic.py` (MetaAgent spawning thesis/antithesis via `Agent()` directly)
- Using `Bash(claude -p)` instead of `Agent()`
- Copying full agent instructions into `{LOG_DIR}/thesis-system-prompt.md` — engine already prepends the template via `thesis_template_path`
- Pruning `lessons.md` between iterations
- Adding resume/pipeline mechanisms or hardcoding `loop_count`
- Adding a fixed retry cap or overwriting retry log dirs

---

## Part 2 — Python Conventions (`skills/tas/runtime/`)

The Python surface area is deliberately small: one module (`dialectic.py`, ~828 lines) plus a shell wrapper (`run-dialectic.sh`) and a pinned dependency file (`requirements.txt`). Conventions are inferred from the one file.

### Naming

- **Module**: lowercase, single word (`dialectic.py`)
- **Functions**: `snake_case`. Private helpers prefixed with `_` (e.g., `_make_client`, `_strip_frontmatter`, `_is_rate_limited`, `_extract_blockers`, `_parse_halt_reason`, `_check_sdk`, `_is_cli_dead`, `_self_test`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `DEGENERATE_RESPONSE_MIN_CHARS`, `UNKNOWN_VERDICT_HALT_AFTER`, `RATE_LIMIT_PATTERNS`, `RATE_LIMIT_MAX_RESPONSE_LEN`, `_VERDICT_PATTERNS`, `_VERDICT_ALIASES`, `_HALT_REASON_KEYWORDS`)
- **Module-level logger**: `logger = logging.getLogger("tas.dialectic")` at `dialectic.py:25`

### Typing

- `from __future__ import annotations` at the top (`dialectic.py:15`) — PEP 563 deferred evaluation.
- Explicit type hints on all public functions and return types (e.g., `async def collect_response(client: Any) -> str`, `def parse_verdict(response: str, convergence_model: str = "standard") -> str`).
- `Any` is used where SDK types would create import-time coupling (the SDK import is deferred — see `_check_sdk` at line 77).
- `dict[str, Any]`, `list[str]`, `tuple[str, str]` — lowercase generics (Python 3.9+ syntax).

### Async / SDK Usage Pattern

The runtime uses `claude_agent_sdk.ClaudeSDKClient` for stateful per-agent sessions. Canonical pattern (from `dialectic.py`):

1. **Deferred import** — `claude_agent_sdk` is imported inside `_make_client` / `collect_response`, not at module top. `_check_sdk()` (line 77) verifies availability at `main()` entry and prints an actionable error otherwise. This keeps `--self-test` runnable without the SDK.

2. **Client construction** — `_make_client()` (line 314) builds a `ClaudeSDKClient` with:
   - `system_prompt=SystemPromptPreset(type="preset", preset="claude_code", append=<step prompt>)` — agent template + step injection goes into `append`.
   - `permission_mode="bypassPermissions"` — uniform for both agents (antithesis is constrained to read-only via `allowed_tools` instead).
   - `allowed_tools=["Read","Write","Edit","Bash","Grep","Glob"]` for thesis; `["Read","Grep","Glob"]` + `disallowed_tools=["Write","Edit","NotebookEdit"]` for antithesis.
   - `cwd=project_root` — so project-level `.claude/settings.local.json` hooks propagate into the dialectic session (see `references/recommended-hooks.md` §Hook Propagation).
   - `max_turns=50`.

3. **Parallel connect** — `await asyncio.gather(thesis.connect(), antithesis.connect())` at line 432 to mask ~12s cold-start.

4. **Response collection** — `collect_response()` (line 94) iterates `client.receive_response()` and accumulates `TextBlock.text` from `AssistantMessage`, falling back to `ResultMessage.result`. Wraps in `try/except` and returns partial data if collection was already in progress when the error fired.

5. **Query with timeout** — `query_and_collect(client, prompt, timeout=600)` wraps `client.query(prompt)` + `collect_response(client)` in `asyncio.wait_for`.

6. **CLI-death reconnection** — `query_with_reconnect()` (line 149) catches `CLIConnectionError`, does one `await client.disconnect(); await client.connect()` cycle, and retries once. Second failure propagates.

7. **Teardown** — `try/finally` around the main loop, LIFO disconnect order (`antithesis` then `thesis`) for cancel-scope safety (line 633).

### Subprocess Invocation Pattern

MetaAgent invokes the dialectic engine via `Bash(bash ${SKILL_DIR}/runtime/run-dialectic.sh {LOG_DIR}/step-config.json)` with `timeout: 900000` (15 min). The wrapper (`run-dialectic.sh`) probes for a Python that has `claude_agent_sdk` installed in this order:

1. `python3` on PATH (tries `python3 -c "import claude_agent_sdk"`)
2. `~/.local/pipx/venvs/claude-agent-sdk/bin/python3`
3. `~/.local/share/uv/tools/claude-agent-sdk/bin/python3`

Exits with actionable pip/pipx/uv install hints if none are found.

**Output contract**: `dialectic.py main()` prints the final JSON result as the **last line of stdout** (line 675). MetaAgent parses that line. Errors are also emitted as structured JSON (`{"status":"error","error":...}`, lines 657 and 671) — never as plain-text tracebacks on stdout.

### Strict Turn Ordering (Enforced in Code)

Turn order is enforced by the Python `PingPong` loop, **not** by prompt-level instructions. See `CLAUDE.md` "Turn Order Is Enforced by Python, Not Prompts."

The main loop in `run_dialectic()` (`dialectic.py:449-602`) always alternates:

1. Round 1: `thesis.query(step_assignment)` → `antithesis.query(briefing + thesis_msg)`
2. Round N+1: `thesis.query(anti_msg)` → `antithesis.query(thesis_msg)`

Thesis always speaks first per round; antithesis always evaluates. **Preserve this alternation when modifying `dialectic.py`.** Do not add conditional logic that lets either agent skip a turn or respond out of order.

### Degeneration HALTs (Structural Safety Net)

The engine HALTs structurally — never on round count — when the dialogue decays. All thresholds are module-level constants at `dialectic.py:31-57`, named so their purpose is self-evident:

| Constant | Value | Check location | Behavior |
|----------|-------|----------------|----------|
| `DEGENERATE_RESPONSE_MIN_CHARS` | 50 | lines 566-568 | Both agents producing <50 chars is "degenerate" |
| `DEGENERATE_HALT_AFTER` | 3 | lines 570-587 | HALT after 3 consecutive degenerate rounds |
| `UNKNOWN_VERDICT_HALT_AFTER` | 5 | lines 535-554 | HALT after 5 consecutive unparseable verdicts |
| `RATE_LIMIT_PATTERNS` | list of 7 phrases | `_is_rate_limited()` line 261 | HALT immediately on match (checked before other degeneration checks) |
| `RATE_LIMIT_MAX_RESPONSE_LEN` | 500 | length gate in `_is_rate_limited` | Long responses are treated as substantive dialogue even if they mention "rate limit" as a domain concept |

HALT reasons (set on the result dict at lines 619-627): `rate_limit`, `dialogue_degeneration`, `unparseable_verdicts`, or `_parse_halt_reason(anti_msg)` for semantic HALT signals (`circular_argumentation`, `external_contradiction`, `missing_information`, `scope_escalation`).

**When adding new degeneration checks, follow the same pattern**: module-level constant, descriptive name, check before falling through to the default REFINE path, emit a structured halt_reason in the result JSON.

### Error Handling

- `main()` wraps both the config load (line 653) and the engine run (line 668) in try/except, emitting `{"status":"error","error":str(exc)}` on stdout and `sys.exit(1)`.
- In-loop errors (e.g., collection after CLI death) are logged at `logger.warning` if partial data exists (line 117); otherwise re-raised.
- The SDK import gate (`_check_sdk`) prints to `sys.stderr` (line 85) and `sys.exit(1)`.

### Required-Fields Validation

`run_dialectic()` validates `config` at line 364-377 against a hardcoded `required_fields` list. Missing fields yield a `halt_reason: "invalid_config"` result with the missing field names — never a Python `KeyError`. Preserve this pattern for new required fields.

### Imports & Organization

- Standard library first (`asyncio`, `json`, `logging`, `re`, `sys`, `pathlib`, `typing`), grouped at the top.
- Third-party (`claude_agent_sdk`) imported **inside functions** to defer cost and allow `--self-test` to run without the SDK.
- Constants immediately after imports, grouped under comment banners (`# ---- Degeneration detection constants ----`, `# ---- YAML frontmatter stripping ----`, etc.).
- One-responsibility functions separated by `# ---...---` banner comments (line 27, 60, 73, 90, 136, 170, 219, 274, 310, 354, 640).

### Logging

- Single module logger: `logger = logging.getLogger("tas.dialectic")` (line 25).
- `main()` sets `logging.basicConfig(level=logging.WARNING, format="%(name)s %(levelname)s: %(message)s", stream=sys.stderr)` at line 660. Stderr is for humans; stdout is reserved for the JSON contract.
- Use `logger.warning` for recoverable anomalies (CLI death with partial data, reconnect attempts). Use `logger.error` for unrecoverable (engine crash).
- Use bare `print(..., file=sys.stderr, flush=True)` for user-visible progress (`"{step_id}: Round {round_num}, {verdict}"` at line 466). The flush matters — MetaAgent reads stderr live while the subprocess runs.

### Self-Test

`dialectic.py` has an embedded `_self_test()` function (line 678). Invoked via `python3 dialectic.py --self-test`. Covers:

- `_strip_frontmatter` — frontmatter / no-frontmatter / empty-input cases
- `parse_verdict` — all regex patterns in both standard and inverted modes
- `_is_rate_limited` — length gate correctness (short error msg → True, long discussion containing "rate limit" → False)

Exits non-zero on failure with `FAIL: N/M passed` summary. See TESTING.md for the full picture of what is and is not verified.

---

## Module Design

- **Single-file runtime**: `dialectic.py` is deliberately not split into packages. All helpers and constants live inline under banner comments. Keep it that way — no `import` from sibling modules. A future split would require updating `run-dialectic.sh` and MetaAgent's invocation path.
- **No `__init__.py`**: `runtime/` is not a Python package. `run-dialectic.sh` invokes `dialectic.py` by absolute path; there is no `from tas.runtime import ...` anywhere.
- **No public API**: The only "exported" surface is `main()` and its JSON stdout contract.

## Shell Scripts

- `run-dialectic.sh` and `hooks/session-start.sh`, `hooks/stop-check.sh` all use `#!/bin/bash` (not `/bin/sh`), guard with `test -n "${VAR:-}"`, and end in `exit 0` for hook scripts (non-blocking by default).
- Hook scripts return structured JSON via `jq -n --arg reason "$REASON" '{"decision":"block","reason":$reason}'` when they need to block (see `hooks/stop-check.sh:85`).
- Prefer `${CLAUDE_PLUGIN_ROOT}` in hook commands, `${CLAUDE_SKILL_DIR}` in SKILL.md — see `references/recommended-hooks.md` §Plugin Environment Variables for the distinction.

---

*Convention analysis: 2026-04-21*
