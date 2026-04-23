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
- Read agent definition files (meta.md, thesis.md, antithesis.md)
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

### Session Bootstrap (non-trivial path only)

Per Phase 6 ISO-01 + D-01: replace the user-tree workspace with a named-branch git worktree under XDG cache. **This block runs ONLY when the Trivial Gate did not respond directly** (i.e., we are about to enter Classify or Phase 0b Resume). Trivial responses skip session creation entirely (worktree-only-for-real-runs invariant — D-01 Rejected: "Trivial Gate 이전에 session bootstrap" → trivial 응답도 worktree 만들면 stale 누적 가속화).

```bash
# Phase 0 inline halt JSON helper (used by the bootstrap block below; mirrors Phase 0b EMIT_HALT shape)
EMIT_HALT() {
  printf '{"status":"halted","workspace":"","halt_reason":"%s","summary":"%s","halted_at":"phase-0-session-bootstrap"}\n' \
    "${HALT_REASON}" "${SUMMARY}"
}

# Phase 6 D-08 backlog guard: refuse new bootstrap if user already has ≥20 stale tas/session-* worktrees
WT_BACKLOG_COUNT="$(git -C "${PROJECT_ROOT}" worktree list --porcelain 2>/dev/null \
  | awk '/^worktree/{wt=$2} /^branch refs\/heads\/tas\/session-/{print wt}' \
  | wc -l | tr -d ' ')"
if [ "${WT_BACKLOG_COUNT:-0}" -ge 20 ]; then
  cat <<'EOF'
⚠ tas/session-* worktree가 20개 이상 누적됐습니다.
정리: `git worktree list | grep tas/session-` 후
       `git worktree remove <path>` + `git branch -D <branch>`
또는: `/tas-workspace clean` (Phase 6 Plan 06-04 — session worktree cleanup 통합)
EOF
  exit 0
fi

# Phase 6 D-01: session worktree bootstrap (ISO-01 + ISO-03)
TS="$(date -u +%Y%m%dT%H%M%SZ)"
PROJECT_NAME="$(basename "${PROJECT_ROOT}")"
case "${PROJECT_NAME}" in
  ""|"/"|*"/"*) PROJECT_NAME="tas-session" ;;  # D-02 defensive fallback
esac
CACHE_ROOT="${XDG_CACHE_HOME:-${HOME}/.cache}/tas-sessions"
SESSION_DIR="${CACHE_ROOT}/${TS}"
SESSION_WORKTREE="${SESSION_DIR}/${PROJECT_NAME}"
SESSION_BRANCH="tas/session-${TS}"

mkdir -p "${SESSION_DIR}" \
  || { HALT_REASON=engine_crash; SUMMARY="세션 캐시 디렉터리 생성 실패: ${SESSION_DIR}"; EMIT_HALT; exit 0; }

# Named branch worktree — NOT --detach (PROJECT.md Key Decisions: reviewable PR identity)
git -C "${PROJECT_ROOT}" worktree add -b "${SESSION_BRANCH}" "${SESSION_WORKTREE}" HEAD \
  || { HALT_REASON=engine_crash; SUMMARY="세션 worktree 생성 실패: ${SESSION_WORKTREE}"; EMIT_HALT; exit 0; }

# Atomic LATEST symlink swap (ln -sfn rename(2) syscall — D-04)
ln -sfn "${SESSION_WORKTREE}" "${CACHE_ROOT}/LATEST" \
  || { HALT_REASON=engine_crash; SUMMARY="LATEST symlink 갱신 실패"; EMIT_HALT; exit 0; }

# Workspace inside the session worktree (replaces former ${PROJECT_ROOT}/_workspace/quick)
mkdir -p "${SESSION_WORKTREE}/_workspace/quick"

export SESSION_WORKTREE SESSION_BRANCH SESSION_DIR  # downstream Phase 1+ consume these
```

All 3 bootstrap failure paths route to the existing `engine_crash` halt_reason enum (Phase 3.1 D-TOPO-05 freeze — NEVER invent a new enum). The halt JSON shape matches Phase 0b's inline helper so Phase 3 "On HALT" rendering handles display unchanged.

---

## Phase 0b: Resume Gate (triggered by --resume)

```text
# SCOPE: SKILL.md may ONLY Read:
#   - ${LATEST_LINK} (symlink resolve, single-step — D-04)
#   - ${WORKSPACE}/checkpoint.json
#   - ${WORKSPACE}/plan.json
#   - ${WORKSPACE}/REQUEST.md
# Directory listing via `ls iteration-*/` is metadata only — allowed.
# Reading dialogue.md, round-*.md, deliverable.md, lessons.md, heartbeat.txt is an I-1 regression.
```

If `$ARGUMENTS` contains `--resume`, route here and skip Phase 1 (Classify). On any pre-condition failure below, emit a halt JSON directly — do NOT call MetaAgent.

### Step 0: Resolve Session via LATEST Symlink (Phase 6 D-04 + D-10)

Cold-resume chicken-and-egg: `checkpoint.json` lives inside the session worktree, but the resume gate must know the session worktree path BEFORE it can find `checkpoint.json`. The `${CACHE_ROOT}/LATEST` symlink (atomically updated by Phase 0 Session Bootstrap, D-04) is the single zero-ambiguity entry point.

```bash
CACHE_ROOT="${XDG_CACHE_HOME:-${HOME}/.cache}/tas-sessions"
LATEST_LINK="${CACHE_ROOT}/LATEST"

# 0.1 — LATEST symlink must exist (no prior /tas run → no_checkpoint HALT)
if [ ! -L "${LATEST_LINK}" ]; then
  HALT_REASON=no_checkpoint
  SUMMARY="LATEST 세션 인덱스 없음. /tas로 새로 시작하세요."
  EMIT_HALT
  exit 0
fi

# 0.2 — Bare readlink is intentional (1-step resolve; BSD compat — Pitfall 9:
#       do NOT add the deep-resolve flag). Chain-attack defense is the prefix-check
#       below, NOT deep resolution. (T-V4-01 mitigation)
RESOLVED="$(readlink "${LATEST_LINK}")"
case "${RESOLVED}" in
  "${CACHE_ROOT}/"*) ;;  # safe — under cache root
  *)
    HALT_REASON=workspace_missing
    SUMMARY="LATEST symlink이 cache root 외부 경로를 가리킵니다."
    EMIT_HALT
    exit 0
    ;;
esac

# 0.3 — Per D-04: LATEST gestures ${SESSION_WORKTREE} directly (1-step resolution)
SESSION_WORKTREE="${RESOLVED}"
WS_BASE="${SESSION_WORKTREE}/_workspace/quick"
```

After Step 0 succeeds, downstream Step 1 (Workspace Resolution) uses `${WS_BASE}` in place of `${PROJECT_ROOT}/_workspace/quick`. Step 2's 7 pre-condition checks operate on `${WORKSPACE}` resolved from `${WS_BASE}` — no schema bump, no new HALT enums.

### Step 1: Workspace Resolution

Parse `$ARGUMENTS` for the `--resume` token. If a path argument follows, take it as `PATH_ARG`; otherwise use latest-auto detection.

```bash
# Path-arg branch (user supplied `/tas --resume <workspace_path>`)
# WS_BASE resolved in Step 0 from LATEST symlink (Phase 6 D-04)
WORKSPACE="$(WS_BASE="${WS_BASE}" python3 -c '
import os, sys
p = os.path.realpath(sys.argv[1])
root = os.path.realpath(os.environ["WS_BASE"])
if p == root or p.startswith(root + os.sep):
    print(p); sys.exit(0)
sys.exit(3)
' "$PATH_ARG")"  # non-zero exit → halt `workspace_missing`

# Latest-auto branch (user supplied `/tas --resume` with no path)
WORKSPACE="$(ls -1dt "${WS_BASE}/"*/ 2>/dev/null \
  | grep -v '/classify-' \
  | head -1 | sed 's#/$##')"
# empty string → halt `no_checkpoint`
```

On path-arg failure → emit `halt_reason: workspace_missing`. On empty latest-auto → emit `halt_reason: no_checkpoint`. The `classify-*` prefix is excluded — Classify-mode workspaces are not resume targets.

### Step 2: Pre-Conditions (emit halt JSON directly — do NOT call MetaAgent on failure)

Run these 7 checks sequentially against the resolved `$WORKSPACE`. Any failure → emit the halt JSON shape (below) to stdout and `exit 0`. The JSON flows to Phase 3 "On HALT" rendering without invoking MetaAgent.

```bash
# 1. Workspace directory exists
test -d "$WORKSPACE" || { HALT_REASON=workspace_missing; EMIT_HALT; exit 0; }

# 2. checkpoint.json present
test -f "$WORKSPACE/checkpoint.json" || { HALT_REASON=no_checkpoint; EMIT_HALT; exit 0; }

# 3. plan.json present
test -f "$WORKSPACE/plan.json" || { HALT_REASON=plan_missing; EMIT_HALT; exit 0; }

# 4. checkpoint.json parses (stdout = one-line JSON, exit 0)
CKPT_JSON="$(python3 "${SKILL_DIR}/runtime/checkpoint.py" read "$WORKSPACE")" \
  || { HALT_REASON=checkpoint_corrupt; EMIT_HALT; exit 0; }

# 5. schema_version == 1
SCHEMA_V="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1]).get("schema_version"))' "$CKPT_JSON")"
[ "$SCHEMA_V" = "1" ] || { HALT_REASON=checkpoint_schema_unsupported; EMIT_HALT; exit 0; }

# 6. status not in {completed, finalized}
CKPT_STATUS="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1]).get("status",""))' "$CKPT_JSON")"
case "$CKPT_STATUS" in
  completed|finalized) HALT_REASON=already_completed; EMIT_HALT; exit 0 ;;
esac

# 7. plan_hash matches recomputed hash of plan.json
EXPECTED_HASH="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1]).get("plan_hash",""))' "$CKPT_JSON")"
ACTUAL_HASH="$(python3 "${SKILL_DIR}/runtime/checkpoint.py" hash "$WORKSPACE/plan.json")"
[ "$EXPECTED_HASH" = "$ACTUAL_HASH" ] || { HALT_REASON=plan_hash_mismatch; EMIT_HALT; exit 0; }
```

Halt JSON shape (emitted on any of the 7 failures — MetaAgent is NEVER called on failure; Phase 0b `Agent()` call count on failure path is 0):

```json
{"status":"halted","workspace":"{path-or-empty}","halt_reason":"{enum}","summary":"{korean-message}","halted_at":"resume-gate"}
```

The `{korean-message}` values come from the Phase 3 Recovery Guidance table for each `halt_reason`. After emitting, Phase 3 "On HALT" rendering handles display unchanged.

### Step 3: User Summary + Confirmation

Derive display values without reading any dialectic artifact. Directory listing via `ls iteration-*/` is metadata only — it does NOT count as reading iteration content (SCOPE comment above).

```bash
# Iteration count (derived from directory structure — metadata only)
ITER_LATEST="$(ls -1d "${WORKSPACE}/iteration-"*/ 2>/dev/null \
  | sed -E 's#.*iteration-([0-9]+)/$#\1#' \
  | sort -n | tail -1)"
ITER_LATEST="${ITER_LATEST:-0}"
N=$(( ITER_LATEST > 0 ? ITER_LATEST : 1 ))

# Parse plan.json top-level fields (NO internal dialectic fields)
PLAN_JSON_CONTENT="$(cat "$WORKSPACE/plan.json")"
REQUEST_TYPE="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1]).get("request_type",""))' "$PLAN_JSON_CONTENT")"
COMPLEXITY="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1]).get("complexity",""))' "$PLAN_JSON_CONTENT")"
LOOP_COUNT="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1]).get("loop_count",1))' "$PLAN_JSON_CONTENT")"

# Checkpoint cursor (current_step + completed_steps)
K="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1]).get("current_step",""))' "$CKPT_JSON")"
COMPLETED_JSON="$(python3 -c 'import json,sys; print(json.dumps(json.loads(sys.argv[1]).get("completed_steps",[])))' "$CKPT_JSON")"
M="$(python3 -c 'import json,sys
arr = json.loads(sys.argv[1])
print(arr[-1] if arr else "")' "$COMPLETED_JSON")"

# slug lookup — map step id -> step name via plan.steps[]
slug() { python3 -c '
import json, sys
steps = json.loads(sys.argv[1]).get("steps",[])
sid = sys.argv[2]
for s in steps:
  if str(s.get("id")) == str(sid):
    print(s.get("name","")); break
' "$PLAN_JSON_CONTENT" "$1"; }

SLUG_PREV="$(slug "$M")"   # may be empty if completed_steps is empty
SLUG_NEXT="$(slug "$K")"
COMPLETED_NAMES="$(python3 -c '
import json,sys
plan = json.loads(sys.argv[1]); ids = json.loads(sys.argv[2])
by_id = {str(s.get("id")): s.get("name","") for s in plan.get("steps",[])}
print(", ".join(by_id.get(str(i), str(i)) for i in ids))
' "$PLAN_JSON_CONTENT" "$COMPLETED_JSON")"
```

Print the summary (Korean, verbatim labels — D-04 format):

```
워크스페이스: {ABSOLUTE_WORKSPACE_PATH}

Iteration {N} / Step {M} ({SLUG_PREV}) 완료.
  완료된 스텝: {COMPLETED_NAMES}
  요청 타입: {REQUEST_TYPE} · 복잡도: {COMPLEXITY} · LOOP_COUNT={LOOP_COUNT}
다음: Step {K} ({SLUG_NEXT}).

계속할까요? (y/n)
```

If `COMPLETED_STEPS` is empty (no steps done yet in the current iteration), substitute the first summary line with `Iteration {N} / 아직 완료된 스텝 없음.` and omit the `완료된 스텝:` row.

Y/N handling (natural-language prompt + wait-for-response — do NOT use `AskUserQuestion`; matches Phase 1 Classify approval UX):

| User input | Synonym set | Action |
|------------|-------------|--------|
| **Approve** | `y` / `yes` / `ok` / `ㅇ` / `ㅇㅇ` / `계속` / `go` | Proceed to Step 4 |
| **Cancel** | `n` / `no` / `cancel` / `취소` / `ㄴ` / `ㄴㄴ` | Print exactly `Resume 취소됨. /tas {original request}로 새 run을 시작하세요.` and exit (do NOT call MetaAgent) |
| **Other** | anything else | Re-ask once: `y/n 로 답해주세요.` — on second non-match, treat as cancel |

### Step 4: Invoke MetaAgent Execute with MODE: resume

Read the original request from the workspace's trust source (do NOT re-read `$ARGUMENTS` — REQUEST.md is canonical for resume):

```bash
ORIGINAL_REQUEST="$(cat "$WORKSPACE/REQUEST.md")"
```

Parse `plan.json` fields needed for the Agent() prompt (`steps`, `loop_policy`, `project_domain`, `focus_angle`) — SKILL.md passes these through verbatim and does NOT interpret them.

```
Agent({
  description: "tas resume: {request_type} ({complexity}, loop×{loop_count})",
  prompt: "Read ${SKILL_DIR}/agents/meta.md and follow its instructions exactly.

MODE: resume
REQUEST: {content of REQUEST.md}
WORKSPACE: {ABSOLUTE_WORKSPACE_PATH}
PROJECT_ROOT: {PROJECT_ROOT}
SKILL_DIR: {SKILL_DIR}
REQUEST_TYPE: {plan.request_type}
COMPLEXITY: {plan.complexity}
PLAN: {plan.steps JSON verbatim}
LOOP_COUNT: {plan.loop_count}
LOOP_POLICY: {plan.loop_policy JSON}
PROJECT_DOMAIN: {plan.project_domain — omit line if null}
FOCUS_ANGLE: {plan.focus_angle — omit line if null}
RESUME_FROM: {checkpoint.current_step}
COMPLETED_STEPS: {checkpoint.completed_steps JSON}
PLAN_HASH: {checkpoint.plan_hash}

Return ONLY the JSON result line.",
  mode: "bypassPermissions",
  model: "opus"
})
```

**Agent() call count on success path: exactly 1.** Do NOT call Classify Agent() under any circumstance on the resume path — re-classify during resume is a Pitfall 3 violation (CLAUDE.md Common Mistakes). If `plan.json` is missing, Step 2 already halted with `plan_missing` — never fall back to Classify.

After MetaAgent returns, the response is a JSON line with the same shape as Phase 2 Execute → Phase 3 "Present Results" handles rendering unchanged.

<!--
Phase 0b does NOT:
- Present a list-selection UI for multiple workspaces (Latest + explicit path only — PROJECT.md Out of Scope)
- Repair corrupt checkpoints (user must `/tas` fresh — no --force-resume)
- Clean up stale workspaces (`/tas-workspace clean` is a separate skill)
- Fall back to Classify if plan.json is missing (halt plan_missing instead — Pitfall 3)
- Invoke /tas-explain inline (user routes there via Phase 3 HALT recovery guidance)
- Read dialectic artifacts (dialogue.md / round-*.md / deliverable.md / lessons.md — I-1 regression)
- Introduce new halt_reason enums (e.g. engine_lost, polling_orphan_death, engine_exit_missing) — Phase 3.1 D-TOPO-05 freeze; step_transition_hang absorbs the polling-orphan-death path
-->

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
  if implementation_chunks != null AND len(implementation_chunks) > 0:
    "\n\n**구현은 {len(implementation_chunks)}개 chunk로 순차 실행됩니다:**\n"
    for c in implementation_chunks:
      "  [{c.id}] {c.title}" + (" (의존: " + ", ".join(c.dependencies_from_prev_chunks) + ")" if non-empty else "") + "\n"
    "\n  override: `chunks: 1` (단일 실행) / `chunks: 2` (병합) / `chunks: N` (다른 개수로 재분해)"
}

Approve or modify (승인 또는 수정). Examples:
  "approve" / "3 iterations" / "skip 테스트" / "reenter from 기획"
  "focus on performance" / "add security check after 검증" / "modify 검증 criteria"
  "chunks: 1" (chunks 분해 취소) / "chunks: 2" (chunks 병합)

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
| **Adjust chunks** | `"chunks: 1"`, `"chunks: 2"`, `"chunks 분해 취소"`, `"chunk 분할 없이"` | Update `plan.implementation_chunks` in-place (integer → MetaAgent re-reasons N-chunk split; `1` or "분해 취소" → set to `null`). Re-hash `plan_hash` via existing plan-adjust routing. If override conflicts with D-01 trigger (e.g., user requests `chunks: 7` > cap 5), show changelog noting cap enforcement. |
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

### Dirty-Tree Information (Phase 6 ISO-02 — explicit warning + auto-proceed)

Per Phase 6 D-03: dirty-tree abort UX is REMOVED. Session worktree isolation makes "uncommitted changes endanger your work" no longer true — `/tas` operates inside `${SESSION_WORKTREE}` (a separate git checkout under `~/.cache/tas-sessions/`), so user's main worktree files are never directly modified.

```bash
DIRTY_COUNT="$(git -C "${PROJECT_ROOT}" status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
if [ "${DIRTY_COUNT}" -gt 0 ]; then
  cat <<EOF
ℹ /tas는 사용자 작업 트리와 분리된 session worktree (${SESSION_WORKTREE}) 에서 실행됩니다.
  현재 작업 트리의 uncommitted 변경사항 (${DIRTY_COUNT}개)은 session worktree에 보이지 않으며,
  session 결과물은 사용자 main 브랜치에 자동 머지되지 않습니다 (manual review only).
  계속 진행합니다.
EOF
fi
# (No abort prompt — explicit information only, then continue.)
```

### Pre-Execution Message (Phase 6 ISO-02 — session-aware)

Display a brief scope message before invoking MetaAgent:

```
Running {len(steps)} step(s) × {loop_count} iteration(s)...
Session: ${SESSION_WORKTREE} (branch: ${SESSION_BRANCH})
```

The legacy "직접 수정됩니다" warning (formerly appended for implement/refactor request types) is REMOVED — under session isolation, code lands inside the session worktree, NOT the user's main tree. Review path is `git -C "${SESSION_WORKTREE}" diff`, NOT `git diff`. Phase 7 (COMMIT-05) will append a manual `git merge tas/session-{ts}` proposal at PASS time.

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
{"status":"completed","workspace":"...","summary":"...","iterations":N,"early_exit":bool,"rounds_total":N,"engine_invocations":N,"references_read":["${SKILL_DIR}/references/meta-execute.md"]}
```

### Validate Attestation

If `status` is `"completed"` and `engine_invocations` is `0` or missing, the result
is suspect — MetaAgent may have simulated the dialectic instead of running the engine.
Warn the user:

```
⚠ MetaAgent reported completion but engine_invocations is 0.
This may indicate the dialectic engine was not invoked. Check workspace logs.
```

**references_read validation** (SLIM-02 attestation):

Parse the `references_read` field from MetaAgent JSON. Expected contents by Mode:
- If the Agent() call was classify: expect `references_read` contains a path **ending with** `/references/meta-classify.md`
- If the Agent() call was execute (new run or resume): expect `references_read` contains a path **ending with** `/references/meta-execute.md`

On empty array or mismatched path, warn the user (do NOT halt):

```
⚠ MetaAgent reported completion but references_read is missing or mismatched.
Prompt-slim attestation violation — result may reflect drift from canonical procedure.
(The engine's actual work is authoritative; this field is a drift-detection signal,
not a failure signal. See CLAUDE.md for details.)
```

This check is **suffix-match only** — SKILL.md does NOT read the referenced files
(see CLAUDE.md §Information Hiding Is Load-Bearing). The path string is treated
as opaque data.

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

Session: ${SESSION_WORKTREE} (branch: ${SESSION_BRANCH})
Review: `git -C "${SESSION_WORKTREE}" log --oneline ${SESSION_BRANCH}`
Diff:   `git -C "${SESSION_WORKTREE}" diff main..${SESSION_BRANCH}`

Changed files (in session worktree): `git -C "${SESSION_WORKTREE}" diff --stat` output
Deliverable: {workspace}/DELIVERABLE.md
Lessons: {workspace}/lessons.md

> `/tas-verify` — independently verify boundary values and correctness
> `/tas-explain {timestamp}` — inspect the dialectic debate
> `/tas-workspace` — manage workspace artifacts
```

The user can review the session branch (changes are NOT in their main tree):
  · Review log: `git -C "${SESSION_WORKTREE}" log --oneline ${SESSION_BRANCH}`
  · Review diff: `git -C "${SESSION_WORKTREE}" diff main..${SESSION_BRANCH}`
  · Discard session: `git -C "${PROJECT_ROOT}" worktree remove "${SESSION_WORKTREE}" && git -C "${PROJECT_ROOT}" branch -D ${SESSION_BRANCH}` (manual — Phase 6 D-08 retention policy: tas does NOT auto-clean)
  · Phase 7 (COMMIT-05, future): `git merge ${SESSION_BRANCH}` proposal will appear here when COMMIT-05 ships

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

Session: ${SESSION_WORKTREE} (branch: ${SESSION_BRANCH})

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

Session: ${SESSION_WORKTREE} (branch: ${SESSION_BRANCH})

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
| `no_checkpoint` | No checkpoint (체크포인트 없음) |
| `plan_missing` | Plan missing (plan.json 없음) |
| `checkpoint_corrupt` | Checkpoint corrupt (체크포인트 손상) |
| `plan_hash_mismatch` | Plan hash mismatch (plan 해시 불일치) |
| `checkpoint_schema_unsupported` | Checkpoint schema unsupported (체크포인트 스키마 미지원) |
| `workspace_missing` | Workspace missing (워크스페이스 경로 오류) |
| `already_completed` | Already completed (이미 완료됨) |
| `sdk_session_hang`     | SDK session hang (SDK 세션 무응답) |
| `step_transition_hang` | Step transition hang (스텝 전환 중 무응답) |
| `bash_wrapper_kill`    | Watchdog forced termination (워치독 강제 종료) |
| `chunk_merge_conflict` | Chunk merge conflict (Chunk 머지 충돌) |
| `worktree_backlog`     | Worktree backlog (worktree 누적 — 환경 정리 필요) |
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
| `no_checkpoint` | "체크포인트가 없습니다. `/tas {원래 요청}`으로 새로 시작하세요." |
| `plan_missing` | "plan.json이 없어 재개할 수 없습니다 (Classify 전 종료 가능). `/tas`로 새로 시작하세요." |
| `checkpoint_corrupt` | "체크포인트 JSON 파싱 실패. `/tas-workspace {workspace}`로 내용을 확인하거나 `/tas`로 새로 시작." |
| `plan_hash_mismatch` | "plan.json이 Classify 승인 이후 수정됐습니다. 원본을 복구하거나 `/tas`로 새로 시작." |
| `checkpoint_schema_unsupported` | "checkpoint schema {v} 미지원 (현재 1만 지원). tas 업데이트 또는 `/tas`로 새로 시작." |
| `workspace_missing` | "워크스페이스 경로 없음 또는 `_workspace/quick/` 밖입니다. `/tas-workspace`로 목록 확인." |
| `already_completed` | "이미 완료된 run입니다. 새 요청은 `/tas`." |
| `sdk_session_hang`     | "SDK 응답이 없어 엔진이 중단됐습니다. `/tas --resume`으로 재시도하거나, 긴 step이면 `TAS_WATCHDOG_TIMEOUT_SEC`을 늘리세요." |
| `step_transition_hang` | "엔진이 결과 없이 종료됐습니다. `/tas --resume`으로 재시도하세요. 반복되면 `/tas-workspace`로 로그를 확인하세요." |
| `bash_wrapper_kill`    | "Watchdog이 설정된 시간 내 응답 부재로 프로세스를 종료했습니다. 긴 step이면 `TAS_WATCHDOG_TIMEOUT_SEC`을 늘린 후 `/tas --resume`으로 재시도하세요." |
| `chunk_merge_conflict` | "Chunk 머지 충돌: cherry-pick + git apply 모두 실패했습니다. 공유 파일을 여러 chunk가 동시에 수정했을 가능성이 큽니다. `plan.json`의 `implementation_chunks`를 재검토하거나 `chunks: 1` 로 override하여 `/tas`로 새로 시작하세요. `merge.log`는 `{workspace}/iteration-*/logs/step-*-implement-chunk-*/merge.log` 에서 확인. 이 경로에서는 `/tas --resume`이 지원되지 않습니다 (mid-chunk resume은 M1 범위 외)." |
| `worktree_backlog`     | "git worktree 엔트리가 10개 이상 누적되어 sub-loop 진입이 차단됐습니다. `git worktree prune` 으로 stale 메타데이터를 정리하거나, `/tas-workspace clean` 으로 workspace 정리 후 다시 시도하세요. 이 halt는 환경 정리 신호일 뿐 chunk 실행 실패가 아닙니다." |
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
