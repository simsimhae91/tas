---
phase: P4-implementation
pipeline: sdlc
execution_mode: sprint
---

# P4: Implementation

Sprint-based execution of implementation stories from Phase 3. Stories are batched by dependency order and executed in parallel within each batch, with per-story dialectical review.

---

## S01: Sprint Planning

### Required
true

### Goal
Load stories from Phase 3 deliverable, build a dependency DAG, detect cycles, and batch stories into sprint groups for parallel execution.

### Read Scope
- required: P3-solutioning/DELIVERABLE.md

### Thesis
role: planner
instruction: |
  Execute the sprint planning algorithm (see references/sprint-planning.md):
  1. **Load stories** — parse all story specs from Phase 3 deliverable. For each story extract: story_id, dependencies, parallel_group, priority, complexity, estimated LOC, files to create/modify.
  2. **Build dependency DAG** — create directed edges from dependency to dependent. Run cycle detection. If cycles exist, report them and suggest how to break them.
  3. **Topological sort** — sort stories in dependency order using Kahn's algorithm. P0 stories first within same dependency level.
  4. **Batch into sprints** — group stories into batches following these rules:
     - All dependencies in earlier (completed) batches
     - Batch size <= MAX_PARALLEL_STORIES (default 3)
     - No file overlap within a batch (check files-to-modify lists)
  5. **Sprint plan output** — table showing: batch number, stories in batch, combined estimated LOC, expected file sets.
  6. **Validation** — confirm: no cycles, dependency order correct, file sets within each batch are disjoint, every story appears exactly once.

### Antithesis
role: plan-auditor
instruction: |
  Audit the sprint plan:
  - Are there any cycles in the dependency graph? Re-trace edges independently.
  - Is the topological sort correct? For every story, confirm all its dependencies appear in earlier batches.
  - Within each batch, are file sets truly disjoint? List every file per story in the batch and check for overlaps.
  - Does every story from Phase 3 appear exactly once in the plan? Flag any missing or duplicate stories.
  - Is the batch sizing reasonable? (No batch should have more than MAX_PARALLEL_STORIES)
  - Are P0 stories prioritized in earlier batches where dependencies allow?

### Convergence
target: plan-validity
model: standard
weight: light

### Pass Criteria
- Zero cycles in dependency graph
- Every story's dependencies are in earlier batches
- File sets within each batch are disjoint
- Every Phase 3 story appears exactly once
- Batch sizes do not exceed MAX_PARALLEL_STORIES

### Output
path: P4-implementation/S01-sprint-planning.md
sections:
  - Story Inventory (parsed from Phase 3)
  - Dependency DAG
  - Topological Order
  - Sprint Batches (batch number, stories, LOC, files)
  - Validation Results

---

## S02: Scaffold

### Required
false

### Skip Condition
Adding features to an existing project with established structure.

### Goal
Create the project skeleton per the Phase 3 architecture: directory structure, configuration files, build scripts, and placeholder files for all story-referenced paths.

### Read Scope
- required: P3-solutioning/DELIVERABLE.md
- required: P4-implementation/S01-sprint-planning.md

### Thesis
role: builder
instruction: |
  Create the project scaffold based on the architecture:
  1. **Directory structure** — create all directories specified in the architecture. Follow the component boundaries.
  2. **Configuration files** — package.json / requirements.txt / go.mod (or equivalent), tsconfig, linter config, .gitignore. Configure the recommended tech stack from Phase 1.
  3. **Build scripts** — dev, build, test, lint commands. Must work out of the box (even if tests are empty).
  4. **Placeholder files** — create empty or minimal placeholder files for every path referenced in any story spec. This ensures stories can import/reference these paths during parallel implementation.
  5. **Shared types/interfaces** — if the architecture defines shared data types or API contracts, create the type definition files now. Stories will implement against these contracts.
  6. **Verify** — run the build command to confirm the scaffold compiles/parses without errors.

  The scaffold must be complete enough that any story from the sprint plan can begin implementation without creating directories or config files.

### Antithesis
role: arch-verifier
instruction: |
  Verify the scaffold against the architecture:
  - Does the directory structure match the architecture's component layout?
  - Does every file path referenced in any story spec exist in the scaffold (even as a placeholder)?
  - Do configuration files match the recommended tech stack?
  - Does the build command succeed? If not, what is broken?
  - Are shared types/interfaces consistent with the API contracts from the architecture?
  - Could a story implementer start coding immediately against this scaffold, or are there missing pieces?

### Convergence
target: arch-conformance
model: standard
weight: light

### Pass Criteria
- Directory structure matches architecture component layout
- Every story-referenced file path exists in the scaffold
- Build command succeeds without errors
- Shared types/interfaces match architecture API contracts

### Output
path: P4-implementation/S02-scaffold.md
sections:
  - Directory Structure Created
  - Configuration Files
  - Placeholder Files (per story reference)
  - Shared Types/Interfaces
  - Build Verification Result

---

## S03: Create Story
scope: per-story

### Required
true

### Goal
Expand a Phase 3 story's acceptance criteria into an implementation-ready spec document with detailed technical approach, code structure, and step-by-step implementation guidance.

### Read Scope
- required: P3-solutioning/DELIVERABLE.md (stories/{story-id}.md section)
- optional: P4-implementation/S02-scaffold.md

### Thesis
role: spec-writer
instruction: |
  Expand the Phase 3 story into an implementation-ready spec:
  1. **Technical approach** — how to implement each acceptance criterion. Reference specific files from the scaffold, specific functions/methods to create, specific data structures to use.
  2. **Code structure** — outline the code organization: which files to create/modify, what each file contains, how files relate to each other.
  3. **Step-by-step implementation** — ordered list of implementation steps. Each step should be small enough to code in one pass. Include:
     - What to implement
     - Which file(s) to touch
     - What to import/depend on
     - Expected behavior after this step
  4. **Error handling** — how each error condition in the acceptance criteria should be handled. Specific error types, messages, recovery behavior.
  5. **Test implementation guide** — expand the Phase 3 test plan into implementable test cases. Include: test file location, test framework setup, specific assertions.
  6. **Integration points** — how this story's code connects to the scaffold's shared types/interfaces. Which contracts it implements or consumes.

  The spec must be complete enough for an implementer to code the story without consulting the architecture document. All ambiguity should be resolved here.

  If scaffold (S02) was not performed, reference the existing project structure directly instead of scaffold output. Implementation steps should account for the existing codebase conventions.

### Antithesis
role: spec-reviewer
instruction: |
  Review the spec for implementation readiness:
  - Could a developer implement this story from the spec alone, without consulting architecture docs? Flag any ambiguous or underspecified sections.
  - Does every acceptance criterion have a corresponding implementation step?
  - Are file paths consistent with the scaffold? Flag any references to files not in the scaffold.
  - Are error handling approaches specific (error type, message, behavior) or vague ("handle errors appropriately")?
  - Does the test guide include specific assertions, or just descriptions of what to test?
  - Are integration points explicitly defined (which interface/type to implement), or left implicit?

### Convergence
target: output-quality
model: standard
weight: medium

### Pass Criteria
- Every acceptance criterion has a corresponding implementation step
- File paths reference existing scaffold files
- Error handling specifies error types, messages, and recovery behavior
- Test cases include specific assertions
- Spec is self-contained for standalone implementation

### Output
path: P4-implementation/{batch}/S03-create-story.md
sections:
  - Technical Approach
  - Code Structure
  - Implementation Steps
  - Error Handling
  - Test Implementation Guide
  - Integration Points

---

## S04: Dev Story
scope: per-story

### Required
true

### Goal
Implement the story based on the S03 create-story spec, producing working code that passes all acceptance criteria and story-level tests.

### Read Scope
- required: P4-implementation/{batch}/{story-id}/S03-create-story.md

### Thesis
role: implementer
instruction: |
  Implement the story in worktree isolation following the S03 spec:
  1. **Follow implementation steps** — execute the steps from S03 in order. Each step should produce compiling/parseable code.
  2. **Run tests** — execute the test plan from S03. All tests must pass.
  3. **Scope compliance** — only modify files listed in the story spec. If you discover a need to modify other files, flag it as a scope violation rather than silently changing them.
  4. **Convention compliance** — follow the project's coding conventions (naming, formatting, patterns) as established in the scaffold.
  5. **Commit format** — commit as `feat({story-id}): {story title}`.
  6. **Implementation report** — document: what was implemented, files modified, test results, any deviations from spec (with justification).

  Do NOT gold-plate. Implement exactly what the acceptance criteria require. If the spec is unclear on a point, implement the simplest correct interpretation and flag the ambiguity.

### Antithesis
role: diff-reviewer
instruction: |
  Review the implementation diff against the story acceptance criteria:
  1. **AC fulfillment** — for each acceptance criterion, trace it through the diff. Can you find the code that implements it? Flag any AC not addressed.
  2. **Scope compliance** — does the diff modify only files listed in the story spec? Flag any out-of-spec file changes.
  3. **Code quality** — apply standard review lenses:
     - Semantic consistency: same concept means the same thing everywhere in the diff
     - Behavioral consistency: all code paths for the same operation behave identically
     - Compositional integrity: function compositions are sound for all valid inputs
     - Value flow soundness: no intermediate computation produces unexpected values
  4. **Test coverage** — do the tests actually verify the acceptance criteria, or do they test implementation details?
  5. **Convention compliance** — does the code follow the patterns established in the scaffold?

  Focus on real issues, not style preferences. A "COUNTER" must identify a specific AC gap or a quality invariant violation.

### Convergence
target: ac-fulfillment
model: standard
weight: heavy

### Pass Criteria
- Every acceptance criterion is traceable in the diff
- Only story-specified files are modified
- Tests pass and verify acceptance criteria
- No quality invariant violations (semantic, behavioral, compositional, value flow)

### Output
path: P4-implementation/{batch}/{story-id}/S04-dev-story.md
sections:
  - Implementation Summary
  - Files Modified
  - AC Fulfillment Trace
  - Test Results
  - Deviations from Spec

---

## S05: QA Story
scope: per-story
condition: skip if no test plan defined for story

### Required
false

### Skip Condition
No test plan defined for story, or no test infrastructure available.

### Goal
Run the automated test suite for the story and report results.

### Read Scope
- required: P4-implementation/{batch}/{story-id}/S03-create-story.md
- required: P4-implementation/{batch}/{story-id}/S04-dev-story.md

### Thesis
role: test-runner
instruction: |
  Execute the test suite defined in S03 and report:
  1. **Run all story tests** — execute the test commands specified in the create-story spec.
  2. **Report results** — for each test: name, pass/fail, actual output vs expected output (for failures).
  3. **Coverage check** — verify all acceptance criteria have at least one passing test.
  4. **Regression check** — run any broader test suites (if configured in scaffold) to ensure no regressions.

### Convergence
target: output-quality
model: standard
weight: minimal

### Pass Criteria
- All story tests execute
- Test results are reported with pass/fail status
- Failed tests include actual vs expected output

### Output
path: P4-implementation/{batch}/{story-id}/S05-qa-story.md
sections:
  - Test Execution Results
  - Coverage Check
  - Regression Check (if applicable)

---

## S06: Review Story
scope: per-story
on_fail: S04-dev-story

### Required
true

### Goal
Final quality gate for the story. Uses inverted convergence model: thesis attacks the implementation, antithesis judges whether attacks are valid blockers.

### Read Scope
- required: P4-implementation/{batch}/{story-id}/S03-create-story.md
- required: P4-implementation/{batch}/{story-id}/S04-dev-story.md
- optional: P4-implementation/{batch}/{story-id}/S05-qa-story.md

### Thesis
role: attacker
instruction: |
  Aggressively review the actual implementation against the story spec:
  1. **AC gap scan** — re-read every acceptance criterion. For each, find the implementing code. If any AC is not fully implemented, file it as a blocker.
  2. **Side effect scan** — does the implementation introduce side effects not mentioned in the spec? (e.g., modifying global state, writing to files not in spec, altering shared types)
  3. **Convention violations** — does the code deviate from patterns established in the scaffold or other completed stories?
  4. **Edge case probes** — for each function/method in the diff, identify at least one edge case input. Does the implementation handle it?
  5. **Integration risk** — will this implementation merge cleanly with the scaffold and other stories? Are imports correct, types compatible, exports aligned?

  Classify each finding as:
  - **BLOCKER** — must fix before merge (AC gap, broken functionality, type error)
  - **WARNING** — should fix but not a merge blocker (style issue, missing edge case that is not in AC)
  - **NOTE** — observation for future improvement

  Be aggressive but honest. Do not manufacture blockers to justify the review role.

### Antithesis
role: judge
instruction: |
  Evaluate each thesis finding:
  1. **For each BLOCKER** — is it a real blocker? Criteria for a valid blocker:
     - It identifies a specific AC that is not met, OR
     - It identifies a concrete bug (not a hypothetical), OR
     - It identifies a type error or compilation failure
     If the blocker is actually a style preference or a hypothetical concern, downgrade it to WARNING.
  2. **For each WARNING** — is it valid? Is it actionable?
  3. **For each NOTE** — acknowledge and move on.
  4. **Final verdict**:
     - 0 valid blockers → **PASS** (ACCEPT)
     - 1+ valid blockers → **FAIL** (COUNTER) with the blocker list

  Be fair. Do not rubber-stamp. Do not inflate warnings to blockers. The goal is a correct verdict, not a quick pass.

### Convergence
target: issue-verdict
model: inverted
weight: heavy

### Pass Criteria
- Every finding is classified (BLOCKER/WARNING/NOTE)
- Blocker classifications are justified with specific evidence
- Final verdict is consistent with blocker count (0 blockers = PASS)

### Output
path: P4-implementation/{batch}/{story-id}/S06-review-story.md
sections:
  - Findings (classified as BLOCKER/WARNING/NOTE)
  - Blocker Evaluation
  - Final Verdict (PASS or FAIL with blocker list)

---

## S07: E2E QA
last_step: true

### Required
false

### Skip Condition
Project has 2 or fewer stories with minimal cross-story integration risk.

### Goal
Integration testing after all sprint batches are merged. Verify cross-story integration, run the full test suite, and identify any gaps.

### Read Scope
- required: P4-implementation/S01-sprint-planning.md
- required: all batch results (P4-implementation/batch-*/*/S06-review-story.md)

### Thesis
role: integration-tester
instruction: |
  Run comprehensive integration testing:
  1. **Full test suite** — run all tests (unit + integration). Report results.
  2. **Cross-story integration** — for each batch boundary, verify that stories from different batches integrate correctly:
     - Data flows across story boundaries (Story A creates data, Story B queries it)
     - API contracts are honored (caller and callee agree on types/shapes)
     - Shared state is consistent
  3. **End-to-end flows** — trace at least one complete user flow (from the Phase 2 UX flows) through the implementation. Verify it works end-to-end.
  4. **Build verification** — clean build from scratch passes. No stale references or missing dependencies.

### Antithesis
role: gap-finder
instruction: |
  Identify gaps in integration testing:
  - Are there cross-story interactions that were not tested? (Check dependency graph from S01 — every edge should have a test.)
  - Are there error paths in the integration that were not tested? (e.g., what happens when Story A's API returns an error and Story B calls it?)
  - Are there any stories that were BLOCKED or had warnings in S06 review? Do their issues affect integration?
  - Does the build produce any warnings (not just errors)?
  - Are there any inconsistencies in shared types across stories?

### Convergence
target: output-quality
model: standard
weight: medium

### Pass Criteria
- Full test suite passes
- At least one end-to-end user flow verified
- Cross-story integration tested at every batch boundary
- Clean build from scratch succeeds
- No untested cross-story data flows identified

### Output
path: P4-implementation/DELIVERABLE.md
sections:
  - Per-Story Status Table (MERGED/BLOCKED/REMAINING)
  - Test Results (unit, integration, e2e)
  - Cross-Story Integration Results
  - Build Verification
  - Remaining Work / HALT Reasons
  - Known Issues and Warnings

---

## Sprint Mode Orchestration

MainOrchestrator drives Phase 4 as follows:

### Sequential Setup (run once)

1. **S01: Sprint Planning** — produces the batch plan.
2. **S02: Scaffold** — creates the project skeleton.

Both steps run as standard MetaAgent `claude -p` sessions (thesis-antithesis-synthesis).

### Per-Story Pipeline (per batch)

For each batch in the sprint plan:

```
For each story in batch (up to MAX_PARALLEL_STORIES in parallel):
  S03: Create Story  →  S04: Dev Story  →  S05: QA Story  →  S06: Review Story
                                                                     │
                                                                     ├─ PASS → queue for merge
                                                                     └─ FAIL → loop back to S04
                                                                                (with blocker list as input)
```

- **S03-S06** form a sequential pipeline per story.
- **Stories within the same batch** can run their pipelines in parallel (up to MAX_PARALLEL_STORIES).
- **S05 is conditional** — skipped if the story has no test plan defined.
- **S06 FAIL** loops back to S04 for that story. The blocker list from S06 becomes additional input for the re-run. S05 re-runs after S04 if applicable.
- **Merge** happens after all stories in the batch pass S06. Stories merge in dependency order.

### Batch Sequencing

```
Batch 1: [stories...]  ← run in parallel, merge all, then →
Batch 2: [stories...]  ← run in parallel, merge all, then →
...
Batch N: [stories...]  ← run in parallel, merge all, then →
S07: E2E QA            ← run once after all batches complete
```

Each batch must complete (all stories merged or blocked) before the next batch begins.
Blocked stories are recorded but do not prevent the next batch from starting (unless they are dependencies).

### MAX_PARALLEL_STORIES

Default: 3. Controls how many stories run their S03-S06 pipeline concurrently within a batch. This maps to concurrent worktree agents in MetaAgent.

---

## Exit Contract

DELIVERABLE.md must contain these fields:

| Field | Required | Description |
|-------|----------|-------------|
| Per-story status table | yes | Every story: MERGED, BLOCKED, or REMAINING with reason |
| Integration test results | yes | Full test suite pass/fail with details |
| Remaining work / HALT reasons | yes | What was not completed and why |
