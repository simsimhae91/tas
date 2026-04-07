---
phase: P1-analysis
pipeline: sdlc
execution_mode: sequential
---

# P1: Analysis

Understand the domain, research feasibility, and produce a project brief.

---

## S01: Idea Enrichment

### Required
true

### Goal
Expand the raw user request into a structured concept document with user personas, core features, value proposition, and success metrics.

### Read Scope
- required: REQUEST.md

### Thesis
role: spec-writer
instruction: |
  Read REQUEST.md and produce a structured concept document covering:
  1. **Vision statement** — one paragraph describing what this project is and why it matters.
  2. **User personas** — 2-4 distinct personas, each with: name, role/archetype, primary goal, pain points, and technical proficiency. Personas must represent genuinely different user segments, not variations of the same user.
  3. **Core features** — list every feature implied or explicitly stated in the request. For each: name, one-sentence description, which persona(s) it serves, and priority estimate (P0 = must-have, P1 = should-have, P2 = nice-to-have).
  4. **Value proposition** — what unique value does this project deliver that existing solutions do not?
  5. **Success metrics** — 3-5 measurable outcomes (e.g., "User can complete core flow in under 2 minutes", "API response time < 200ms for 95th percentile"). Every metric must have a numeric target.

  Ground every claim in the original request. If the request is vague on a point, state your assumption explicitly rather than silently inventing requirements.

### Antithesis
role: spec-reviewer
instruction: |
  Review the concept document for completeness and internal consistency:
  - Are personas genuinely distinct? (different goals, not just different names)
  - Does every feature trace back to at least one persona's need? Flag any orphan features.
  - Are success metrics actually measurable with a numeric target? Reject vague metrics like "good performance" or "easy to use."
  - Does the vision statement match what the features actually deliver?
  - Are assumptions called out, or are invented requirements presented as given?
  If any feature appears to contradict the request or another feature, raise it as a contention.

### Convergence
target: output-quality
model: standard
weight: medium

### Pass Criteria
- Every persona has a distinct primary goal that differs from other personas
- Every feature traces to at least one persona need
- Success metrics include numeric targets
- Assumptions from the original request are explicitly labeled

### Output
path: P1-analysis/S01-idea-enrichment.md
sections:
  - Vision Statement
  - User Personas
  - Core Features
  - Value Proposition
  - Success Metrics
  - Assumptions

---

## S02: Tech Research

### Required
false

### Skip Condition
Technology stack already specified in request, or project scope is single-feature / CLI tool.

### Goal
Identify technology options for the project, evaluate trade-offs across at least two candidate stacks, and recommend a stack with rationale.

### Read Scope
- required: REQUEST.md
- required: P1-analysis/S01-idea-enrichment.md

### Thesis
role: researcher
instruction: |
  Based on the concept document and original request, research and compare technology options:
  1. **Candidate stacks** — propose at least 2 realistic technology stacks (language, framework, database, infrastructure). Each must be plausible for the project scope.
  2. **Evaluation criteria** — define 4-6 criteria relevant to this project (e.g., learning curve, ecosystem maturity, performance characteristics, hosting cost, community support, type safety).
  3. **Comparison matrix** — evaluate each candidate against every criterion. Include concrete evidence: version numbers, benchmark data, community size, known limitations.
  4. **Pros AND cons** — for each candidate, list at least 2 pros and 2 cons. Cons must be genuine drawbacks, not hedged compliments.
  5. **Recommendation** — pick one stack with clear rationale tied to project requirements and personas. Explain what you are trading off.

  If the request specifies a technology, still evaluate it against alternatives to confirm it is the right choice — do not rubber-stamp.

### Antithesis
role: objectivity-verifier
instruction: |
  Verify the tech research for objectivity and completeness:
  - Does every candidate have genuine cons listed, or is the recommended stack suspiciously clean?
  - Is there evidence of bias toward popular/familiar technologies without project-specific justification?
  - Are evaluation criteria relevant to this specific project, or are they generic?
  - Does the comparison matrix contain concrete data points (versions, benchmarks, costs) or only qualitative assertions?
  - Does the recommendation rationale connect to the personas and features from S01?
  - If the request specified a technology, was it still critically evaluated?
  Flag any missing cons or unsubstantiated claims.

### Convergence
target: output-quality
model: standard
weight: medium

### Pass Criteria
- At least 2 candidate stacks compared with pros AND cons for each
- Evaluation criteria are specific to the project, not generic
- Recommendation rationale references project requirements from S01
- No candidate has zero cons listed

### Output
path: P1-analysis/S02-tech-research.md
sections:
  - Candidate Stacks
  - Evaluation Criteria
  - Comparison Matrix
  - Recommendation
  - Trade-offs Accepted

---

## S03: Domain Analysis

### Required
false

### Skip Condition
Domain is simple and well-known (e.g., TODO app, personal blog), no regulatory concerns.

### Goal
Research domain constraints, regulatory requirements, competitive landscape, and established patterns relevant to the project.

### Read Scope
- required: REQUEST.md
- required: P1-analysis/S01-idea-enrichment.md

### Thesis
role: domain-analyst
instruction: |
  Analyze the domain context for this project:
  1. **Domain constraints** — what rules, conventions, or expectations exist in this domain? (e.g., healthcare requires HIPAA, fintech requires PCI-DSS, e-commerce expects certain checkout flows)
  2. **Regulatory requirements** — identify any legal/compliance requirements. If none apply, state that explicitly with reasoning.
  3. **Competitive landscape** — identify 2-3 existing solutions in this space. For each: what they do well, what they lack, and how this project differentiates.
  4. **Established patterns** — what UX patterns, data models, or architectural patterns are standard in this domain? Deviating from these needs justification.
  5. **Domain risks** — what domain-specific risks could derail the project? (e.g., API deprecation, regulatory changes, market saturation) List at least 3 risks with severity and mitigation.

  Be specific to the actual domain. Do not produce generic risks like "scope creep" or "technical debt" — those are project management concerns, not domain risks.

### Antithesis
role: depth-verifier
instruction: |
  Verify the domain analysis for depth and specificity:
  - Are domain constraints specific to this domain, or could they apply to any project?
  - Were regulatory requirements actually researched, or was "N/A" asserted without investigation?
  - Do competitive analysis entries describe real products with specific strengths/weaknesses, or are they vague placeholders?
  - Are established patterns grounded in the actual domain (with examples), or are they generic software patterns?
  - Are domain risks genuinely domain-specific? Reject any risk that applies to all software projects equally.
  - Are mitigations actionable and specific, or just "monitor the situation"?

### Convergence
target: output-quality
model: standard
weight: medium

### Pass Criteria
- Domain constraints are specific to the identified domain
- Regulatory requirements are researched (not assumed N/A without reasoning)
- At least 2 real competitors identified with specific strengths/weaknesses
- Domain risks are domain-specific with actionable mitigations

### Output
path: P1-analysis/S03-domain-analysis.md
sections:
  - Domain Constraints
  - Regulatory Requirements
  - Competitive Landscape
  - Established Patterns
  - Domain Risks and Mitigations

---

## S04: Create Brief
last_step: true

### Required
true

### Goal
Synthesize all prior research (concept, tech, domain) into a comprehensive project brief that serves as the single handoff document to Phase 2.

### Read Scope
- required: P1-analysis/S01-idea-enrichment.md
- optional: P1-analysis/S02-tech-research.md
- optional: P1-analysis/S03-domain-analysis.md

### Thesis
role: brief-writer
instruction: |
  Consolidate S01 (concept), S02 (tech research), and S03 (domain analysis) into a single project brief:
  1. **Project scope** — clear boundaries: what is IN scope and what is OUT of scope. Every in-scope item must trace to a feature from S01.
  2. **Target personas** — refined from S01, incorporating domain analysis insights. Each persona with primary use case.
  3. **Technology recommendation** — the recommended stack from S02 with rationale. Include key trade-offs accepted.
  4. **Risk register** — combine tech risks from S02 and domain risks from S03. Rank by severity x likelihood. Include top 3 with mitigation strategies.
  5. **Success metrics** — refined from S01, validated against domain standards and competitive baseline.
  6. **Key decisions** — list decisions made during analysis with rationale. These become constraints for Phase 2.
  7. **Deferred items** — anything explicitly excluded from scope that may be revisited later.

  Do NOT introduce new information. Every claim in the brief must trace to S01, S02, or S03. If you identify a gap in the research, flag it as an open question rather than filling it with assumptions.

  If tech research (S02) was not performed, mark the Technology Recommendation section as "Deferred — evaluate during Solutioning phase" and note this in Open Questions. If domain analysis (S03) was not performed, limit the Risk Register to risks identifiable from the concept document and mark domain-specific risk slots as "Deferred — domain analysis not performed."

### Antithesis
role: traceability-verifier
instruction: |
  Verify the brief for traceability and completeness:
  - Does every scope item trace to a specific feature from S01? Flag any new items not in the research.
  - Does every persona match S01's personas (refined is fine, invented is not)?
  - Does the tech recommendation match S02's conclusion? Flag any silent changes.
  - Does the risk register include risks from both S02 and S03? Flag any omitted risks.
  - Are success metrics consistent with S01's metrics? Flag any that were silently changed.
  - Are there any unsupported claims — statements that do not trace to S01, S02, or S03?
  - Does the brief contain enough information for Phase 2 (Planning) to begin without re-researching?

### Convergence
target: output-quality
model: standard
weight: heavy

### Pass Criteria
- Every scope item traces to a feature in S01
- Risk register includes risks from both S02 (tech) and S03 (domain)
- No unsupported claims — every assertion traces to S01, S02, or S03
- Brief is self-contained: Phase 2 can begin from this document alone
- Open questions are listed rather than filled with assumptions
- Success metrics have numeric targets

### Output
path: P1-analysis/DELIVERABLE.md
sections:
  - Project Scope (In/Out)
  - Target User Personas
  - Technology Recommendation
  - Risk Register (Top 3)
  - Success Metrics
  - Key Decisions
  - Deferred Items
  - Open Questions

---

## Exit Contract

DELIVERABLE.md must contain these fields for Phase 2 handoff:

| Field | Required | Description |
|-------|----------|-------------|
| Project scope boundaries | yes | What is in scope and what is out |
| Target user personas | yes | Personas with primary use cases |
| Technology recommendation | yes | Recommended stack with rationale |
| Top 3 risks and mitigations | yes | Severity-ranked with actionable mitigations |
| Success metrics | yes | Measurable outcomes with numeric targets |
