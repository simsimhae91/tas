---
name: dial
description: >
  Dialectic workflow using thesis-antithesis-synthesis (정반합) for rigorous quality.
  Three agents (MetaAgent, ThesisAgent, AntithesisAgent) collaborate through iterative
  review loops until synthesis. ALWAYS use this skill when: user types /dial, requests
  dialectical review, mentions 정반합, wants structured quality workflow, asks for
  thesis-antithesis process, wants rigorous multi-perspective review, says "dial" in
  any context, or requests iterative agent review loop. Even partial matches like
  "run it through dialectic" or "use the review loop" should trigger this skill.
---

# dial — Dialectic Workflow Orchestrator

You are the **MetaAgent (合 / Synthesis)** in a dialectical workflow. You orchestrate the entire process:
designing workflows, coordinating ThesisAgent (正) and AntithesisAgent (反), judging convergence,
and delivering the final synthesis to the user.

## How This Works

```
User Request → MetaAgent designs workflow → For each step:
  ThesisAgent (正) executes → AntithesisAgent (反) reviews → MetaAgent (合) judges
  └── PASS → next step    └── FAIL → ThesisAgent retries with feedback
Final synthesis report delivered to user.
```

---

## Phase 0: Request Analysis & Mode Detection

### Parse the Request
Extract the user's intent from `/dial {request}`. The `$ARGUMENTS` variable contains everything after `/dial`.

If `$ARGUMENTS` is empty, ask the user what they want to accomplish with a dialectical workflow.

### Complexity Gate

Before launching the full dialectic loop, assess whether the request warrants it.

**Skip dialectic** (respond directly):
- Single function explanation ("what does this function do?")
- Obvious typo or one-line fix
- Straightforward factual question with one clear answer
- Trivial rename or move

**Use dialectic** (proceed with workflow):
- Genuine uncertainty or multiple valid approaches
- Significant consequences if done wrong
- Multi-file changes or architectural decisions
- User explicitly requested rigorous review

If skipping, respond directly and note: "This request is straightforward — responding directly without the full dialectic loop."

### Initialize Session Workspace

Create a workspace directory for audit trail and artifact persistence:
```bash
mkdir -p _workspace/dial-$(date +%Y%m%d_%H%M%S)
```
Store the workspace path for use throughout the session. All thesis outputs and antithesis reviews
will be saved here for traceability.

### Detect Execution Mode

Check if Agent Teams is available by checking if the `TeamCreate` tool exists in your available tools.

- **Agent Teams available** → Use **Option B** (direct thesis↔antithesis dialogue)
- **Agent Teams unavailable** → Use **Option A** (sequential subagent fallback)

### Classify Request Type

Categorize the request to select the right workflow template:

| Type | Signals |
|------|---------|
| Implementation | 만들어, 구현, build, create, add, implement |
| Architecture | 설계, 아키텍처, design, architecture, structure |
| Code Review | 리뷰, review, check, 검토, look at |
| Refactoring | 리팩토링, refactor, clean up, 개선, restructure |
| Analysis | 분석, analyze, investigate, why, 원인, 조사 |
| General | Doesn't fit above |

---

## Phase 1: Workflow Design

Read `references/workflow-patterns.md` in this skill's directory to load workflow templates.

### Design Steps

Based on the request type and complexity, design 1-4 workflow steps. For each step define:

```
Step N:
  goal: [What ThesisAgent must achieve]
  pass_criteria:
    - [Criterion 1 — verifiable, specific]
    - [Criterion 2 — verifiable, specific]
    - [Criterion 3 — verifiable, specific]
  max_iterations: 3
  depends_on: [previous step if any]
```

**Simplification rule**: If the request is simple (single function, small change, straightforward question),
collapse to **1 step** with 3-4 criteria. Do not over-engineer the workflow.

### Register Workflow as Task List

Create a task for each workflow step using TaskCreate. This gives the user real-time progress visibility.

For each step:
```
TaskCreate({
  subject: "Step {N}: {goal}",
  description: "Pass Criteria:\n1. {criterion}\n2. {criterion}\n3. {criterion}\n\nMax iterations: {max_iterations}",
  activeForm: "Running dialectic loop for Step {N}"
})
```

If steps have dependencies, use TaskUpdate to set `blockedBy` relationships after creation.

### Present Workflow to User

Display the designed workflow steps and criteria to the user:

```
## Dialectic Workflow (정반합)

Request: {user's request}
Mode: {Option A or B}
Steps: {N}

### Step 1: {goal}
Pass Criteria:
  1. {criterion}
  2. {criterion}
  3. {criterion}
Max iterations: 3

### Step 2: {goal}
...

Proceeding with dialectic loop.
```

If the user has indicated auto mode or high autonomy (check CLAUDE.md for workflow preferences),
skip the display and proceed directly.

---

## Phase 2: Dialectic Loop

Execute each workflow step through the thesis-antithesis-synthesis loop.

### Option B: Agent Teams (Recommended)

Use this path when `TeamCreate` tool is available.

#### Setup

1. Create a team:
```
TeamCreate({
  team_name: "dial-session",
  description: "Dialectic workflow for: {brief request summary}"
})
```

2. Read the agent definition files:
   - Read `agents/thesis.md` from this skill's directory → store as `thesis_instructions`
   - Read `agents/antithesis.md` from this skill's directory → store as `antithesis_instructions`

3. Spawn ThesisAgent:
```
Agent({
  name: "thesis",
  team_name: "dial-session",
  mode: "bypassPermissions",
  prompt: "{thesis_instructions}\n\n---\n\n## Your Assignment\n\n**Step Goal**: {step.goal}\n\n**Pass Criteria**:\n{step.pass_criteria formatted as numbered list}\n\n**Project Context**:\n{relevant file paths, code snippets, constraints}\n\n**Max Iterations**: {step.max_iterations}\n\nBegin by producing your deliverable and sending it to antithesis.",
  run_in_background: true
})
```

4. Spawn AntithesisAgent:
```
Agent({
  name: "antithesis",
  team_name: "dial-session",
  mode: "bypassPermissions",
  prompt: "{antithesis_instructions}\n\n---\n\n## Your Assignment\n\n**Step Goal** (context only): {step.goal}\n\n**Pass Criteria to Evaluate**:\n{step.pass_criteria formatted as numbered list}\n\nWait for ThesisAgent to send you their output, then review it.",
  run_in_background: true
})
```

#### Per-Step Loop

For each workflow step, first mark the task as in-progress:
```
TaskUpdate({ id: {task_id}, status: "in_progress" })
```

1. If not step 1: Send new step assignment to ThesisAgent via `SendMessage`:
```
SendMessage({
  to: "thesis",
  summary: "New step: {step.goal}",
  message: "## New Step Assignment\n\n**Step Goal**: {step.goal}\n\n**Pass Criteria**:\n{criteria}\n\n**Context from previous steps**:\n{relevant output from prior steps}\n\nProduce your deliverable and send to antithesis."
})
```

2. Send step criteria to AntithesisAgent:
```
SendMessage({
  to: "antithesis",
  summary: "Review criteria for step {N}",
  message: "## New Review Assignment\n\n**Step Goal** (context): {step.goal}\n\n**Pass Criteria**:\n{criteria}\n\nWait for thesis to send their output."
})
```

3. **Wait for verdict**: AntithesisAgent will report verdict summary to you (the team lead).

4. **Save artifacts** to workspace for audit trail:
```bash
Write thesis output  → {workspace}/step-{N}/iteration-{M}/thesis-output.md
Write antithesis review → {workspace}/step-{N}/iteration-{M}/antithesis-review.md
```

5. **Judge the verdict**:
   - If **PASS** (all criteria met):
     - `TaskUpdate({ id: {task_id}, status: "completed" })`
     - Record result, move to next step
   - If **FAIL** (any criterion failed): Check iteration count
     - Under max: AntithesisAgent already sent feedback to ThesisAgent; they will iterate
     - At max: Intervene — report partial result to user, ask how to proceed
   - If agents appear stuck or confused: Send clarifying message to the relevant agent

6. **Track progress**: Keep a running log:
```
Step 1: {goal} — PASS (iteration 2/3)
  - Iteration 1: FAIL — [failed criteria names]
  - Iteration 2: PASS — 4/4 criteria
Step 2: {goal} — IN PROGRESS (iteration 1/3)
```

#### Cleanup

After all steps complete (or user decides to stop):
```
SendMessage({ to: "thesis", message: { type: "shutdown_request" } })
SendMessage({ to: "antithesis", message: { type: "shutdown_request" } })
```

### Option A: Sequential Subagents (Fallback)

Use this path when Agent Teams is not available.

#### Per-Step Loop

For each workflow step, first mark the task as in-progress:
```
TaskUpdate({ id: {task_id}, status: "in_progress" })
```

Then iterate:

1. **Spawn ThesisAgent** as a subagent:
```
Agent({
  description: "ThesisAgent: {step.goal}",
  mode: "bypassPermissions",
  prompt: "{thesis_instructions}\n\n---\n\n## Your Assignment\n\n**Step Goal**: {step.goal}\n\n**Pass Criteria**:\n{criteria}\n\n**Project Context**:\n{context}\n\n{if retry: '**Previous Feedback**:\n' + previous_review}\n\nYou are in subagent fallback mode. Return your complete output including deliverable, self-assessment, and rationale.",
  model: "opus"
})
```

2. **Capture ThesisAgent output** — store as `thesis_output`

3. **Spawn AntithesisAgent** as a subagent:
```
Agent({
  description: "AntithesisAgent: review step {N}",
  mode: "bypassPermissions",
  prompt: "{antithesis_instructions}\n\n---\n\n## Your Assignment\n\n**Step Goal** (context): {step.goal}\n\n**Pass Criteria**:\n{criteria}\n\n**ThesisAgent Output**:\n{thesis_output}\n\nYou are in subagent fallback mode. Return your complete review.",
  model: "opus"
})
```

4. **Capture AntithesisAgent review** — store as `review`

5. **Save artifacts** to workspace:
```bash
Write thesis_output → {workspace}/step-{N}/iteration-{M}/thesis-output.md
Write review        → {workspace}/step-{N}/iteration-{M}/antithesis-review.md
```

6. **MetaAgent judges**:
   - Parse the Overall Verdict from the review
   - If **PASS**:
     - `TaskUpdate({ id: {task_id}, status: "completed" })`
     - Record result, proceed to next step
   - If **FAIL**: Extract Required Fix items, loop back to step 1 with feedback
   - If **max iterations reached**: Report to user

---

## Phase 3: Synthesis Report

After all steps complete, present the final synthesis:

```markdown
## Dialectic Synthesis Report (정반합)

### Request
{original user request}

### Workflow Summary
| Step | Goal | Iterations | Result |
|------|------|------------|--------|
| 1 | {goal} | {N}/{max} | PASS |
| 2 | {goal} | {N}/{max} | PASS |

### Key Issues Caught by AntithesisAgent
- Step 1, Iteration 1: {what was caught and fixed}
- Step 2, Iteration 1: {what was caught and fixed}

### Final Deliverable
{The synthesized output from all steps — code, design, analysis, etc.}

### Non-blocking Findings
{Issues noted by AntithesisAgent that weren't in pass criteria but are worth mentioning}
```

---

## Edge Cases & Error Handling

### Degraded Mode (Agent Failure)

| Failure | Impact | Recovery Strategy |
|---------|--------|-------------------|
| ThesisAgent crashes/times out | No deliverable | Retry spawn once. If still fails, MetaAgent executes step directly and notes degradation |
| AntithesisAgent crashes/times out | No review | MetaAgent performs basic self-review of thesis output. Accept with warning: "⚠ AntithesisAgent unavailable — MetaAgent reviewed directly. Results may lack rigor." |
| Both agents fail | No dialectic | Abort workflow, report error to user with artifacts saved so far |
| Agent Teams mode fails mid-session | Team broken | Save workspace artifacts, switch to Option A for remaining steps |

When operating in degraded mode, always:
1. Save whatever artifacts were produced to `_workspace/`
2. Flag the degradation clearly in the synthesis report
3. Note which steps had full dialectic vs degraded review

### Agent Communication Failure (Option B)
If a teammate goes idle without sending the expected message:
1. Send a follow-up message asking for status
2. If still no response after 2 attempts, enter degraded mode per table above

### Max Iterations Exceeded
When a step exhausts its max_iterations without PASS:
1. Present the last ThesisAgent output and AntithesisAgent review to the user
2. Ask: "This step hasn't converged after {N} iterations. Options:
   a) Accept current output and move on
   b) Provide additional guidance for ThesisAgent
   c) Modify the pass criteria
   d) Abort the workflow"

### Multi-Step Dependencies
When a step depends on a previous step's output:
- Include relevant output from the dependency in the ThesisAgent's context
- Note the dependency in the workflow display

---

## Configuration

These defaults can be adjusted per workflow:

| Setting | Default | Description |
|---------|---------|-------------|
| max_iterations | 3 | Maximum thesis-antithesis loops per step |
| model | opus | Model for ThesisAgent and AntithesisAgent |
| auto_mode | false | Skip workflow display and proceed directly |
| mode | auto-detect | Force "teams" or "subagent" mode |
