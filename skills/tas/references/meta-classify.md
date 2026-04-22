# Classify Mode

MetaAgent reads this file after Mode Detection when `MODE == classify`. It is the
procedural body for classify — the canonical plan-construction procedure that was
previously inlined in `${SKILL_DIR}/agents/meta.md` (pre-Phase-5 L98-240). Mode
Detection itself stays in `${SKILL_DIR}/agents/meta.md`; this file assumes the
caller has already determined `MODE == classify`.

For the canonical field list of the final Classify JSON, see
`${SKILL_DIR}/agents/meta.md` §Final JSON Contract (added in Plan 05-03 Wave 2).

---

Analyze the user's request and return an execution plan as JSON. This mode does NOT execute
any steps — it produces a plan that MainOrchestrator presents to the user for confirmation.

## Phase 1: Project Context Scan (lightweight)

**Attestation first step (SLIM-02):** If you have not already appended
`"${SKILL_DIR}/references/meta-classify.md"` to your in-memory `references_read` list
(per `${SKILL_DIR}/agents/meta.md` §Mode-bound Reference Load), do so now. This is the
first actionable step of Classify Mode; attestation must be self-enforced at Read-time
so it is populated even if execution halts before Phase 4 Output.

If `PROJECT_ROOT` is provided, briefly scan for project indicators — do NOT deep-dive:

- Package files: `package.json`, `Cargo.toml`, `go.mod`, `pyproject.toml`, `Gemfile`
- Framework signals: Next.js / React / Vue (from package.json), Django / Rails, Flutter (`pubspec.yaml`)
- Workspace structure: multiple `package.json` / `go.mod` at different depths (monorepo), `dags/` or pipeline configs (data-pipeline), `*.tf` / `*.hcl` / CloudFormation / Pulumi (iac-infra)
- Domain heuristic: `web-frontend` / `web-backend` / `api` / `library` / `cli` / `mobile` / `monorepo` / `data-pipeline` / `iac-infra` / `unknown`

This scan informs the testing strategy (e.g., web projects may need Playwright UI testing).

## Phase 2: Classification

Determine: **request_type** (`implement|design|review|refactor|analyze|general`),
**complexity** (`simple|medium|complex`), **steps** (1-4 adaptive).

### Complexity Heuristic

| Level | Indicators | Steps |
|-------|-----------|-------|
| `simple` | Single function, narrow scope, pure analysis/review | 1 |
| `medium` | Multi-file change, new feature in existing module | 2-3 |
| `complex` | New subsystem, user-facing behavior, wide blast radius | 4 |

Consider implied blast radius, not just wording — "add a button that posts to /api/x"
touches UI, API wiring, and state.

### Step Template Selection

Read `{SKILL_DIR}/references/workflow-patterns.md` for canonical templates.
- `implement|refactor` complex → 기획→구현→검증→테스트
- `medium` → typically 기획→구현→검증 or 구현→검증
- `simple` → single combined step
- `design|review|analyze` → document-producing templates (no 구현/테스트)

## Phase 2c: Chunk Sizing (implement|refactor complex only)

Decide whether the 구현 step should split into **2..5 vertical-layer chunks** for worktree-isolated sequential relay (Phase 4). Chunks exist for **context-window preservation** + **synthesis-boundary integrity** — NOT for parallelism (M1 is sequential-only).

**Do NOT execute chunks in Classify** — Phase 2c writes the plan field only. Worktree creation, dialectic invocation, and merge happen in Execute Phase 2d.5 (see below).

### Trigger Heuristic (CONTEXT D-01)

| Condition | `implementation_chunks` value |
|-----------|-------------------------------|
| `complexity == "simple"` OR `request_type in ["design","review","analyze","general"]` | `null` (no decomposition) |
| `complexity == "medium"` with single-module reasoning | `null` |
| `complexity == "medium"` with 2+ module references in reasoning | `2` (chunk count — MetaAgent fills 2-element array) |
| `complexity == "complex"` with single-subject reasoning | `null` OR `2` (MetaAgent judgement) |
| `complexity == "complex"` with vertical layers 2+ identifiable (e.g., schema + handler + UI) | `2..5` — one chunk per identifiable layer |
| ANY condition | **Hard cap: 5**. If more than 5 layers are identified, degrade to `null` with reasoning "이 요청은 여러 /tas run으로 나누라 권장" |

**Vertical layer principle** (D-01 Rationale): split on dependency direction (e.g., DB/schema → API/handler → UI/render · or infra → runtime → integration), NOT on file-count balance or directory boundaries. Horizontal splits sever vertical dependencies and make chunk N+1's thesis operate on wrong assumptions (Pitfall 7).

**Range limitation**: Phase 2c uses only the request text + lightweight `PROJECT_ROOT` scan results from Phase 1. Do NOT deep-read project source code to refine chunk boundaries (project-code read prohibition — PROJECT.md Constraints).

### `implementation_chunks[]` Schema (CONTEXT D-02)

When decomposing, populate each array element with these 6 fields:

| Field | Type | Constraint | Description |
|-------|------|-----------|-------------|
| `id` | string | 1-indexed numeric string ("1", "2", ...) | Chunk identifier. Matches step id conventions (Phase 1 CONTEXT D-01). |
| `title` | string | ≤ 60 chars | Short label shown on the user approve screen (SKILL.md Phase 1 Display Plan). |
| `scope` | string | ≤ 300 chars, prose | What this chunk delivers — semantic boundary, not a file glob. |
| `pass_criteria` | string[] | ≥ 1 item | Chunk-level dialectic PASS conditions (injected into that chunk's `step_assignment`). |
| `dependencies_from_prev_chunks` | string[] | chunk 1 MUST be `[]`; chunk N may list `["1"]`, `["1","2"]`, etc. | Ordered dependency graph. Non-empty ⇒ prior-chunk summary is required injection into this chunk's thesis (Phase 2d.5 relay). |
| `expected_files` | string[] | glob patterns, advisory only | Initial contention guard (see Disjointness Check). Dialectic may touch paths outside this list at runtime — that is not a HALT trigger. |

### Expected_files Disjointness Check (advisory)

Before finalizing `implementation_chunks[]`, perform a **glob-expanded exact-string** comparison across all chunks' `expected_files`. If any path appears in 2+ chunks:

1. Assign the shared path to the **earliest** chunk in the dependency order.
2. Remove it from later chunks; later chunks reference chunk N's completion via `dependencies_from_prev_chunks`.
3. If the assignment still cannot be made coherent (e.g., schema AND UI both must edit the same config file in a way that cannot be serialized), degrade to `implementation_chunks: null` and add to `reasoning`: `"chunks 간 파일 경합 감지로 분해 취소 — 단일 dialectic 실행"`.

`expected_files` is treated as opaque strings for comparison (shell-safe — **never pass to a shell** for expansion; use `fnmatch`-style matching only). This mitigates user-influenced metacharacter injection (T-04-01).

### Plan Hash Invariant (CONTEXT D-02 · Phase 1 D-02)

`implementation_chunks` is a canonical-JSON plan field — it feeds into `plan_hash`. Once the plan is approved, the array is immutable (Phase 1 `plan_hash_mismatch` HALT guards post-approval edits). `chunks: 1` / `chunks: 2` user overrides during Phase 1 Display Plan MUST re-hash via the existing plan-adjust routing (see `SKILL.md` Phase 1 Handle User Response) BEFORE persisting to `plan.json`.

### Approval UX (forward reference)

`SKILL.md` Phase 1 Display Plan renders the chunks structure + dependency graph on the approve screen with override hints (`chunks: 1` / `chunks: N`). Classify does not control display — it just produces the field. See `skills/tas/SKILL.md` Phase 1.

## Phase 3: Plan Validation (Adaptive)

| Complexity | Validation |
|-----------|------------|
| `simple` / `medium` | None — return directly |
| `complex` | Light — 1 round via dialectic engine |

**Complex only**: Create `classify-{timestamp}/logs/validation/`, write lightweight
thesis ("plan proposer") and antithesis ("plan challenger") prompts + step-config.json,
invoke the engine per `references/engine-invocation-protocol.md` (Scenario B —
spawn via `nohup ... & echo $!` with `run_in_background: false`, poll
`engine.done` / `engine.exit` markers locally in ≤9.5-min chunks, then parse
final JSON line from `tail -n 1 engine.log`). If REFINE/COUNTER, adjust the plan.

**Do NOT use Agent() for plan validation.** Always use the dialectic engine.

## Phase 4: Output

Your entire response must be ONLY the JSON line. No progress text, no explanations.

(Canonical schema: see `${SKILL_DIR}/agents/meta.md` §Final JSON Contract — added in Plan 05-03 Wave 2.)

**Quick mode plan:**
```json
{"command":"classify","mode":"quick","request_type":"{type}","complexity":"{level}","steps":[{"id":"1","name":"{name}","goal":"{goal}","pass_criteria":["{criterion 1}","{criterion 2}"]}],"loop_count":1,"loop_policy":{"reentry_point":"구현","early_exit_on_no_improvement":true,"persistent_failure_halt_after":3},"implementation_chunks":null,"workspace":"_workspace/quick/{YYYYmmdd_HHMMSS}/","reasoning":"{why this complexity, these steps, and this loop count}","project_domain":"{domain or null}"}
```

`implementation_chunks` is `null` by default. When Phase 2c decomposes a complex implement/refactor request into vertical layers, this field is the 6-field array (see §Phase 2c Schema above). Once approved and written to `plan.json`, the field is immutable (plan_hash invariant — Phase 1 D-02).

`workspace` path uses absolute timestamp — generate with `date +%Y%m%d_%H%M%S`.
`project_domain` informs the execute-mode 테스트 strategy (e.g., `web-frontend` → Playwright).

**Step name enum (REQUIRED)**: `steps[].name` MUST be one of the canonical Korean
names: `기획`, `구현`, `검증`, `테스트`. English or ad-hoc names (e.g., `research`,
`ideation`, `dialectic`, `finalize`) break the inverted-step logic and are rejected.
A 1-step plan uses the most applicable canonical name; 2-step plans typically use
`기획` + `구현`; 3-step plans add `검증`; 4-step plans add `테스트`.

**Default `loop_count` by complexity**:
- `simple` / `medium` → 1 (single pass is sufficient)
- `complex` → 1, but propose 2-3 if the reasoning identifies clear polish dimensions
  (e.g., UX-critical UI work, performance-sensitive paths, accessibility requirements)

The user can override `loop_count` at the plan approval step. Do not inflate `loop_count`
without concrete justification in `reasoning` — each iteration costs tokens.

**Direct response** (request is trivial but reached classify):
```json
{"command":"classify","mode":"direct","response":"{brief answer}","reasoning":"Trivial request"}
```

---
