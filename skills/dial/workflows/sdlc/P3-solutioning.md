---
phase: P3-solutioning
pipeline: sdlc
execution_mode: sequential
---

# P3: Solutioning

Produce technical architecture and implementation stories ready for development.

---

## S01: Architecture

### Required
true

### Goal
Design system architecture from Phase 2 PRD requirements, producing a component-level design with data model, API contracts, and infrastructure plan.

### Read Scope
- required: P2-planning/DELIVERABLE.md

### Thesis
role: architect
instruction: |
  Read the Phase 2 deliverable and design the system architecture:
  1. **System overview** — high-level diagram (mermaid or text) showing major components and their interactions.
  2. **Component design** — for each component:
     - Name and responsibility (single responsibility principle)
     - Public interface (key functions/methods/endpoints)
     - Dependencies on other components
     - Technology choice (from Phase 1 recommendation)
  3. **Data model** — entities, relationships, key attributes. Include:
     - Entity-relationship description (or mermaid ER diagram)
     - Which component owns each entity
     - Data flow between components (which data crosses boundaries)
  4. **API contracts** — for each inter-component boundary:
     - Endpoint or function signature
     - Request/response shapes
     - Error responses
  5. **Infrastructure** — hosting, deployment, CI/CD approach. Keep proportional to project scope.
  6. **Cross-cutting concerns** — authentication, authorization, logging, error handling approach.
  7. **Open questions resolved** — address open questions from Phase 2 DELIVERABLE.md.

  Every P0 requirement from Phase 2 must be addressable by the architecture. If a requirement cannot be addressed, flag it as a design constraint issue.

### Antithesis
role: soundness-verifier
instruction: |
  Verify the architecture for soundness and requirement coverage:
  - Can every P0 requirement from Phase 2 be implemented within this architecture? Trace each P0 requirement to a specific component. Flag any unreachable requirements.
  - Do components have clear boundaries? Are there components with overlapping responsibilities?
  - Is there a single point of failure (SPOF)? If the architecture is simple enough that SPOF is acceptable, that is fine — but it must be acknowledged.
  - Does the data model support all features? Trace at least 2 P0 features through the data model to verify fields and relationships are sufficient.
  - Are API contracts complete? Do they include error responses, not just happy paths?
  - Does the infrastructure plan match the recommended tech stack from Phase 1?
  - Are cross-cutting concerns addressed consistently, or does each component handle them differently?

### Convergence
target: output-quality
model: standard
weight: heavy

### Pass Criteria
- Every P0 requirement traces to a specific component
- Components have non-overlapping responsibilities with clear boundaries
- Data model supports at least 2 traced P0 feature flows end-to-end
- API contracts include error responses
- No unacknowledged single points of failure
- Phase 2 open questions are addressed

### Output
path: P3-solutioning/S01-architecture.md
sections:
  - System Overview
  - Component Design
  - Data Model
  - API Contracts
  - Infrastructure
  - Cross-Cutting Concerns
  - Open Questions Resolved

---

## S02: Epic and Story Breakdown

### Required
true

### Goal
Decompose the architecture into implementable epics and stories following story-spec-format.md, with dependency ordering and parallel execution groups.

### Read Scope
- required: P2-planning/DELIVERABLE.md
- required: P3-solutioning/S01-architecture.md

### Thesis
role: story-writer
instruction: |
  Break down the architecture into epics and stories:
  1. **Epic inventory** — one epic per major feature area or architectural component. Each epic:
     - Name and description
     - Which P0/P1 requirements it covers
     - Estimated total LOC
  2. **Stories** — break each epic into stories following the format in `references/story-spec-format.md`. Each story must:
     - Have a unique ID (e.g., AUTH-001, DATA-002)
     - Be independently implementable (can be built and tested in isolation)
     - Estimate at or below 300 LOC (split L-complexity stories)
     - List exact files to create or modify
     - Include acceptance criteria (2-4 verifiable conditions)
     - Include a test plan (2-3 specific test cases)
     - Specify dependencies on other stories (by story ID)
  3. **Dependency graph** — show which stories depend on which. No circular dependencies.
  4. **Parallel groups** — batch stories into groups where all stories in a group are independent of each other AND modify disjoint file sets.
  5. **Execution order** — list parallel groups in dependency order (group 1 runs first, group 2 after group 1 completes, etc.)

  Every P0 requirement must be traced to at least one story. P1 requirements should be included if within project scope.

### Antithesis
role: granularity-verifier
instruction: |
  Verify the story breakdown for granularity, independence, and traceability:
  - Is every story independently implementable? Can it be built and tested without waiting for unreleased stories (beyond declared dependencies)?
  - Are any stories over 300 LOC estimate? Flag for splitting.
  - Do all P0 requirements trace to at least one story? List any untraced P0 requirements.
  - Are story dependencies explicit and complete? Look for hidden dependencies: Story A modifies a file that Story B reads, but no dependency is declared.
  - Within each parallel group: do any two stories modify the same file? This would cause merge conflicts.
  - Does each story have verifiable acceptance criteria (not vague "works correctly")?
  - Does each story have a test plan with specific inputs and expected outputs?
  - Are story IDs unique across all epics?

### Convergence
target: output-quality
model: standard
weight: heavy

### Pass Criteria
- Every P0 requirement traces to at least one story
- No story exceeds 300 LOC estimate
- Stories within each parallel group have disjoint file sets
- No circular dependencies in the dependency graph
- Every story has verifiable acceptance criteria and a test plan
- Story IDs are unique

### Output
path: P3-solutioning/S02-epic-story-breakdown.md
sections:
  - Epic Inventory
  - Story Specs (per story, following story-spec-format.md)
  - Dependency Graph
  - Parallel Groups
  - Execution Order

---

## S03: Readiness Check
last_step: true

### Required
false

### Skip Condition
Small project with 3 or fewer stories where readiness is self-evident.

### Goal
Validate that the stories are implementation-ready: cross-check against architecture, verify test plans, and confirm parallel groups are truly independent.

### Read Scope
- required: P3-solutioning/S01-architecture.md
- required: P3-solutioning/S02-epic-story-breakdown.md

### Thesis
role: cross-checker
instruction: |
  Perform a readiness check on the stories against the architecture:
  1. **Architecture alignment** — for each story, verify the files it creates/modifies match the architecture's component structure. Flag any story that references files or components not in the architecture.
  2. **Test plan validation** — for each story, verify the test plan:
     - Tests cover acceptance criteria (not just happy paths)
     - Test inputs are specific (not "various inputs")
     - Expected outputs are deterministic
  3. **Dependency verification** — re-trace the dependency graph:
     - Every story's dependencies are in earlier parallel groups
     - No hidden dependencies (file overlap between stories in the same group)
  4. **Integration test strategy** — define how stories integrate after each batch:
     - Which cross-story interactions need testing
     - Integration test scenarios (at least one per batch boundary)
  5. **Summary table** — story index with: ID, epic, parallel group, estimated LOC, complexity, file count.

### Antithesis
role: completeness-verifier
instruction: |
  Verify the readiness check caught everything:
  - Does every story have both acceptance criteria AND a test plan? Flag any story missing either.
  - Are parallel groups truly independent? Re-check file sets for overlap within each group.
  - Does the integration test strategy cover cross-story data flow? (e.g., if Story A creates entities that Story B queries, is there an integration test for that?)
  - Are there any stories where the technical spec is too vague for standalone implementation? (A developer should be able to implement the story from its spec alone.)
  - Does the summary table match the actual story details? (Correct LOC, correct group assignment)
  - Is the execution order achievable? (No group depends on a later group)

### Convergence
target: output-quality
model: standard
weight: medium

### Pass Criteria
- Every story has acceptance criteria AND a test plan
- Parallel groups have no file overlap
- Integration test strategy covers at least one scenario per batch boundary
- Summary table is accurate and consistent with story details
- No story references files or components outside the architecture

### Output
path: P3-solutioning/DELIVERABLE.md
sections:
  - Architecture Summary (components, key interfaces, data model)
  - Story Index (ID, epic, group, LOC, complexity)
  - Parallel Execution Plan (batches with stories)
  - Per-Story Estimated LOC and Complexity
  - Integration Test Strategy
  - Readiness Verdict

---

## Exit Contract

DELIVERABLE.md must contain these fields for Phase 4 handoff:

| Field | Required | Description |
|-------|----------|-------------|
| Architecture summary | yes | Components, key interfaces, data model overview |
| Story index with dependency order | yes | All stories with IDs, dependencies, and ordering |
| Parallel execution plan | yes | Batches of independent stories |
| Per-story estimated LOC and complexity | yes | Size estimates for sprint planning |
| Integration test strategy | no | Cross-story test scenarios per batch boundary |
