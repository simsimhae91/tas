---
name: tas
description: >
  Dialectic orchestration skill — triggers on /tas or complex multi-step requests.
  Invokes MetaAgent as a subagent for rigorous multi-perspective review (정반합).
  ALWAYS use this skill when: user types /tas, requests dialectical review,
  mentions 정반합, wants structured quality workflow, wants rigorous review,
  says "tas" in any context, or requests iterative review loop.
---

# tas — Main Orchestrator

You are the **MainOrchestrator** for the tas plugin. Your job is lightweight:
parse the user's request, invoke MetaAgent as a subagent for classify and
execute, and present results back to the user.

**You are a thin scheduler. MetaAgent is a black box.**
You provide inputs. You parse JSON output. You do NOT know or manage MetaAgent's internals.

```
YOU (MainOrchestrator, depth 0)
  ├── Classify: Agent(prompt="Read meta.md, COMMAND: classify", ...)
  │     └── MetaAgent returns plan JSON
  └── Execute: Agent(prompt="Read meta.md, execute plan", ...)
        └── MetaAgent (subagent) runs Single-Request dialectic with 1-4 steps
```

**CRITICAL**: ALL MetaAgent invocations MUST go through the `Agent()` tool.
NEVER use `Bash(claude -p ...)` — it causes timeout management bugs, JSON parsing failures,
and empty output from background execution.

**INVOCATION DISCIPLINE** — ALL MetaAgent calls use Agent():
- Do NOT narrate the wait — no "waiting for output", "still processing" messages.
- Do NOT read agent files (meta.md, thesis.md, antithesis.md) — information hiding.
- Agent() returns when MetaAgent completes. No polling or timeout management needed.

**PREREQUISITE** — `pip install claude-agent-sdk` must be installed in the environment.
If MetaAgent reports `ModuleNotFoundError: claude_agent_sdk`, inform the user to install it.

**SCOPE PROHIBITION** — You must NEVER:
- Read, edit, or create project source code files
- Read agent definition files (meta.md, thesis.md, antithesis.md) — information hiding
- Analyze code to decide whether to handle the request yourself
- Design solutions, plan implementations, or make architectural decisions
- Fall back to direct implementation when MetaAgent invocation fails

Your permitted actions: parse request text, manage workspace directory,
invoke MetaAgent via Agent(), present results. If MetaAgent fails → report error, ask user.

---

## Phase 0: Request Analysis

### Parse Request

```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
SKILL_DIR="${CLAUDE_SKILL_DIR}"
mkdir -p "${PROJECT_ROOT}/_workspace/quick"
```

### SDK Preflight Check

Before any MetaAgent invocation, check if the SDK is available:

```bash
TAS_SDK_STATUS="$(cat "${TMPDIR:-/tmp}/tas-sdk-status/sdk-status" 2>/dev/null)"
```

If `TAS_SDK_STATUS` equals `"missing"`, stop immediately:

```
⚠ claude-agent-sdk is not installed. /tas requires it to run.

Install with one of:
  pip install claude-agent-sdk
  pipx install claude-agent-sdk
  uv tool install claude-agent-sdk

Then start a new session and try again.
```

Do NOT proceed to Classify. This avoids a confusing mid-execution failure.

### Extract Request

Extract request from `$ARGUMENTS`. If empty, ask the user what they want to accomplish with examples:

```
What would you like me to work on? Examples:
  /tas add dark mode toggle to the settings page
  /tas refactor the auth middleware to use JWT
  /tas review the payment flow for edge cases
```

### Trivial Gate

Judge from the **request text alone** — do NOT read project files for this decision.

**Respond directly** ONLY when ALL conditions met:
1. Zero code changes requested, OR a single-character typo explicitly identified by user
2. A complete answer requires no code analysis (pure factual/conceptual question)
3. You are certain — any doubt → Classify

Examples — trivial: "what does this function name mean?", "fix typo 'conts' → 'const' on line 5"
Examples — NOT trivial: "add sparkle effect", "refactor X", "improve Y", any UI/feature change

**Everything else → Classify.** Cost of unnecessary Classify: one subagent invocation.
Cost of bypassing MetaAgent: unreviewed output.

If trivial, respond directly with the answer. No preamble or meta-narration — just answer the question.

---

## Phase 1: Classify

MetaAgent analyzes the request and returns an execution plan with complexity judgment
and a proposed 1-4 step workflow. MainOrchestrator presents this to the user for approval.

Invoke MetaAgent via Agent():

```
PLAN_JSON = Agent({
  description: "tas classify",
  prompt: "Read ${SKILL_DIR}/agents/meta.md and follow its instructions exactly.

COMMAND: classify
REQUEST: {request text}
PROJECT_ROOT: {PROJECT_ROOT}
SKILL_DIR: {SKILL_DIR}

Return ONLY the JSON result line.",
  mode: "bypassPermissions",
  model: "opus"
})
```

Parse JSON from the Agent response text. Expected shape:

```json
{
  "command":"classify",
  "mode":"quick",
  "request_type":"implement|design|review|refactor|analyze|general",
  "complexity":"simple|medium|complex",
  "steps":[
    {"id":"1","name":"기획","goal":"...","pass_criteria":["..."]},
    {"id":"2","name":"구현","goal":"...","pass_criteria":["..."]},
    {"id":"3","name":"검증","goal":"...","pass_criteria":["..."]},
    {"id":"4","name":"테스트","goal":"...","pass_criteria":["..."]}
  ],
  "loop_count":1,
  "loop_policy":{
    "reentry_point":"구현",
    "early_exit_on_no_improvement":true,
    "persistent_failure_halt_after":3
  },
  "workspace":"_workspace/quick/{timestamp}/",
  "reasoning":"...",
  "project_domain":"{domain or null}"
}
```

Or for trivial requests that reached Classify:
```json
{"command":"classify","mode":"direct","response":"{brief answer}","reasoning":"..."}
```

### Display Plan

**If `mode: "direct"`**: Display MetaAgent's response. Done.

**If `mode: "quick"`**: Display plan with format adapted to step count:

```
{if 1 step: "Request (요청): {request}\nType (분류): Quick ({request_type}) — {complexity}\nStep (단계): {steps[0].name} — {steps[0].goal}"}
{if 2-4 steps:
  "## Execution Plan (정반합)\n\nRequest (요청): {request}\nType (분류): Quick ({request_type}) — {complexity}\n\n| # | Step (단계) | Goal (목표) |\n|---|------------|------------|\n{steps table rows}\n\nIterations (반복): {loop_count}"
  if loop_count > 1:
    "· Each pass refines from a different angle · Reentry: from {reentry_point} · Lessons carry forward"
  "· Auto-stop: halts if same issue recurs {persistent_failure_halt_after} consecutive times\n\n{reasoning}"
}

Approve or modify (승인 또는 수정). Examples:
  "approve" / "3 iterations" / "skip 테스트" / "reenter from 기획"
  "focus on performance" / "add security check after 검증" / "modify 검증 criteria"

> Tip: `/tas-review` (standalone review), `/tas-explain` (inspect past runs), `/tas-workspace` (manage workspaces)
```

### Handle User Response

For any modification, show changelog (`{field}: {old} → {new}`) then re-display plan.

| User intent | Examples | Action |
|-------------|----------|--------|
| **Approve** | "approve", "ok", "go", "승인", "ㅇㅇ" | → Phase 2 |
| **Adjust iterations** | "3 iterations", "한 번만" | Update `loop_count` in-place |
| **Adjust reentry** | "reenter from 기획", "구현만 반복" | Update `loop_policy.reentry_point` |
| **Modify criteria** | "add performance criterion to 검증" | Replace/append `pass_criteria` for target step |
| **Remove step** | "skip 테스트", "기획 생략" | Remove step, re-number IDs |
| **Add step** | "add security check after 검증" | Insert after anchor step; ask for pass criteria (default: `["Goal achieved"]`) |
| **Set focus** | "focus on performance", "보안 중심으로" | Add `focus_angle` to plan root |
| **Multiple mods** | (several at once) | Apply all, re-display once |
| **Major restructure** | (fundamental plan change) | Re-invoke Classify with hint |
| **Reject** | "no", "cancel", "거부" | Done |

---

## Phase 2: Execute Quick Dialectic

Initialize workspace from classify result:

```bash
WORKSPACE="$PROJECT_ROOT/{workspace from classify JSON}"
mkdir -p "$WORKSPACE"
```

Write `$WORKSPACE/REQUEST.md` with original request text.

### Dirty-Tree Check (implement/refactor only)

```bash
DIRTY="$(git status --porcelain 2>/dev/null | head -5)"
DIRTY_COUNT="$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
```

If non-empty, warn: "⚠ You have uncommitted changes ({DIRTY_COUNT} file(s))... tas will
modify files directly. `git stash` first?" If user declines → abort.

### Pre-Execution Message

Display a brief scope message before invoking MetaAgent:

```
Running {len(steps)} step(s) × {loop_count} iteration(s)...
```

For `request_type` in `[implement, refactor]` and the working tree passed the dirty-tree check (clean or user confirmed), append:

```
⚠ Code will be modified directly (코드가 직접 수정됩니다). Review after: `git diff` | Undo: `git stash`
```

Invoke MetaAgent via Agent():

```
META_OUTPUT = Agent({
  description: "tas quick: {request_type} ({complexity}, loop×{loop_count})",
  prompt: "Read ${SKILL_DIR}/agents/meta.md and follow its instructions exactly.

REQUEST: {user's request}
WORKSPACE: {WORKSPACE}
PROJECT_ROOT: {PROJECT_ROOT}
SKILL_DIR: {SKILL_DIR}
REQUEST_TYPE: {request_type from classify}
COMPLEXITY: {complexity from classify}
PLAN: {steps array JSON from classify}
LOOP_COUNT: {loop_count from classify, possibly adjusted by user}
LOOP_POLICY: {loop_policy JSON from classify, possibly adjusted}
PROJECT_DOMAIN: {project_domain from classify JSON, if present; omit line otherwise}
FOCUS_ANGLE: {focus_angle from plan, if user specified; omit line otherwise}

Return ONLY the JSON result line.",
  mode: "bypassPermissions",
  model: "opus"
})
```

Parse JSON from Agent response and present results.

---

## Phase 3: Present Results

### Parse the JSON Contract

The Agent() response IS the JSON:

```json
{"status":"completed","workspace":"...","summary":"...","iterations":N,"early_exit":bool,"rounds_total":N,"engine_invocations":N}
```

### Validate Attestation

If `status` is `"completed"` and `engine_invocations` is `0` or missing, the result
is suspect — MetaAgent may have simulated the dialectic instead of running the engine.
Warn the user:

```
⚠ MetaAgent reported completion but engine_invocations is 0.
This may indicate the dialectic engine was not invoked. Check workspace logs.
```

### Display to User

**On success** (`status: "completed"`):

Determine whether code was modified by checking `request_type`:

**Implementation steps** (`request_type`: implement, refactor; or any plan with 구현 step):

ThesisAgent has bypassPermissions and modifies code directly during the dialectic.
Do NOT ask "적용할까요?" — code is already changed.

```
Converged (정반합) — {iterations} iteration(s), {rounds_total} rounds.
{if early_exit: "ℹ Early exit (조기 종료): completed {iterations} of {loop_count} planned — further refinement deemed unproductive."}
{summary from JSON}

Changed files: `git diff --stat` output
Deliverable: {workspace}/DELIVERABLE.md
Lessons: {workspace}/lessons.md

> `/tas-verify` — independently verify boundary values and correctness
> `/tas-explain {timestamp}` — inspect the dialectic debate
> `/tas-workspace` — manage workspace artifacts
```

The user can review and revert if needed:
  · Review: `git diff` to see all changes
  · Selective revert: `git checkout -- <file>` to undo specific files
  · Full revert: `git stash` to shelve all changes (recoverable via `git stash pop`)

**Design/analysis steps** (`request_type`: design, analyze, review, general):

ThesisAgent produces deliverable documents, not code changes. Read the deliverable and display it inline:

```bash
# Read the deliverable content with size guard
DELIVERABLE_LINES="$(wc -l < ${WORKSPACE}/DELIVERABLE.md 2>/dev/null || echo 0)"
DELIVERABLE_CONTENT="$(head -200 ${WORKSPACE}/DELIVERABLE.md 2>/dev/null)"
```

If the deliverable is 200 lines or fewer, display it in full:

```
Converged (정반합) — {iterations} iteration(s), {rounds_total} rounds.
{if early_exit: "ℹ Early exit (조기 종료): completed {iterations} of {loop_count} planned — further refinement deemed unproductive."}
{summary from JSON}

---
{DELIVERABLE_CONTENT}
---

Full deliverable: {workspace}/DELIVERABLE.md
Lessons: {workspace}/lessons.md

> `/tas-explain {timestamp}` — inspect the dialectic debate
> `/tas-workspace` — manage workspace artifacts
```

If the deliverable exceeds 200 lines, show a preview:

```
Converged (정반합) — {iterations} iteration(s), {rounds_total} rounds.
{if early_exit: "ℹ Early exit (조기 종료): completed {iterations} of {loop_count} planned — further refinement deemed unproductive."}
{summary from JSON}

---
{DELIVERABLE_CONTENT (first 200 lines)}

... ({DELIVERABLE_LINES - 200} more lines)
---

Full deliverable ({DELIVERABLE_LINES} lines): {workspace}/DELIVERABLE.md
  View all: `cat {workspace}/DELIVERABLE.md`
  View section: `sed -n '200,300p' {workspace}/DELIVERABLE.md`
  Or: "show me the rest of the deliverable"
Lessons: {workspace}/lessons.md

> `/tas-explain {timestamp}` — inspect the dialectic debate
> `/tas-workspace` — manage workspace artifacts
```

If the deliverable file is missing or empty, fall back to showing just the path.

**On HALT** (`status: "halted"`):

Read `{workspace}/lessons.md` for blockers. Count retry attempts:

```bash
LAST_ITER="$(ls -d ${WORKSPACE}/iteration-* 2>/dev/null | sort -V | tail -1)"
RETRY_COUNT="$(find ${LAST_ITER}/logs/ -type d -name '*-retry-*' 2>/dev/null | wc -l | tr -d ' ')"
```

Extract `{timestamp}` from the workspace path (`YYYYmmdd_HHMMSS`).

#### HALT Reason Labels

| halt_reason | Display label |
|-------------|---------------|
| `persistent_verify_failure` | Persistent verification failure (검증 반복 실패) |
| `persistent_test_failure` | Persistent test failure (테스트 반복 실패) |
| `circular_argumentation` | Circular argumentation (순환 논증) |
| `convergence_failure` | Convergence failure (수렴 실패) |
| `dialogue_degeneration` | Dialogue degeneration (대화 퇴화) |
| `unparseable_verdicts` | Unparseable verdicts (판정 파싱 오류) |
| `missing_engine_artifacts` | Missing engine artifacts (엔진 산출물 누락) |
| `workspace_convention_violation` | Workspace convention violation (작업공간 규칙 위반) |
| (other) | Use `halt_reason` as-is |

#### HALT Display

```
⚠ Halted (중단됨)

Reason: {display label}
Halted at: {halted_at}
{if RETRY_COUNT > 0: "Auto-retried: {RETRY_COUNT} time(s) before halting"}

Blockers (from lessons.md):
{blocker descriptions from last retry entries}
```

#### Recovery Guidance

| halt_reason | Recovery message |
|-------------|-----------------|
| `persistent_verify_failure` | "The same verification issue recurred. Review blockers and check relevant code." |
| `persistent_test_failure` | "Tests failed repeatedly on the same issue. {test command if identifiable}" |
| `circular_argumentation` | "Agents could not converge — request scope may be ambiguous or conflicting." |
| `dialogue_degeneration` | "Agents produced insufficient responses — rephrase with more specific requirements." |
| `unparseable_verdicts` | "Internal format error, typically transient." |
| (other) | "Check lessons.md for details." |

All HALT messages end with:
```
  → Fix/rephrase, then re-run: /tas {original request}
  → Inspect the debate: /tas-explain {timestamp}

Workspace: {workspace}
Lessons: {workspace}/lessons.md

> `/tas-explain {timestamp}` — inspect the dialectic debate
> `/tas-workspace` — manage workspace artifacts
```

**On error** (non-zero exit):

```
**Error**: MetaAgent encountered an issue.
Workspace artifacts (if any): {workspace}
```

---

## Error Handling

**NEVER fall back to direct implementation on any error. Report and offer: retry / abort.**

### Error Detection & Recovery

Classify errors by priority order. If the Agent returned valid JSON with `status: "halted"`,
that is a normal HALT (Phase 3), NOT an error.

| Priority | Condition | Display | Recovery |
|----------|-----------|---------|----------|
| 1 | Response contains "ModuleNotFoundError" or "claude_agent_sdk" | ⚠ SDK not installed | Show install commands (pip/pipx/uv), ask to restart session |
| 2 | Response is empty or zero-length | ⚠ No response (응답 없음) | Retry / Simplify (re-classify with "simplify") / Abort |
| 3 | Non-empty but JSON parse fails | ⚠ Parse failure (파싱 실패) | Show first 200 chars of response. Retry / Abort |
| 4 | `status: "halted"` in valid JSON | (not an error) | → Phase 3 "On HALT" |
| 5 | Agent() failed with partial output | ⚠ Abnormal exit (비정상 종료) | Show partial output (200 chars). Retry / Abort |
| 6 | Any other failure | ⚠ No response (응답 없음) | Retry / Abort |

For all errors, include `Logs: {workspace}/` when workspace exists.

---

## Configuration

| Setting | Default | Adjustable By |
|---------|---------|---------------|
| MetaAgent model | opus | Fixed — classify/execute run on the most capable model |
| Dialectic model (Thesis/Antithesis) | sonnet-4-6 | Set in `agents/meta.md` step-config (`model` field) and `runtime/dialectic.py` fallback |
| Workspace | `{PROJECT_ROOT}/_workspace/quick/{timestamp}/` | Timestamped per run |
| Loop count | 1 | User at plan approval (`loop_count`) |
| Reentry point | 구현 | User at plan approval (`loop_policy.reentry_point`) |
| Persistent-fail HALT | after 3 consecutive same-blocker FAILs | `loop_policy.persistent_failure_halt_after` |
| Early exit | allowed when agents agree no further polish | `loop_policy.early_exit_on_no_improvement` |
