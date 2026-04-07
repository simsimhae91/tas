# Game Dev Phase Overview & Inter-Phase Contracts

Phase-level overview and deliverable contracts for the Game Dev pipeline.
Step-by-step workflow definitions are in `workflows/gamedev/P{N}-*.md`.

---

## Phase Summary

| Phase | Goal | Steps | Workflow File |
|-------|------|-------|---------------|
| 1. Preproduction | Game concept, domain/market/tech research | 6 | `P1-preproduction.md` |
| 2. Design | GDD, narrative, PRD, UX specification | 5 | `P2-design.md` |
| 3. Technical | Game architecture, stories, test design | 6 | `P3-technical.md` |
| 4. Production | Sprint execution, code review, QA | 7 | `P4-production.md` |

---

## Inter-Phase Deliverable Contracts

These define what MUST flow between phases via `DELIVERABLE.md`.
MetaAgent validates these during phase transitions.

### Phase 1 → Phase 2

| Required | Field | Source Step |
|----------|-------|------------|
| yes | Core loop definition | S02 Game Brief |
| yes | Experience pillars | S02 Game Brief |
| yes | Target audience + platform | S01 Game Concept Enrichment |
| yes | Tech recommendation | S05 Tech Research |
| yes | Risk register (top 3) | S06 Create Summary |
| no | Feature priority matrix | S01 Game Concept Enrichment |

### Phase 2 → Phase 3

| Required | Field | Source Step |
|----------|-------|------------|
| yes | GDD summary + system count | S01 GDD |
| yes | Requirements matrix | S05 Validate PRD |
| yes | UX flow summary | S04 Create UX |
| yes | Narrative integration points | S02 Narrative Design |
| no | Deferred items | S05 Validate PRD |

### Phase 3 → Phase 4

| Required | Field | Source Step |
|----------|-------|------------|
| yes | Architecture summary | S01 Game Architecture |
| yes | Story index + dependencies | S02 Epics & Stories |
| yes | Parallel execution plan | S02 Epics & Stories |
| yes | Per-story specs | S02 (stories/*.md) |
| yes | Project context | S04 Project Context |
| no | Test strategy + designs | S05 Test Framework, S06 Test Design |
