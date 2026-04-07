---
phase: P2-planning
pipeline: sdlc
execution_mode: sequential
---

# P2: Planning

Produce a PRD and UX flows that fully specify what to build.

---

## S01: Create PRD

### Required
true

### Goal
Write a Product Requirements Document from the Phase 1 brief, covering functional and non-functional requirements with priority levels and traceability to personas.

### Read Scope
- required: P1-analysis/DELIVERABLE.md

### Thesis
role: prd-writer
instruction: |
  Read the Phase 1 deliverable and produce a PRD:
  1. **Functional requirements** — for every in-scope feature, write specific requirements. Each requirement must have:
     - Unique ID (e.g., FR-001)
     - Description (what the system must do, not how)
     - Priority (P0 = must-have for MVP, P1 = should-have, P2 = nice-to-have)
     - Source persona(s) — which persona needs this
     - Acceptance criteria — 2-3 verifiable conditions for "done"
  2. **Non-functional requirements** — performance, security, accessibility, scalability, reliability. Each with:
     - Unique ID (e.g., NFR-001)
     - Category
     - Measurable target (tied to success metrics from Phase 1 where applicable)
     - Priority
  3. **Constraints** — technology constraints (from Phase 1 tech recommendation), business constraints, timeline constraints.
  4. **Assumptions** — carry forward from Phase 1, add any new planning-phase assumptions.
  5. **Out of scope** — carry forward from Phase 1 brief.

  Every P0 requirement must trace to a persona need and a feature from Phase 1. Do not invent requirements that are not grounded in the brief.

### Antithesis
role: completeness-verifier
instruction: |
  Verify the PRD for completeness and internal consistency:
  - Does every in-scope feature from Phase 1 have at least one requirement? List any uncovered features.
  - Are P0 requirements genuinely must-have for MVP, or are nice-to-haves inflated?
  - Do any requirements contradict each other? (e.g., "offline-first" vs "real-time sync" without reconciliation)
  - Does every functional requirement have verifiable acceptance criteria, or are some vague ("works well", "intuitive")?
  - Are non-functional requirements measurable? Reject any without a numeric target.
  - Do constraints align with the Phase 1 technology recommendation?
  - Are there requirements that no persona needs? Flag orphan requirements.

### Convergence
target: output-quality
model: standard
weight: heavy

### Pass Criteria
- Every in-scope feature from Phase 1 maps to at least one requirement
- All P0 requirements have verifiable acceptance criteria
- Non-functional requirements include measurable targets
- No contradictions between requirements
- No orphan requirements (every requirement traces to a persona)
- Requirement IDs are unique and consistent

### Output
path: P2-planning/S01-create-prd.md
sections:
  - Functional Requirements
  - Non-Functional Requirements
  - Constraints
  - Assumptions
  - Out of Scope

---

## S02: UX Flows

### Required
false

### Skip Condition
Project has no user-facing interface (CLI tool, backend API, library, data pipeline).

### Goal
Design user experience flows for each core feature, covering all personas with both happy paths and error paths.

### Read Scope
- required: P1-analysis/DELIVERABLE.md
- required: P2-planning/S01-create-prd.md

### Thesis
role: ux-designer
instruction: |
  Design UX flows based on the PRD requirements and Phase 1 personas:
  1. **Flow inventory** — list every distinct user flow needed. Group by feature area.
  2. **Primary flows** (one per P0 feature at minimum) — for each flow:
     - Flow name and owning persona(s)
     - Entry point (how the user arrives)
     - Step-by-step screens/states (use text descriptions or mermaid sequence diagrams)
     - Happy path: normal completion
     - Error paths: at least one error/edge case per flow (e.g., invalid input, network failure, permission denied)
     - Exit point (where the user ends up)
  3. **Screen inventory** — list all unique screens/views referenced across flows.
  4. **Navigation map** — how screens connect (which screen leads to which).
  5. **Interaction patterns** — common patterns used across flows (e.g., form validation approach, loading states, empty states, confirmation dialogs).

  Flows must cover ALL personas from Phase 1. If a persona has no unique flow, explain why they share flows with another persona.

### Antithesis
role: coverage-verifier
instruction: |
  Verify UX flows for coverage and usability:
  - Does every persona have at least one flow where they are the primary actor? Flag any persona with zero flows.
  - Does every P0 requirement from the PRD have a corresponding UX flow? List uncovered P0 requirements.
  - Does every flow include at least one error path? Flag happy-path-only flows.
  - Are there dead-end screens (screens with no exit path)?
  - Does the screen inventory match what the flows actually reference? Flag phantom screens (listed but never used) or missing screens (used but not listed).
  - Do the interaction patterns cover basic states: loading, empty, error, success?
  - Can a user reach every screen in the inventory from the entry point via the navigation map?

### Convergence
target: output-quality
model: standard
weight: medium

### Pass Criteria
- Every persona has at least one flow as primary actor
- Every P0 requirement has a corresponding UX flow
- Every flow includes at least one error path
- No dead-end screens in the navigation map
- Screen inventory matches flow references (no phantoms, no gaps)

### Output
path: P2-planning/S02-ux-flows.md
sections:
  - Flow Inventory
  - Primary Flows (per feature)
  - Screen Inventory
  - Navigation Map
  - Interaction Patterns

---

## S03: Validate PRD
last_step: true

### Required
true

### Goal
Cross-check the PRD against UX flows, resolve any gaps or inconsistencies, and produce the final validated planning deliverable.

### Read Scope
- required: P2-planning/S01-create-prd.md
- optional: P2-planning/S02-ux-flows.md

### Thesis
role: reconciler
instruction: |
  Cross-check the PRD (S01) against UX flows (S02) and produce a reconciled deliverable:
  1. **Requirements-to-flows matrix** — for every functional requirement, identify which UX flow(s) implement it. Flag any requirement with no flow.
  2. **Flows-to-requirements matrix** — for every UX flow, identify which requirement(s) it fulfills. Flag any flow that serves no requirement (potential scope creep).
  3. **Gap analysis** — list discrepancies:
     - Requirements without flows
     - Flows without requirements
     - Acceptance criteria that conflict with flow behavior
     - Non-functional requirements not addressed by any interaction pattern
  4. **Resolution** — for each gap, propose a resolution: add a missing flow, add a missing requirement, or justify the gap.
  5. **Final PRD summary** — requirement count by priority (P0/P1/P2), organized by feature.
  6. **UX flow summary** — screens per feature, primary path count.
  7. **Deferred items** — anything explicitly removed or deferred during reconciliation.
  8. **Open questions** — technical questions that Phase 3 (Solutioning) must resolve.

  If UX flows (S02) were not produced, skip the requirements-to-flows cross-check. Instead, perform internal PRD consistency validation: check for contradictions between requirements, verify acceptance criteria are verifiable, and confirm priority assignments are justified.

### Antithesis
role: consistency-verifier
instruction: |
  Verify the reconciliation for completeness and correctness:
  - Is the requirements-to-flows mapping truly 1:1 or 1:many? Are any mappings forced (requirement mapped to a flow that does not actually implement it)?
  - Are there orphan requirements — requirements that exist in the PRD but have no flow and no justification for the gap?
  - Are there unspecified screens — screens referenced in flows but not appearing in the screen inventory?
  - Do the gap resolutions actually close the gaps, or do they defer everything?
  - Does the final PRD summary accurately count requirements by priority?
  - Are deferred items genuinely deferrable, or are P0 requirements being silently dropped?
  - Are open questions specific enough for Phase 3 to act on, or are they vague?

### Convergence
target: output-quality
model: standard
weight: heavy

### Pass Criteria
- Every P0 requirement maps to at least one UX flow
- No orphan requirements without justification
- No unspecified screens (every screen in flows is in the inventory)
- Gap resolutions are concrete (not all deferred)
- Requirement count by priority is accurate
- Open questions are specific and actionable

### Output
path: P2-planning/DELIVERABLE.md
sections:
  - PRD Summary (requirement count by priority)
  - Requirements Matrix (requirement ID to feature to persona)
  - UX Flow Summary (screens per feature, primary paths)
  - Gap Analysis and Resolutions
  - Deferred Items
  - Open Questions for Phase 3

---

## Exit Contract

DELIVERABLE.md must contain these fields for Phase 3 handoff:

| Field | Required | Description |
|-------|----------|-------------|
| PRD summary with requirement count | yes | P0/P1/P2 counts organized by feature |
| Requirements matrix | yes | Requirement ID to feature to persona mapping |
| UX flow summary | yes | Screens per feature, primary path count |
| Deferred/out-of-scope items | no | Items explicitly excluded |
| Open questions needing technical resolution | no | Questions Phase 3 must answer |
