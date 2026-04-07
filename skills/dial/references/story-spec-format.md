# Story Spec Format

Standard format for implementation stories produced by Phase 3 (Solutioning).
Each story is a single markdown file in the `stories/` directory.

---

## Template

```markdown
# {EPIC-ID}/{STORY-ID}: {Story Title}

## Metadata

| Field | Value |
|-------|-------|
| Epic | {epic name} |
| Priority | P0 / P1 / P2 |
| Complexity | S / M / L |
| Dependencies | {story IDs this depends on, or "none"} |
| Parallel Group | {batch number for sprint planning} |
| Est. LOC | {rough line count estimate} |
| Files | {list of files to create or modify} |

## Requirement Trace

| Source | Reference |
|--------|-----------|
| PRD | {requirement ID and text} |
| UX Flow | {screen/flow reference} |
| Architecture | {component/API reference} |

## Description

{What this story implements and why. 2-3 sentences max.}

## Acceptance Criteria

- [ ] {Criterion 1 — verifiable, specific}
- [ ] {Criterion 2 — verifiable, specific}
- [ ] {Criterion 3 — verifiable, specific}

## Technical Spec

{Implementation details: data structures, algorithms, API contracts,
 error handling approach. Enough detail for ThesisAgent to implement
 without ambiguity.}

## Test Plan

- [ ] {Test 1: input → expected output}
- [ ] {Test 2: edge case → expected behavior}
- [ ] {Test 3: error case → expected handling}

## Implementation Notes (Thesis Guide)

{Hints for ThesisAgent: which existing patterns to follow, which files
 to reference for conventions, known gotchas.}

## Review Criteria (Antithesis Guide)

{What AntithesisAgent should focus on beyond standard lenses:
 domain-specific concerns, integration risks, performance expectations.}
```

---

## Naming Convention

```
stories/{EPIC-ID}-{STORY-NUMBER}-{slug}.md
```

Examples:
- `stories/AUTH-001-login-flow.md`
- `stories/AUTH-002-session-management.md`
- `stories/DATA-001-schema-setup.md`

## Sizing Guide

| Complexity | Est. LOC | Max Files | Description |
|------------|----------|-----------|-------------|
| S | < 100 | 1-2 | Single function or small component |
| M | 100-300 | 2-5 | Feature module or integration |
| L | 300+ | 5+ | Should be split into smaller stories |

Stories estimated at L complexity should be split. If splitting isn't possible
(e.g., tightly coupled), flag for sequential execution (not parallel).

## Dependency Rules

- Stories in the same parallel group MUST have no dependencies on each other
- A story's dependencies must all be in earlier parallel groups
- Circular dependencies indicate a design problem — resolve in Solutioning
