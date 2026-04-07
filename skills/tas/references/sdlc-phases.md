# SDLC Phase Overview & Inter-Phase Contracts

Phase-level overview and deliverable contracts for the Software Dev pipeline.
Step-by-step workflow definitions are in `workflows/sdlc/P{N}-*.md`.

---

## Phase Summary

| Phase | Goal | Steps | Workflow File |
|-------|------|-------|---------------|
| 1. Analysis | Understand domain, research feasibility, produce brief | 4 | `P1-analysis.md` |
| 2. Planning | PRD, UX flows, requirements specification | 3 | `P2-planning.md` |
| 3. Solutioning | Architecture, stories, implementation plan | 3 | `P3-solutioning.md` |
| 4. Implementation | Sprint execution, code review, QA | 7 | `P4-implementation.md` |

---

## Inter-Phase Deliverable Contracts

These define what MUST flow between phases via `DELIVERABLE.md`.
MetaAgent validates these during phase transitions.

### Phase 1 → Phase 2

| Required | Field | Source Step |
|----------|-------|------------|
| yes | Project scope (in/out) | S04 Create Brief |
| yes | Personas + use cases | S01 Idea Enrichment |
| yes | Tech recommendation | S02 Tech Research |
| yes | Risk register (top 3) | S04 Create Brief |
| yes | Success metrics | S01 Idea Enrichment |

### Phase 2 → Phase 3

| Required | Field | Source Step |
|----------|-------|------------|
| yes | PRD summary + requirement count | S01 Create PRD |
| yes | Requirements matrix | S03 Validate PRD |
| yes | UX flow summary | S02 UX Flows |
| no | Deferred items | S03 Validate PRD |
| no | Open questions | S03 Validate PRD |

### Phase 3 → Phase 4

| Required | Field | Source Step |
|----------|-------|------------|
| yes | Architecture summary | S01 Architecture |
| yes | Story index + dependencies | S02 Epic & Story Breakdown |
| yes | Parallel execution plan | S02 Epic & Story Breakdown |
| yes | Per-story specs | S02 (stories/*.md) |
| no | Integration test strategy | S03 Readiness Check |
