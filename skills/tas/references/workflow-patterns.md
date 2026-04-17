# Workflow Patterns Reference

MetaAgent reads this file during Classify Mode (Phase 2) to select and customize
a workflow template based on the request type and complexity.

## Request Type Classification

Classify the request into one of these types:

| Type | Signals |
|------|---------|
| **implement** | "만들어", "구현", "build", "create", "add", "implement" |
| **design** | "설계", "아키텍처", "design", "architecture", "structure" |
| **review** | "리뷰", "review", "check", "검토", "look at" |
| **refactor** | "리팩토링", "refactor", "clean up", "개선", "restructure" |
| **analyze** | "분석", "analyze", "investigate", "why", "원인", "조사" |
| **general** | Doesn't fit above — use adaptive workflow |

## Complexity → Step Count

Pick step count adaptively based on the request's actual blast radius, not keyword surface.

| Complexity | Indicators | Step count |
|-----------|-----------|------------|
| `simple` | Single function, narrow modification, pure question/analysis, ≤30 LOC change | **1** |
| `medium` | Multi-file change, new feature in existing module, design with one dominant concern | **2-3** |
| `complex` | New subsystem, user-facing behavior, wide integration, production-critical path | **4** |

"add a button that posts to /api/x" is NOT simple — it touches UI, API wiring, and state.
Err on the side of complex when the request implies user-facing behavior.

---

## Canonical 4-Step Flow (implement / refactor at complex)

The default flow for complex implementation/refactoring work:
**기획(Plan) → 구현(Implement) → 검증(Verify) → 테스트(Test)**

| Step | Goal | Default Pass Criteria |
|------|------|-----------------------|
| **1. 기획 (Plan)** | Determine approach, identify affected files, define interfaces, surface constraints | - Approach addresses all stated requirements<br>- Existing patterns and conventions in the project identified<br>- Affected files enumerated<br>- No unnecessary complexity or speculative abstractions<br>- Dependencies and risks surfaced |
| **2. 구현 (Implement)** | Write the code per the 기획 output | - Code compiles/parses without errors<br>- All requirements from 기획 addressed<br>- Follows project conventions (read neighboring files)<br>- No scope creep or dead code<br>- Standard/idiomatic patterns used<br>- Self-assessment against 기획's pass criteria |
| **3. 검증 (Verify)** — *inverted* | Find every real defect before tests run | - Semantic consistency (same concept, same meaning)<br>- Behavioral consistency across all code paths<br>- Compositional integrity (A → B sound for all inputs)<br>- Value flow soundness (no NaN/Infinity/type mismatch intermediates)<br>- Defensive measures applied before value consumption<br>- 0 blockers = PASS, ≥1 blockers = FAIL (→ retry 구현) |
| **4. 테스트 (Test)** — *inverted* | Prove correctness through execution — static + dynamic where applicable | - Static: unit tests written and passing<br>- Static: type checks pass, lint clean<br>- Dynamic (web): Playwright CLI via Bash (`npx playwright test`) + screenshots + UI/UX evaluation<br>- Dynamic (backend/CLI): integration tests run, output verified<br>- Coverage adequate for the scope of changes<br>- PASS (all green + coverage adequate) or FAIL (→ retry 구현) |

### 검증 vs 테스트 Boundary

- **검증** is **static code analysis** — reading the diff and reasoning about correctness.
  No execution required. Catches design flaws, logic errors, composition issues.
- **테스트** is **execution-based** — running the code (unit, integration, dynamic).
  For web projects, MUST include browser-based UI/UX evaluation via Playwright CLI (Bash).

Both use the **inverted convergence model**: thesis attacks/executes, antithesis judges.

### Dynamic Testing by Domain

| Domain | 테스트 Requirements |
|--------|---------------------|
| `web-frontend` | Unit tests + Playwright navigation + screenshots + visual/behavioral evaluation |
| `web-backend` / `api` | Unit tests + integration tests hitting actual endpoints |
| `cli` | Unit tests + subprocess execution tests with real args |
| `library` | Unit tests + usage-example verification |
| `mobile` | Unit tests + (platform-specific) emulator smoke test if tooling available |
| `monorepo` | Per-package unit tests + cross-package integration tests + build isolation check (each package builds independently) |
| `data-pipeline` | Unit tests on transform functions + idempotency check (run twice, same result) + schema validation against sample data |
| `iac-infra` | `terraform validate` / `terraform plan` (or equivalent) + lint (`tflint`, `checkov`) + dry-run showing expected resource changes |
| `unknown` | Unit tests + whatever execution the project's build tooling provides |

For web projects, Playwright CLI via Bash (`npx playwright test`, `npx playwright screenshot`)
is the dynamic verification channel — Playwright MCP tools are not available in dialectic
agent sessions. ThesisAgent spins up the dev server and runs tests/captures screenshots
via Bash; AntithesisAgent evaluates the results.

---

## Adaptive Variants by Complexity

### Simple (1 step) — all request types

Collapse into a single step combining the relevant concerns. Example for `implement` simple:

| Step | Goal | Pass Criteria |
|------|------|---------------|
| 1. Combined | Implement and self-verify | - Code meets requirement<br>- Follows conventions<br>- No NaN/Infinity/compositional gaps<br>- Boundary trace included in self-assessment |

### Medium (2-3 steps)

Pick the subset of the canonical flow most relevant to the request:

- `implement` medium: 기획 → 구현 → 검증 (테스트 omitted or folded into 검증)
- `refactor` medium: 기획(현황+전략) → 구현 → 검증
- `design` medium: 요구사항 → 설계 → 검토 (no 구현/테스트)

Use judgment — skip stages that add no value for the specific request.

---

## Non-Implementation Templates

For requests that don't produce code.

### Architecture (design)

| Step | Goal | Default Pass Criteria |
|------|------|-----------------------|
| 1. Requirements | Extract and clarify requirements | - All explicit requirements captured<br>- Implicit requirements surfaced<br>- Constraints identified |
| 2. Design | Propose architecture with rationale | - Design addresses all requirements<br>- Trade-offs explicitly stated<br>- Alternatives considered and rejected with reasoning |
| 3. Trade-off Review | Stress-test the design | - Scalability implications addressed<br>- Failure modes identified<br>- Migration/adoption path clear |

### Code Review

| Step | Goal | Default Pass Criteria |
|------|------|-----------------------|
| 1. Analysis | Understand code changes and context | - All changed files identified<br>- Change purpose understood<br>- Surrounding context captured |
| 2. Issues | Identify bugs, risks, quality concerns | - Each issue has specific file:line reference<br>- Severity categorized (critical/major/minor)<br>- No false positives from misunderstanding |
| 3. Improvements | Propose concrete fixes | - Each improvement is actionable<br>- Improvements address identified issues<br>- No suggestions contradicting project conventions |

### Analysis

| Step | Goal | Default Pass Criteria |
|------|------|-----------------------|
| 1. Scope | Define investigation boundaries | - Investigation boundaries clear<br>- Key files/systems identified<br>- Success criteria defined |
| 2. Investigation | Gather evidence and trace causes | - Multiple sources consulted<br>- Evidence cited with specific references<br>- Alternative hypotheses considered |
| 3. Conclusions | Synthesize findings | - Conclusions supported by evidence<br>- Confidence level stated<br>- Recommended next steps provided |

### General (Adaptive)

For requests that don't fit a template:
1. Break request into 2-4 logical steps
2. For each step, define 3-5 verifiable pass criteria
3. Order steps by dependency

---

## Pass Criteria Authoring Guide

Good pass criteria are:

- **Verifiable**: AntithesisAgent can objectively evaluate against it
- **Specific**: No ambiguity about what passing means
- **Relevant**: Directly tied to the step goal
- **Countable**: 3-6 criteria per step

## Workflow Customization

MetaAgent may customize templates:
- **Collapse steps**: Simple requests → fewer steps
- **Add criteria**: Domain-specific requirements (e.g., accessibility for web-frontend)
- **Inject testing strategy**: For 테스트 step, inject domain-specific dynamic test requirements

Steps do not have round caps. The dialectic loop continues until genuine convergence
or a HALT condition. Within-iteration FAIL → 구현 jumps are governed by
`loop_policy.persistent_failure_halt_after` (default 3 consecutive same-blocker
FAILs → HALT the iteration).

---

## Iteration Support (loop_count > 1)

Focus angle selection, lessons learned extraction, and early-exit logic are defined in
`meta.md` Phase 2b–2g. Lesson entry schema is in `workspace-convention.md`.
