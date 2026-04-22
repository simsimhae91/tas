# Execute Mode

MetaAgent reads this file after Mode Detection when `MODE == execute` (new run or
resume path). It is the procedural body for execute — the canonical iteration loop
+ chunk sub-loop + finalization procedure that was previously inlined in
`${SKILL_DIR}/agents/meta.md` (pre-Phase-5 L241-1085). Mode Detection itself
stays in `${SKILL_DIR}/agents/meta.md`; this file assumes the caller has already
determined `MODE == execute`.

Shared contracts (`engine_invocations` schema, convergence verdict tokens,
`references_read` attestation field) live in `${SKILL_DIR}/agents/meta.md`
§Final JSON Contract and §Convergence Model — do NOT restate them here.

---

Run the approved plan across 1..`LOOP_COUNT` iterations. Each iteration is a full or
partial pass (see reentry rules), producing a DELIVERABLE.md. Lessons accumulate across
iterations. After the loop, write the cross-iteration synthesis to `{WORKSPACE}/DELIVERABLE.md`.

## Phase 1: Initialize

**Attestation first step (SLIM-02):** If you have not already appended
`"${SKILL_DIR}/references/meta-execute.md"` to your in-memory `references_read` list
(per `${SKILL_DIR}/agents/meta.md` §Mode-bound Reference Load), do so now. This is the
first actionable step of Execute Mode (applies to both `MODE: new` and `MODE: resume`);
attestation must be self-enforced at Read-time so it is populated even if execution
halts before Phase 5 JSON Response.

```bash
mkdir -p {WORKSPACE}
touch {WORKSPACE}/lessons.md  # if not exists
```

### Initial checkpoint write (CHKPT-03 + CHKPT-01)

**Branch on MODE:**

- **MODE: resume** (Phase 2 — resume path):
  1. Read `{WORKSPACE}/plan.json` (file exists — this is the resume trust source).
  2. Cross-check: the `PLAN` JSON received from SKILL.md MUST match `plan.json[steps]` byte-for-byte after canonical JSON re-serialization. Mismatch → emit `{"status":"halted","workspace":"{WORKSPACE}","halt_reason":"resume_plan_mismatch","summary":"SKILL.md가 전달한 PLAN과 workspace의 plan.json이 일치하지 않습니다.","halted_at":"execute-initialize-resume"}` and return.
  3. Compute plan hash defence-in-depth:
     ```
     Bash({
       command: "python3 {SKILL_DIR}/runtime/checkpoint.py hash {WORKSPACE}/plan.json",
       run_in_background: false,
       description: "Re-verify plan_hash on resume"
     })
     ```
     Compare stdout (64-char hex) to input `PLAN_HASH`. Mismatch → emit `{"status":"halted","workspace":"{WORKSPACE}","halt_reason":"plan_hash_mismatch","summary":"plan.json이 Classify 승인 이후 수정됐습니다. 원본을 복구하거나 /tas로 새로 시작.","halted_at":"execute-initialize-resume"}` and return.
  4. **SKIP `write-plan`** — plan.json is immutable after Classify approval (CHKPT-03 mtime invariant).
  5. **SKIP initial checkpoint write** — existing `checkpoint.json` is the trust source. Do NOT overwrite.
  6. **Chunk guard (M1 Phase 2 scope limit)** — read the current checkpoint via `python3 {SKILL_DIR}/runtime/checkpoint.py read {WORKSPACE}` (re-read; do NOT cache). If `checkpoint.current_chunk != null` OR `checkpoint.completed_chunks != []`, emit `{"status":"halted","workspace":"{WORKSPACE}","halt_reason":"chunk_resume_not_supported_in_m1","summary":"Chunk sub-loop 재개는 M1 Phase 2 범위 외입니다. Phase 4 릴리스 후 지원 예정.","halted_at":"execute-initialize-resume"}` and return.

- **MODE absent (new run — Phase 1 original path):** Only on the first entry into Execute Mode for this workspace. If `{WORKSPACE}/plan.json` already exists, skip this entire block (defence-in-depth fallback for legacy invocations without MODE:resume — the resume path above is the canonical route). Execute the 3 numbered steps below.

1. **Persist plan.json** (canonical JSON, immutable after this write):

   Compose the plan dict from the Classify output: `request`, `request_type`,
   `complexity`, `steps`, `loop_count`, `loop_policy`, `implementation_chunks`
   (value as produced by Classify Phase 2c — either `null` when no decomposition
   was triggered, OR the 6-field array `[{id, title, scope, pass_criteria,
   dependencies_from_prev_chunks, expected_files}]` when a complex
   implement/refactor request produced vertical-layer decomposition — see
   Classify Phase 2c above), `project_domain`, `focus_angle: null`,
   `approved_at: <ISO 8601 UTC>`.

   ```
   Bash({
     command: "python3 {SKILL_DIR}/runtime/checkpoint.py write-plan {WORKSPACE} --json '<compact JSON of plan dict>'",
     run_in_background: false,
     description: "Persist approved plan (CHKPT-03)"
   })
   ```

   Exit 3 (plan.json already exists) MUST be treated as "resume path" — re-read existing plan.json and skip step 2+3 below.

2. **Compute plan_hash** (CONTEXT D-02):

   ```
   Bash({
     command: "python3 {SKILL_DIR}/runtime/checkpoint.py hash {WORKSPACE}/plan.json",
     run_in_background: false,
     description: "Compute plan_hash"
   })
   ```

   Capture stdout (single line, 64-char hex) as `{PLAN_HASH}`. Store in in-memory
   binding for this Execute invocation; **do not cache across processes** (read
   back via `hash` CLI if needed).

3. **Initial checkpoint.json** (CHKPT-01 · `status: running` · `completed_steps: []`):

   Build payload with all 9 required fields:
   - `schema_version`: `1` (integer — CONTEXT D-03)
   - `workspace`: `"{WORKSPACE}"` (absolute path)
   - `plan_hash`: `"{PLAN_HASH}"`
   - `current_step`: ID of the first step to execute (from `PLAN.steps[0].id`)
   - `completed_steps`: `[]`
   - `current_chunk`: `null` (initial write — no chunk has started; populated by
     Phase 2d.5 Chunk Sub-loop during chunked-step execution; resets to `null`
     when that step completes)
   - `completed_chunks`: `[]` (initial write — empty; populated by Phase 2d.5
     as each chunk cherry-pick merge succeeds; resets to `[]` when the step
     completes — iteration-scoped per CONTEXT D-08)
   - `status`: `"running"`
   - `updated_at`: `<ISO 8601 UTC, microsecond precision, +00:00 suffix>`

   ```
   Bash({
     command: "python3 {SKILL_DIR}/runtime/checkpoint.py write {WORKSPACE} --json '<compact JSON of payload>'",
     run_in_background: false,
     description: "Initial checkpoint write (CHKPT-01)"
   })
   ```

**Info-hiding invariant**: Only MetaAgent writes these files. `SKILL.md` has no
awareness of `checkpoint.json` or `plan.json` in Phase 1 (readers arrive in
Phase 2 Resume Gate). **Classify Mode workspaces** (`_workspace/quick/classify-*/`)
MUST NOT receive a checkpoint — this block applies to Execute Mode only
(Pitfall P1-07).

Read once:
- `{SKILL_DIR}/agents/thesis.md`, `{SKILL_DIR}/agents/antithesis.md`
- `{SKILL_DIR}/references/engine-invocation-protocol.md` — how to invoke `run-dialectic.sh` (run_in_background, liveness, completion handling). You MUST follow this protocol.
- `{SKILL_DIR}/references/workspace-convention.md` §"Iteration & Retry Flow" — canonical retry/HALT rules
- `{SKILL_DIR}/references/workflow-patterns.md` §"Iteration Support" — focus angle selection
- `{SKILL_DIR}/references/failure-patterns.md` + `{SKILL_DIR}/references/planning-antithesis-directive.md` — injected into antithesis for 기획 steps only

Parse: `PLAN` (steps array), `LOOP_COUNT` (≥1), `LOOP_POLICY` (reentry_point,
early_exit_on_no_improvement, persistent_failure_halt_after).

Initialize: `iteration_results[]`, `lessons=""` (append-only), `focus_angles_used{}`.

## Phase 2: Iteration Loop

**MODE: resume iteration cursor (D-03 + D-06):**

If `MODE == "resume"`, derive `ITER_LATEST` from directory structure before entering the loop:

```bash
ITER_LATEST=$(ls -1d "${WORKSPACE}/iteration-"*/ 2>/dev/null \
  | sed -E 's#.*iteration-([0-9]+)/$#\1#' \
  | sort -n | tail -1)
ITER_LATEST=${ITER_LATEST:-1}
```

For `i` in `1..(ITER_LATEST-1)`: verify `{WORKSPACE}/iteration-{i}/DELIVERABLE.md` exists.
  - Exists → skip the iteration (trust `lessons.md` already appended). Include the iteration's `DELIVERABLE.md` in `improvement_context` when reentering for iteration `ITER_LATEST+1` or later.
  - Missing → emit `{"status":"halted","halt_reason":"resume_iteration_damaged","workspace":"{WORKSPACE}","summary":"iteration-{i} 디렉터리는 있는데 DELIVERABLE.md가 누락되었습니다. /tas-workspace로 정리 후 /tas로 새로 시작하세요.","halted_at":"execute-iteration-loop-resume"}` and return.

For `i == ITER_LATEST`: enter the per-step loop below with the resume-skip block (see `#### Resume cursor application` in §Phase 2d) ACTIVE for `S.id in COMPLETED_STEPS`.

For `i > ITER_LATEST`: normal Phase 2a/2b/2c/2d flow (as in new-run mode). `completed_steps[]` resets to `[]` when entering a new iteration per Phase 1 D-01 (step 9.5 writes fresh state per iteration).

For iteration `i` in `1..LOOP_COUNT`:

```bash
ITER_DIR={WORKSPACE}/iteration-{i}
mkdir -p $ITER_DIR/logs
```

### Phase 2a: Determine Step Subset

- **Iteration 1**: execute all steps in `PLAN` (full flow)
- **Iteration 2+**: skip steps that come before `LOOP_POLICY.reentry_point`
  (default reentry: `구현` → skip `기획` since the plan is stable)

Example: with `reentry_point="구현"`, iteration 2's step list is `[구현, 검증, 테스트]`.

If the user set reentry to `기획`, the full flow runs every iteration (full redesign).

### Phase 2b: Select Focus Angle (Iteration 2+)

Select this iteration's focus angle per `references/workflow-patterns.md`
§"Iteration Support" — priority order (external override → antithesis
carry-over → domain rotation → fallback) and the full domain rotation table
live there. Record the selected angle in `focus_angles_used` so later
iterations don't repeat it.

### Phase 2c: Assemble Improvement Context (Iteration 2+)

Read `{WORKSPACE}/iteration-{i-1}/DELIVERABLE.md` and `{WORKSPACE}/lessons.md`.

Build `improvement_context` containing:
1. **Previous Iteration Summary** — abbreviated summary of what was delivered
2. **Accumulated Lessons Learned** — full contents of lessons.md
3. **This Iteration's Focus: {focus_angle}** — with directives:
   - 구현: treat current state as baseline, make targeted improvements for {focus_angle}, do not regress
   - 검증/테스트: higher bar — apply {focus_angle} as primary lens alongside standard invariants

State clearly: "Acceptance Criteria were ALREADY SATISFIED. Do NOT re-implement from scratch."

For iteration 1, `improvement_context` is empty.

### Phase 2d: Step Execution Loop (within iteration)

Initialize per-iteration state:
- `step_results_this_iter`: []
- `cumulative_context_this_iter`: "" (within-iteration cross-step context)
- `consecutive_fail_count`: dict `{step_name: count}` (persistent-failure detector)

For each step `S` in the iteration's step subset:

### Resume cursor application (only when `MODE: resume` AND `i == ITER_LATEST`)

If `MODE == "resume"` AND current iteration index `i == ITER_LATEST` AND `S.id in COMPLETED_STEPS`:

  1. Log to stderr: `ALREADY DONE: step {S.id} ({slug}) — resume idempotent skip`
  2. Read `{ITER_DIR}/logs/step-{S.id}-{slug}/deliverable.md`
     (**do NOT** read `dialogue.md`, `round-*.md`, or `lessons.md` from this directory — single-file re-injection only; RESUME-02 info-hiding applies to MetaAgent too, though the constraint is stricter for SKILL.md.)
  3. Build a short summary (≤ 200 words) of the deliverable content and append to `cumulative_context_this_iter` under the heading `## Prior Step (resumed): {S.name}`.
  4. `continue` — skip the rest of the Step Execution Loop for this step. Do NOT re-execute. Do NOT overwrite the existing `deliverable.md` (1-DF-02 idempotent invariant — SHA-256 of `deliverable.md` MUST be byte-identical before and after resume).

Rationale: RESUME-03. The existing `deliverable.md` is the trust source; re-execution would clobber it and break the file-boundary state invariant (CLAUDE.md §파일 경계로 상태 전달). This skip branch re-derives from disk each time — do NOT cache `COMPLETED_STEPS` or deliverable content in a prompt variable (Pitfall 4).

### Step Roles by Name

Map the step's `name` to thesis/antithesis role framing:

| Step name | Thesis role | Antithesis role | Convergence target |
|-----------|-------------|-----------------|---------------------|
| `기획` / `Plan` | Proposer — drafts design/approach | Challenger — scope coverage, completeness | design soundness |
| `구현` / `Implement` | Implementer — writes code with bypassPermissions | Reviewer — code quality, convention, integrity | code correctness |
| `검증` / `Verify` | Attacker — aggressively finds defects | Judge — evaluates defect severity (blocker vs noise) | 0 blockers or documented exceptions |
| `테스트` / `Test` | Test author/executor — writes tests, runs, captures results | Evaluator — coverage sufficiency, real-run results (incl. UI/UX for web) | tests pass + coverage complete |
| (any other) | Proposer | Challenger | output quality |

For `review | analyze | design` request types, you may have only a Plan-like or single step —
use the proposer/challenger default.

### Convergence Model

- `검증` uses **inverted model** (attacker vs judge): verdict is `PASS` (0 blockers) or `FAIL` (≥1 blockers).
- `테스트` uses **inverted model**: verdict is `PASS` (tests pass, coverage adequate) or `FAIL`.
- All other steps use **standard model** (thesis proposes, antithesis ACCEPT/REFINE/COUNTER).

### Prepare Dialectic Config

For each step, build the config the Python engine consumes.

1. **Log directory**:
   ```
   LOG_DIR={ITER_DIR}/logs/step-{S.id}-{slug}/
   mkdir -p $LOG_DIR
   ```
   On within-iteration retry (FAIL → 구현 → re-check), append `-retry-{N}`:
   `step-{S.id}-{slug}-retry-1`, etc. Retries live inside the current iteration's directory.

2. **Assemble system prompts** — write ONLY the step-specific injection.
   The engine prepends full agent templates via `thesis_template_path`/`antithesis_template_path`
   in step-config.json. Do NOT copy agent instructions into prompt files.

   **Standard (기획/구현/일반)**:
   ```
   Thesis system prompt = "---\nSTEP ROLE: {thesis_role}\nSTEP GOAL: {S.goal}\nPASS CRITERIA:\n{S.pass_criteria as bullets}"
   Antithesis system prompt = "---\nSTEP ROLE: {antithesis_role}\nSTEP GOAL: {S.goal}\nPASS CRITERIA:\n{S.pass_criteria as bullets}"
   ```

   **기획-only antithesis enhancement** (when `S.name == "기획"`):

   Append the directive + failure_patterns content to the antithesis system
   prompt EXACTLY as specified in `references/planning-antithesis-directive.md`.
   Do NOT append any of that content to `thesis-system-prompt.md` — the
   asymmetry is the anti-confirmation-bias mechanism.

   **Inverted (검증/테스트)**:
   ```
   Thesis system prompt = "---\nROLE OVERRIDE: You are an ATTACKER. Aggressively find defects/test failures. Do NOT produce a deliverable — produce an issue list.\nSTEP GOAL: {S.goal}\nPASS CRITERIA:\n{S.pass_criteria}"
   Antithesis system prompt = "---\nROLE OVERRIDE: You are a JUDGE. For each issue thesis raises, judge: genuine blocker or noise? Output PASS (0 blockers) or FAIL (with blocker list).\nSTEP GOAL: {S.goal}"
   ```

3. **Write prompts to files**:
   - `{LOG_DIR}/thesis-system-prompt.md`
   - `{LOG_DIR}/antithesis-system-prompt.md`

4. **Build step_context** — the shared input visible to both agents:
   ```
   ## Original Request
   {REQUEST}

   ## Project Context
   - Root: {PROJECT_ROOT}
   - Domain: {project_domain from classify, if any}

   ## Iteration Context (iteration 2+ only)
   {improvement_context from Phase 2c — includes prior deliverable summary,
    accumulated lessons, and this iteration's focus angle}

   ## Prior Step Outputs (within this iteration)
   {cumulative_context_this_iter — empty on first step of iteration}

   ## Retry Context (if this is a within-iteration retry)
   {blockers/failures from the previous failed check, otherwise omit}
   ```

   **Synthesis Context injection (Phase 4 — integrated verify/test after chunked 구현)**

   When `S.name in {"검증", "테스트"}` AND `cumulative_chunk_context` is non-empty (implying the prior 구현 step was chunked and relayed per Phase 2d.5), **prepend** the following Synthesis Context section to `step_assignment` BEFORE the standard step goal / pass_criteria content. This ensures the integrated verify/test dialectic evaluates the **merged PROJECT_ROOT state** as a whole — not as chunk-N-biased — and surfaces synthesis-boundary regressions that chunk-level verify would miss (Pitfall 15).

   Template (build the chunk plan + deliverable-path list from `plan.implementation_chunks`):

   ```
   ## Synthesis Context (구현 step was chunked — 본 검증은 머지된 통합 상태 대상)

   **Chunk plan**:
     [{c1.id}] {c1.title}
     [{c2.id}] {c2.title} (depends on: {c2.dependencies_from_prev_chunks})
     ...
     [{cN.id}] {cN.title} (depends on: {cN.dependencies_from_prev_chunks})

   **Each chunk deliverable** (Read if needed — not inlined here to preserve context budget):
     - {ITER_DIR}/logs/step-{S_impl.id}-implement-chunk-{c1.id}/deliverable.md
     - {ITER_DIR}/logs/step-{S_impl.id}-implement-chunk-{c2.id}/deliverable.md
     - ...
     - {ITER_DIR}/logs/step-{S_impl.id}-implement-chunk-{cN.id}/deliverable.md

   **Synthesis focus** (이 verify/test 는 다음 4가지를 중점 검증):
     1. Public API / contracts at chunk boundaries — chunk N과 chunk N+1 간 시그니처 일치 여부
     2. Shared file final state — 여러 chunk가 건드린 파일의 최종 상태가 각 chunk 의도와 합치하는지
     3. Value flow integrity — 데이터가 chunk 1 → chunk 2 → … → chunk N을 거쳐 흐를 때 경계에서 변질되지 않았는지
     4. Regression — 후속 chunk가 초기 chunk의 기능을 깨뜨리지 않았는지 (chunk 1 초기 의도 vs 최종 상태 대조)

   **Not to be re-audited** (이미 chunk별 dialectic으로 검증 완료 — 중복 검증 금지):
     - 각 chunk 내부 구현 품질 (chunk 1 thesis의 로컬 로직, chunk 2 thesis의 변수 명명 등)
     - chunk별 내부 코드 스타일 · 컨벤션 일관성
   ```

   **Ownership + scope**:
   - `agents/antithesis.md` template is **UNCHANGED** — Synthesis focus is delivered via `step_context` (per-step injection), not via template edits. This preserves the Phase 5 Prompt Slim objective (meta-file token budget < 5,500).
   - `cumulative_chunk_context` itself (the ≤ 50KB in-memory relay from Phase 2d.5) is appended separately AFTER the Synthesis Context block if present, so the verify/test dialectic sees the structured focus first, then the per-chunk summary content.
   - When 구현 step was NOT chunked (`plan.implementation_chunks == null` OR the step was never chunked in this iteration), the Synthesis Context block is NOT injected — verify/test runs exactly as before Phase 4.
   - For `S.name == "테스트"` on web-frontend domain, the existing Playwright CLI directive (if present in the current file) remains in effect; Synthesis Context prepends it.

   **Injection happens once per integrated verify/test step** — subsequent retries within the same iteration reuse the same Synthesis Context (it does not change between retry-0 and retry-N of the same step).

5. **Testing-specific context injection** (테스트 step only):

   If `project_domain` in `["web-frontend"]`:
   ```
   ## Testing Strategy
   This is a web project. Testing must include BOTH:
   - Static: unit tests, type checks, lint
   - Dynamic: spin up local dev server (e.g., `npm run dev`), run Playwright tests
     via Bash (`npx playwright test`), capture screenshots via Playwright CLI
     (`npx playwright screenshot`), evaluate UI/UX (layout, rendering, interactive
     behavior, accessibility visible in snapshot).
     NOTE: Playwright MCP tools are NOT available in dialectic agent sessions.
     Always use Bash-based Playwright CLI execution.
   Thesis must execute the dynamic run and include screenshots/test output as evidence.
   Antithesis must evaluate the screenshots and test output.
   ```

   For non-web domains, static tests + command execution (e.g., `cargo test`, `pytest`) are sufficient.

6. **Write step-config.json** to `{LOG_DIR}/step-config.json`:
   ```json
   {
     "thesis_prompt_path": "{LOG_DIR}/thesis-system-prompt.md",
     "antithesis_prompt_path": "{LOG_DIR}/antithesis-system-prompt.md",
     "thesis_template_path": "{SKILL_DIR}/agents/thesis.md",
     "antithesis_template_path": "{SKILL_DIR}/agents/antithesis.md",
     "step_assignment": "## Step Assignment\n\n**Goal**: {S.goal}\n\n**Pass Criteria**:\n{criteria}\n\n**Context**:\n{step_context}\n\nProduce your initial position with reasoning and self-assessment.",
     "antithesis_briefing": "## Step Criteria\n\n**Goal** (context): {S.goal}\n\n**Pass Criteria**:\n{criteria}\n\nYou will receive ThesisAgent's position. Evaluate and respond.",
     "log_dir": "{LOG_DIR}",
     "step_id": "{S.id}",
     "step_goal": "{S.goal}",
     "project_root": "{PROJECT_ROOT}",
     "model": "claude-sonnet-4-6",
     "convergence_model": "{standard|inverted}",
     "language": "{ONLY set non-English if user explicitly requested a specific output language (e.g. '한국어로 작성'). Default: English. A Korean request with no language instruction means English output.}"
   }
   ```

   Template paths tell the engine where to find agent instruction files for prepending.

7. **Spawn engine** per `references/engine-invocation-protocol.md` — fire-and-forget
   via `nohup`, capture PID on stdout:

   ```
   Bash({
     command: "nohup bash ${SKILL_DIR}/runtime/run-dialectic.sh ${LOG_DIR}/step-config.json > ${LOG_DIR}/engine.log 2>&1 & echo $!",
     run_in_background: false,
     description: "Spawn dialectic engine for step {S.id}"
   })
   ```

   The call returns in milliseconds with stdout being a single integer — the
   engine PID. Capture it as `ENGINE_PID`.

   > **Phase 3.1 topology note** (TOPO-02 / D-TOPO-03): the three elements
   > `nohup` + `&` + `echo $!` are all load-bearing — removing any one
   > breaks orphan survival. `run_in_background: false` is also critical:
   > `true` would register a harness-tracked shell reference bound to this
   > subagent session, which the Claude Code harness reaps when the subagent
   > returns, killing the engine mid-round (Phase 3 close blocker — see
   > FINDINGS-nohup-bg-pattern.md §7). **NEVER attach `timeout:` to this
   > `Bash(...)` call** — the spawn itself is ms-long; engine lifetime is
   > tracked via file markers.
   >
   > The Phase 3 Bash `timeout(1)` Layer B watchdog (WATCH-03) runs **inside**
   > `run-dialectic.sh`, not at the `Bash()` tool level. Phase 3.1 adds an
   > EXIT trap (TOPO-01) ahead of that wrapper so `engine.done` + `engine.exit`
   > are written on every exit path (normal / raise / SIGTERM 124 or 143 /
   > SIGKILL 137). The `run-dialectic.sh` script MUST NOT use the `exec`
   > keyword on its final invocation lines — bash must remain Python's parent
   > so the EXIT trap can fire (Phase 3.1 Issue #1 close-out).

8. **Poll engine completion locally** (MetaAgent-owned — Scenario B) — do NOT
   return to MainOrchestrator yet. MainOrchestrator is not polling; MetaAgent
   owns the full engine lifecycle within a single Execute Mode Agent() call.

   The 10-min Bash cap requires chunking polls into ≤9.5-min calls. Each
   inner chunk is a single foreground `Bash(...)` call that returns in ≤570s
   (19 × 30s). Repeat the call until stdout ends with `done` or `dead`:

   ```
   Bash({
     command: "for i in $(seq 1 19); do
                 test -f \"${LOG_DIR}/engine.done\" && { echo done; exit 0; };
                 kill -0 \"$ENGINE_PID\" 2>/dev/null || { echo dead; exit 0; };
                 sleep \"${TAS_POLL_INTERVAL_SEC:-30}\";
               done; echo pending",
     run_in_background: false,
     description: "Poll engine for step {S.id} (<=9.5min)"
   })
   ```

   - If stdout trailing line is `done`: engine terminated cleanly (marker
     exists). Proceed to classify.
   - If stdout trailing line is `dead`: PID died without writing the marker.
     Proceed to classify — classification will resolve to
     `step_transition_hang` per D-TOPO-05.
   - If stdout trailing line is `pending`: still running. Re-invoke the same
     `Bash(...)` call in the next turn. The polling call MUST stay foreground
     (same `run_in_background: false` discipline as the spawn in step 7) —
     a background-flagged polling call would register a harness-tracked shell
     reference subject to the same reap policy that triggered Phase 3.1.

   `TAS_POLL_INTERVAL_SEC` env var (default 30s) overrides the interval. Do
   NOT attach a `timeout:` parameter — each call self-caps at 19 × 30s.

8b. **Classify verdict** — after polling terminates (trailing line `done` or
   `dead`), read exit and last log line:

   ```
   Bash({
     command: "EXIT=\"$(cat ${LOG_DIR}/engine.exit 2>/dev/null || echo lost)\";
              LAST=\"$(tail -n 1 ${LOG_DIR}/engine.log 2>/dev/null)\";
              printf '%s\\n%s\\n' \"$EXIT\" \"$LAST\"",
     run_in_background: false,
     description: "Read engine exit code + last log line for step {S.id}"
   })
   ```

   Apply the Phase 3 D-05 + Phase 3.1 D-TOPO-05 classification
   (authoritative table: `references/engine-invocation-protocol.md`
   §Failure classification):

   - `EXIT=0` + LAST valid `status: "completed"` / `"halted"` JSON →
     pass through: this becomes the step's final return JSON.
   - `EXIT=124` or `EXIT=137` or `EXIT=143` → synthesize HALT JSON with
     `"halt_reason": "bash_wrapper_kill"`, `"watchdog_layer": "B"`,
     `"wrapper_exit": <EXIT>`. (143 = SIGTERM propagated through bash EXIT
     trap — Plan 02 Test C ordering; shares row with 124/137.)
   - `EXIT=0` + LAST JSON parse-fail or absent → synthesize HALT JSON with
     `"halt_reason": "step_transition_hang"`, `"watchdog_layer": "B"`.
   - `EXIT="lost"` (exit file absent) + `! test -f engine.done` + PID dead →
     synthesize HALT JSON with `"halt_reason": "step_transition_hang"`,
     `"watchdog_layer": "B"` (D-TOPO-05 absorbs polling-orphan-death — no
     new enum).
   - Other non-zero + JSON absent → synthesize HALT JSON with
     `"halt_reason": "engine_crash"`.

   **MetaAgent-owned HALT forensics (info-hiding boundary):** for
   `bash_wrapper_kill` / `step_transition_hang`, fill `last_heartbeat` by
   reading `heartbeat.txt` — this cat lives inside MetaAgent:

   ```
   Bash({
     command: "cat {LOG_DIR}/heartbeat.txt",
     run_in_background: false,
     description: "Forensics: last heartbeat before HALT (MetaAgent-owned read)"
   })
   ```

   File absence → `last_heartbeat: null` (not an error). SKILL.md must NEVER
   read `heartbeat.txt` directly — that would regress the Phase 2 D-07
   Allowed Read list (Canary #4 guard). If `dialectic.py` already emitted a
   halted JSON with `last_heartbeat` populated via the Phase 3 outer
   try/finally path, that JSON takes precedence over MetaAgent's local
   `cat`.

   The synthesized (or passed-through) JSON is this step's result. It has
   the existing pre-Phase-3.1 shape — `status: completed` or
   `status: halted` — so MainOrchestrator's Phase 2 handler in SKILL.md
   works byte-identical to before. Do NOT emit an intermediate envelope
   that exposes the MetaAgent-internal spawn metadata (`engine_pid` + path
   fields) under any status keyword such as the previously-drafted
   "engine-launched" placeholder — Scenario B keeps that record strictly
   MetaAgent-internal.

9. **Read deliverable** at `deliverable_path` and append a summary to
   `cumulative_context_this_iter` (so downstream steps within this iteration can reference).

9.5. **Update checkpoint.json** (CHKPT-01): after appending the step's deliverable
     summary to `cumulative_context_this_iter`, atomically update the workspace
     checkpoint.

     Build the payload for the **completed step** `{S.id}`:
     - `schema_version`: `1`
     - `workspace`: `"{WORKSPACE}"`
     - `plan_hash`: `"{PLAN_HASH}"` (carry forward unchanged from Phase 1 Initialize)
     - `current_step`: ID of the next step in this iteration's subset, or `null`
       if `{S.id}` was the last step of the final iteration
     - `completed_steps`: `<prior completed_steps[]> + ["{S.id}"]`
     - `current_chunk`: within a chunked 구현 step, set to the in-progress
       chunk id (string); otherwise `null` (at step boundaries — when the step
       itself completes, reset to `null` because all chunks have merged).
       See Phase 2d.5 Chunk Sub-loop for chunk-aware writes during step execution.
     - `completed_chunks`: within a chunked 구현 step, the ordered list of
       successfully-merged chunk ids (e.g. `["1","2"]` when chunk 3 is in progress);
       otherwise `[]` (reset on step boundary and at new iteration start per
       CONTEXT D-08). Chunk-field values are advisory/forensic — they are
       NOT a resume trust source (Phase 2 D-06 `chunk_resume_not_supported_in_m1`
       HALT gates mid-chunk resume).
     - `status`: `"running"` (use `"halted"` + `halt_reason` on the HALT path —
       see Within-Iteration FAIL Handling below; `"finalized"` is set by Phase 3
       Final Aggregate)
     - `updated_at`: `<ISO 8601 UTC now>`

     Invoke:
     ```
     Bash({
       command: "python3 {SKILL_DIR}/runtime/checkpoint.py write {WORKSPACE} --json '<compact JSON of payload>'",
       run_in_background: false,
       description: "Update checkpoint after step {S.id}"
     })
     ```

     This call is synchronous, sub-second, and stdlib-only.
     **Do NOT cache the payload in memory across steps** — re-derive from
     `plan.json` + the running `completed_steps[]` on every call. (In-memory
     state promotion is forbidden — see CLAUDE.md Common Mistakes.)

### Phase 2d.5: Chunk Sub-loop (when S.name == 구현 AND implementation_chunks non-null + non-empty)

When the current step is 구현 AND `plan.implementation_chunks` is a non-null, non-empty array, the step executes as a **sub-loop of chunks** instead of a single dialectic. Each chunk runs in a detached git worktree, uses the Scenario B invocation contract verbatim (per chunk), and merges into `PROJECT_ROOT` via cherry-pick before the next chunk starts (sequential relay — M1 has NO parallel execution).

**Entry condition check** (place at the top of step 7, before engine spawn):

```
if S.name == "구현" and isinstance(plan.implementation_chunks, list) and len(plan.implementation_chunks) > 0:
    # enter Phase 2d.5 (this section) — SKIP the standard single-dialectic steps 7/8/8b/9 below
    # (step 9.5 checkpoint update still runs, but with chunk-aware payload; see Merge + Checkpoint below)
else:
    # fall through to standard single-dialectic path (existing steps 7/8/8b/9/9.5)
```

**Sub-loop pre-flight** — runs ONCE before iterating over chunks (CONTEXT D-03 + Bash Sketch 1). Execute via a single Bash() call:

```
Bash({
  command: "mkdir -p \"${WORKSPACE}/chunks\" && \
git -C \"${PROJECT_ROOT}\" worktree prune --expire=1.hour.ago && \
STALE=\"$(git -C \"${PROJECT_ROOT}\" worktree list --porcelain 2>/dev/null | awk -v ws=\"${WORKSPACE}/chunks/chunk-\" '$1==\"worktree\" && index($2,ws)==1 {print $2}')\" && \
for stale in ${STALE}; do git -C \"${PROJECT_ROOT}\" worktree remove --force \"${stale}\" 2>/dev/null || true; done && \
WT_COUNT=\"$(git -C \"${PROJECT_ROOT}\" worktree list --porcelain 2>/dev/null | awk '$1==\"worktree\"' | wc -l | tr -d ' ')\" && \
echo \"WT_COUNT=${WT_COUNT}\"",
  run_in_background: false,
  description: "Phase 2d.5 pre-flight: prune + stale cleanup + count"
})
```

If the returned `WT_COUNT >= 10`, emit HALT JSON with `halt_reason: worktree_backlog` (NEW enum, D-03 — environment pollution domain, justified exception to Phase 3.1 D-TOPO-05 watchdog/hang enum freeze). Also write the halt checkpoint via `checkpoint.py write` (see FAIL/HALT Cleanup sketch below) and return to the orchestrator.

Initialize sub-loop locals:
- `cumulative_chunk_context = ""` (in-memory only — iteration-scoped; NO file persistence per CONTEXT D-04)
- `completed_chunks = []` (ordered list of successfully-merged chunk ids; mirrors the checkpoint payload field)

**For each chunk c in plan.implementation_chunks (in order — sequential relay):**

1. **Resolve chunk paths**:
   ```
   CHUNK_PATH="$(cd \"${WORKSPACE}\" && pwd)/chunks/chunk-${c.id}"
   CHUNK_LOG_DIR="${ITER_DIR}/logs/step-${S.id}-implement-chunk-${c.id}"
   mkdir -p "${CHUNK_LOG_DIR}"
   ```
   Absolute-path enforcement via `$(cd … && pwd)` (POSIX-safer than `realpath` on macOS; mitigates T-04-02 symlink redirection — the resolved path MUST start with `${PROJECT_ROOT}/_workspace/quick/` before any worktree operation).

2. **Create worktree**:
   ```
   git -C "${PROJECT_ROOT}" worktree add --detach "${CHUNK_PATH}" HEAD
   ```
   `--detach` is MANDATORY (no branch pollution). `HEAD` = current PROJECT_ROOT HEAD, which already reflects prior chunks' merges (sequential stacking per D-03).

3. **Build step-config.json** for this chunk. Key differences from standard step config:
   - `project_root = ${CHUNK_PATH}` (the detached worktree — the dialectic engine sees this as its project root; engine is chunk-agnostic)
   - `log_dir = ${CHUNK_LOG_DIR}`
   - `step_id` label = `${S.id}-chunk-${c.id}` (for engine_invocations attestation uniqueness)
   - `step_assignment` includes: `c.scope` + `c.pass_criteria` + `cumulative_chunk_context` (prior chunks' summaries, if any). If `c.dependencies_from_prev_chunks` is non-empty, `cumulative_chunk_context` MUST already contain summaries for all referenced chunk ids (this is guaranteed by sequential order).
   - Thesis/antithesis system prompts built from the same `#### Prepare Dialectic Config` rules above — S.name is still `구현`, so use the `구현` Step Roles row (Implementer/Reviewer).

4. **Spawn engine for this chunk** — follow `references/engine-invocation-protocol.md` §Standard invocation pattern VERBATIM with variable substitution. Do NOT copy the spawn bash inline (Pitfall 12 cross-file drift prevention). Substitutions:
   - `LOG_DIR` → `${CHUNK_LOG_DIR}`
   - `step-config.json` → `${CHUNK_LOG_DIR}/step-config.json`
   - `description` → `"Spawn dialectic engine for step ${S.id} chunk ${c.id}"`
   - All three load-bearing elements (`nohup` + `&` + `echo $!`) + `run_in_background: false` + EXIT-trap contract (no `exec` in run-dialectic.sh) remain non-negotiable per chunk invocation.

5. **Poll engine.done / engine.exit** — same 19×30s polling-loop Bash pattern as §Standard invocation pattern § Liveness probe, with `${CHUNK_LOG_DIR}` substituted throughout. Each chunk counts toward `engine_invocations` attestation independently.

6. **Classify verdict** — apply the Phase 3 D-05 + Phase 3.1 D-TOPO-05 classification table verbatim (authoritative copy in `references/engine-invocation-protocol.md` §Failure classification). NO new halt_reason enum from the watchdog family per chunk.

7. **Verdict branch** — ACCEPT/PASS path:

   (7a) **Read chunk deliverable**:
   ```
   Bash({
     command: "cat \"${CHUNK_LOG_DIR}/deliverable.md\"",
     run_in_background: false,
     description: "Read chunk ${c.id} deliverable"
   })
   ```

   (7b) **MetaAgent commit** (CONTEXT D-06 — MetaAgent owns, NOT thesis):
   ```
   Bash({
     command: "if [ -n \"$(git -C \\\"${CHUNK_PATH}\\\" status --porcelain)\" ]; then \
  git -C \"${CHUNK_PATH}\" add -A && \
  git -C \"${CHUNK_PATH}\" commit -m \"chunk-${c.id}: ${c.title}\" -m \"dialectic verdict: ${VERDICT}\" -m \"rounds: ${ROUNDS}\"; \
  echo \"COMMIT_OK\"; \
else \
  echo \"COMMIT_EMPTY\"; \
fi",
     run_in_background: false,
     description: "MetaAgent commit chunk ${c.id}"
   })
   ```
   If stdout == `COMMIT_EMPTY`, this chunk had no file changes — skip the cherry-pick merge step below, skip summary generation (no diff to summarize), mark chunk c as completed (add to `completed_chunks`), continue to next chunk.

   (7c) **Compose chunk summary** (CONTEXT D-04 — Bash Sketch 3 adaptation; MetaAgent composes the summary from the template in D-04 using `cat deliverable.md` + `git diff HEAD~..HEAD --name-only` + `git log HEAD~..HEAD --format='%s%n%b'`). The template (verbatim from D-04):
   ```
   ## Chunk {c.id}: {c.title}
   **Scope**: {c.scope}
   **Files changed** (from chunk worktree `git diff HEAD~..HEAD --name-only`):
   - {path 1}
   - {path 2}

   **Public API / contracts surfaced** (parsed from thesis deliverable):
   - `{signature or contract}` — {1-line description}

   **Contracts assumed by next chunks**:
   - {what next chunk can assume is done}

   **Open issues carried forward** (if any):
   - {unresolved decision that chunk N+1 must handle}
   ```

   Enforce 5KB per-entry cap: if `wc -c` of summary > 5120 bytes, compress "Files changed" / "Public API" sections or append `... (truncated; see ${CHUNK_LOG_DIR}/deliverable.md)` — the deliverable.md stays as single-source-of-truth; the next chunk's thesis MAY Read it if needed.

   Append to `cumulative_chunk_context` in-memory. Enforce 50KB cumulative hard cap (5 chunks × 10KB headroom over 5KB per-entry) — if exceeded, compress earliest-chunk summaries to `... (N chunks summarized, see iteration-{N}/logs/step-{S.id}-implement-chunk-{k}/deliverable.md)`.

   (7d) **Merge chunk into PROJECT_ROOT** (CONTEXT D-05 — Bash Sketch 2 verbatim):
   ```
   Bash({
     command: "CHUNK_SHA=\"$(git -C \\\"${CHUNK_PATH}\\\" rev-parse HEAD)\"; \
PRE_MERGE_SHA=\"$(git -C \\\"${PROJECT_ROOT}\\\" rev-parse HEAD)\"; \
MERGE_LOG=\"${CHUNK_LOG_DIR}/merge.log\"; \
touch \"${MERGE_LOG}\"; \
if git -C \"${PROJECT_ROOT}\" cherry-pick \"${CHUNK_SHA}\" 2> >(tee -a \"${MERGE_LOG}\" >&2); then \
  echo 'MERGE_MODE=cherry-pick'; \
else \
  git -C \"${PROJECT_ROOT}\" cherry-pick --abort 2>/dev/null || true; \
  if git -C \"${CHUNK_PATH}\" diff HEAD~..HEAD --binary 2>> \"${MERGE_LOG}\" | git -C \"${PROJECT_ROOT}\" apply --index --binary 2>> \"${MERGE_LOG}\"; then \
    if git -C \"${PROJECT_ROOT}\" commit -m \"chunk-${c.id}: ${c.title}\" 2>> \"${MERGE_LOG}\"; then \
      echo 'MERGE_MODE=git-apply'; \
    else \
      git -C \"${PROJECT_ROOT}\" reset --hard \"${PRE_MERGE_SHA}\" 2>/dev/null || true; \
      git -C \"${PROJECT_ROOT}\" clean -fd 2>/dev/null || true; \
      echo 'MERGE_MODE=FAILED'; \
    fi; \
  else \
    git -C \"${PROJECT_ROOT}\" reset --hard \"${PRE_MERGE_SHA}\" 2>/dev/null || true; \
    git -C \"${PROJECT_ROOT}\" clean -fd 2>/dev/null || true; \
    echo 'MERGE_MODE=FAILED'; \
  fi; \
fi",
     run_in_background: false,
     description: "Merge chunk ${c.id}: cherry-pick primary then git-apply fallback"
   })
   ```
   Parse stdout last line. If `MERGE_MODE=FAILED`, enter the Merge Conflict HALT path below. `PRE_MERGE_SHA` MUST be captured at the VERY START of this Bash block (mitigates T-04-03 — ensures safe reset even if the user had uncommitted work prior to sub-loop entry, in which case the worktree_add itself would have warned; reset-to-PRE_MERGE_SHA is the guaranteed recovery anchor).

   (7e) **Remove chunk worktree**:
   ```
   Bash({
     command: "git -C \"${PROJECT_ROOT}\" worktree remove --force \"${CHUNK_PATH}\" 2>/dev/null || true",
     run_in_background: false,
     description: "Remove chunk ${c.id} worktree post-merge"
   })
   ```

   (7f) **Checkpoint update** — call step 9.5 `checkpoint.py write` with chunk-aware payload:
   - `current_chunk = c.id` if more chunks remain; else set to `null` when the chunk just merged is the last one (step about to complete)
   - `completed_chunks = completed_chunks + [c.id]` (append)
   - `current_step` unchanged (step is still in progress until all chunks merge)
   - `status = "running"`

   (7g) **Continue to next chunk** (sequential relay).

8. **Verdict branch — FAIL/HALT path (D-10)**:

   Apply the FAIL branch table:
   | chunk c verdict | halt_reason | cleanup + HALT |
   |-----------------|-------------|----------------|
   | dialectic verdict FAIL | `persistent_dialectic_fail` (re-use existing) | yes |
   | engine HALT (sdk_session_hang / step_transition_hang / bash_wrapper_kill / engine_crash) | engine-emitted halt_reason pass-through | yes |
   | commit stderr (rare git error, NOT empty diff) | `engine_crash` (re-use existing) | yes |
   | worktree add failure | `worktree_backlog` (NEW, D-03) | yes (likely pre-flight caught it, but defense-in-depth) |

   Execute the FAIL/HALT cleanup sequence (CONTEXT D-10 — Bash Sketch 4 verbatim):
   ```
   Bash({
     command: "git -C \"${PROJECT_ROOT}\" worktree remove --force \"${CHUNK_PATH}\" 2>/dev/null || true; \
git -C \"${PROJECT_ROOT}\" worktree prune 2>/dev/null || true",
     run_in_background: false,
     description: "Cleanup chunk ${c.id} worktree after FAIL/HALT"
   })
   ```

   Then `checkpoint.py write` with HALT payload:
   - `current_step = S.id` (step never completed)
   - `completed_steps` unchanged (pre-chunk-subloop value)
   - `current_chunk = c.id` (the failing chunk — forensic)
   - `completed_chunks = completed_chunks` (successfully-merged chunks so far — forensic)
   - `status = "halted"`
   - `halt_reason = <reason from branch table>`
   - `updated_at = now`

   Emit HALT JSON to stdout (same format as step 9 HALT JSON contract — `status: halted`, `workspace`, `halt_reason`, `summary` with user-facing Korean recovery guidance, `halted_at: "execute-chunk-subloop-<phase-label>"`, `current_chunk`, `completed_chunks`). Return to the outer Execute Phase 2d loop (which then routes to Phase 2e / final aggregate).

**NO re-chunking / NO within-iter chunk retry** (CONTEXT D-10): Do NOT invoke Classify again from Execute Mode (structurally impossible — Classify is a separate invocation). Do NOT auto-retry the same chunk within the iteration. User recovery path is `/tas {original request}` for a fresh start, optionally with `chunks: 1` override to force single-dialectic execution.

**Merge Conflict HALT path** (when `MERGE_MODE=FAILED`): the cleanup Bash above already ran `git reset --hard PRE_MERGE_SHA` + `git clean -fd` on PROJECT_ROOT. Then emit HALT with:
- `halt_reason: "chunk_merge_conflict"` (NEW, CONTEXT D-05 — merge domain, justified exception to Phase 3.1 D-TOPO-05 watchdog/hang enum freeze)
- `summary`: user-facing Korean wording (see SKILL.md Phase 3 Recovery Guidance — Plan 05 adds the row: "Chunk N (title) 머지 충돌. 공유 파일을 여러 chunk가 동시에 수정했을 가능성이 큽니다. plan.json을 재검토하거나 /tas로 새로 시작하세요. /tas --resume은 이 경로에서 지원되지 않습니다.")
- `merge_log`: `${CHUNK_LOG_DIR}/merge.log` (forensic reference; SKILL.md does NOT read merge.log — info-hiding)

**All chunks merged successfully — sub-loop exit path**:

- `cumulative_context_this_iter += "\n## 구현 step (chunked)\n" + cumulative_chunk_context` (append the accumulated chunk summaries to the iteration-level cross-step context, so downstream verify/test steps can reference)
- Resume to standard step 9 (deliverable summary append) — use the last chunk's `deliverable.md` as the canonical step deliverable for the iteration DELIVERABLE.md index, OR synthesize a meta-deliverable pointer: `"See chunks/chunk-{1..N}/deliverable.md for per-chunk deliverables; synthesis summary above in cumulative_chunk_context."` — CLAUDE's Discretion; planner locks the synthesis-pointer choice at execution time.
- Run standard step 9.5 checkpoint update with:
  - `current_chunk = null` (step completed, all chunks merged — reset)
  - `completed_chunks = []` (reset at step boundary per CONTEXT D-08)
  - `current_step = ${next step id}` or `null` if 구현 was the last step
  - `completed_steps = <prior> + [${S.id}]`
  - `status = "running"` (or `"finalized"` only at Phase 3 Final Aggregate)

### Within-Iteration FAIL Handling

Implement the retry/HALT logic exactly as specified in
`references/workspace-convention.md` §"Iteration & Retry Flow" →
"Within an iteration". Summary (authoritative copy is in the reference):

- No fixed retry cap — iterate until PASS, HALT, or persistent failure
- Compare each FAIL to the prior FAIL of the same step: substantively identical
  → increment `consecutive_fail_count[step]`, else reset to 1
- `consecutive_fail_count[step] >= persistent_failure_halt_after` → HALT with
  `persistent_verify_failure` or `persistent_test_failure`
- Otherwise: build retry context, jump back to 구현 (re-run 검증 first on
  테스트 FAIL if in plan). Retries live in sibling `-retry-{N}/` dirs
- **Write halt checkpoint** (CHKPT-01 halted): before returning the HALT JSON to
  the orchestrator, call `checkpoint.py write` with `status: "halted"` and
  `halt_reason: "<reason>"` (values: `persistent_verify_failure`,
  `persistent_test_failure`, or the engine-emitted `halt_reason` from the last
  JSON line — including **Phase 3 watchdog values**:
  `sdk_session_hang` (Layer A asyncio.timeout expired inside dialectic.py),
  `step_transition_hang` (Layer B exit 0 + last-line JSON absent),
  `bash_wrapper_kill` (Layer B exit 124/137 via coreutils timeout SIGTERM/SIGKILL)
  — see 03-CONTEXT.md D-06). `current_step` remains the ID of the failing step,
  `completed_steps[]` remains the pre-HALT list. `updated_at` is the HALT moment.
  This write lets Phase 2 resume surface the last known progress and the halt reason.

**Engine HALT** (circular argumentation etc.): stop iteration, proceed to Phase 2e.

**Chunk FAIL/HALT (Phase 2d.5 chunk sub-loop)**: chunk-level failures route through the Phase 2d.5 FAIL branch table above, NOT through this persistent-failure retry logic. Specifically:

- chunk FAIL/HALT is NEVER auto-retried within the iteration (CONTEXT D-10)
- chunk FAIL/HALT does NOT increment `consecutive_fail_count` (that counter tracks single-dialectic 검증/테스트 FAIL retries, not chunk-level failures)
- cleanup Bash is inline at the failure branch (worktree remove + prune + optional reset --hard PRE_MERGE_SHA) — no Bash trap (MetaAgent is a subagent; Python finally is not available at this layer)
- HALT checkpoint write populates `current_chunk` + `completed_chunks` (forensic — Phase 2 D-06 halt gate blocks resume into a chunked step)
- Two new halt_reason enums are permitted here: `chunk_merge_conflict` (D-05, merge domain) and `worktree_backlog` (D-03, environment pollution domain). These are justified exceptions to Phase 3.1 D-TOPO-05's watchdog/hang enum freeze because they live in entirely different failure domains. NO new watchdog/hang enum is introduced.

### Phase 2e: Iteration Synthesis

After all steps in the iteration complete (or HALT'd), write `{ITER_DIR}/DELIVERABLE.md`
using the per-iteration format defined in `workspace-convention.md` §Per-Iteration DELIVERABLE.md.
Include: iteration number, status, focus angle, steps executed with outcomes, deliverable
content, and non-blocking observations (carry-over candidates for future iterations).

### Phase 2f: Lessons Learned Extraction

Append this iteration's lessons to `{WORKSPACE}/lessons.md` using the format in
`workspace-convention.md` §lessons.md Format. Include: focus angle, concrete improvements,
blockers resolved, patterns observed, open observations, rejected alternatives.

Lessons are **cumulative** — never prune prior iterations' entries.

### Phase 2g: Early-Exit Check

If `early_exit_on_no_improvement` is true and both agents explicitly stated "no meaningful
further improvement possible" in their final exchange → early-exit (log in lessons.md).
PASS alone is NOT exit grounds — only mutual "no further polish" signals.

HALT'd iteration → break loop, proceed to Phase 3 with status `halted`.

---

## Phase 3: Final Aggregate

After the iteration loop completes (naturally or via early-exit/HALT), write
`{WORKSPACE}/DELIVERABLE.md` — the cross-iteration synthesis using the format in
`workspace-convention.md` §Top-Level DELIVERABLE.md Format. Include: request type,
complexity, status, iteration summary table, final deliverable content, key takeaways
from lessons.md, and unresolved items (if any).

## Phase 4: Pre-Output Self-Check (MANDATORY)

Verify engine artifacts exist via `Bash(...)`:

```bash
MISSING=0; MISSING_PATHS=""
for step_dir in {WORKSPACE}/iteration-*/logs/step-*/; do
  [ -d "$step_dir" ] || continue
  for required in step-config.json round-1-thesis.md dialogue.md deliverable.md; do
    [ ! -f "$step_dir/$required" ] && echo "MISSING: $step_dir$required" && MISSING_PATHS="$MISSING_PATHS $step_dir$required" && MISSING=1
  done
done
echo "SELF_CHECK_RESULT=$MISSING"
```

If `MISSING=1` → return `{"status":"halted","halt_reason":"missing_engine_artifacts","missing_paths":[...]}`.
This is non-negotiable — catches simulated dialectic content.

## Phase 5: JSON Response

Your entire response must be ONLY the JSON line:

(Canonical schema: see `${SKILL_DIR}/agents/meta.md` §Final JSON Contract — added in Plan 05-03 Wave 2.)

**Completed successfully** (all planned iterations or clean early-exit):
```json
{"status":"completed","workspace":"{WORKSPACE}","summary":"{1-2 sentence}","iterations":{executed},"early_exit":{bool},"rounds_total":{N},"engine_invocations":{N_bash_calls},"execution_mode":"pingpong"}
```

(See `${SKILL_DIR}/agents/meta.md` §Final JSON Contract for the canonical definition of `engine_invocations` — added in Plan 05-03 Wave 2.)

**Halted mid-iteration** (persistent failure or dialectic HALT):
```json
{"status":"halted","workspace":"{WORKSPACE}","summary":"{halt reason}","iterations":{executed},"halt_reason":"{persistent_verify_failure | persistent_test_failure | circular_argumentation | ...}","halted_at":"iteration-{N}/{step name}","rounds_total":{N},"execution_mode":"pingpong"}
```

---
