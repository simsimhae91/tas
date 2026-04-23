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
      chunks/                                   ← chunk worktrees (Phase 4; transient — git worktree-tracked, removed after merge)
        chunk-1/                                ← detached HEAD worktree for chunk 1
        chunk-2/
        chunk-3/
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
          step-2-implement-chunk-1/             ← Phase 4: chunk-level dialectic log dir
            thesis-system-prompt.md
            antithesis-system-prompt.md
            step-config.json                    ← project_root = {WORKSPACE}/chunks/chunk-1
            round-*.md
            deliverable.md                      ← chunk-level deliverable (feeds cumulative_chunk_context)
            merge.log                           ← merge forensics (cherry-pick stderr + apply stderr on HALT)
          step-2-implement-chunk-2/
          step-2-implement-chunk-3/
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
| Chunk worktree | `{WORKSPACE}/chunks/chunk-{c.id}/` | `.../chunks/chunk-1/` |
| Chunk log dir | `iteration-{N}/logs/step-{S.id}-implement-chunk-{c.id}/` | `iteration-1/logs/step-2-implement-chunk-3/` |

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

### checkpoint.json fields (schema_version 1, 11 fields — 9 M1 + 2 Phase 6 additive)

| Field | Type | Required | Null allowed? | Values / Constraints |
|-------|------|----------|---------------|----------------------|
| `schema_version` | integer | yes | no | MUST equal `1`. Other values → HALT with `halt_reason: "checkpoint_schema_unsupported"` |
| `workspace` | string | yes | no | Absolute path to `_workspace/quick/{timestamp}/` (self-documenting for crash dumps) |
| `plan_hash` | string | yes | no | SHA-256 hex (64 chars) of canonical `plan.json` at Classify approval time |
| `current_step` | string \| null | yes | **yes** | ID of the **next** step to execute; `null` only when `status == "finalized"` |
| `completed_steps` | string[] | yes | no | Ordered list of step IDs already completed; `[]` at initial write |
| `current_chunk` | string \| null | yes | **yes** | ID of chunk currently in progress within a chunked 구현 step (Phase 4). `null` when the current step is not chunked, or when all chunks of a chunked step have merged. Resets to `null` at step boundary. |
| `completed_chunks` | string[] | yes | no | Ordered list of chunk IDs already cherry-pick merged within the current 구현 step (Phase 4). `[]` outside chunked-step execution and at initial write. Resets to `[]` at step boundary (iteration-scoped per 04-CONTEXT.md D-08). |
| `status` | string | yes | no | Enum: `"running"` \| `"halted"` \| `"finalized"` |
| `updated_at` | string | yes | no | ISO 8601 UTC timestamp (e.g., `"2026-04-21T12:34:56.789012+00:00"`); regenerated on each write |
| `halt_reason` | string \| null | no (optional) | yes | Present only when `status == "halted"` |
| `session_branch` | string \| null | yes (Phase 6+) | yes | Named branch created by SKILL.md Phase 0 session bootstrap (e.g., `"tas/session-20260423T143000Z"`). `null` allowed only for legacy pre-Phase-6 checkpoints. Information-only field — Phase 0b 7-check does NOT validate it; redundant with LATEST symlink resolve but enables forensics from `cat checkpoint.json` alone. Plan 06-03 Task 2 documents the payload composition. |
| `session_worktree_path` | string \| null | yes (Phase 6+) | yes | Absolute path to session worktree (e.g., `"/Users/foo/.cache/tas-sessions/20260423T143000Z/tas"`). Same null-rules + information-only semantics as `session_branch`. Phase 6 D-06 additive — `schema_version` remains `1` (NO bump — Phase 1 D-03 9-field contract preserved + Phase 2 D-07 resume gate Step 5 unchanged). |

### Example — initial write (after Classify approval, before step 1 starts)

```json
{
  "schema_version": 1,
  "workspace": "/Users/name/.cache/tas-sessions/20260421T123456Z/project/_workspace/quick/20260421_123456",
  "plan_hash": "7c9e6679f1a3f83e1d2a4b2c5e3d7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e",
  "current_step": "1",
  "completed_steps": [],
  "current_chunk": null,
  "completed_chunks": [],
  "status": "running",
  "updated_at": "2026-04-21T12:34:56.789012+00:00",
  "session_branch": "tas/session-20260421T123456Z",
  "session_worktree_path": "/Users/name/.cache/tas-sessions/20260421T123456Z/project"
}
```

### Example — after step 2 completes (next is step 3)

```json
{
  "schema_version": 1,
  "workspace": "/Users/name/.cache/tas-sessions/20260421T123456Z/project/_workspace/quick/20260421_123456",
  "plan_hash": "7c9e6679f1a3f83e1d2a4b2c5e3d7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e",
  "current_step": "3",
  "completed_steps": ["1", "2"],
  "current_chunk": null,
  "completed_chunks": [],
  "status": "running",
  "updated_at": "2026-04-21T12:48:12.345678+00:00",
  "session_branch": "tas/session-20260421T123456Z",
  "session_worktree_path": "/Users/name/.cache/tas-sessions/20260421T123456Z/project"
}
```

### Example — mid-chunk progress (구현 step chunked, chunk 2 in progress)

```json
{
  "schema_version": 1,
  "workspace": "/Users/name/.cache/tas-sessions/20260422T100000Z/project/_workspace/quick/20260422_100000",
  "plan_hash": "7c9e6679f1a3f83e1d2a4b2c5e3d7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e",
  "current_step": "2",
  "completed_steps": ["1"],
  "current_chunk": "2",
  "completed_chunks": ["1"],
  "status": "running",
  "updated_at": "2026-04-22T10:12:34.567890+00:00",
  "session_branch": "tas/session-20260422T100000Z",
  "session_worktree_path": "/Users/name/.cache/tas-sessions/20260422T100000Z/project"
}
```

### Example — halted mid-chunk (chunk 2 merge conflict)

```json
{
  "schema_version": 1,
  "workspace": "/Users/name/.cache/tas-sessions/20260422T100000Z/project/_workspace/quick/20260422_100000",
  "plan_hash": "7c9e6679f1a3f83e1d2a4b2c5e3d7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e",
  "current_step": "2",
  "completed_steps": ["1"],
  "current_chunk": "2",
  "completed_chunks": ["1"],
  "status": "halted",
  "halt_reason": "chunk_merge_conflict",
  "updated_at": "2026-04-22T10:15:01.000000+00:00",
  "session_branch": "tas/session-20260422T100000Z",
  "session_worktree_path": "/Users/name/.cache/tas-sessions/20260422T100000Z/project"
}
```

### Example — halted mid-run (persistent verify failure on step 3)

```json
{
  "schema_version": 1,
  "workspace": "/Users/name/.cache/tas-sessions/20260421T123456Z/project/_workspace/quick/20260421_123456",
  "plan_hash": "7c9e6679f1a3f83e1d2a4b2c5e3d7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e",
  "current_step": "3",
  "completed_steps": ["1", "2"],
  "current_chunk": null,
  "completed_chunks": [],
  "status": "halted",
  "halt_reason": "persistent_verify_failure",
  "updated_at": "2026-04-21T13:02:44.567890+00:00",
  "session_branch": "tas/session-20260421T123456Z",
  "session_worktree_path": "/Users/name/.cache/tas-sessions/20260421T123456Z/project"
}
```

### plan.json notes

- `plan.json` is written **once**, at Execute Mode Phase 1 Initialize (immediately after Classify approval), via `python3 runtime/checkpoint.py write-plan`. The write CLI enforces "already exists → exit 3"; **plan.json is mtime-immutable after approval**.
- `plan.json` uses canonical JSON serialization (`sort_keys=True`, `separators=(",",":")`, `ensure_ascii=False`) so that re-formatting by tools like `jq` does not invalidate `plan_hash`.
- The plan dict includes an `implementation_chunks` field: `null` when Classify Phase 2c did not trigger vertical-layer decomposition, or a 6-field array `[{id, title, scope, pass_criteria, dependencies_from_prev_chunks, expected_files}]` when the 구현 step runs as a sub-loop (Phase 4). The field is in canonical JSON and therefore covered by `plan_hash`.

### plan_hash algorithm

Canonical JSON (`sort_keys=True, separators=(",", ":"), ensure_ascii=False`) → SHA-256 hex digest (64 chars). Single source of truth: `skills/tas/runtime/checkpoint.py::compute_plan_hash`.

### Atomic write invariant

Both `plan.json` and `checkpoint.json` writes follow the tempfile + `fsync` + `os.replace` pattern implemented in `skills/tas/runtime/checkpoint.py::_atomic_write_json`. After any call (or exception), the target file either reflects the pre-call state or the full new payload — never a torn write.

---

## Session Layer (Phase 6)

Phase 6 introduced a session-isolation layer **outside the project tree**. Every `/tas` invocation creates a named-branch git worktree under `${HOME}/.cache/tas-sessions/`, isolating tas's output channel from the user's main branch + working tree. The workspace home (`_workspace/quick/{ts}/`), Phase 4 chunk worktrees (`chunks/chunk-N/`), and all dialectic logs nest INSIDE the session worktree — `${PROJECT_ROOT}/_workspace/` no longer exists post-Phase-6 for new runs (existing M1 directories remain on disk for forensics; companion commands stop seeing them per Plan 06-04 grep-0-matches guarantee).

### Directory Structure

```
~/.cache/tas-sessions/                            ← CACHE_ROOT (= ${XDG_CACHE_HOME:-${HOME}/.cache}/tas-sessions)
├── LATEST → 20260423T143000Z/<project>/         ← atomic ln -sfn (Phase 6 D-04: gestures SESSION_WORKTREE directly, NOT SESSION_DIR)
├── 20260423T143000Z/                            ← SESSION_DIR (= CACHE_ROOT/${TS}, where TS = `date -u +%Y%m%dT%H%M%SZ`)
│   └── <project>/                               ← SESSION_WORKTREE (named branch tas/session-{TS})
│       ├── (full project source — git checkout) ← user code at named branch's HEAD (sequential chunk merges land here)
│       └── _workspace/quick/{ts}/               ← workspace home (NOW nested inside session worktree, was ${PROJECT_ROOT}/_workspace/quick/)
│           ├── REQUEST.md
│           ├── plan.json                        ← schema unchanged (Plan 06-03 explicit: plan.json UNCHANGED → plan_hash unaffected)
│           ├── checkpoint.json                  ← +2 fields session_branch + session_worktree_path (Phase 6 D-06 additive, schema_version still 1)
│           ├── DELIVERABLE.md
│           ├── lessons.md
│           ├── chunks/                          ← Phase 4 chunk worktrees (NOW nested inside session worktree — CLAUDE.md "chunks must live at $(cd ${WORKSPACE} && pwd)/chunks/chunk-N/" preserved)
│           │   └── chunk-N/                     ← detached HEAD off SESSION_WORKTREE HEAD (Phase 4 D-03 sequential stacking on session branch)
│           └── iteration-N/logs/...
└── 20260420T101122Z/<project>/                  ← prior session, retained (Phase 6 ISO-06 + D-08 forensics policy)
```

### Naming Variables

| Variable | Definition | Example |
|----------|-----------|---------|
| `${CACHE_ROOT}` | `${XDG_CACHE_HOME:-${HOME}/.cache}/tas-sessions` | `/Users/foo/.cache/tas-sessions` |
| `${SESSION_DIR}` | `${CACHE_ROOT}/${TS}` (TS = `date -u +%Y%m%dT%H%M%SZ`) | `${CACHE_ROOT}/20260423T143000Z` |
| `${SESSION_WORKTREE}` | `${SESSION_DIR}/$(basename ${PROJECT_ROOT})` (Phase 6 D-02 defensive `basename`) | `${SESSION_DIR}/tas` |
| `${SESSION_BRANCH}` | `tas/session-${TS}` | `tas/session-20260423T143000Z` |

### Session Layer SSOT Boundary

| Surface | SSOT location | Notes |
|---------|--------------|-------|
| Session bootstrap (worktree create + LATEST symlink) | `skills/tas/SKILL.md` Phase 0 (Plan 06-02) | 4-layer info hiding — SKILL.md owns workspace lifecycle. MetaAgent inherits worktree, never creates one. |
| Cold-resume LATEST resolve + chain-attack defense | `skills/tas/SKILL.md` Phase 0b Step 0 (Plan 06-02 + D-10) | Bare `readlink` (1-step, NOT `readlink -f`) + `case "${RESOLVED}" in "${CACHE_ROOT}/"*) ;; *) HALT ;;` |
| MetaAgent SESSION_WORKTREE awareness + step-config.json non-chunk project_root | `skills/tas/references/meta-execute.md` Phase 1 Initialize (Plan 06-03 Task 1) | Substitutes `{PROJECT_ROOT}` → `{SESSION_WORKTREE}` for non-chunked steps; chunk-specific `project_root = ${CHUNK_PATH}` UNCHANGED. |
| Phase 4 chunk cherry-pick target retarget | `skills/tas/references/meta-execute.md` Phase 2d.5 (Plan 06-05 — 16 substitutions) | Variable swap only; cherry-pick + git apply --index --binary fallback + PRE_MERGE_SHA rollback + chunk_merge_conflict HALT 4 behaviors byte-identical. |
| Per-chunk engine spawn contract documentation | `skills/tas/references/engine-invocation-protocol.md` §Sub-loop invocations (Plan 06-05 — added cherry-pick target bullet) | Standard invocation pattern + Return metadata + Failure classification UNCHANGED — only adds a documentation bullet for the new target variable. |
| Companion command session-index resolution | `skills/tas-{explain,workspace,review}/SKILL.md` (Plan 06-04 — inline duplication, D-05 Discretion) | Each companion has its own LATEST resolver + chain-attack defense; `/tas-workspace clean` extends with session-worktree pruning (Q-G recommendation). |
| Checkpoint schema 11-field documentation | this file (Task 1 above) — §Checkpoint Schema | Additive 2 fields; `schema_version: 1` preserved; Phase 2 D-07 resume gate Step 5 unchanged; `runtime/checkpoint.py` requires NO code change (verified accepts `**fields`). |

### ISO-06 Forensics Retention Policy

Per Phase 6 D-08 + REQUIREMENTS ISO-06: HALT/PASS path **both retain** the session worktree + branch. Auto-cleanup is forbidden — tas never deletes session worktrees without user consent. Removal is exclusively user-initiated via one of:

1. **`/tas-workspace clean`** (Phase 6 D-08 + Q-G extension — Plan 06-04 Task 2) — recommended UX. Lists discovered `tas/session-*` worktrees + presents Y/N confirmation + runs `git worktree remove --force` then `git branch -D` (Q-F: this order is mandatory; git refuses `branch -D` of a checked-out branch).
2. **Direct `git worktree remove "${SESSION_WORKTREE}"`** + `git branch -D tas/session-${TS}` — manual surgical removal of one session.
3. **`rm -rf ~/.cache/tas-sessions/`** — nuclear cache wipe (loses all forensic history; user accepts).
4. **`/tas-workspace --prune <ts>`** — RESERVED but NOT IMPLEMENTED in Phase 6 (D-08 Discretion: chose `clean` extension over a new sub-command per Q-G recommendation; future Phase 7+ may revisit).

**Backlog signal:** SKILL.md Phase 0 D-08 backlog guard (Plan 06-02) emits an inline abort with cleanup guidance when `git worktree list | grep tas/session- | wc -l ≥ 20`. This is NOT a halt enum (Phase 3.1 D-TOPO-05 freeze respected) — it is an environmental cleanup signal.

**Phase 0b cold-resume + LATEST corruption handling:** if user manually deletes a session worktree but `~/.cache/tas-sessions/LATEST` still points to it, Phase 0b Step 1 `test -d "$WORKSPACE"` fails → existing `workspace_missing` HALT (Phase 2 D-04) — no new code path, no new enum. If the `~/.cache/tas-sessions/LATEST` symlink itself is missing (no prior /tas), Phase 0b Step 0 emits `no_checkpoint` HALT (existing enum).

### Cross-references

- Plan 06-02 (SKILL.md Phase 0 + 0b + Phase 1 + Phase 4 Present Result) — bootstrap + cold-resume + dirty-tree + display
- Plan 06-03 (meta-execute.md Phase 1 Initialize + checkpoint payload) — MetaAgent SESSION_WORKTREE awareness + 11-field payload composition
- Plan 06-04 (3 companion command SKILL.md) — LATEST resolver + Q-G clean extension + /tas-review bootstrap reuse
- Plan 06-05 (meta-execute.md Phase 2d.5 + engine-invocation-protocol.md) — 16 chunk sub-loop substitutions + protocol addendum
- Plan 06-07 (Canary #10 simulate_session_isolation.py) — runtime regression guard for the entire layer

---

## Chunk Merge Workflow (Phase 4)

When `plan.implementation_chunks` is non-null + non-empty, the 구현 step runs as a sub-loop of chunks (MetaAgent Execute Phase 2d.5). This section documents the workspace-side workflow — the orchestration sequence itself lives in `agents/meta.md` Phase 2d.5, and the per-chunk engine invocation contract lives in `references/engine-invocation-protocol.md` §Standard invocation pattern + §Sub-loop invocations.

### Pre-flight (once per sub-loop entry)

- `mkdir -p {WORKSPACE}/chunks`
- `git -C {PROJECT_ROOT} worktree prune --expire=1.hour.ago` (reaps stale metadata)
- Discover stale `{WORKSPACE}/chunks/chunk-*` entries via `git worktree list --porcelain` + `awk`, and `worktree remove --force` each (`|| true` so cleanup failure does not block progress; the next run's prune catches residue)
- Worktree count guard: if `git worktree list --porcelain | awk '$1=="worktree"' | wc -l >= 10`, HALT with `halt_reason: worktree_backlog` and route user to `/tas-workspace clean` + `git worktree prune` (see SKILL.md Phase 3 Recovery Guidance for the full Korean message).

### Per-chunk cycle (repeats in order for each chunk in `plan.implementation_chunks`)

1. **Worktree add**: `git -C {PROJECT_ROOT} worktree add --detach {CHUNK_PATH} HEAD` where `CHUNK_PATH = $(cd {WORKSPACE} && pwd)/chunks/chunk-{c.id}` (absolute path via POSIX `cd && pwd` — do not rely on `realpath` which is not always installed on macOS).
2. **Log dir + step-config.json**: `mkdir -p {CHUNK_LOG_DIR}` where `CHUNK_LOG_DIR = iteration-{N}/logs/step-{S.id}-implement-chunk-{c.id}`. The step-config.json's `project_root` is set to `{CHUNK_PATH}` (not the main project root) — this is the only chunk-aware wiring the dialectic engine sees.
3. **Engine invocation**: per `references/engine-invocation-protocol.md` §Standard invocation pattern, with `LOG_DIR → CHUNK_LOG_DIR` substitution. Polling + classification inherit unchanged.
4. **MetaAgent commit** (on verdict ACCEPT/PASS): `git -C {CHUNK_PATH} add -A && git -C {CHUNK_PATH} commit -m "chunk-{c.id}: {c.title}" -m "dialectic verdict: {VERDICT}" -m "rounds: {ROUNDS}"`. Empty diff (`git status --porcelain` empty) → skip commit + skip merge, mark chunk as completed anyway.
5. **Summary generation**: MetaAgent composes a ≤5KB summary per 04-CONTEXT.md D-04 template and appends to an in-memory `cumulative_chunk_context` (iteration-scoped; NOT persisted).
6. **Merge**: `git -C {PROJECT_ROOT} cherry-pick {CHUNK_SHA}` as primary path; on failure, `git cherry-pick --abort` then `git diff HEAD~..HEAD --binary | git -C {PROJECT_ROOT} apply --index --binary` + commit as fallback. Capture `PRE_MERGE_SHA` as the first action so both-paths-failed → `git reset --hard {PRE_MERGE_SHA}` + `git clean -fd` + HALT `chunk_merge_conflict` is a safe rollback. `merge.log` inside the chunk log dir receives stderr from both cherry-pick and apply attempts (forensics).
7. **Worktree remove**: `git -C {PROJECT_ROOT} worktree remove --force {CHUNK_PATH} 2>/dev/null || true` (post-merge cleanup).
8. **Checkpoint write**: step 9.5 atomic write with `current_chunk` + `completed_chunks` populated. At the final chunk's merge, `current_chunk` resets to `null` and `completed_chunks` resets to `[]` because the step itself completes (step-boundary semantics per 04-CONTEXT.md D-08).

### FAIL / HALT path

Any chunk's dialectic FAIL / engine HALT / merge conflict triggers:
- inline worktree remove (per failure branch — no Bash trap)
- `git worktree prune` (defensive)
- `checkpoint.py write` with `status: "halted"`, forensic `current_chunk` + `completed_chunks`, and a halt_reason from the Phase 4 branch table (`persistent_dialectic_fail` / engine-emitted enum / `chunk_merge_conflict` / `worktree_backlog`)
- HALT JSON emission back to the outer Execute Phase 2d loop
- No within-iter chunk retry. No re-Classify. User recovery = fresh `/tas` invocation (optionally with `chunks: 1` override).

### SSOT boundary (Pitfall 12 cross-file drift prevention)

- **This file** (`workspace-convention.md`) owns: directory layout, checkpoint schema fields/examples, merge workflow outline.
- **`agents/meta.md` Phase 2d.5** owns: orchestration sequence (for-each-chunk + summary composition + commit/merge call site + checkpoint write timing).
- **`references/engine-invocation-protocol.md`** owns: spawn + poll + classify contract (Standard invocation pattern + Sub-loop invocations addendum).
- No file copies the authoritative body of another; cross-references are always 1-paragraph delegations ("see §X in Y for the substitution table").

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
