# Workspace Convention

This document defines the directory structure, file formats, and naming rules used by tas.
MainOrchestrator, MetaAgent, and the dialectic engine all reference this as the single
source of truth for workspace layout.

---

## Directory Structure

```
_workspace/
  quick/                                      ← all runs (timestamped for isolation)
    {YYYYmmdd_HHMMSS}/
      REQUEST.md                                ← original user request
      plan.json                                 ← approved plan (Classify output, mtime-immutable after approval)
      checkpoint.json                           ← step-boundary progress (atomic write, updated after each step)
      DELIVERABLE.md                            ← final cross-iteration synthesis
      lessons.md                                ← lessons learned, appended per iteration
      iteration-1/
        DELIVERABLE.md                          ← this iteration's synthesized output
        logs/
          step-1-plan/
            thesis-system-prompt.md
            antithesis-system-prompt.md
            step-config.json
            round-1-thesis.md
            round-1-antithesis.md
            round-2-thesis.md
            ...
            deliverable.md                      ← per-step converged output
          step-1-plan-retry-1/                  ← within-iteration FAIL retry
            ...
          step-2-implement/
          step-3-verify/
          step-4-test/
      iteration-2/                              ← only if loop_count > 1
        DELIVERABLE.md
        logs/
          step-2-implement/                     ← reentry_point onwards; 기획 skipped by default
          step-3-verify/
          step-4-test/
      iteration-3/
        ...
    classify-{YYYYmmdd_HHMMSS}/                 ← classify-mode validation logs (complex only)
      logs/validation/
        ...
```

Every run is timestamp-isolated. A run may be **resumed** via `/tas --resume` (Phase 2; the resume path reads `checkpoint.json` and `plan.json` but never writes to a prior workspace). Each fresh `/tas` invocation still produces a new timestamped workspace — resume is opt-in, not automatic.

### Naming Rules

| Element | Pattern | Example |
|---------|---------|---------|
| Run workspace | `quick/{timestamp}/` | `quick/20260414_143000/` |
| Classify workspace | `quick/classify-{timestamp}/` | `quick/classify-20260414_142958/` |
| Iteration dir | `iteration-{N}/` | `iteration-1/`, `iteration-2/` |
| Step log dir | `iteration-{N}/logs/step-{id}-{slug}/` | `iteration-1/logs/step-2-implement/` |
| Within-iter retry dir | `step-{id}-{slug}-retry-{N}/` | `step-3-verify-retry-1/` |
| Final cross-iter deliverable | `{workspace}/DELIVERABLE.md` | (always exact) |
| Per-iteration deliverable | `iteration-{N}/DELIVERABLE.md` | (always exact) |
| Lessons log | `lessons.md` | (always exact, at workspace root) |
| Original request | `REQUEST.md` | (always exact) |

- Iteration `N`: 1-indexed, incremented per full plan pass
- Step `id`: as assigned in the classify plan (1-indexed)
- `slug`: kebab-case English derived from step name (기획 → `plan`, 구현 → `implement`, 검증 → `verify`, 테스트 → `test`)
- `timestamp`: `YYYYmmdd_HHMMSS` (e.g., `20260414_143000`)

---

## Top-Level DELIVERABLE.md Format (cross-iteration synthesis)

Written by MetaAgent after the iteration loop terminates (naturally, by early-exit,
or on HALT). Summarizes all iterations and references the final artifact.

```markdown
---
request_type: {implement | design | review | refactor | analyze | general}
complexity: {simple | medium | complex}
status: {completed | halted}
iterations_planned: {LOOP_COUNT}
iterations_executed: {actual count}
early_exit: {true | false}
rounds_total: {sum across all iterations and steps}
created: {ISO 8601 timestamp}
---

# Dialectic Synthesis Report (정반합)

## Request
{REQUEST verbatim}

## Iteration Summary
| # | Focus | Outcome | Rounds | Key Improvement |
|---|-------|---------|--------|-----------------|
| 1 | baseline | completed | 9 | initial implementation |
| 2 | UX polish | completed | 6 | keyboard nav + empty state |
| 3 | edge cases | early-exit | 4 | (agents agreed no further) |

## Final Deliverable
{Content of the final iteration's DELIVERABLE.md — code summary + file list for
 implement/refactor, or document for design/analyze}

## Lessons Learned
See `lessons.md` — full iteration-by-iteration lesson log.

### Key Takeaways
- {1-2 most important lessons from the whole run}

## Unresolved Items
{Blockers from HALT'd iterations, if any; otherwise "none"}
```

## Per-Iteration DELIVERABLE.md Format

Written at the end of each iteration before lessons extraction.

```markdown
---
iteration: {N}
status: {completed | halted}
focus_angle: {angle or "baseline (iteration 1)"}
rounds_total: {sum across steps this iteration}
within_iter_retries: {count of 구현 re-runs due to FAIL}
created: {ISO 8601 timestamp}
---

# Iteration {N} Deliverable

## Focus
{focus_angle or "Baseline implementation"}

## Steps Executed
| # | 단계 | Outcome | Rounds |
|---|------|---------|--------|
| 2 | 구현 | CONVERGED | 3 |
| 3 | 검증 | PASS | 2 |
| 4 | 테스트 | PASS | 1 |

## Deliverable
{For implement/refactor: summary of code changes + file list}
{For design/analyze/review: the synthesized document}

## Non-blocking Observations (carry-over candidates)
- {observation 1}
- {observation 2}
```

## lessons.md Format

Append-only log at `{workspace}/lessons.md`. Each iteration appends one section.

Required sections per iteration entry:

```markdown
## Iteration {N} ({ISO 8601 timestamp})

### Focus Angle
{angle or "baseline"}

### Concrete Improvements Made This Iteration
- {diff-level summary of what changed}

### Blockers Resolved
- {blocker} → {resolution}

### Patterns Observed
- {design tension, convention discovery, etc.}

### Open Observations (for future iterations)
- {carry-over candidates for next iteration's focus}

### Rejected Alternatives
- {alternative} — rejected: {reason}

---
```

Lessons are **cumulative** — never prune prior iterations' entries. The next iteration's
thesis/antithesis receive this file's contents in their step context.

---

## Per-Step Log Format

The Python dialectic engine writes these files under `iteration-{N}/logs/step-{id}-{slug}/`.
MetaAgent does not edit them directly.

| File | Producer | Content |
|------|----------|---------|
| `thesis-system-prompt.md` | MetaAgent | Step-specific injection only (role/goal/criteria). Full agent template is prepended by the engine via `thesis_template_path` |
| `antithesis-system-prompt.md` | MetaAgent | Step-specific injection only (role/goal/criteria). Full agent template is prepended by the engine via `antithesis_template_path` |
| `step-config.json` | MetaAgent | Engine input: prompt paths, goals, model, convergence_model |
| `round-{N}-thesis.md` | Engine | Thesis's response that round (full text) |
| `round-{N}-antithesis.md` | Engine | Antithesis's response that round (full text) |
| `dialogue.md` | Engine | Unified conversation transcript across all rounds |
| `deliverable.md` | Engine | The converged output for this step |

Retry runs create parallel directories (`step-{id}-{slug}-retry-{N}/`) — prior logs are preserved.

---

## Iteration & Retry Flow

### Within an iteration

Steps execute sequentially. Each step's `deliverable.md` is appended to an in-memory
`cumulative_context_this_iter` that is visible to downstream steps in the same iteration.

On inverted step FAIL (검증/테스트):

1. Engine returns `{"verdict":"FAIL","blockers":[...]}`
2. MetaAgent compares blockers to the previous FAIL of this step (within the iteration):
   - Substantively identical → increment `consecutive_fail_count[step]`
   - Different → reset counter to 1
3. If `consecutive_fail_count[step] >= loop_policy.persistent_failure_halt_after`:
   - HALT the iteration with `halt_reason: persistent_{verify|test}_failure`
   - Break out of the step loop and proceed to iteration synthesis (Phase 2e)
4. Otherwise:
   - Build retry context: `## Required Fixes from {step name}\n{blockers}`
   - Re-execute the **구현** step with retry context appended
   - After successful re-구현, re-execute the failed check step
   - Retries are logged as sibling dirs within the same iteration (`-retry-1`, `-retry-2`, ...)

### Across iterations

1. After iteration `i` completes, MetaAgent writes `iteration-{i}/DELIVERABLE.md`
2. Lessons are extracted and appended to `{workspace}/lessons.md`
3. Early-exit check: if agents signaled "no further improvement possible" and
   `loop_policy.early_exit_on_no_improvement` is true → terminate loop
4. Otherwise: iteration `i+1` begins
   - Step subset = plan steps from `loop_policy.reentry_point` onwards (default: skip 기획)
   - A **focus angle** is selected (see workflow-patterns.md)
   - Improvement context includes: prior iteration's deliverable summary, full lessons.md
     contents, and the chosen focus angle directive
   - Thesis/antithesis receive this as part of their step_context

Iteration-level HALT does NOT prevent the final DELIVERABLE.md from being written — the
cross-iteration synthesis records partial progress and halt reason.

---

## Checkpoint Schema

This workspace persists two state files: `plan.json` (the approved Classify output, immutable after write) and `checkpoint.json` (step-boundary progress, atomically rewritten after each completed step). Together they are the sole trust source for Phase 2 resume — other files (`dialogue.md`, `round-*.md`, `deliverable.md`) are opaque to the resume path.

### checkpoint.json fields (schema_version 1)

| Field | Type | Required | Null allowed? | Values / Constraints |
|-------|------|----------|---------------|----------------------|
| `schema_version` | integer | yes | no | MUST equal `1`. Other values → HALT with `halt_reason: "checkpoint_schema_unsupported"` |
| `workspace` | string | yes | no | Absolute path to `_workspace/quick/{timestamp}/` (self-documenting for crash dumps) |
| `plan_hash` | string | yes | no | SHA-256 hex (64 chars) of canonical `plan.json` at Classify approval time |
| `current_step` | string \| null | yes | **yes** | ID of the **next** step to execute; `null` only when `status == "finalized"` |
| `completed_steps` | string[] | yes | no | Ordered list of step IDs already completed; `[]` at initial write |
| `current_chunk` | string \| null | yes | **yes** | Phase 4 reserved slot. In Phase 1: always `null` |
| `completed_chunks` | string[] | yes | no | Phase 4 reserved slot. In Phase 1: always `[]` |
| `status` | string | yes | no | Enum: `"running"` \| `"halted"` \| `"finalized"` |
| `updated_at` | string | yes | no | ISO 8601 UTC timestamp (e.g., `"2026-04-21T12:34:56.789012+00:00"`); regenerated on each write |
| `halt_reason` | string \| null | no (optional) | yes | Present only when `status == "halted"` |

### Example — initial write (after Classify approval, before step 1 starts)

```json
{
  "schema_version": 1,
  "workspace": "/Users/name/project/_workspace/quick/20260421_123456",
  "plan_hash": "7c9e6679f1a3f83e1d2a4b2c5e3d7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e",
  "current_step": "1",
  "completed_steps": [],
  "current_chunk": null,
  "completed_chunks": [],
  "status": "running",
  "updated_at": "2026-04-21T12:34:56.789012+00:00"
}
```

### Example — after step 2 completes (next is step 3)

```json
{
  "schema_version": 1,
  "workspace": "/Users/name/project/_workspace/quick/20260421_123456",
  "plan_hash": "7c9e6679f1a3f83e1d2a4b2c5e3d7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e",
  "current_step": "3",
  "completed_steps": ["1", "2"],
  "current_chunk": null,
  "completed_chunks": [],
  "status": "running",
  "updated_at": "2026-04-21T12:48:12.345678+00:00"
}
```

### Example — halted mid-run (persistent verify failure on step 3)

```json
{
  "schema_version": 1,
  "workspace": "/Users/name/project/_workspace/quick/20260421_123456",
  "plan_hash": "7c9e6679f1a3f83e1d2a4b2c5e3d7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e",
  "current_step": "3",
  "completed_steps": ["1", "2"],
  "current_chunk": null,
  "completed_chunks": [],
  "status": "halted",
  "halt_reason": "persistent_verify_failure",
  "updated_at": "2026-04-21T13:02:44.567890+00:00"
}
```

### plan.json notes

- `plan.json` is written **once**, at Execute Mode Phase 1 Initialize (immediately after Classify approval), via `python3 runtime/checkpoint.py write-plan`. The write CLI enforces "already exists → exit 3"; **plan.json is mtime-immutable after approval**.
- `plan.json` uses canonical JSON serialization (`sort_keys=True`, `separators=(",",":")`, `ensure_ascii=False`) so that re-formatting by tools like `jq` does not invalidate `plan_hash`.
- The plan dict preserves a Phase 4 reserved slot: `implementation_chunks: null` (not omitted) so downstream schema migration is forward-compatible.

### plan_hash algorithm

Canonical JSON (`sort_keys=True, separators=(",", ":"), ensure_ascii=False`) → SHA-256 hex digest (64 chars). Single source of truth: `skills/tas/runtime/checkpoint.py::compute_plan_hash`.

### Atomic write invariant

Both `plan.json` and `checkpoint.json` writes follow the tempfile + `fsync` + `os.replace` pattern implemented in `skills/tas/runtime/checkpoint.py::_atomic_write_json`. After any call (or exception), the target file either reflects the pre-call state or the full new payload — never a torn write.

---

## Read Scope

MetaAgent loads these into agent context per step:

1. **Always**: `REQUEST.md`, accumulated prior step outputs (`cumulative_context`)
2. **Project context**: `PROJECT_ROOT` path and domain hint from classify
3. **Per step**: the step's goal and pass criteria
4. **On retry**: the blockers from the failed check

Agents have file access via their session — they may read project source directly when needed
(ThesisAgent uses `bypassPermissions` mode for writes during 구현 step).

---

## Language Convention

Output language defaults to **English**. Set to another language ONLY when the user explicitly
requests a specific output language (e.g., "한국어로 작성해줘"). The language of the request
itself does NOT determine output language — a Korean request with no explicit instruction
means English output.

Step names may use Korean (기획/구현/검증/테스트) internally for consistency with this
document's terminology. The `slug` field converts them to English for file paths.
