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
  "request_type":"implement|design|review|refactor|analyze",
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
  "reasoning":"..."
}
```

Or for trivial requests that reached Classify:
```json
{"command":"classify","mode":"direct","response":"{brief answer}","reasoning":"..."}
```

### Display Plan

**If `mode: "direct"`**: Display MetaAgent's response. Done.

**If `mode: "quick"` with `complexity: "simple"` (1 step)**:
```
Request (요청): {request}
Type (분류): Quick ({request_type}) — {complexity}
Step (단계): {steps[0].name} — {steps[0].goal}

Approve or modify? (승인 또는 수정)
```

**If `mode: "quick"` with `complexity: "medium"` or `"complex"` (2-4 steps)**:
```
## Execution Plan (정반합)

Request (요청): {request}
Type (분류): Quick ({request_type}) — {complexity}

| # | Step (단계) | Goal (목표) |
|---|------------|------------|
| 1 | {steps[0].name} | {steps[0].goal} |
| 2 | {steps[1].name} | {steps[1].goal} |
...

Iterations (반복): {loop_count}
  · Reentry point (재진입): {loop_policy.reentry_point} (from iteration 2)
  · Early exit (조기 종료): {"allowed" if early_exit_on_no_improvement else "not allowed"}
  · Persistent failure HALT: after {loop_policy.persistent_failure_halt_after} consecutive same-blocker failures
  · Lessons accumulate across iterations in lessons.md

{reasoning}

Approve or modify. Examples: "approve", "3 iterations", "reenter from 기획", "skip 테스트"
```

### Handle User Response

After applying any modification below, show a brief changelog before re-displaying the plan:

```
Changes:
- {field}: {old value} → {new value}
```

Then re-display the updated plan.

- **Approve** ("approve", "ok", "yes", "go", "lgtm", "승인", "ㅇㅇ") → Initialize workspace, → Phase 2
- **Adjust iteration count** (e.g., "3 iterations", "3번 반복해줘", "한 번만"):
  - Parse the new `loop_count` integer from user text
  - Update the plan JSON in place (no re-classify needed)
  - Show changelog and re-display plan
- **Adjust reentry point** (e.g., "reenter from 기획", "기획부터 다시", "구현만 반복"):
  - Update `loop_policy.reentry_point` to `기획` or `구현` accordingly
  - Show changelog and re-display plan
- **Modify pass criteria** (e.g., "add performance criterion to 검증", "기획 pass criteria를 ~로 변경"):
  - Identify the target step by name from user text
  - Replace or append to that step's `pass_criteria` array
  - Re-display plan (no re-classify needed)
- **Remove step** (e.g., "skip 테스트", "테스트 단계 빼줘", "기획 생략"):
  - Remove the named step from `steps` array
  - Re-number remaining step IDs sequentially
  - Re-display plan
- **Add step** (e.g., "add security check after 검증", "검증 후에 보안 점검 단계 추가해줘"):
  - Insert new step after the named anchor step with user-specified goal
  - Ask the user for concrete pass criteria: "What should pass criteria be for this step? (e.g., 'No SQL injection in user inputs', 'All endpoints return < 200ms')"
  - If user provides criteria, use them. If user says "skip" or equivalent, assign `pass_criteria: ["Goal achieved"]`
  - Re-number step IDs sequentially
  - Show changelog and re-display plan
- **Set focus angle** (e.g., "focus on performance", "성능 관점으로 리뷰해줘", "보안 중심으로"):
  - Add `focus_angle` field to the plan JSON root: `"focus_angle": "{user-specified angle}"`
  - This is passed to MetaAgent Execute and influences iteration focus
  - Re-display plan
- **Multiple modifications** (several adjustments at once):
  - Apply all modifications sequentially, then re-display once
- **Major plan restructure** → Re-invoke classify with the user's adjustment hint, → Display Plan again
- **Reject** ("no", "cancel", "abort", "거부") → Done

---

## Phase 2: Execute Quick Dialectic

Initialize workspace from classify result:

```bash
WORKSPACE="$PROJECT_ROOT/{workspace from classify JSON}"
mkdir -p "$WORKSPACE"
```

Write `$WORKSPACE/REQUEST.md` with original request text.

### Dirty-Tree Check (implement/refactor only)

For `request_type` in `[implement, refactor]`, check for uncommitted changes before execution:

```bash
DIRTY="$(git status --porcelain 2>/dev/null | head -5)"
DIRTY_COUNT="$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
```

If `DIRTY` is non-empty, warn the user:

```
⚠ You have uncommitted changes ({DIRTY_COUNT} file(s)):
{DIRTY}
{if DIRTY_COUNT > 5: "  ... and {DIRTY_COUNT - 5} more"}

tas will modify files directly. To preserve your current state, run `git stash` first.
Continue anyway?
```

If user declines, abort. If user confirms (or request_type is not implement/refactor), proceed.

### Pre-Execution Message

Display a brief scope message before invoking MetaAgent:

```
Running {len(steps)} step(s) × {loop_count} iteration(s)...
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
{"status":"completed","workspace":"...","summary":"...","iterations":N,"early_exit":bool,"rounds_total":N}
```

### Display to User

**On success** (`status: "completed"`):

Determine whether code was modified by checking `request_type`:

**Implementation steps** (`request_type`: implement, refactor; or any plan with 구현 step):

ThesisAgent has bypassPermissions and modifies code directly during the dialectic.
Do NOT ask "적용할까요?" — code is already changed.

```
Converged (정반합) — {iterations} iteration(s), {rounds_total} rounds.{" (early exit)" if early_exit}
{summary from JSON}

Changed files: `git diff --stat` output
Deliverable: {workspace}/DELIVERABLE.md
Lessons: {workspace}/lessons.md

> **Recommended**: Run `/tas-verify` to independently trace boundary values.
```

The user can review and revert if needed:
  · Review: `git diff` to see all changes
  · Selective revert: `git checkout -- <file>` to undo specific files
  · Full revert: `git stash` to shelve all changes (recoverable via `git stash pop`)

**Design/analysis steps** (`request_type`: design, analysis, review):

ThesisAgent produces deliverable documents, not code changes. Read the deliverable and display it inline:

```bash
# Read the deliverable content with size guard
DELIVERABLE_LINES="$(wc -l < ${WORKSPACE}/DELIVERABLE.md 2>/dev/null || echo 0)"
DELIVERABLE_CONTENT="$(head -200 ${WORKSPACE}/DELIVERABLE.md 2>/dev/null)"
```

If the deliverable is 200 lines or fewer, display it in full:

```
Converged (정반합) — {iterations} iteration(s), {rounds_total} rounds.{" (early exit)" if early_exit}
{summary from JSON}

---
{DELIVERABLE_CONTENT}
---

Full deliverable: {workspace}/DELIVERABLE.md
Lessons: {workspace}/lessons.md
```

If the deliverable exceeds 200 lines, show a preview:

```
Converged (정반합) — {iterations} iteration(s), {rounds_total} rounds.{" (early exit)" if early_exit}
{summary from JSON}

---
{DELIVERABLE_CONTENT (first 200 lines)}

... ({DELIVERABLE_LINES - 200} more lines)
---

Full deliverable: {workspace}/DELIVERABLE.md
Lessons: {workspace}/lessons.md
```

If the deliverable file is missing or empty, fall back to showing just the path.

**On HALT** (`status: "halted"`):

Read `{workspace}/lessons.md` to extract the specific blockers that caused the halt.

Map `halt_reason` to a human-readable label:

| halt_reason (raw) | Display label |
|-------------------|---------------|
| `persistent_verify_failure` | Persistent verification failure |
| `persistent_test_failure` | Persistent test failure |
| `circular_argumentation` | Circular argumentation — agents could not converge |
| `convergence_failure` | Convergence failure |
| `dialogue_degeneration` | Dialogue degeneration — agents produced empty responses |
| `unparseable_verdicts` | Unparseable verdicts — agent output format error |
| `missing_engine_artifacts` | Missing engine artifacts (internal error) |
| `workspace_convention_violation` | Workspace convention violation (internal error) |
| (other) | Use `halt_reason` as-is |

```
⚠ Halted early.

Reason: {display label from table above}
Halted at: {halted_at}

Blockers identified (from lessons.md):
{List the specific blocker descriptions from the last retry entries in lessons.md}

Suggested next steps:
```

Provide actionable recovery guidance based on `halt_reason`:

| halt_reason | Guidance |
|-------------|----------|
| `persistent_verify_failure` | "The same verification issue recurred {N} times. Check the blocker above and fix it manually, then re-run: `/tas {original request}`" |
| `persistent_test_failure` | "Tests failed repeatedly on the same issue. Run the failing test manually to diagnose: `{test command from lessons.md if available}`. Fix and re-run `/tas`." |
| `circular_argumentation` | "Thesis and Antithesis could not converge. Run `/tas-explain {timestamp}` to see the debate, then rephrase your request with more specific constraints." |
| (other) | "Check `{workspace}/lessons.md` for details. You can retry with `/tas {request}` or inspect workspace logs." |

Extract `{timestamp}` from the workspace path (the `YYYYmmdd_HHMMSS` directory name).

```
Workspace: {workspace}
Lessons: {workspace}/lessons.md
Dialogue: `/tas-explain {timestamp}` — see what was debated
```

**On error** (non-zero exit):

```
**Error**: MetaAgent encountered an issue.
Workspace artifacts (if any): {workspace}
```

---

## Error Handling

**NEVER fall back to direct implementation on any error. Report and offer: retry / abort.**

### Error Classification

When MetaAgent invocation fails, classify the error and present structured recovery:

**Type A — JSON Parse Failure** (Agent returned text but not valid JSON):
```
⚠ Could not parse MetaAgent response.
Cause: Response was not valid JSON.
Logs: check {workspace}/ for details.

→ Retry / Abort
```

**Type B — Agent Timeout or Empty Response** (zero-length result or Agent() hung):
```
⚠ No response from MetaAgent (timeout or empty output).
Cause: Request complexity may have exceeded processing capacity.

→ Retry / Reduce complexity (fewer steps) and retry / Abort
```
If user chooses complexity downgrade: re-invoke Classify with hint "simplify to fewer steps".

**Type C — Agent invocation failure with partial output** (Agent() errored but produced partial JSON or non-JSON):

Note: If the Agent returned valid JSON with `status: "halted"`, that is a normal HALT — handled by Phase 3 "On HALT" above, NOT by this error handler. Type C applies only when the Agent() call itself failed (non-zero exit, partial output, etc.).

```
⚠ MetaAgent exited abnormally (invocation failure).
Logs: {workspace}/ — check for partial output in logs/ directories.

→ Retry / Abort
```

**Type D — SDK Not Installed** (Agent response contains "ModuleNotFoundError" or "claude_agent_sdk"):
```
⚠ claude-agent-sdk is not installed. /tas requires it to run.

Install with one of:
  pip install claude-agent-sdk
  pipx install claude-agent-sdk
  uv tool install claude-agent-sdk

Then start a new session and try again.
```

### Detection Priority

| Priority | Check | Error Type |
|----------|-------|------------|
| 1 | Response contains "ModuleNotFoundError" or "claude_agent_sdk" | Type D |
| 2 | Response is empty or zero-length | Type B |
| 3 | Response is non-empty but JSON parse fails | Type A |
| 4 | JSON parsed successfully with `status: "halted"` | Phase 3 "On HALT" (not an error) |
| 5 | Agent() invocation failed (non-zero exit, partial output) | Type C |
| 6 | Any other Agent() failure | Type B (default) |

---

## Configuration

| Setting | Default | Adjustable By |
|---------|---------|---------------|
| Agent model | opus | Fixed — always use the most capable model |
| Workspace | `{PROJECT_ROOT}/_workspace/quick/{timestamp}/` | Timestamped per run |
| Loop count | 1 | User at plan approval (`loop_count`) |
| Reentry point | 구현 | User at plan approval (`loop_policy.reentry_point`) |
| Persistent-fail HALT | after 3 consecutive same-blocker FAILs | `loop_policy.persistent_failure_halt_after` |
| Early exit | allowed when agents agree no further polish | `loop_policy.early_exit_on_no_improvement` |
