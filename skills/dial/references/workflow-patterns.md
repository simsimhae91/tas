# Workflow Patterns Reference

MetaAgent reads this file during Phase 1 (Workflow Design) to select and customize
a workflow template based on the request type.

## Request Type Classification

Classify the request into one of these types:

| Type | Signals |
|------|---------|
| **Implementation** | "만들어", "구현", "build", "create", "add", "implement" |
| **Architecture** | "설계", "아키텍처", "design", "architecture", "structure" |
| **Code Review** | "리뷰", "review", "check", "검토", "look at" |
| **Refactoring** | "리팩토링", "refactor", "clean up", "개선", "restructure" |
| **Analysis** | "분석", "analyze", "investigate", "why", "원인", "조사" |
| **General** | Doesn't fit above — use adaptive workflow |

---

## Workflow Templates

### Implementation

Goal: Produce working code that meets requirements.

| Step | Goal | Default Pass Criteria |
|------|------|-----------------------|
| 1. Design | Determine approach, identify affected files, define interfaces | - Approach addresses all requirements<br>- Existing patterns/conventions identified<br>- No unnecessary complexity |
| 2. Implement | Write the code | - Code compiles/parses without errors<br>- All requirements addressed<br>- Follows project conventions<br>- No scope creep or dead code<br>- Standard/idiomatic patterns used |
| 3. Verify | Validate correctness and design quality | - Consistent semantics across all appearances<br>- All code paths behave consistently<br>- Type signatures accept all reasonable inputs<br>- Domain-standard patterns included<br>- Names/messages accurately describe behavior<br>- Numeric computations produce valid intermediates for all inputs — trace at least one boundary set<br>- Defensive measures applied before value consumption |

**Simplification**: Simple requests (single function, small change) → collapse to 1 step with combined criteria.

### Architecture

Goal: Produce a sound technical design with clear trade-offs.

| Step | Goal | Default Pass Criteria |
|------|------|-----------------------|
| 1. Requirements | Extract and clarify requirements | - All explicit requirements captured<br>- Implicit requirements surfaced<br>- Constraints identified |
| 2. Design | Propose architecture with rationale | - Design addresses all requirements<br>- Trade-offs explicitly stated<br>- Alternatives considered and rejected with reasoning |
| 3. Trade-off Review | Stress-test the design | - Scalability implications addressed<br>- Failure modes identified<br>- Migration/adoption path clear |

### Code Review

Goal: Find real issues and propose actionable improvements.

| Step | Goal | Default Pass Criteria |
|------|------|-----------------------|
| 1. Analysis | Understand code changes and context | - All changed files identified<br>- Change purpose understood<br>- Surrounding context captured |
| 2. Issues | Identify bugs, risks, quality concerns | - Each issue has specific file:line reference<br>- Severity categorized (critical/major/minor)<br>- No false positives from misunderstanding |
| 3. Improvements | Propose concrete fixes | - Each improvement is actionable<br>- Improvements address identified issues<br>- No suggestions contradicting project conventions |

### Refactoring

Goal: Improve code structure while preserving behavior.

| Step | Goal | Default Pass Criteria |
|------|------|-----------------------|
| 1. Current State | Analyze what exists and why | - Problem areas identified with evidence<br>- Current behavior documented<br>- Dependencies mapped |
| 2. Plan | Define refactoring strategy | - Step-by-step plan with clear order<br>- Each step preserves behavior<br>- Risk areas identified |
| 3. Execute | Perform the refactoring | - All planned changes applied<br>- No behavior changes (unless intended)<br>- Code cleaner by stated metrics |
| 4. Regression Check | Verify nothing broke | - All original functionality preserved<br>- No new warnings or errors<br>- Integration points still work |

### Analysis

Goal: Answer a question or investigate an issue with evidence.

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
- **Add criteria**: Domain-specific requirements
- **Add dependencies**: `depends_on` links between steps

Note: Steps do not have iteration caps. The dialectic loop continues until genuine convergence or a HALT condition is reached.

---

## Pipeline Phase Templates

For multi-phase project workflows, see the pipeline-specific reference files:
- **Software Dev (SDLC)**: `sdlc-phases.md` — Analysis → Planning → Solutioning → Implementation
- **Game Dev**: `gamedev-phases.md` — Preproduction → Design → Technical → Production
