---
phase: P1-preproduction
pipeline: gamedev
execution_mode: sequential
steps: 6
---

# P1: Preproduction

Develop the game concept, research the domain and market, and evaluate technology options.

---

## S01: Game Concept Enrichment

### Required
true

### Goal
Expand the raw user request into a structured game concept with enough detail to write a formal game brief.

### Read Scope
- required: REQUEST.md

### Thesis
role: concept-designer
instruction: |
  Read the raw request and expand it into a structured game concept document covering:
  - **Target audience**: who plays this game — age range, gaming experience, platform habits
  - **Core player fantasy**: what power/experience/identity the player inhabits (e.g., "lone survivor in a hostile world", "master builder of civilizations")
  - **Experience goals**: 3-5 emotional/experiential outcomes the game must deliver (e.g., tension, discovery, mastery, social bonding)
  - **Genre vision**: primary and secondary genres, how they combine, what makes this take distinctive
  - **Platform considerations**: target platform(s), input method(s), session length expectations
  - **Initial scope sense**: solo/multiplayer, estimated content volume (hours of gameplay, number of levels/maps), team size implications

  Ground every expansion in the original request — do not invent features the user did not hint at. Where the request is ambiguous, state the interpretation explicitly.

### Antithesis
role: viability-analyst
instruction: |
  Verify the enriched concept is internally coherent and estimable:
  - **Audience-genre alignment**: does the target audience actually play this genre on this platform? Flag mismatches (e.g., hardcore sim targeted at casual mobile players)
  - **Player fantasy distinctiveness**: is the core fantasy specific enough to differentiate from comparable titles, or is it generic?
  - **Experience goal consistency**: do any experience goals contradict each other (e.g., "relaxing" + "high-stakes competitive")?
  - **Scope estimability**: is there enough detail to make rough scope judgments, or are critical dimensions still undefined?
  - **Platform feasibility**: do the described features fit the platform's constraints (input, performance, session length)?

  For each issue found, propose a specific resolution — not just "clarify X" but "resolve by choosing Y because Z".

### Convergence
target: output-quality
model: standard
weight: medium

### Pass Criteria
- Target audience defined with at least 2 distinguishing characteristics
- Core player fantasy stated in one sentence and is not a genre label
- Experience goals (3-5) are non-contradictory and traceable to the original request
- Genre vision specifies primary genre and at least one differentiator from existing titles
- Platform and input method explicitly stated
- No unresolved ambiguities from the original request remain unstated

### Output
path: P1-preproduction/S01-game-concept-enrichment.md
sections:
  - Target Audience
  - Core Player Fantasy
  - Experience Goals
  - Genre Vision
  - Platform Considerations
  - Initial Scope Sense
  - Interpretations and Assumptions

---

## S02: Game Brief

### Required
true

### Goal
Formalize the enriched game concept into a structured game brief that serves as the foundation for all subsequent research and design.

### Read Scope
- required: P1-preproduction/S01-game-concept-enrichment.md

### Thesis
role: brief-writer
instruction: |
  Draft game-brief.md from the enriched concept, formalizing:
  - **Genre**: primary and secondary genre classification
  - **Setting**: world, time period, aesthetic direction
  - **Core loop**: the moment-to-moment gameplay cycle the player repeats (describe as a verb chain, e.g., "explore → gather → craft → build → defend")
  - **Experience pillars**: 3-5 non-negotiable qualities that every design decision must support (e.g., "emergent player stories", "tactical depth", "accessible onboarding")
  - **Target platform**: platform(s), minimum specs if relevant, distribution channels
  - **Target audience**: refined from S01 with behavioral descriptors (play frequency, spending habits, genre familiarity)

  The core loop must be concrete enough to evaluate whether a proposed feature serves it. Pillars must be prioritized (if forced to cut, which survives last?).

### Antithesis
role: coherence-verifier
instruction: |
  Verify the game brief is internally coherent and actionable:
  - **Pillar-loop alignment**: does every experience pillar directly manifest in the core loop? Flag any pillar that is aspirational but has no loop hook
  - **Audience-genre fit**: does the target audience description match the genre and platform? Would this audience actually seek out this game?
  - **Player fantasy integrity**: does the brief preserve the core fantasy from S01, or has formalization diluted it?
  - **Setting-mechanics coherence**: does the setting support the core loop or fight it (e.g., a stealth game set in a wide-open featureless desert)?
  - **Contradictions**: scan all sections for statements that contradict each other

  Trace each finding to specific sentences in the brief. Propose rewording for any coherence issues.

### Convergence
target: output-quality
model: standard
weight: medium

### Pass Criteria
- Core loop described as a concrete verb chain (not abstract goals)
- Experience pillars (3-5) each have a clear connection to the core loop
- Target audience includes behavioral descriptors beyond demographics
- Setting description is specific enough to inform art direction
- No contradictions between any two sections of the brief
- Pillar priority order is stated

### Output
path: P1-preproduction/S02-game-brief.md
sections:
  - Genre
  - Setting
  - Core Loop
  - Experience Pillars
  - Target Platform
  - Target Audience

---

## S03: Domain Research

### Required
false

### Skip Condition
Team has deep genre expertise, or game jam / rapid prototype where formal research is disproportionate.

### Goal
Research genre conventions, comparable titles, design patterns, and common pitfalls to inform design decisions.

### Read Scope
- required: P1-preproduction/S01-game-concept-enrichment.md
- required: P1-preproduction/S02-game-brief.md

### Thesis
role: genre-analyst
instruction: |
  Analyze the game's genre landscape and extract actionable design lessons:
  - **Comparable titles**: identify at least 3 games in the same or adjacent genre. For each, document: core loop, what they did well, where they fell short, player reception
  - **Genre conventions**: what players expect from this genre (controls, UI patterns, progression pacing, session structure). Violating these needs justification
  - **Genre subversions**: successful examples of breaking genre norms — what they changed, why it worked, what risk it carried
  - **Design lessons**: concrete takeaways for this project. Frame as "do X because comparable title Y showed Z" or "avoid X because comparable title Y failed at Z"
  - **Player expectation gaps**: areas where player expectations differ from the proposed design — these are risk points requiring explicit design decisions

  Cite specific titles and specific design decisions, not general genre platitudes.

### Antithesis
role: depth-verifier
instruction: |
  Verify the domain research has sufficient depth and balance:
  - **Success AND failure**: are both successful patterns and cautionary examples cited? Research that only shows successes has survivorship bias
  - **Specificity**: are design lessons tied to specific titles and specific mechanics, or are they generic advice (e.g., "make it fun")?
  - **Player expectation coverage**: are expectation gaps identified for the areas where this game's design departs from genre norms?
  - **Genre-specific failure modes**: are the known ways this genre fails documented (e.g., RTS: overwhelming complexity; survival: empty mid-game; RPG: stat bloat)?
  - **Recency**: are the comparable titles relevant to current player expectations, not just historically important?

  For missing depth, specify what comparable title or failure mode should be added and why.

### Convergence
target: output-quality
model: standard
weight: medium

### Pass Criteria
- At least 3 comparable titles analyzed with specific mechanics cited
- Both successful patterns and cautionary failures documented
- Genre-specific failure modes for the target genre identified (at least 2)
- Player expectation gaps between proposed design and genre norms listed
- Every design lesson traces to a specific title and specific outcome
- At least one genre subversion example analyzed

### Output
path: P1-preproduction/S03-domain-research.md
sections:
  - Comparable Titles Analysis
  - Genre Conventions
  - Genre Subversions
  - Design Lessons
  - Player Expectation Gaps
  - Genre-Specific Failure Modes

---

## S04: Market Research

### Required
false

### Skip Condition
Non-commercial project (hobby, game jam, educational), or commercial strategy not yet relevant.

### Goal
Evaluate market positioning, audience segments, competitive landscape, and monetization options.

### Read Scope
- required: P1-preproduction/S01-game-concept-enrichment.md
- required: P1-preproduction/S02-game-brief.md

### Thesis
role: market-analyst
instruction: |
  Produce a market analysis covering:
  - **Audience segments**: break the target audience into 2-3 segments with distinct motivations (e.g., competitive players vs. casual explorers). For each: size estimate, spending behavior, acquisition channels
  - **Competitive positioning**: where this game sits relative to competitors. Identify the positioning gap — what does this game offer that competitors don't, and vice versa?
  - **Monetization model options**: evaluate 2-3 monetization models (premium, F2P, hybrid, etc.) for fit with the game type and audience. Recommend one with rationale
  - **Market timing and trends**: current genre popularity trends, saturation level, emerging opportunities
  - **Risk factors**: market risks — audience too niche, genre oversaturated, monetization backlash potential, platform store visibility challenges

  Back claims with evidence from comparable titles, market data, or observable trends. Avoid unsupported optimism.

### Antithesis
role: objectivity-verifier
instruction: |
  Verify the market analysis is objective and evidence-based:
  - **Evidence backing**: are audience size estimates, trends, and positioning claims supported by comparable data or observable market signals? Flag unsupported claims
  - **Risk acknowledgment**: are downside risks given equal treatment to opportunities, or is the analysis skewed optimistic?
  - **Monetization-pillar compatibility**: does the recommended monetization model align with the game's experience pillars? Flag conflicts (e.g., pay-to-win in a game with a fairness pillar, aggressive ads in an immersion-focused game)
  - **Audience realism**: are the audience segments based on observable player behaviors, or are they aspirational?
  - **Competitive honesty**: does the competitive positioning acknowledge what competitors do better, not just where they fall short?

  For each objectivity issue, propose how to reframe the claim with appropriate caveats.

### Convergence
target: output-quality
model: standard
weight: medium

### Pass Criteria
- At least 2 audience segments defined with distinct motivations
- Competitive positioning identifies both advantages and disadvantages vs. competitors
- Monetization recommendation does not conflict with any experience pillar
- At least 2 market risk factors identified with severity assessment
- Claims reference comparable titles or observable market signals
- No unsupported superlatives ("huge market", "massive demand") remain

### Output
path: P1-preproduction/S04-market-research.md
sections:
  - Audience Segments
  - Competitive Positioning
  - Monetization Model Analysis
  - Market Timing and Trends
  - Risk Factors

---

## S05: Tech Research

### Required
false

### Skip Condition
Engine/framework already decided (specified in request or team standard).

### Goal
Evaluate engine and framework options for the target game type and platform, and recommend a technology stack.

### Read Scope
- required: P1-preproduction/S01-game-concept-enrichment.md
- required: P1-preproduction/S02-game-brief.md

### Thesis
role: tech-evaluator
instruction: |
  Compare engines and frameworks suitable for this game type and target platform:
  - **Candidates**: identify 2-4 viable engine/framework options. For each, document:
    - Strengths for this game type (built-in systems that match needed features)
    - Weaknesses or gaps (what would need custom implementation)
    - Platform support quality (build pipeline, certification, performance)
    - Learning curve and ecosystem maturity
    - Licensing and cost implications
  - **Recommendation**: select one option with clear rationale tied to the game's specific needs (core loop requirements, platform constraints, content pipeline needs)
  - **Technical constraints**: platform-specific constraints that affect design (mobile memory limits, console certification requirements, web browser limitations, input device capabilities)
  - **Build pipeline**: how assets flow from creation to runtime — tools, formats, compression, loading strategy

  Evaluate engines against the game's actual requirements (from the brief), not general-purpose capability lists.

### Antithesis
role: thoroughness-verifier
instruction: |
  Verify the tech evaluation is thorough and unbiased:
  - **Balanced evaluation**: does each candidate have both pros AND cons documented, or is the evaluation steering toward a predetermined choice?
  - **Platform constraint coverage**: are target platform constraints addressed specifically (not "runs on mobile" but "texture memory budget on target devices, APK size limits, thermal throttling")?
  - **Familiar-tech bias**: is the recommendation justified by project needs, or does it show bias toward the most commonly used or most familiar option?
  - **Missing candidates**: are there viable options not considered? If an obvious candidate is excluded, is the exclusion justified?
  - **Game-type fit**: is the evaluation grounded in this specific game's needs (e.g., a 2D puzzle game doesn't need AAA 3D engine features)?

  For each gap, specify what information is missing and why it matters for the decision.

### Convergence
target: output-quality
model: standard
weight: medium

### Pass Criteria
- At least 2 engine/framework candidates evaluated with pros AND cons
- Recommendation rationale references specific game requirements from the brief
- Platform constraints documented with concrete limits (memory, size, performance targets)
- No candidate evaluation is entirely positive or entirely negative
- Build pipeline described from asset creation to runtime
- Licensing/cost implications stated for the recommended option

### Output
path: P1-preproduction/S05-tech-research.md
sections:
  - Engine/Framework Candidates
  - Comparative Evaluation
  - Recommendation and Rationale
  - Platform Constraints
  - Build Pipeline
  - Licensing and Cost

---

## S06: Create Summary

### Required
true

### Goal
Synthesize all preproduction research into a cohesive phase deliverable with risk register and clear handoff to Phase 2.

### Read Scope
- required: P1-preproduction/S01-game-concept-enrichment.md
- required: P1-preproduction/S02-game-brief.md
- optional: P1-preproduction/S03-domain-research.md
- optional: P1-preproduction/S04-market-research.md
- optional: P1-preproduction/S05-tech-research.md

### Thesis
role: synthesizer
instruction: |
  Consolidate all prior step outputs into a cohesive DELIVERABLE.md that serves as the single input for Phase 2:
  - **Summary**: 2-3 sentences capturing the game concept, target, and key decisions
  - **Core loop definition**: finalized moment-to-moment gameplay cycle
  - **Experience pillars**: prioritized list with brief rationale for each
  - **Target audience and platform**: consolidated from brief and market research
  - **Technology recommendation**: engine choice with rationale summary
  - **Risk register**: top 3 risks (one gameplay, one market, one technical) with severity, likelihood, and mitigation strategy for each
  - **Key decisions**: major decisions made during preproduction with rationale
  - **Deferred items**: questions or decisions explicitly deferred to later phases

  Ensure no information is lost between steps — if domain research raised a concern that affects the brief, it must appear in the deliverable. Resolve any contradictions between step outputs rather than carrying them forward.

  For any skipped research step, mark the corresponding deliverable section based on available information only. In the Risk Register: if domain research was skipped, note "Domain risks not formally assessed"; if market research was skipped, note "Market risks not formally assessed"; if tech research was skipped, note "Tech recommendation deferred to Technical phase." Still produce 3 risks from whatever information is available.

### Antithesis
role: traceability-verifier
instruction: |
  Verify the summary is complete, traceable, and contradiction-free:
  - **Traceability**: does every claim in the deliverable trace to a specific prior step output? Flag any statement that appears in the summary but not in any source step
  - **Risk register completeness**: are all three risk categories covered (gameplay, market, technical)? Does each risk have a concrete mitigation, not just "monitor"?
  - **Cross-step consistency**: do conclusions from different steps contradict each other? (e.g., tech research recommends engine X but domain research shows comparable titles avoid it)
  - **No unsupported decisions**: are all technology choices, audience definitions, and scope decisions backed by prior research?
  - **Deferred items captured**: were any unresolved questions from prior steps dropped rather than deferred?
  - **Handoff completeness**: does the deliverable contain everything Phase 2 needs to begin design without re-reading Phase 1 step files?

  For each traceability gap, cite the source step and the missing connection.

### Convergence
target: output-quality
model: standard
weight: heavy

### Pass Criteria
- Every deliverable section traces to at least one prior step output
- Risk register has exactly 3 entries: one gameplay, one market, one technical
- Each risk has severity, likelihood, and a specific mitigation action
- No contradictions between deliverable content and source step outputs
- Core loop, pillars, audience, platform, and tech recommendation all present
- Deferred items list is non-empty (some decisions always belong to later phases)

### Output
path: P1-preproduction/DELIVERABLE.md
sections:
  - Summary
  - Core Loop Definition
  - Experience Pillars
  - Target Audience and Platform
  - Technology Recommendation
  - Risk Register
  - Key Decisions
  - Deferred Items

last_step: true

---

## Exit Contract

The following must be present in the DELIVERABLE.md for Phase 2 to begin:

- Core loop definition (moment-to-moment gameplay)
- Experience pillars (3-5 non-negotiable qualities)
- Target audience and platform
- Technology recommendation with rationale
- Top 3 risks (gameplay, market, technical) and mitigations
