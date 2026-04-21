# Architecture

**Analysis Date:** 2026-04-21

## Pattern Overview

**Overall:** Dialectic multi-agent orchestration plugin for Claude Code. A 4-layer system executes a 정반합 (thesis-antithesis-synthesis) quality workflow under **enforced context-isolation boundaries**. Each layer communicates with the next through a specific invocation mechanism that also doubles as a context boundary, preventing upper layers from contaminating the decision space of lower layers.

**Key Characteristics:**

- **Context isolation is load-bearing** — each layer boundary is a different invocation mechanism (Agent subagent → Python subprocess → SDK stateful session), chosen specifically to strand prior context on the caller side. Information hiding is enforced structurally, not just editorially.
- **Turn order is structurally guaranteed by Python, not prompts** — the dialectic PingPong loop in `skills/tas/runtime/dialectic.py` deterministically alternates thesis→antithesis. Agent prompts no longer carry "FIRST MOVER"/"REACTIVE" instructions.
- **Asymmetric content flow** — downward (inputs), rich; upward (returns), a single JSON result line. The orchestrator never sees the dialectic's intermediate reasoning.
- **File-mediated persistence** — state between steps/iterations flows through explicit files under `_workspace/quick/{timestamp}/`, never through in-memory hand-offs that cross a boundary.
- **Scope prohibition as behavioral guardrail** — the orchestrator skill is forbidden from reading project source; this prevents it from "helpfully" skipping the dialectic and handling the request itself.
- **No fixed round caps** — convergence is judged semantically (ACCEPT/PASS/FAIL verdict parsing); HALT is triggered by degeneration signals (rate limit, unparseable verdicts, repeated degenerate responses) detected in `skills/tas/runtime/dialectic.py`, not by artificial iteration ceilings.

## Layers

**Layer 1 — MainOrchestrator (Skill):**
- Purpose: Parse user request, gate trivial questions, invoke MetaAgent, present final result. Thin scheduler only.
- Location: `skills/tas/SKILL.md`
- Contains: Request parsing, SDK preflight check, Trivial Gate logic, Classify/Execute invocation via `Agent()`, JSON result presentation, HALT display, error handling.
- Depends on: `Agent()` tool (Claude Code built-in), `${CLAUDE_SKILL_DIR}` environment variable, `hooks/session-start.sh` SDK-status marker, `git` for dirty-tree check.
- Used by: End-user's Claude Code session (slash command `/tas`).
- **Enforced constraints** (SKILL.md §SCOPE PROHIBITION): NEVER read project source, NEVER read agent definition files (meta.md, thesis.md, antithesis.md), NEVER fall back to direct implementation on failure.

**Layer 2 — MetaAgent (Agent subagent):**
- Purpose: Classify requests into 1-4 step plans; Execute approved plans by coordinating the dialectic engine per step; aggregate per-iteration deliverables into a cross-iteration synthesis.
- Location: `skills/tas/agents/meta.md`
- Contains: Classify Mode (Phases 1-4), Execute Mode (Phases 1-5 with nested iteration loop), Within-Iteration FAIL handling, Lessons Learned extraction, Pre-Output Self-Check for engine artifacts, final JSON response contract.
- Depends on: `Bash(bash skills/tas/runtime/run-dialectic.sh ...)` as the sole producer of dialectic content, `skills/tas/references/workflow-patterns.md`, `skills/tas/references/workspace-convention.md`, `skills/tas/references/failure-patterns.md` (for 기획-only antithesis injection).
- Used by: MainOrchestrator via `Agent()` (twice per run — classify, then execute).
- **Enforced constraints** (meta.md §CRITICAL): Never Write dialectic content directly (round logs, per-step `deliverable.md`, 正/反 role-play); never spawn thesis/antithesis via `Agent()`. The Python engine is the sole authorized producer. Attestation via `engine_invocations` count in final JSON — zero with completed status = protocol violation.

**Layer 3 — Dialectic Engine (Python subprocess):**
- Purpose: Execute the PingPong dialogue loop for one step. Manage two stateful `ClaudeSDKClient` sessions, route messages between them, parse verdicts, detect degeneration, write per-round logs and per-step `deliverable.md`, emit final JSON result on the last stdout line.
- Location: `skills/tas/runtime/dialectic.py` (launcher: `skills/tas/runtime/run-dialectic.sh`)
- Contains: `run_dialectic()` async PingPong loop, verdict parser (`parse_verdict` — regex patterns for `## Response: ACCEPT/REFINE/COUNTER/HALT`, `## Judgment: PASS/FAIL`, Korean `판정:`, standalone bold), client factory (`_make_client` — thesis gets Read/Write/Edit/Bash/Grep/Glob; antithesis gets Read/Grep/Glob only), degeneration detectors (`_is_rate_limited`, consecutive UNKNOWN/degenerate counters), YAML frontmatter stripper for template prepending.
- Depends on: `claude-agent-sdk>=0.1.50` (found via `skills/tas/runtime/run-dialectic.sh` in system Python → pipx venv → uv tool fallback chain), `skills/tas/agents/thesis.md` + `skills/tas/agents/antithesis.md` as template prepends, the per-step `step-config.json` MetaAgent writes.
- Used by: MetaAgent, invoked once per step (plus once per within-iteration retry) via `Bash(bash run-dialectic.sh {step-config.json})`.
- **Enforced constraints** (dialectic.py): Thesis-then-antithesis ordering is structural in the main `while True:` loop (lines 449-602); last line of stdout MUST be JSON per the MetaAgent output contract; degeneration HALT reasons are classified and reported in the result dict.

**Layer 4 — Thesis / Antithesis (SDK stateful sessions):**
- Purpose: ThesisAgent (正) proposes positions, defends, concedes, produces deliverables. AntithesisAgent (反) evaluates, counters, refines, accepts; in inverted mode (검증/테스트), acts as judge rendering PASS/FAIL on attacker-produced issue lists.
- Location: `skills/tas/agents/thesis.md`, `skills/tas/agents/antithesis.md`
- Contains: Role definitions, verdict format contracts, review lenses (antithesis §Pre-ACCEPT Quality Invariant Check — semantic consistency, behavioral consistency, compositional integrity, value flow soundness), concession protocol, inverted-mode role overrides.
- Depends on: `ClaudeSDKClient` from `claude-agent-sdk`; system prompt assembled by `dialectic.py` as `{agent_template with frontmatter stripped} + \n\n + {step-specific injection from MetaAgent} + \n\n + {language instruction}`.
- Used by: `skills/tas/runtime/dialectic.py` `_make_client()` factory.
- **Enforced constraints**: Thesis has `bypassPermissions` + write tools (for 구현 Write/Edit); antithesis is read-only (`disallowed_tools: Write, Edit, NotebookEdit`). Both use `model: claude-sonnet-4-6` by default (configurable via step-config.json `model` field).

## Data Flow

**Per-run flow (one `/tas` invocation):**

1. User types `/tas {request}` → MainOrchestrator in `skills/tas/SKILL.md` activates.
2. MainOrchestrator reads `${TMPDIR}/tas-sdk-status/sdk-status` (written by `hooks/session-start.sh`); aborts with install advice if `missing`.
3. Trivial Gate: if request is a pure factual question and orchestrator is certain → answer directly, skip everything else.
4. **Classify**: MainOrchestrator calls `Agent(prompt="Read skills/tas/agents/meta.md...COMMAND: classify...")` → MetaAgent returns a JSON plan (`request_type`, `complexity`, 1-4 `steps`, `loop_count`, `loop_policy`, `workspace`, `project_domain`).
5. MainOrchestrator displays plan; user approves or modifies (`loop_count`, `reentry_point`, skip/add steps, set `focus_angle`).
6. **Execute**: MainOrchestrator writes `{WORKSPACE}/REQUEST.md` and calls `Agent(prompt="Read skills/tas/agents/meta.md...REQUEST:...WORKSPACE:...PLAN:...LOOP_COUNT:...")`.
7. MetaAgent runs the iteration loop (see Nested Loop Structure below).
8. MetaAgent returns a JSON result line: `{"status":"completed|halted","workspace":...,"summary":...,"iterations":N,"early_exit":bool,"rounds_total":N,"engine_invocations":N,"execution_mode":"pingpong"}`.
9. MainOrchestrator parses JSON, validates `engine_invocations > 0`, displays result with `DELIVERABLE.md` inline preview (design/analyze) or `git diff --stat` (implement/refactor), on HALT extracts blockers from `lessons.md` and provides recovery guidance.
10. On session end, `hooks/stop-check.sh` blocks exit if `REQUEST.md` exists but `DELIVERABLE.md` is missing/empty (and no active dialectic process / recent workspace writes).

**Per-step dialectic flow (inside MetaAgent Execute):**

1. MetaAgent creates `{ITER_DIR}/logs/step-{id}-{slug}/` and writes **two** system-prompt files (step-specific injection ONLY — role/goal/pass_criteria; the full agent template is NOT copied):
   - `thesis-system-prompt.md`
   - `antithesis-system-prompt.md`
   - For `기획` steps only, the antithesis prompt is augmented with §Planning-Phase Directive + contents of `skills/tas/references/failure-patterns.md` (asymmetric — thesis does not receive this).
2. MetaAgent writes `{LOG_DIR}/step-config.json` containing: prompt paths, `thesis_template_path`, `antithesis_template_path`, `step_assignment`, `antithesis_briefing`, `log_dir`, `step_id`, `step_goal`, `project_root`, `model`, `convergence_model` (`standard` for 기획/구현, `inverted` for 검증/테스트), `language`.
3. MetaAgent invokes `Bash(bash skills/tas/runtime/run-dialectic.sh {LOG_DIR}/step-config.json, timeout: 900000)`.
4. `dialectic.py` reads the config, prepends agent templates (with YAML frontmatter stripped by `_strip_frontmatter`), injects language instruction, creates two `ClaudeSDKClient` instances with asymmetric tool permissions, connects both in parallel.
5. **PingPong loop**:
   - Round 1: thesis receives `step_assignment`, produces position → log `round-1-thesis.md` + append to `dialogue.md`.
   - Antithesis receives `antithesis_briefing + thesis position`, produces verdict → log `round-1-antithesis.md`, parse verdict via `parse_verdict()`.
   - If ACCEPT: thesis is asked for a final converged deliverable → log `round-{N}-final.md`, break.
   - If PASS/FAIL (inverted mode only): antithesis's judgment becomes the deliverable → break.
   - If HALT or degeneration (rate_limit, ≥5 consecutive UNKNOWN, ≥3 consecutive degenerate rounds): break with `halt_reason` in result.
   - Otherwise (REFINE/COUNTER): thesis receives antithesis response, produces updated position → next round.
6. `dialectic.py` writes `{LOG_DIR}/deliverable.md` (final converged output for this step) and prints JSON result on last stdout line: `{"status":"completed|halted","rounds":N,"verdict":"ACCEPT|PASS|FAIL|HALT","deliverable_path":"..."}` (+ `blockers` for FAIL, + `halt_reason` for HALT).
7. MetaAgent parses JSON, reads `deliverable.md`, appends summary to `cumulative_context_this_iter`.
8. For inverted-mode FAIL: MetaAgent compares blockers to prior FAIL of same step; if identical ≥ `persistent_failure_halt_after` times → HALT iteration; else build retry context and re-execute 구현 step (new `step-{id}-{slug}-retry-{N}/` sibling dir).
9. After all steps: MetaAgent writes `{ITER_DIR}/DELIVERABLE.md` (per-iteration synthesis) and appends iteration lessons to `{WORKSPACE}/lessons.md`.
10. After all iterations: MetaAgent writes `{WORKSPACE}/DELIVERABLE.md` (cross-iteration synthesis), runs Pre-Output Self-Check (`find {WORKSPACE}/iteration-*/logs/step-*/` for `step-config.json`, `round-1-thesis.md`, `dialogue.md`, `deliverable.md`), then returns final JSON.

**State Management:**

- **Within a step** — thesis/antithesis sessions are stateful (`ClaudeSDKClient` conversation history preserved across rounds). State dies on session disconnect at step end.
- **Within an iteration** — `cumulative_context_this_iter` is an in-memory string MetaAgent builds by appending each step's `deliverable.md` summary. Visible to downstream steps as part of `step_context`.
- **Across iterations** — `{WORKSPACE}/lessons.md` is the persistent channel (append-only; never pruned). Iteration `i+1`'s agents receive the full `lessons.md` contents via `improvement_context` alongside a selected `focus_angle`.
- **Across runs** — nothing persists by design. Each `/tas` invocation produces a fresh timestamped workspace. No "resume" mechanism.
- **Cross-boundary returns** — MetaAgent → MainOrchestrator: a single JSON line. Dialectic content NEVER flows back into MainOrchestrator's context.

## Key Abstractions

**Dialectic Engine (PingPong loop):**
- Purpose: Represents a single-step thesis↔antithesis dialogue as a deterministic state machine.
- Examples: `skills/tas/runtime/dialectic.py` `run_dialectic()` (lines 358-637).
- Pattern: Async coroutine with unbounded `while True:` loop, exiting on verdict-terminal (ACCEPT/PASS/FAIL/HALT) or degeneration thresholds. Turn order hard-coded in Python; agent prompts no longer responsible for it.

**Convergence Model (standard vs inverted):**
- Purpose: Two modes of "how does the step end?". Standard: antithesis accepts thesis's proposal (ACCEPT) → thesis produces final deliverable. Inverted: thesis attacks, antithesis judges PASS (0 blockers) or FAIL (≥1 blockers, listed for retry).
- Examples: `skills/tas/runtime/dialectic.py` lines 468-497 (verdict handling), `skills/tas/agents/meta.md` §Convergence Model table.
- Pattern: Selected per step by `step.name`: `기획` / `구현` / others → standard; `검증` / `테스트` → inverted. Communicated to engine via `step-config.json` `convergence_model` field.

**Workflow Pattern Library:**
- Purpose: Canonical step templates (기획/구현/검증/테스트) with default pass criteria, complexity→step-count mapping, domain-specific testing strategy.
- Examples: `skills/tas/references/workflow-patterns.md` §Canonical 4-Step Flow, §Dynamic Testing by Domain, §Non-Implementation Templates.
- Pattern: Read by MetaAgent during Classify Mode to select template; read during Execute Mode to inject domain-specific testing context into 테스트 step. Step name enum is strictly enforced (`기획`, `구현`, `검증`, `테스트` only — ad-hoc names are rejected).

**Workspace Convention:**
- Purpose: Single source of truth for directory layout, file naming, retry dir scheme, DELIVERABLE.md / lessons.md formats. All three layers (orchestrator, MetaAgent, engine) reference it.
- Examples: `skills/tas/references/workspace-convention.md` §Directory Structure, §Naming Rules, §Iteration & Retry Flow.
- Pattern: Naming rules are regular (`quick/{timestamp}/`, `iteration-{N}/`, `step-{id}-{slug}/`, retry `-retry-{N}`). Timestamp format `YYYYmmdd_HHMMSS`. Slug is kebab-case English (기획→plan, 구현→implement, 검증→verify, 테스트→test).

**Attestation / Self-Check:**
- Purpose: Detect simulated dialectic (MetaAgent writing content directly instead of invoking the engine). MainOrchestrator cannot audit internals, so a structural proof is required.
- Examples: `skills/tas/agents/meta.md` §Phase 4 Pre-Output Self-Check (lines 487-503), §Phase 5 `engine_invocations` attestation.
- Pattern: (1) Filesystem check — every `iteration-*/logs/step-*/` must contain `step-config.json`, `round-1-thesis.md`, `dialogue.md`, `deliverable.md`; if any missing → HALT with `missing_engine_artifacts`. (2) `engine_invocations: 0` with `status: completed` is treated as protocol violation by MainOrchestrator in `skills/tas/SKILL.md` Phase 3 "Validate Attestation".

**Focus Angle Rotation:**
- Purpose: In iteration 2+, apply a fresh perspective to push past the previous iteration's PASS without re-implementing from scratch.
- Examples: `skills/tas/agents/meta.md` §Phase 2b Select Focus Angle (lines 220-246).
- Pattern: Priority (1) external override from orchestrator, (2) carry-over from antithesis's "Non-blocking Observations", (3) domain-specific rotation table (e.g., `web-frontend`: UX polish → accessibility → performance → edge cases → error states), (4) fallback "general code quality polish". `focus_angles_used` set prevents repetition.

## Entry Points

**User-facing slash command `/tas`:**
- Location: `skills/tas/SKILL.md` (activates on `/tas` or complex multi-step requests per YAML frontmatter `description`)
- Triggers: User typing `/tas {request}`, `/tas-review`, or any request matching trigger phrases ("정반합", "dialectical review", "tas").
- Responsibilities: Parse `$ARGUMENTS`, manage `_workspace/quick/{timestamp}/`, invoke MetaAgent twice (classify + execute), present results.

**Companion slash commands:**
- `/tas-review` → `skills/tas-review/SKILL.md`: Collects git diff (supports branch/SHA/`--staged`/`#PR`, 800-line truncation guard), invokes MetaAgent with `request_type=review`.
- `/tas-verify` → `skills/tas-verify/SKILL.md`: Independent post-synthesis boundary-value tracing. Runs AFTER `/tas`; not part of the dialectic loop. Auto-detects most recent workspace.
- `/tas-explain` → `skills/tas-explain/SKILL.md`: Read-only dialectic dialogue summarizer. Reads `dialogue.md` / `DELIVERABLE.md` / `lessons.md` from a specified (or latest) workspace and produces a plain-language summary.
- `/tas-workspace` → `skills/tas-workspace/SKILL.md`: Workspace management (list / latest / show / clean / stats subcommands).

**MetaAgent entry:**
- Location: `skills/tas/agents/meta.md` §Self-Bootstrap (lines 32-38)
- Triggers: `Agent(prompt="Read ${SKILL_DIR}/agents/meta.md and follow its instructions exactly. COMMAND: classify|<absent>. REQUEST: ...")` from MainOrchestrator.
- Responsibilities: Parse prompt parameters, detect mode (Classify if `COMMAND: classify` present; else Execute), run the corresponding phase sequence, return ONLY the JSON result line.

**Dialectic engine entry:**
- Location: `skills/tas/runtime/dialectic.py` `main()` (line 644) via `skills/tas/runtime/run-dialectic.sh`
- Triggers: `Bash(bash skills/tas/runtime/run-dialectic.sh {LOG_DIR}/step-config.json)` from MetaAgent.
- Responsibilities: Resolve Python with `claude-agent-sdk` installed (tries `python3` → `~/.local/pipx/venvs/claude-agent-sdk/bin/python3` → `~/.local/share/uv/tools/claude-agent-sdk/bin/python3`), load config JSON, run `asyncio.run(run_dialectic(config))`, print JSON result on last stdout line.

**Hook entry points:**
- `hooks/session-start.sh` (SessionStart hook per `hooks/hooks.json`): Preflight-checks `claude-agent-sdk` import in available Pythons. Writes status marker to `${TMPDIR}/tas-sdk-status/sdk-status` (`ok` or `missing`). If missing, prints install advice (pip/pipx/uv).
- `hooks/stop-check.sh` (Stop hook per `hooks/hooks.json`): Deliverable Integrity Guard. If `REQUEST.md` exists in latest workspace but `DELIVERABLE.md` missing/empty, AND no `dialectic.py` process matching workspace key is alive, AND no files modified in workspace within 3 minutes → emits `{"decision":"block","reason":...}` to prevent silent session-end mid-run. Otherwise `exit 0`.

## Error Handling

**Strategy:** Detect-and-HALT with structured reason codes and recovery guidance. Never fall back to direct implementation. Every failure mode has a named `halt_reason` with a localized display label and recovery message in `skills/tas/SKILL.md` Phase 3 tables.

**Patterns:**

- **Structural errors in the engine** (`skills/tas/runtime/dialectic.py`): Config load failure (missing required fields → `invalid_config`), SDK not installed (`_check_sdk()` → exit 1 with install advice), engine crash (wrapped in try/except at `main()` → prints `{"status":"error","error":...}` JSON).
- **Dialogue degeneration HALTs** (`skills/tas/runtime/dialectic.py`): `rate_limit` (phrase match + length gate < 500 chars), `unparseable_verdicts` (≥5 consecutive UNKNOWN verdicts), `dialogue_degeneration` (≥3 consecutive rounds where both agents < 50 chars). Detected inline during the PingPong loop.
- **Convergence HALTs from antithesis**: `circular_argumentation`, `external_contradiction`, `missing_information`, `scope_escalation` — parsed from the HALT response text by `_parse_halt_reason()` via keyword matching.
- **Persistent FAIL in inverted steps** (MetaAgent Execute, §Within-Iteration FAIL Handling): Compare blockers to prior FAIL; if identical ≥ `loop_policy.persistent_failure_halt_after` (default 3) → HALT iteration with `persistent_verify_failure` or `persistent_test_failure`.
- **Protocol-violation detection**: `engine_invocations: 0` with `status: completed` → MainOrchestrator warns user (`skills/tas/SKILL.md` Phase 3 "Validate Attestation"). Missing engine artifacts (no `step-config.json` / `round-1-thesis.md` / `dialogue.md` / `deliverable.md` in a step dir) → MetaAgent HALTs with `missing_engine_artifacts` before returning.
- **Orchestrator-level errors** (`skills/tas/SKILL.md` §Error Handling table): Priority-ordered classification of Agent() return: ModuleNotFoundError → SDK install advice; empty response → Retry/Abort; parse failure → show first 200 chars; halted status in valid JSON → NOT an error (→ HALT display); partial output → show 200 chars.
- **CLI death reconnect** (`skills/tas/runtime/dialectic.py` `query_with_reconnect`): If `CLIConnectionError` raised, disconnect and reconnect once. Fails permanently on second death.
- **Dirty-tree warning** (`skills/tas/SKILL.md` §Dirty-Tree Check): For `implement`/`refactor`, warn user about uncommitted changes before invoking MetaAgent; abort if user declines.

## Cross-Cutting Concerns

**Logging:**
- Per-round, per-step markdown logs written by `dialectic.py` to `iteration-{N}/logs/step-{id}-{slug}/`:
  - `round-{N}-thesis.md`, `round-{N}-antithesis.md`, `round-{N}-final.md` (on ACCEPT), `round-{N}-halt.md` (on HALT).
  - Unified conversation transcript: `dialogue.md` (append per turn, speaker-labeled with verdict tags).
- Python `logger` (`tas.dialectic`) at WARNING level, streamed to stderr (e.g., CLI reconnect warnings).
- Progress messages to stdout/stderr by the engine during long steps (`step_id: Round N, VERDICT`).
- MetaAgent writes summary files: `{ITER_DIR}/DELIVERABLE.md`, `{WORKSPACE}/DELIVERABLE.md`, `{WORKSPACE}/lessons.md` (append-only, load-bearing for cross-iteration context).

**Validation:**
- Engine config validation: `skills/tas/runtime/dialectic.py` `run_dialectic()` checks required fields (`log_dir`, `step_id`, `step_goal`, `project_root`, `thesis_prompt_path`, `antithesis_prompt_path`, `step_assignment`, `antithesis_briefing`) → returns `invalid_config` HALT on missing.
- Step name enum validation (MetaAgent Classify Mode): Must be `기획` / `구현` / `검증` / `테스트`. Ad-hoc names rejected.
- MetaAgent Pre-Output Self-Check (Phase 4, MANDATORY): bash loop verifies required artifacts exist in every step dir before emitting completed status.
- Verdict parser self-tests: `python3 skills/tas/runtime/dialectic.py --self-test` runs regression tests for `parse_verdict`, `_strip_frontmatter`, `_is_rate_limited`.

**Authentication / Permissions:**
- MetaAgent + orchestrator use `permission_mode: bypassPermissions` for Agent() calls (allows workspace mkdir, Bash invocation, log writes).
- ThesisAgent session: `bypassPermissions` + `allowed_tools: [Read, Write, Edit, Bash, Grep, Glob]` — writes code directly during 구현 steps.
- AntithesisAgent session: `bypassPermissions` + `allowed_tools: [Read, Grep, Glob]` + `disallowed_tools: [Write, Edit, NotebookEdit]` — read-only by construction.
- Both clients: `max_turns: 50`, `cwd: project_root`, system prompt uses `SystemPromptPreset(type="preset", preset="claude_code", append=...)`.

**Model Selection:**
- MetaAgent (classify + execute): `opus` — hard-coded in YAML frontmatter of `skills/tas/agents/meta.md` and in `Agent(..., model: "opus")` calls from `skills/tas/SKILL.md`.
- ThesisAgent / AntithesisAgent: `claude-sonnet-4-6` — set in MetaAgent's `step-config.json` `model` field and fallback default in `dialectic.py` `_make_client()`.

## Nested Loop Structure

**Within-Iteration Retry Loop** (`skills/tas/agents/meta.md` §Within-Iteration FAIL Handling):
- Unbounded retries until PASS, HALT, or persistent failure.
- Triggered on inverted-step FAIL (검증/테스트 returning blockers).
- Logic: Compare new blockers to previous FAIL of same step.
  - Substantively identical → increment `consecutive_fail_count[step]`.
  - Different blockers → reset counter to 1.
  - Counter ≥ `loop_policy.persistent_failure_halt_after` (default 3) → HALT iteration with `persistent_verify_failure` or `persistent_test_failure`.
- Retry dir naming: `iteration-{N}/logs/step-{id}-{slug}-retry-{K}/` (sibling of original step dir). **Never overwrite originals.** For 테스트 FAIL, re-run 검증 first if it exists in the plan.
- Retry context: `## Required Fixes from {step}\n{blockers}` appended to the 구현 retry prompt.

**Cross-Iteration Loop** (`skills/tas/agents/meta.md` §Phase 2 Iteration Loop):
- User-specified `loop_count` (default 1 per complexity; user may adjust at plan approval).
- Iteration 1 runs the full plan.
- Iteration 2+ runs the subset from `loop_policy.reentry_point` onwards (default `구현` — skips `기획`).
- Each iteration 2+ selects a `focus_angle` (external override → antithesis carry-over → domain rotation → fallback) and assembles `improvement_context` (previous iteration's DELIVERABLE.md summary + full lessons.md + focus directive).
- Per-iteration artifacts: `iteration-{N}/DELIVERABLE.md` + append to `{WORKSPACE}/lessons.md`.
- Early exit: if `loop_policy.early_exit_on_no_improvement` is true AND both agents explicitly state "no meaningful further improvement possible" in their final exchange (PASS alone is NOT sufficient) → terminate loop, set `early_exit: true` in final JSON.
- HALT'd iteration → break the cross-iteration loop, proceed to Phase 3 with `status: halted` (DELIVERABLE.md is still written with partial progress).

**`lessons.md` is load-bearing**: append-only across all iterations in a run; never pruned. Subsequent iterations receive the full file as context. Entries contain: focus angle, concrete improvements, blockers resolved, patterns observed, open observations, rejected alternatives.

---

*Architecture analysis: 2026-04-21*
