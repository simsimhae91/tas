---
phase: P2-design
pipeline: gamedev
execution_mode: sequential
steps: 5
---

# P2: Design

Produce a complete Game Design Document, narrative framework, PRD, and UX specification.

---

## S01: Game Design Document

### Required
true

### Goal
Write a comprehensive Game Design Document (GDD) that translates the game brief into detailed system designs covering every aspect of gameplay.

### Read Scope
- required: P1-preproduction/DELIVERABLE.md

### Thesis
role: system-designer
instruction: |
  Draft a comprehensive GDD from the Phase 1 deliverable, covering every gameplay system:
  - **Core mechanics**: detailed description of each mechanic the player interacts with. For each: inputs, outputs, feedback loops, failure states. Describe how the mechanic feels moment-to-moment, not just what it does
  - **Progression systems**: how the player advances — skill trees, unlocks, level gates, mastery curves. Define short-term (session), medium-term (multi-session), and long-term (endgame) progression arcs
  - **Economy design**: all resource types, sources (how players earn), sinks (how players spend), exchange rates, inflation/deflation controls. Economy must be a closed system — every source has a corresponding sink
  - **Difficulty model**: how challenge scales — enemy AI, level design parameters, player power curve. Address the full skill range from newcomer to veteran. Define difficulty modes if applicable
  - **Multiplayer design** (if applicable): netcode model, session types, matchmaking, anti-cheat considerations, social features. If single-player only, explicitly state this
  - **Content structure**: levels, maps, episodes, or other content units. How content is organized, gated, and paced. Replayability mechanics if applicable
  - **System interactions**: how systems connect — what happens when progression unlocks new mechanics, how economy feeds into difficulty, how content gates connect to progression

  Every system must connect to the core loop from the brief. If a system exists without a core loop connection, justify its inclusion or remove it.

### Antithesis
role: system-verifier
instruction: |
  Verify the GDD is complete, coherent, and mechanically sound:
  - **Core loop coverage**: does every described system connect to the core loop? Flag any system that exists in isolation
  - **System interlocking**: do systems that interact have consistent interfaces? (e.g., if progression unlocks weapons and economy prices weapons, do unlock conditions and prices use the same tier model?)
  - **Economy balance**: does the economy have both sinks AND sources for every resource? Are there any obvious exploit vectors (infinite resource generation, negative costs)?
  - **Difficulty range**: does the difficulty model address both newcomers and veterans? Are there difficulty cliffs (sudden spikes) or plateaus (extended boredom)?
  - **Completeness**: are all mechanics from the brief represented? Are there emergent interactions between systems that need rules (e.g., what happens when a player is in combat and opens the crafting menu)?
  - **Contradiction scan**: check for statements that contradict each other across sections (e.g., "permadeath" in one section, "respawn at checkpoint" in another)

  For each issue, propose a specific mechanical resolution, not just "needs clarification".

### Convergence
target: output-quality
model: standard
weight: heavy

### Pass Criteria
- Every system described connects to the core loop with the connection explicitly stated
- Economy has documented sources and sinks for each resource type
- Difficulty model addresses at least 3 skill levels (newcomer, intermediate, veteran)
- Progression defines short, medium, and long-term arcs
- No contradictions between any two sections
- System interaction matrix covers all pairwise system connections

### Output
path: P2-design/S01-game-design-document.md
sections:
  - Core Mechanics
  - Progression Systems
  - Economy Design
  - Difficulty Model
  - Multiplayer Design (or Single-Player Statement)
  - Content Structure
  - System Interaction Matrix

---

## S02: Narrative Design

### Required
false

### Skip Condition
Game has minimal narrative (pure puzzle, racing, arcade, abstract strategy).

### Goal
Design the narrative framework, world-building, and player-facing text strategy that supports and enhances the gameplay experience.

### Read Scope
- required: P1-preproduction/DELIVERABLE.md
- required: P2-design/S01-game-design-document.md

### Thesis
role: narrative-designer
instruction: |
  Draft narrative-design.md that creates a narrative layer supporting the gameplay systems:
  - **World lore**: setting history, factions, geography, rules of the world. Lore should explain why the game's mechanics exist in-world (why do enemies respawn? why does the player have special abilities?)
  - **Story structure**: narrative arc(s), act structure, key plot beats. For non-linear games, describe the narrative graph. For emergent narrative games, describe the systems that generate stories
  - **Character design**: player character identity, key NPCs with motivations, antagonist design. Characters should embody the game's themes
  - **Dialogue system**: how dialogue is delivered (cutscenes, in-game, text boxes, environmental), branching model (linear, choice-based, systemic), voice acting scope
  - **Narrative-gameplay integration**: specific points where narrative and gameplay intersect — tutorial justification, progression gates as story beats, lore rewards for exploration, narrative consequences for player choices
  - **Tone and style guide**: writing style, humor level, darkness level, vocabulary constraints. Examples of in-character and out-of-character writing

  Scale narrative scope to match the game type. A puzzle game needs minimal narrative; an RPG needs deep narrative. Match effort to the game's experience pillars.

### Antithesis
role: coherence-verifier
instruction: |
  Verify narrative design supports gameplay rather than fighting it:
  - **Narrative-gameplay alignment**: does the narrative support the experience pillars, or is it decorative? Flag narrative elements that don't connect to any gameplay system
  - **Player agency match**: does the narrative's agency model match the game's agency model? (e.g., a branching story in a linear game, or a fixed story in an open-world sandbox — both are mismatches)
  - **Tone consistency**: is the tone consistent across all narrative elements? Flag tonal whiplash between sections
  - **Lore contradictions**: does the world lore contradict any game mechanic? (e.g., lore says magic is rare but the player has 20 spells from the start)
  - **Scope appropriateness**: for minimal-narrative games (puzzles, sports, rhythm), verify the narrative scope doesn't exceed what the game type warrants. For narrative-heavy games, verify depth is sufficient
  - **Integration point coverage**: are narrative hooks placed at every major gameplay transition (onboarding, new mechanic introduction, progression gates, endgame)?

  Distinguish between "nice to have" narrative and "mechanically necessary" narrative. Focus critique on the latter.

### Convergence
target: output-quality
model: standard
weight: medium

### Pass Criteria
- Narrative scope matches the game type (not over- or under-invested)
- At least 3 specific narrative-gameplay integration points documented
- Player agency model in narrative matches agency model in GDD
- Tone guide includes at least 2 writing examples
- World lore does not contradict any documented game mechanic
- Dialogue system design matches the target platform's capabilities

### Output
path: P2-design/S02-narrative-design.md
sections:
  - World Lore
  - Story Structure
  - Character Design
  - Dialogue System
  - Narrative-Gameplay Integration Points
  - Tone and Style Guide

---

## S03: Create PRD

### Required
true

### Goal
Translate the GDD and narrative design into a Product Requirements Document with prioritized functional and non-functional requirements.

### Read Scope
- required: P2-design/S01-game-design-document.md
- optional: P2-design/S02-narrative-design.md

### Thesis
role: prd-writer
instruction: |
  Draft the PRD by translating design documents into implementable requirements:
  - **Functional requirements**: one requirement per game system/mechanic from the GDD. Each requirement must be testable (define what "working" means). Assign priority:
    - P0: core loop requirements — the game is not playable without these
    - P1: experience pillar requirements — the game is playable but not compelling without these
    - P2: polish and depth — enhance but don't define the experience
  - **Non-functional requirements**: performance targets (frame rate, load times, memory), reliability (crash rate, save integrity), security (anti-cheat if multiplayer)
  - **Platform requirements**: target platform-specific requirements — input handling, screen sizes, certification requirements (console TRC/XR), store requirements (ratings, metadata)
  - **Accessibility requirements**: configurable difficulty, remappable controls, colorblind modes, subtitle options, motor accessibility. Scope to what's appropriate for the game type
  - **Localization scope**: target languages, text volume estimate, voice localization if applicable, cultural adaptation needs
  - **Requirement dependencies**: which requirements depend on others. This feeds the story dependency graph in Phase 3

  Every GDD system must have at least one functional requirement. If a system has no requirement, it is either missing from the PRD or unnecessary in the GDD.

### Antithesis
role: traceability-verifier
instruction: |
  Verify PRD completeness and traceability:
  - **GDD coverage**: does every GDD system have at least one corresponding requirement? List any GDD systems with no PRD requirement
  - **Priority justification**: are P0 items truly core-loop-essential? Are any P1 items actually P0 (game unplayable without them)?
  - **Testability**: can each requirement be verified with a concrete test? Flag requirements that use subjective language ("feels good", "looks nice") without measurable criteria
  - **Contradiction scan**: do any requirements contradict each other? (e.g., "load time < 3s" but "preload all level assets")
  - **Platform constraint reflection**: do platform requirements match the tech research from Phase 1? Are certification requirements for the target platform included?
  - **Dependency completeness**: are requirement dependencies explicit and acyclic?

  For each traceability gap, specify the GDD system missing coverage and suggest the requirement that should exist.

### Convergence
target: output-quality
model: standard
weight: heavy

### Pass Criteria
- Every GDD system has at least one corresponding functional requirement
- P0 requirements are exactly those needed for a minimal playable core loop
- Each requirement has a testable acceptance criterion
- No contradictions between requirements
- Platform certification requirements included for the target platform
- Requirement dependency graph is acyclic

### Output
path: P2-design/S03-prd.md
sections:
  - Functional Requirements (by priority)
  - Non-Functional Requirements
  - Platform Requirements
  - Accessibility Requirements
  - Localization Scope
  - Requirement Dependencies

---

## S04: Create UX

### Required
false

### Skip Condition
Game has minimal UI (text-based, single-screen, no menu system).

### Goal
Design the complete player-facing UX: screen inventory, HUD, menus, input handling, onboarding, and accessibility.

### Read Scope
- required: P2-design/S01-game-design-document.md
- optional: P2-design/S02-narrative-design.md
- required: P2-design/S03-prd.md

### Thesis
role: ux-designer
instruction: |
  Draft ux-spec.md covering all player-facing interaction design:
  - **Screen inventory**: every distinct screen/view in the game (main menu, HUD, pause, inventory, settings, etc.). For each: purpose, key elements, navigation entry/exit points
  - **HUD layout**: in-game heads-up display design — what information is always visible, what appears contextually, information hierarchy, screen-edge placement
  - **Menu flows**: navigation tree from main menu through all submenus. Include flow diagrams showing how screens connect. Mark which transitions are reversible
  - **Input schemes**: control mappings for each target platform/input method. Default bindings, remapping support, simultaneous input handling (gamepad + mouse). Describe input feel targets (response time, dead zones)
  - **Onboarding/tutorial**: how each core mechanic is introduced. Sequence of teaching moments, pacing, mandatory vs. optional tutorials. Map each teaching moment to the mechanic it introduces
  - **Accessibility**: specific accessibility features — subtitle size options, colorblind modes, input remapping, difficulty assists, screen reader support where applicable. Scope to platform norms

  Every core mechanic from the GDD must have a UX surface. Every HUD element and menu must have a clear purpose tied to a game system.

### Antithesis
role: coverage-verifier
instruction: |
  Verify UX completeness and player experience quality:
  - **Game state coverage**: does every game state (gameplay, pause, inventory, dialogue, combat, death, loading, etc.) have a corresponding UX design? Flag states with no screen definition
  - **Onboarding completeness**: does the onboarding sequence cover every core mechanic? Are mechanics introduced in dependency order (don't teach crafting before teaching resource gathering)?
  - **Platform input fit**: do input schemes work for the target platform? Are there input conflicts (same button for two actions in the same context)? Are touch targets large enough for mobile?
  - **Dead-end check**: can the player reach any screen from which there is no way to navigate back or forward? Trace all navigation paths
  - **HUD information overload**: does the HUD show too much information simultaneously? Is critical information distinguishable from secondary information?
  - **Accessibility baseline**: are minimum accessibility features present (remappable controls, subtitle options, difficulty options)?

  For each coverage gap, specify the game state or mechanic missing UX treatment.

### Convergence
target: output-quality
model: standard
weight: medium

### Pass Criteria
- Every game state identified in the GDD has a corresponding screen/view
- Onboarding covers all core mechanics in dependency order
- Input schemes defined for every target platform with no binding conflicts
- No dead-end screens (every screen has at least one exit path)
- HUD elements are prioritized (critical vs. contextual vs. optional)
- Accessibility features include at minimum: remappable controls and subtitle options

### Output
path: P2-design/S04-ux-spec.md
sections:
  - Screen Inventory
  - HUD Layout
  - Menu Flows
  - Input Schemes
  - Onboarding and Tutorial Sequence
  - Accessibility Features

---

## S05: Validate PRD

### Required
true

### Goal
Cross-check PRD against GDD, narrative design, and UX spec to ensure complete consistency and produce the phase deliverable.

### Read Scope
- required: P2-design/S01-game-design-document.md
- optional: P2-design/S02-narrative-design.md
- required: P2-design/S03-prd.md
- optional: P2-design/S04-ux-spec.md

### Thesis
role: reconciler
instruction: |
  Reconcile all Phase 2 outputs and produce the validated DELIVERABLE.md:
  - **PRD ↔ GDD reconciliation**: verify every PRD requirement maps to a GDD system and vice versa. Resolve gaps:
    - GDD system with no requirement → add requirement or justify exclusion
    - Requirement with no GDD system → trace to brief or remove
  - **PRD ↔ UX reconciliation**: verify every requirement with a player-facing component has a UX screen/element. Resolve gaps:
    - Requirement with no UX surface → add UX design or mark as backend-only
    - UX element with no requirement → add requirement or remove element
  - **Narrative ↔ GDD reconciliation**: verify narrative integration points from S02 correspond to actual game systems and UX surfaces
  - **Requirements matrix**: produce a traceability matrix: Requirement ID → GDD System → UX Screen → Narrative Hook (if applicable)
  - **Inconsistency resolution**: for each inconsistency found, document the resolution and rationale

  The deliverable must be self-contained — Phase 3 reads only this file, not individual step outputs.

### Antithesis
role: consistency-verifier
instruction: |
  Verify the reconciliation is complete and the deliverable is self-contained:
  - **1:1 mapping**: does the requirements matrix show a complete mapping from PRD requirements to GDD systems? Are there orphan requirements (no GDD system) or orphan systems (no requirement)?
  - **UX traceability**: does every UX screen trace to at least one requirement? Are there screens that exist without a corresponding requirement?
  - **Narrative integration**: do narrative hooks reference actual game states that appear in both the GDD and UX spec?
  - **Resolution completeness**: were all inconsistencies found in reconciliation actually resolved, or were some deferred without being listed as deferred?
  - **Deliverable self-containment**: can Phase 3 begin work using only this deliverable, without needing to read individual P2 step files? Is critical information from any step missing from the deliverable?
  - **Deferred items**: are items deferred to later phases explicitly listed with rationale?

  For each orphan or gap, specify the exact requirement ID, GDD system, or UX screen affected.

### Convergence
target: output-quality
model: standard
weight: heavy

### Pass Criteria
- Requirements matrix has no orphan requirements and no orphan GDD systems
- Every UX screen traces to at least one PRD requirement
- Narrative integration points reference valid GDD systems and UX screens
- All inconsistencies are resolved or explicitly deferred with rationale
- Deliverable contains all information Phase 3 needs (architecture cannot start without it)
- Deferred items list is present and non-empty

### Output
path: P2-design/DELIVERABLE.md
sections:
  - Summary
  - GDD Summary (system count, core loop description)
  - Requirements Matrix (Requirement ID → GDD System → UX Screen)
  - UX Flow Summary (screens per feature, primary player journeys)
  - Narrative Integration Points
  - Key Decisions
  - Deferred Items

last_step: true

---

## Exit Contract

The following must be present in the DELIVERABLE.md for Phase 3 to begin:

- GDD summary with system count and core loop description
- Requirements matrix (requirement ID → GDD system → UX screen)
- UX flow summary (screens per feature, primary player journeys)
- Narrative integration points (where narrative hooks into gameplay)
- Deferred/out-of-scope items
