---
phase: P4-production
pipeline: gamedev
execution_mode: sprint
steps: 7
---

# P4: Production

Execute sprint-based implementation with parallel worktree agents, review, and QA. Follows the sprint-planning.md algorithm for story batching and execution.

---

## S01: Sprint Planning

### Required
true

### Goal
Load stories from Phase 3, build the dependency DAG, batch into sprint groups respecting file overlap and dependency order.

### Read Scope
- required: P3-technical/DELIVERABLE.md

### Thesis
role: sprint-planner
instruction: |
  Execute the sprint-planning.md algorithm:
  - **Load stories**: read all story specs from the Phase 3 deliverable. Extract story ID, dependencies, parallel group, priority, complexity, and file lists
  - **Build dependency DAG**: create directed edges from each dependency to its dependent. Verify the graph is acyclic
  - **Topological sort**: sort stories in dependency order using priority as tiebreaker (P0 first)
  - **Batch into sprints**: group stories into batches where:
    - All dependencies are in earlier (completed) batches
    - Batch size does not exceed MAX_PARALLEL_STORIES (default: 3)
    - No two stories in the same batch modify the same file
  - **Batch ordering**: within each batch, sort by priority (P0 first), then complexity (S before M)
  - **Sprint summary**: produce a sprint plan showing batch composition, estimated total LOC per batch, and critical path identification

  If cycles are detected in the dependency graph, report the cycle and suggest which story to split to break it.

### Antithesis
role: plan-validator
instruction: |
  Verify the sprint plan is valid and optimal:
  - **Cycle detection**: confirm no cycles exist in the dependency graph
  - **Dependency order**: verify that for every story, all its dependencies appear in earlier batches
  - **File disjointness**: verify no two stories in the same batch modify the same file. Check not just declared files but also shared config files, asset manifests, and build scripts
  - **Priority ordering**: are all P0 stories scheduled before P1 stories (across batches)? If not, justify the ordering
  - **Batch size**: does every batch respect MAX_PARALLEL_STORIES?
  - **Critical path**: is the critical path (longest dependency chain) correctly identified?

  For each plan issue, propose a specific rebatching.

### Convergence
target: plan-validity
model: standard
weight: medium

### Pass Criteria
- Dependency graph is acyclic
- All P0 stories appear in earlier batches than any P1 story they don't depend on
- No batch exceeds MAX_PARALLEL_STORIES
- No two stories in the same batch share any files
- Critical path length is documented
- Total batch count and per-batch LOC estimates are present

### Output
path: P4-production/S01-sprint-planning.md
sections:
  - Story Load Summary
  - Dependency Graph
  - Sprint Batches (batch number, stories, estimated LOC)
  - Critical Path
  - Configuration (MAX_PARALLEL_STORIES, MERGE_TARGET)

---

## S02: Scaffold

### Required
false

### Skip Condition
Adding features to an existing project with established structure.

### Goal
Create the project skeleton: directory structure, engine configuration, placeholder assets, build scripts, and dependency installation for the target platform.

### Read Scope
- required: P3-technical/DELIVERABLE.md
- required: P4-production/S01-sprint-planning.md

### Thesis
role: scaffolder
instruction: |
  Create the project scaffold matching the architecture:
  - **Directory structure**: create all directories from the project-context.md folder structure. Every path referenced by any story must exist
  - **Engine configuration**: initialize the chosen engine/framework with project settings — resolution, target platform, build profiles (debug/release), input configuration
  - **Placeholder assets**: create minimal placeholder assets for stories that have asset dependencies — empty sprite sheets with correct dimensions, silent audio files with correct format, stub data files with correct schema
  - **Build scripts**: create build configuration for the target platform — build commands, asset pipeline scripts, platform-specific packaging (APK, IPA, console package). Include both debug and release configurations
  - **Dependency installation**: install all third-party dependencies from the tech recommendation. Pin versions to avoid compatibility drift
  - **Entry point**: create the minimal application entry point that initializes the engine, sets up the game loop stub, and exits cleanly. The scaffold must build and run (showing an empty screen or placeholder) before any story implementation begins

  The scaffold must build and run successfully in its empty state. This is the baseline that all story implementations build upon.

### Antithesis
role: scaffold-verifier
instruction: |
  Verify the scaffold is complete and functional:
  - **Architecture match**: does the directory structure match the architecture from Phase 3? Are there missing directories that stories will need?
  - **Build verification**: does the project build in its scaffolded state? Are build commands for both debug and release configurations working?
  - **Platform targeting**: are build scripts configured for the correct target platform? Are platform-specific settings (screen orientation, permissions, capabilities) configured?
  - **Story path existence**: does every file path referenced by any story in the sprint plan exist (at least as an empty file or directory)?
  - **Placeholder asset validity**: are placeholder assets in the correct format and dimensions? Will stories be able to reference them without format errors?
  - **Dependency versions**: are all dependencies pinned to specific versions? Are there known compatibility issues between dependencies?

  For each scaffold gap, specify the missing element and which stories it would block.

### Convergence
target: output-quality
model: standard
weight: medium

### Pass Criteria
- Directory structure matches architecture and all story-referenced paths exist
- Project builds and runs in scaffolded state (empty screen, no crashes)
- Build scripts target the correct platform with debug and release configurations
- Placeholder assets exist for all declared asset dependencies
- All dependencies installed with pinned versions
- Engine configuration matches target platform settings from Phase 1

### Output
path: P4-production/S02-scaffold.md
sections:
  - Directory Structure Created
  - Engine Configuration
  - Placeholder Assets
  - Build Scripts
  - Dependencies Installed
  - Build Verification Result

---

## PER-STORY STEPS (S03-S06)

Steps S03 through S06 execute for each story within the current sprint batch. Each story gets its own directory under the batch: `P4-production/batch-{N}/{story-id}/`.

Stories within the same batch execute S03 in parallel (worktree isolation). S04-S06 execute sequentially per story after S03 completes.

---

## S03: Create Story

### Required
true

### Goal
Implement a single story in an isolated worktree according to its specification, including gameplay behavior tests.

### Read Scope
- required: P3-technical/DELIVERABLE.md (architecture, project context)
- optional: P4-production/S02-scaffold.md
- required: current story spec from P3-technical/S02-epics-and-stories.md

### Thesis
role: story-implementer
instruction: |
  Implement the assigned story in the isolated worktree:
  - **Follow the spec**: implement exactly what the story's technical spec describes. Do not add features not in the spec. Do not skip features that are in the spec
  - **Project conventions**: follow all naming, style, and pattern conventions from project-context.md
  - **Acceptance criteria**: implement until all acceptance criteria are met. Self-check each criterion before marking complete
  - **Test implementation**: write all tests from the story's test plan:
    - Unit tests for pure logic
    - Component tests for system behavior
    - Gameplay behavior tests where specified — these test player-observable outcomes, not internal state
  - **Play-test criteria**: for gameplay stories, implement play-test verification that validates the player experience described in the story's play-test criteria
  - **No hardcoded values**: game parameters (damage, speed, costs, timers, spawn rates) must be data-driven (loaded from config/data files), not hardcoded in source. This enables tuning without code changes
  - **Asset references**: all asset references must use the path conventions from project-context.md. Verify referenced assets exist (at least as placeholders)

  Produce a self-assessment: which acceptance criteria pass, which need verification, and any concerns about the implementation.

  If scaffold (S02) was not performed, reference the existing project structure directly instead of scaffold output.

### Antithesis
role: story-reviewer
instruction: |
  Perform diff-based review of the story implementation:
  - **Acceptance criteria verification**: for each criterion in the story spec, verify the implementation satisfies it. Cite specific code
  - **Scope compliance**: does the implementation match the story scope? Flag added features (scope creep) or missing features (incomplete)
  - **Review criteria**: apply the story-specific review criteria from the spec's Review Criteria section
  - **Gameplay behavior tests**: do gameplay tests actually test player-observable behavior? Flag tests that only check internal state when player-observable behavior was specified
  - **Hardcoded values**: scan for hardcoded game parameters (magic numbers in game logic). Every tunable value should come from data/config
  - **Asset reference validity**: do all asset references point to existing files with correct paths?
  - **Convention compliance**: does the code follow project-context.md conventions (naming, patterns, structure)?

  Classify each finding as Required Fix (must fix before merge) or Suggestion (improvement, not blocking).

### Convergence
target: ac-fulfillment
model: standard
weight: medium

### Pass Criteria
- All acceptance criteria from the story spec are met
- No scope creep (no unspecified features added)
- Game parameters are data-driven, not hardcoded
- All asset references point to existing files
- Gameplay behavior tests verify player-observable outcomes
- Code follows project-context.md conventions

### Output
path: P4-production/batch-{N}/{story-id}/S03-create-story.md
sections:
  - Implementation Summary
  - Acceptance Criteria Status
  - Test Results
  - Self-Assessment

---

## S04: Dev Story

### Required
true

### Goal
Address review findings from S03 (or S06 on_fail re-entry), iterate until all Required Fixes are resolved.

### Read Scope
- required: P3-technical/DELIVERABLE.md (architecture, project context)
- required: current story spec
- required: P4-production/batch-{N}/{story-id}/S03-create-story.md (or S06 review)

### Thesis
role: story-implementer
instruction: |
  Address each Required Fix from the review:
  - **Fix each finding**: implement the fix for every Required Fix. Reference the specific finding ID
  - **No regressions**: verify existing acceptance criteria still pass after fixes. Run all tests
  - **Data-driven verification**: if hardcoded values were flagged, extract them to config/data files and verify the game reads them correctly at runtime
  - **Asset reference fixes**: if asset references were invalid, correct them and verify the assets load
  - **Gameplay behavior test fixes**: if gameplay tests were flagged as testing internal state, rewrite them to test player-observable outcomes
  - **Re-self-assess**: update the self-assessment with fix results

  Produce a fix report mapping each Required Fix to the change made.

### Antithesis
role: fix-verifier
instruction: |
  Verify all Required Fixes are addressed without regressions:
  - **Fix completeness**: is each Required Fix from the previous review addressed? Map each fix to the specific finding
  - **No regressions**: do all previously passing acceptance criteria still pass?
  - **Fix quality**: are fixes genuine resolutions or workarounds? (e.g., commenting out a test is not a fix)
  - **New issues**: did any fix introduce new problems? Check for cascading effects
  - **Hardcoded value sweep**: re-scan for any remaining hardcoded game parameters
  - **Asset reference re-check**: verify all asset references after fixes

  Mark each Required Fix as RESOLVED or UNRESOLVED. If any are UNRESOLVED, specify what remains.

### Convergence
target: ac-fulfillment
model: standard
weight: medium

### Pass Criteria
- Every Required Fix from the review is marked RESOLVED
- All acceptance criteria pass (no regressions)
- No hardcoded game parameters remain in game logic code
- All asset references are valid
- No new Required Fix-level issues introduced by the fixes

### Output
path: P4-production/batch-{N}/{story-id}/S04-dev-story.md
sections:
  - Fix Report (finding ID → change made)
  - Acceptance Criteria Status (all must pass)
  - Test Results
  - Remaining Issues (if any)

---

## S05: QA Story

### Required
false

### Skip Condition
No test plan defined for story, or no test infrastructure available.

### Goal
Run focused QA on the implemented story: test suite execution, gameplay behavior validation, and balance verification.

### Read Scope
- required: current story spec
- required: P4-production/batch-{N}/{story-id}/S04-dev-story.md
- required: P3-technical/DELIVERABLE.md (test-designs.md reference)

### Thesis
role: qa-engineer
instruction: |
  Execute comprehensive QA for this story:
  - **Test suite execution**: run all tests (unit, component, integration) for this story. Report pass/fail for each test
  - **Gameplay behavior validation**: for gameplay stories, execute the play-test criteria:
    - Set up the game state described in preconditions
    - Execute the player action sequence
    - Verify the expected player-observable outcomes
  - **Balance verification**: if this story affects game balance (economy, progression, difficulty), run relevant test cases from test-designs.md:
    - Economy: verify resource flow stays within bounds
    - Progression: verify gates open/close correctly
    - Difficulty: verify challenge scales as designed
  - **Boundary testing**: test extreme inputs for this story's functionality (zero, one, max values, rapid repeated inputs)
  - **State transition testing**: test interactions with other game states (what happens if this feature activates during a scene transition, during save, during pause)

  Produce a QA report with pass/fail per test, any unexpected behaviors discovered, and a recommendation (PASS or FAIL with reasons).

### Antithesis
role: qa-verifier
instruction: |
  Verify the QA process was thorough:
  - **Test completeness**: were all tests from the story's test plan executed? Were all relevant test cases from test-designs.md run?
  - **Gameplay test fidelity**: do gameplay behavior test results describe what actually happened in player-observable terms? Or do they just report code-level pass/fail?
  - **Balance test coverage**: for stories affecting balance, were the specific exploit vectors from test-designs.md tested (arbitrage, duplication, overflow)?
  - **Edge case coverage**: were boundary conditions tested? Were state transition edge cases tested?
  - **Failure reproduction**: for any failed test, is the failure reproducible? Is the root cause identified?

  If QA coverage is insufficient, specify which tests must be added before the story can proceed.

### Convergence
target: ac-fulfillment
model: standard
weight: medium

### Pass Criteria
- All tests from the story's test plan pass
- Gameplay behavior validation produces expected player-observable outcomes
- Balance verification shows no values outside designed bounds (if applicable)
- Boundary tests pass without crashes or undefined behavior
- QA recommendation is PASS (or FAIL with specific, actionable reasons)

### Output
path: P4-production/batch-{N}/{story-id}/S05-qa-story.md
sections:
  - Test Execution Results (pass/fail per test)
  - Gameplay Behavior Validation
  - Balance Verification (if applicable)
  - Boundary Test Results
  - Unexpected Behaviors
  - QA Recommendation (PASS/FAIL)

---

## S06: Review Story

### Required
true

### Goal
Post-QA adversarial review: thesis attacks the implementation to find defects, antithesis judges whether findings are genuine issues.

**This step uses the INVERTED convergence model: thesis is the attacker, antithesis is the judge.**

on_fail: S04-dev-story

### Read Scope
- required: current story spec
- required: P4-production/batch-{N}/{story-id}/S05-qa-story.md
- required: P3-technical/DELIVERABLE.md (architecture, performance budget)

### Thesis
role: adversarial-reviewer
instruction: |
  Attack the implementation to find defects that QA missed:
  - **Performance budget**: does this story's implementation stay within the frame time and memory budgets from the architecture? Estimate the cost of this story's runtime operations (per-frame calculations, memory allocations, asset memory)
  - **Shared game state races**: does this implementation access shared mutable game state? If so, what happens when another system modifies that state concurrently? Check for:
    - Multiple systems reading/writing the same game state in the same frame
    - Event handlers that modify state another handler reads
    - Async operations (asset loading, save) that access game state without synchronization
  - **Platform constraint compliance**: does the implementation respect target platform constraints? Check:
    - Memory allocation patterns (allocations per frame, garbage generation)
    - Touch target sizes for mobile
    - Input latency for action games
    - Thread safety for console platforms
  - **Semantic consistency**: does this implementation use the same terminology, parameter names, and data types as other implemented stories? Flag divergences that will cause integration bugs
  - **Edge case attacks**: try to break the implementation with unusual but valid inputs — empty strings, Unicode, extreme values, rapid state changes, simultaneous conflicting inputs
  - **Integration surface**: what assumptions does this code make about other stories' implementations? Are those assumptions documented or just hoped for?

  Classify findings:
  - CRITICAL: will cause crashes, data loss, or security issues
  - MAJOR: will cause visible bugs or performance problems
  - MINOR: code quality or maintainability concern

### Antithesis
role: review-judge
instruction: |
  Judge whether each finding from the adversarial review is a genuine issue:
  - **Finding validity**: is each finding a real problem, or is it theoretical/unlikely? A finding is valid if it can be triggered by normal gameplay or foreseeable edge cases
  - **Severity accuracy**: is the severity classification correct? Verify CRITICAL findings are genuinely crash/data-loss risks, not just code style preferences labeled as critical
  - **Performance claims**: are performance budget claims backed by concrete estimates, or are they speculation? Verify frame-time estimates are based on actual operation costs, not intuition
  - **Race condition plausibility**: for shared state race findings, can the race actually occur given the game's execution model? (e.g., single-threaded game loops don't have true race conditions, but frame-ordering issues are still valid)
  - **Platform constraint relevance**: are platform constraint findings relevant to the actual target platform, or generic concerns?
  - **False positive identification**: identify findings that are technically correct but practically irrelevant (e.g., micro-optimization suggestions for code that runs once at startup)

  For each finding, render a verdict: VALID (must fix), DEFERRED (real but can fix later), or DISMISSED (not a real issue) with rationale.

  If any VALID finding exists with CRITICAL or MAJOR severity → step result is FAIL → story returns to S04-dev-story.
  If all findings are DEFERRED or DISMISSED → step result is PASS.

### Convergence
target: issue-verdict
model: inverted
weight: heavy

### Pass Criteria
- All CRITICAL and MAJOR findings are judged VALID, DEFERRED, or DISMISSED with rationale
- No CRITICAL finding is DISMISSED without concrete justification
- Performance estimates reference the actual frame budget from the architecture
- Race condition analysis accounts for the game's actual execution model
- PASS/FAIL verdict is rendered with clear reasoning

### Output
path: P4-production/batch-{N}/{story-id}/S06-review-story.md
sections:
  - Findings (ID, description, severity, category)
  - Verdicts (finding ID → VALID/DEFERRED/DISMISSED with rationale)
  - Performance Assessment
  - Integration Risk Assessment
  - Step Result (PASS/FAIL)

---

## S07: E2E QA

### Required
false

### Skip Condition
Project has 2 or fewer stories with minimal cross-story integration risk.

### Goal
Run end-to-end QA across the entire sprint batch: integration testing, play-testing verification, performance profiling, and platform certification checks.

### Read Scope
- required: P3-technical/DELIVERABLE.md (test-designs.md, test-strategy.md, architecture)
- required: P4-production/S01-sprint-planning.md
- required: P4-production/S02-scaffold.md
- required: All S06-review-story.md files from the current batch

### Thesis
role: e2e-qa-engineer
instruction: |
  Execute end-to-end QA across the entire batch of merged stories:
  - **Integration testing**: run all integration tests defined in test-strategy.md. Focus on cross-story interactions — do stories that were developed in parallel integrate correctly when merged?
  - **Play-testing verification**: execute end-to-end gameplay scenarios that span multiple stories:
    - Core loop playthrough: can the player complete one full cycle of the core loop using the implemented features?
    - Progression flow: can the player progress from the starting state through all implemented progression gates?
    - Economy flow: can the player earn, spend, and manage all implemented resources without breaking invariants?
  - **Performance profiling**: measure actual runtime performance against the architecture's performance budget:
    - Frame rate: average and minimum FPS during typical gameplay
    - Memory: peak memory usage by category
    - Load times: scene transition times
    - Input latency: time from input to visual response
  - **Platform certification checks**: verify the build meets target platform requirements:
    - Console: TRC/XR compliance for relevant requirements (suspend/resume, save data handling, user switching)
    - Mobile: APK/IPA size, permissions, background behavior, thermal throttling behavior
    - PC: resolution scaling, windowed/fullscreen, input device switching
  - **Regression check**: verify that features from prior batches still work correctly after this batch's merge

  Produce a comprehensive E2E QA report with go/no-go recommendation for the batch.

### Antithesis
role: e2e-verifier
instruction: |
  Verify the E2E QA process was thorough:
  - **Integration coverage**: were all cross-story interaction points tested? Are there story pairs that interact but weren't integration-tested?
  - **Play-test scenario coverage**: do play-test scenarios cover the primary player journey for all implemented features? Are there implemented features with no play-test scenario?
  - **Performance measurement validity**: are performance measurements taken under realistic conditions (representative content, target hardware)? Are measurements reproducible?
  - **Platform check completeness**: for the target platform, are all mandatory certification requirements checked? List any certification requirements that were not verified
  - **Regression thoroughness**: were prior batch features tested with the same rigor as the current batch, or just smoke-tested?
  - **Deferred items**: are there known issues from S06 reviews that were DEFERRED? Are any of them now manifesting as E2E failures?

  If E2E QA reveals failures, classify each as:
  - BATCH-BLOCKING: this batch cannot ship without fixing this
  - NEXT-BATCH: can be addressed in the next batch
  - KNOWN-ISSUE: documented, accepted risk

### Convergence
target: output-quality
model: standard
weight: heavy

### Pass Criteria
- All integration tests pass
- Core loop playthrough completes without crashes or broken state
- Performance metrics are within budget (or deviations are documented and accepted)
- Platform certification checks pass for all mandatory requirements
- No regressions from prior batches
- Go/no-go recommendation is rendered with evidence

### Output
path: P4-production/S07-e2e-qa.md
sections:
  - Integration Test Results
  - Play-Testing Verification
  - Performance Profile (actual vs. budget)
  - Platform Certification Results
  - Regression Check Results
  - Known Issues and Deferred Items
  - Go/No-Go Recommendation

last_step: true

---

## Sprint Mode Orchestration

MetaAgent orchestrates Production phase using the following loop:

```
1. Execute S01 (Sprint Planning) — produces batch plan
2. Execute S02 (Scaffold) — creates project skeleton
3. For each batch in the sprint plan:
   a. For each story in the batch (PARALLEL, worktree isolation):
      i.   S03: Create Story
      ii.  S04: Dev Story (if S03 review has Required Fixes)
      iii. S05: QA Story
      iv.  S06: Review Story
           - If FAIL → return to S04 with review findings
           - If PASS → story is ready for merge
   b. Merge all PASS stories in dependency order
      - On conflict: spawn conflict-resolver agent
   c. S07: E2E QA for the batch
      - If BATCH-BLOCKING failures: address before next batch
4. After all batches: produce final DELIVERABLE.md
```

### Story Pipeline State Machine

```
S03-create-story → S04-dev-story → S05-qa-story → S06-review-story
                        ↑                              |
                        └──────── on_fail ─────────────┘
```

### Worktree Isolation Rules

- Each story in a batch gets its own git worktree
- Stories CANNOT read each other's worktree changes
- Merge happens only after S06 PASS
- Conflict resolution uses the conflict-resolver agent

---

## Exit Contract

The following must be present in the DELIVERABLE.md:

- Per-story status table (MERGED/BLOCKED/REMAINING)
- QA report: test pass rates, gameplay behavior validation, platform verification
- Remaining work / HALT reasons
