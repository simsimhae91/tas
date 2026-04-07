# Sprint Planning Algorithm

MetaAgent uses this algorithm when executing Implementation phases to plan and
execute story batches with parallel worktree agents.

---

## Overview

```
stories/*.md → Build DAG → Topological Sort → Batch into Sprints → Execute
```

---

## Step 1: Build Story Dependency DAG

1. Read all story specs from `stories/` directory
2. For each story, extract:
   - `story_id` (from filename)
   - `dependencies` (from Metadata table)
   - `parallel_group` (from Metadata table)
   - `priority` (P0 > P1 > P2)
   - `complexity` (S/M/L)
   - `files` (list of files to create/modify)
3. Build directed acyclic graph: edges from dependency → dependent

### Cycle Detection

If the dependency graph contains cycles:
1. Identify the cycle (list story IDs)
2. Report to MainOrchestrator as error
3. Suggest breaking the cycle by splitting the most complex story in the cycle

---

## Step 2: Topological Sort

Sort stories in dependency order using Kahn's algorithm:

```
1. Compute in-degree for each story
2. Queue all stories with in-degree 0
3. While queue not empty:
   a. Dequeue story with highest priority (P0 first)
   b. Add to sorted order
   c. For each dependent: decrement in-degree, enqueue if 0
4. If sorted order < total stories: cycle exists (caught in Step 1)
```

---

## Step 3: Batch into Sprint Groups

Group stories into batches for parallel execution:

```
MAX_PARALLEL_STORIES = 3  (default, adjustable)

1. Take stories in topological order
2. For each story:
   a. If all dependencies are in completed batches AND
      current batch size < MAX_PARALLEL_STORIES AND
      no file overlap with other stories in current batch:
      → Add to current batch
   b. Else: start new batch
3. Within each batch, sort by priority (P0 first)
```

### File Overlap Detection

Two stories CANNOT be in the same batch if they modify the same file.
Check the `Files` field in each story's Metadata table.

This prevents merge conflicts within a batch (conflicts between batches
are handled by the conflict resolver).

### Batch Output

```
Sprint 1: [AUTH-001, DATA-001, UI-001]  (independent, no file overlap)
Sprint 2: [AUTH-002, DATA-002]          (depend on Sprint 1 stories)
Sprint 3: [INTEG-001]                   (depends on Sprint 2)
```

---

## Step 4: Execute Sprint Batches

### Per-Batch Execution

For each sprint batch:

1. **Spawn thesis agents in parallel** with worktree isolation:
```
For each story in batch:
  Agent({
    name: "thesis-{story_id}",
    description: "Implement {story_id}",
    mode: "bypassPermissions",
    isolation: "worktree",
    run_in_background: true,
    prompt: "{thesis_instructions}\n\n## Story Assignment\n{story spec content}\n\nWorktree mode. Implement this story."
  })
```

2. **Wait for all thesis agents** in the batch to complete

3. **Sequential antithesis review** per completed story:
```
For each completed story:
  Agent({
    description: "Review {story_id}",
    mode: "bypassPermissions",
    prompt: "{antithesis_instructions}\n\n## Review Assignment\n**Story Spec**:\n{spec}\n**Git Diff**:\n{diff from worktree}\n\nDiff-review mode. Review against story acceptance criteria."
  })
```

4. **Judge each review**:
   - **ACCEPT** → Queue for merge
   - **REFINE / COUNTER** → Thesis responds, dialogue continues until convergence
   - **HALT** (circular argumentation, contradictory spec, missing dependency) → Mark as BLOCKED, continue with other stories

5. **Merge passed stories** in dependency order:
   - Cherry-pick or merge from worktree branch to develop branch
   - If conflict: spawn conflict-resolver agent
   - After merge: run integration tests (if defined in architecture.md)

6. **Post-batch validation**:
   - Run integration tests across all merged stories
   - If test failure: `git blame` to identify responsible story, spawn thesis fix attempt (max 2)

### Merge Strategy

```
For each passed story (in dependency order):
  1. Attempt merge from worktree branch to develop
  2. If clean: commit with message "feat({story-id}): {title}"
  3. If conflict:
     a. Spawn conflict-resolver agent with:
        - Both diffs
        - Both story specs
        - Target (already-merged) branch state
     b. If resolved: commit
     c. If unresolved: mark MERGE_BLOCKED, continue others, report
  4. Run story-specific tests (from Test Plan)
```

---

## Error Handling

| Failure | Detection | Recovery |
|---------|-----------|----------|
| Thesis crash in worktree | Agent error/timeout | Re-spawn with existing commits if any, else 1 retry |
| Unresolved merge conflict | Conflicts remain post-resolution | Mark MERGE_BLOCKED, continue others, report to user |
| Integration test failure | Non-zero exit after merge | `git blame` to identify story, thesis addresses in continued dialogue |
| HALT (impasse) | Circular argumentation or contradictory spec | Mark BLOCKED with HALT reason, continue others, report to user |
| MetaAgent crash mid-sprint | Process exit | Preserve worktree branches + workspace, allow resume |

### Partial Completion

When a batch cannot fully complete:
1. Merge all PASS stories
2. List BLOCKED stories with HALT reasons
3. Write partial results to `DELIVERABLE.md`
4. Set `"status": "partial"` in output JSON

---

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| MAX_PARALLEL_STORIES | 3 | Maximum concurrent worktree agents per batch |
| MERGE_TARGET | develop | Branch to merge completed stories into |
| TERMINATION | convergence or HALT | No fixed retry cap — dialogue continues until agreement or irrecoverable impasse |
