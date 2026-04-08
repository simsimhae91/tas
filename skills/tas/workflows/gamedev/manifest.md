# GameDev Pipeline Step Manifest

Step metadata for MainOrchestrator. Do NOT open workflow definition files (P{N}-*.md) directly.

---

## P1-preproduction
execution: sequential

| Step | Name | Required | Skip Condition |
|------|------|----------|----------------|
| S01 | Game Concept Enrichment | yes | — |
| S02 | Game Brief | yes | — |
| S03 | Domain Research | no | Team has deep genre expertise, or game jam / rapid prototype |
| S04 | Market Research | no | Non-commercial project (hobby, game jam, educational) |
| S05 | Tech Research | no | Engine/framework already decided (specified in request or team standard) |
| S06 | Create Summary | yes | — |

## P2-design
execution: sequential

| Step | Name | Required | Skip Condition |
|------|------|----------|----------------|
| S01 | Game Design Document | yes | — |
| S02 | Narrative Design | no | Minimal narrative (pure puzzle, racing, arcade, abstract strategy) |
| S03 | Create PRD | yes | — |
| S04 | Create UX | no | Minimal UI (text-based, single-screen, no menu system) |
| S05 | Validate PRD | yes | — |

## P3-technical
execution: sequential

| Step | Name | Required | Skip Condition |
|------|------|----------|----------------|
| S01 | Game Architecture | yes | — |
| S02 | Create Epics and Stories | yes | — |
| S03 | Check Readiness | no | 3 or fewer stories |
| S04 | Project Context | no | Small project where context is self-evident from architecture and stories |
| S05 | Test Framework | no | Prototype phase where formal testing strategy is premature |
| S06 | Test Design | no | Prototype phase, or test framework step was skipped |

## P4-production
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
