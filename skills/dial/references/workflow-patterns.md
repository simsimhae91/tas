# Workflow Patterns Reference

MetaAgent reads this file during Phase 1 (Workflow Design) to select and customize a workflow template based on the user's request type.

## Request Type Classification

Classify the user's `/dial {request}` into one of these types:

| Type | Signals in Request |
|------|-------------------|
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
| 2. Implement | Write the code | - Code compiles/parses without errors<br>- All requirements addressed<br>- Follows project conventions<br>- No scope creep<br>- No dead code or unused artifacts<br>- Standard/idiomatic patterns used |
| 3. Verify | Validate correctness and design quality | - Same concept has consistent semantics across all appearances (params, callbacks, errors)<br>- All code paths for the same operation behave consistently<br>- Type signatures accept all reasonable inputs (not overly restrictive)<br>- Domain-standard patterns included (not deferred as "nice to have")<br>- Names and messages accurately describe actual behavior |

**Simplification**: For simple requests (single function, small change), collapse to 1 step with combined criteria.

### Architecture

Goal: Produce a sound technical design with clear trade-offs.

| Step | Goal | Default Pass Criteria |
|------|------|-----------------------|
| 1. Requirements | Extract and clarify requirements from the request | - All explicit requirements captured<br>- Implicit requirements surfaced<br>- Constraints identified |
| 2. Design | Propose architecture with rationale | - Design addresses all requirements<br>- Trade-offs explicitly stated<br>- Alternatives considered and rejected with reasoning |
| 3. Trade-off Review | Stress-test the design | - Scalability implications addressed<br>- Failure modes identified<br>- Migration/adoption path clear |

### Code Review

Goal: Find real issues and propose actionable improvements.

| Step | Goal | Default Pass Criteria |
|------|------|-----------------------|
| 1. Analysis | Understand the code changes and their context | - All changed files identified<br>- Change purpose understood<br>- Surrounding code context captured |
| 2. Issues | Identify bugs, risks, and quality concerns | - Each issue has specific file:line reference<br>- Severity categorized (critical/major/minor)<br>- No false positives from misunderstanding context |
| 3. Improvements | Propose concrete fixes | - Each improvement is actionable (not vague)<br>- Improvements address identified issues<br>- No suggestions that contradict project conventions |

### Refactoring

Goal: Improve code structure while preserving behavior.

| Step | Goal | Default Pass Criteria |
|------|------|-----------------------|
| 1. Current State | Analyze what exists and why it needs change | - Problem areas identified with evidence<br>- Current behavior documented<br>- Dependencies mapped |
| 2. Plan | Define refactoring strategy | - Step-by-step plan with clear order<br>- Each step preserves existing behavior<br>- Risk areas identified |
| 3. Execute | Perform the refactoring | - All planned changes applied<br>- No behavior changes (unless explicitly intended)<br>- Code is cleaner by stated metrics |
| 4. Regression Check | Verify nothing broke | - All original functionality preserved<br>- No new warnings or errors<br>- Integration points still work |

### Analysis

Goal: Answer a question or investigate an issue with evidence.

| Step | Goal | Default Pass Criteria |
|------|------|-----------------------|
| 1. Scope | Define what to investigate and where to look | - Investigation boundaries clear<br>- Key files/systems to examine identified<br>- Success criteria for the analysis defined |
| 2. Investigation | Gather evidence and trace causes | - Multiple sources consulted (code, logs, docs)<br>- Evidence cited with specific references<br>- Alternative hypotheses considered |
| 3. Conclusions | Synthesize findings into actionable answer | - Conclusions supported by evidence<br>- Confidence level stated<br>- Recommended next steps provided |

### General (Adaptive)

For requests that don't fit a template:

1. Break the request into 2-4 logical steps
2. For each step, define 3-5 verifiable pass criteria
3. Order steps by dependency

---

## Pass Criteria Authoring Guide

Good pass criteria are:

- **Verifiable**: AntithesisAgent can objectively determine PASS/FAIL
  - Bad: "Code is well-written"
  - Good: "Functions are under 30 lines with single responsibility"

- **Specific**: No ambiguity about what "passing" means
  - Bad: "Handles errors properly"
  - Good: "All async calls have try/catch with typed error handling"

- **Relevant**: Directly tied to the step goal
  - Bad: "Has comprehensive documentation" (for an implementation step)
  - Good: "Public API functions have JSDoc with param/return types"

- **Countable**: 3-6 criteria per step is the sweet spot
  - Too few (1-2): Review is too shallow
  - Too many (7+): Loop becomes expensive, criteria overlap

## Workflow Customization

MetaAgent may customize templates:
- **Collapse steps**: Simple requests → fewer steps
- **Add criteria**: Domain-specific requirements
- **Adjust max_iterations**: Default 3, reduce for simple steps, increase for complex ones
- **Add dependencies**: `depends_on` links between steps when output of one feeds into next
