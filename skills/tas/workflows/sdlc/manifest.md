# SDLC Pipeline Step Manifest

Step metadata for MainOrchestrator. Do NOT open workflow definition files (P{N}-*.md) directly.

---

## P1-analysis
execution: sequential

| Step | Name | Required | Skip Condition |
|------|------|----------|----------------|
| S01 | Idea Enrichment | yes | — |
| S02 | Tech Research | no | Tech stack already specified in request, or single-feature / CLI tool |
| S03 | Domain Analysis | no | Simple, well-known domain, no regulatory concerns |
| S04 | Create Brief | yes | — |

## P2-planning
execution: sequential

| Step | Name | Required | Skip Condition |
|------|------|----------|----------------|
| S01 | Create PRD | yes | — |
| S02 | UX Flows | no | No user-facing interface (CLI, backend API, library, data pipeline) |
| S03 | Validate PRD | yes | — |

## P3-solutioning
execution: sequential

| Step | Name | Required | Skip Condition |
|------|------|----------|----------------|
| S01 | Architecture | yes | — |
| S02 | Epic and Story Breakdown | yes | — |
| S03 | Readiness Check | no | 3 or fewer stories where readiness is self-evident |

## P4-implementation
execution: sprint

| Step | Name | Required | Scope | Skip Condition |
|------|------|----------|-------|----------------|
| S01 | Sprint Planning | yes | phase | — |
| S02 | Scaffold | no | phase | Existing project with established structure |
| S03 | Create Story | yes | per-story | — |
| S04 | Dev Story | yes | per-story | — |
| S05 | QA Story | no | per-story | No test plan or test infrastructure available |
| S06 | Review Story | yes | per-story | — |
| S07 | E2E QA | no | phase | 2 or fewer stories with minimal cross-story integration risk |
