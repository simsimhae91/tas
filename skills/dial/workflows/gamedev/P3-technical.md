---
phase: P3-technical
pipeline: gamedev
execution_mode: sequential
steps: 6
---

# P3: Technical

Produce game architecture, implementation stories, project context, and test design ready for development.

---

## S01: Game Architecture

### Required
true

### Goal
Design the complete technical architecture for the game: engine structure, entity system, scene management, data pipeline, and platform abstraction.

### Read Scope
- required: P2-design/DELIVERABLE.md

### Thesis
role: game-architect
instruction: |
  Propose a comprehensive game architecture based on the Phase 2 deliverable:
  - **Engine layer structure**: define the runtime layers (platform abstraction, core engine, game framework, game logic, UI). For each layer: responsibility, public API surface, what it depends on, what depends on it
  - **Entity/component design**: choose and justify ECS (Entity Component System) vs. OOP hierarchy vs. hybrid. Define core components/classes for player, enemies, items, projectiles, UI elements. Show how game objects are composed
  - **Scene management**: how scenes/levels are loaded, transitioned, and unloaded. Memory management strategy for scene assets. Scene graph structure if applicable
  - **Asset pipeline**: how assets flow from source files to runtime — formats, compression, atlas packing, streaming strategy. Define the asset manifest format
  - **Data serialization**: save/load system design — what state is persisted, serialization format, versioning for save compatibility across updates. Config/tuning data format (JSON, YAML, binary) and hot-reload support
  - **Platform abstraction**: how platform-specific code (input, rendering, audio, file I/O, networking) is isolated behind interfaces. Define the abstraction boundaries
  - **Performance budget**: frame time budget breakdown (update, render, physics, AI, audio) for the target platform. Memory budget by category (textures, audio, game state, engine overhead)

  Justify each architectural decision against the game's specific requirements — not general "best practices". If ECS is chosen, explain what about this game makes ECS appropriate. If OOP, same.

### Antithesis
role: soundness-verifier
instruction: |
  Verify the architecture is sound, complete, and fit for this game:
  - **P0 requirement addressability**: can every P0 requirement from the PRD be implemented within this architecture? Walk through the top 3 most complex P0 requirements and trace the implementation path through the architecture layers
  - **Game pattern appropriateness**: are game-specific patterns used where appropriate (object pooling for projectiles, spatial partitioning for collision, state machines for AI)? Flag generic patterns used where game-specific ones would be better
  - **Performance budget realism**: does the performance budget account for the game's actual workload? (e.g., if the game has 100+ entities on screen, does the frame budget reflect that?) Are budget numbers based on the target platform's actual capabilities?
  - **Data model completeness**: does the data model support save/load for ALL persistent game state? Can the save format handle game updates without breaking existing saves?
  - **Single points of failure**: are there components where a failure cascades to a full crash? Is the game resilient to individual system failures (e.g., audio system crash shouldn't freeze gameplay)?
  - **Platform abstraction coverage**: does the abstraction layer cover ALL platform-specific operations, or are there platform calls leaking into game logic?

  For each soundness issue, propose an architectural change — not just "needs improvement".

### Convergence
target: arch-conformance
model: standard
weight: heavy

### Pass Criteria
- Every P0 requirement has a traceable implementation path through the architecture
- Entity/component model choice is justified against this game's specific entity complexity
- Performance budget sums to available frame time on the target platform
- Save/load design covers all persistent state types identified in the GDD
- No platform-specific code exists outside the platform abstraction layer
- At least 3 game-specific patterns identified and placed in the architecture

### Output
path: P3-technical/S01-game-architecture.md
sections:
  - Engine Layer Structure
  - Entity/Component Design
  - Scene Management
  - Asset Pipeline
  - Data Serialization and Save System
  - Platform Abstraction
  - Performance Budget

---

## S02: Create Epics and Stories

### Required
true

### Goal
Decompose the architecture and requirements into implementable stories following story-spec-format.md, with gameplay stories including play-test criteria.

### Read Scope
- required: P2-design/DELIVERABLE.md
- required: P3-technical/S01-game-architecture.md

### Thesis
role: story-writer
instruction: |
  Create epics from game systems and break them into implementation stories:
  - **Epic creation**: one epic per major game system (e.g., CORE — core mechanics, PROG — progression, ECON — economy, UI — user interface, SAVE — save system, AUDIO — audio, NET — networking). Each epic has a description and acceptance criteria
  - **Story breakdown**: break each epic into stories following story-spec-format.md. For each story:
    - Metadata: epic, priority, complexity, dependencies, parallel group, estimated LOC, files
    - Requirement trace: PRD requirement → GDD system → UX screen
    - Acceptance criteria: testable conditions for completion
    - Technical spec: implementation details sufficient for a developer to start coding
    - Test plan: unit tests, integration tests, and for gameplay stories — play-test criteria
  - **Gameplay story play-test criteria**: stories that affect player-observable behavior must include play-test criteria: what the player should experience when the feature works correctly (e.g., "player can defeat the tutorial enemy within 3 attempts using only basic attack")
  - **Story sizing**: target each story at S or M complexity (< 300 LOC). Split L-complexity stories into smaller ones
  - **Parallel groups**: assign stories to parallel groups based on file independence and dependency order

  Ensure every P0 requirement has at least one story. Gameplay-critical paths (core loop, progression gates, economy transactions) must have dedicated stories, not be split across unrelated stories.

### Antithesis
role: granularity-verifier
instruction: |
  Verify story quality, granularity, and completeness:
  - **Independent implementability**: can each story be implemented and tested in isolation? Flag stories that implicitly depend on uncommitted work from other stories
  - **Size compliance**: are all stories within the 300 LOC target? Flag any story estimated above 300 LOC and suggest how to split it
  - **P0 traceability**: does every P0 requirement from the PRD have at least one story? List any P0 requirements with no corresponding story
  - **Play-test criteria coverage**: do all gameplay-critical stories (core mechanics, progression, economy transactions, difficulty) have play-test criteria? Flag gameplay stories with only code-level tests
  - **Dependency accuracy**: are story dependencies correct and complete? Are there hidden dependencies (story A creates a function that story B calls, but no dependency is declared)?
  - **Parallel group validity**: can stories in the same parallel group truly run in parallel? Do they modify the same files?

  For each granularity issue, propose the specific split or dependency correction needed.

### Convergence
target: output-quality
model: standard
weight: heavy

### Pass Criteria
- Every P0 requirement traces to at least one story
- No story exceeds 300 estimated LOC
- All gameplay-critical stories have play-test criteria in their test plans
- Story dependencies form a DAG (no cycles)
- Stories in the same parallel group share no files
- Each story has testable acceptance criteria (not subjective descriptions)

### Output
path: P3-technical/S02-epics-and-stories.md
sections:
  - Epic Index (epic ID, name, description, story count)
  - Story Specs (full story-spec-format.md per story)
  - Dependency Graph (text representation)
  - Parallel Group Assignment

---

## S03: Check Readiness

### Required
false

### Skip Condition
Small project with 3 or fewer stories.

### Goal
Validate that all stories are implementation-ready by cross-checking against architecture, verifying test plans, and checking parallel group safety.

### Read Scope
- required: P3-technical/S01-game-architecture.md
- required: P3-technical/S02-epics-and-stories.md

### Thesis
role: cross-checker
instruction: |
  Cross-check stories against architecture and validate implementation readiness:
  - **Architecture alignment**: for each story, verify the technical spec references real components, APIs, and data structures from the architecture. Flag specs that reference nonexistent architecture elements
  - **Test plan validation**: verify each story's test plan is executable — test inputs are concrete, expected outputs are specific, test setup is achievable. For gameplay tests, verify play-test criteria describe observable behavior
  - **Parallel group safety**: for each parallel group, verify stories share no mutable game state. Check for:
    - Same file modifications (already checked in S02, reconfirm)
    - Shared singleton access (e.g., two stories both modifying the global game state manager)
    - Shared asset dependencies (two stories expecting different formats for the same asset)
  - **Asset dependency declaration**: verify every story that requires art, audio, or data assets has those dependencies declared. Missing asset declarations cause runtime failures
  - **Integration point coverage**: verify that for every pair of systems that interact (from the GDD system interaction matrix), there is at least one story that tests the integration

  Produce a readiness report with READY/NOT_READY status per story and specific blockers for NOT_READY stories.

### Antithesis
role: completeness-verifier
instruction: |
  Verify the readiness check is thorough:
  - **AC + test plan universality**: does every single story have both acceptance criteria AND a test plan? List any story missing either
  - **Parallel group state isolation**: beyond file overlap, are there runtime state conflicts? Two stories in the same group that both initialize the same game system, register the same event handlers, or write to the same save data
  - **Asset dependency completeness**: are placeholder asset requirements specified (format, dimensions, naming)? Stories that need assets but don't specify requirements will block at implementation time
  - **Architecture reference accuracy**: do technical specs reference the correct architecture layer? (e.g., a UI story should reference the UI layer, not the engine core)
  - **Missing integration stories**: are there system pairs from the interaction matrix with no integration coverage? These become bugs in production

  For each completeness gap, specify the story ID and the specific missing element.

### Convergence
target: plan-validity
model: standard
weight: medium

### Pass Criteria
- Every story has acceptance criteria AND a test plan
- No parallel group has stories sharing mutable game state
- All asset dependencies are declared with format and naming requirements
- Every NOT_READY story has a specific, actionable blocker listed
- System interaction pairs from the GDD all have integration test coverage
- Readiness report covers 100% of stories

### Output
path: P3-technical/S03-readiness-check.md
sections:
  - Readiness Summary (READY/NOT_READY counts)
  - Per-Story Readiness Status
  - Parallel Group Safety Report
  - Asset Dependency Audit
  - Integration Coverage Matrix
  - Blockers and Resolutions

---

## S04: Project Context

### Required
false

### Skip Condition
Small project where context is self-evident from architecture and stories.

### Goal
Compile implementation context that agents need to write code correctly: conventions, engine idioms, folder structure, and integration patterns.

### Read Scope
- required: P3-technical/S01-game-architecture.md
- required: P3-technical/S02-epics-and-stories.md
- optional: P3-technical/S03-readiness-check.md

### Thesis
role: context-writer
instruction: |
  Create project-context.md with actionable implementation context:
  - **Folder structure**: complete directory tree showing where each type of file goes (source, assets, configs, tests, build output). Map architecture layers to directories
  - **Codebase conventions**: naming conventions (files, classes, functions, variables), code style rules, import ordering, documentation requirements. Be specific to the chosen language/engine
  - **Engine idioms**: patterns specific to the chosen engine/framework — lifecycle hooks, preferred APIs, deprecated APIs to avoid, common pitfalls. Include code snippets for the most common patterns
  - **Asset naming and organization**: naming scheme for sprites, models, audio, data files. Directory structure for assets. Format requirements per asset type
  - **Integration patterns**: how components communicate (events, direct calls, message bus, signals). Show the concrete integration pattern with a code example
  - **Error handling**: standard error handling approach — exceptions vs. result types, logging conventions, crash recovery patterns
  - **Build and run**: how to build, run, and test the project. Command-line instructions for common operations

  Context must be concrete enough that an agent implementing a story can follow it without additional questions. Avoid generic advice — every instruction should reference the actual project's architecture and technology choices.

### Antithesis
role: usefulness-verifier
instruction: |
  Verify the project context is actionable and accurate:
  - **Actionability**: can an agent reading only this document and a story spec produce correctly structured code? Are there ambiguities that would require guessing?
  - **Engine accuracy**: are engine-specific patterns accurate for the chosen engine version? Are there recommended patterns that are actually deprecated or anti-patterns?
  - **Concreteness**: does the context include concrete file paths, code snippets, and command-line examples? Or is it abstract advice (e.g., "follow best practices")?
  - **Completeness vs. noise**: does the context cover what agents actually need (folder structure, naming, patterns, commands) without including information they won't use?
  - **Architecture consistency**: do the conventions and patterns described here match the architecture from S01? Flag any contradictions

  For each usefulness gap, specify what concrete information is missing and provide an example of what it should look like.

### Convergence
target: output-quality
model: standard
weight: light

### Pass Criteria
- Folder structure maps every architecture layer to a concrete directory
- Code conventions include naming rules for the chosen language with examples
- At least 3 engine-specific patterns shown with code snippets
- Integration pattern demonstrated with a concrete code example
- Build/run/test commands are complete and executable
- No generic advice without project-specific application

### Output
path: P3-technical/S04-project-context.md
sections:
  - Folder Structure
  - Codebase Conventions
  - Engine Idioms and Patterns
  - Asset Naming and Organization
  - Integration Patterns
  - Error Handling
  - Build and Run Commands

---

## S05: Test Framework

### Required
false

### Skip Condition
Prototype phase where formal testing strategy is premature.

### Goal
Define the testing strategy: test layers, tools, gameplay test patterns, and performance thresholds.

### Read Scope
- required: P3-technical/S01-game-architecture.md
- optional: P3-technical/S04-project-context.md

### Thesis
role: test-strategist
instruction: |
  Create test-strategy.md defining the project's testing approach:
  - **Test layers**: define each layer and what it tests:
    - Unit tests: individual functions, pure game logic (damage calculation, pathfinding, state transitions)
    - Component tests: individual game systems in isolation (inventory management, save/load, progression)
    - Integration tests: system interactions (economy feeding into progression, combat triggering audio)
    - Gameplay behavior tests: player-observable behavior verification (can complete tutorial, can reach level 2, economy doesn't break after 100 transactions)
    - Performance tests: frame rate, memory, load times under target conditions
  - **Tools and frameworks**: testing framework for the chosen engine/language, assertion library, mocking approach for engine systems, performance profiling tools
  - **Gameplay test patterns**: how to test game-specific behavior:
    - State verification: assert game state after a sequence of player actions
    - Simulation: run N game ticks and verify invariants (no negative health, no infinite resources)
    - Replay testing: record input sequences, replay against new builds, compare outcomes
    - Balance verification: parameterized tests across difficulty levels
  - **Performance thresholds**: concrete targets tied to the target platform:
    - Frame rate: minimum and target FPS
    - Memory: peak memory budget by category
    - Load times: maximum acceptable load time per scene type
    - Input latency: maximum frame delay from input to visual response

  Every game system from the architecture must have at least one test layer assigned.

### Antithesis
role: coverage-verifier
instruction: |
  Verify the test strategy provides adequate coverage:
  - **System coverage**: does each game system from the architecture have an assigned test approach? List systems with no test strategy
  - **Gameplay behavior focus**: do gameplay tests verify player-observable behavior (what the player sees and experiences), not just code-level correctness? A test that "health variable decreases" is unit-level; a test that "player sees health bar decrease and death screen appears at zero" is gameplay-level
  - **Platform-tied thresholds**: are performance thresholds based on the actual target platform's capabilities, or are they generic? (e.g., "60 FPS" is meaningless without specifying the hardware)
  - **Test data strategy**: how is test data managed? Are there fixtures, factories, or generated data? Is test data isolated between tests?
  - **Edge case coverage**: does the strategy account for edge cases that are common in games — save corruption recovery, alt-tab during loading, controller disconnect mid-game, network interruption in multiplayer?

  For each coverage gap, specify the system or scenario missing test coverage and the recommended test approach.

### Convergence
target: output-quality
model: standard
weight: medium

### Pass Criteria
- Every architecture component has at least one test layer assigned
- Gameplay behavior tests describe player-observable outcomes, not just code assertions
- Performance thresholds specify the target hardware/platform
- At least 3 gameplay test patterns documented with concrete examples
- Test data strategy defined (fixtures, factories, or generation approach)
- At least 2 game-specific edge cases have test approaches (save corruption, input disconnect, etc.)

### Output
path: P3-technical/S05-test-strategy.md
sections:
  - Test Layers
  - Tools and Frameworks
  - Gameplay Test Patterns
  - Performance Thresholds
  - Test Data Strategy
  - Edge Case Coverage

---

## S06: Test Design

### Required
false

### Skip Condition
Prototype phase, or test framework step was skipped.

### Goal
Design specific test cases for critical game systems: core loop, economy balance, progression gating, and boundary conditions.

### Read Scope
- required: P3-technical/S01-game-architecture.md
- required: P3-technical/S02-epics-and-stories.md
- optional: P3-technical/S05-test-strategy.md

### Thesis
role: test-designer
instruction: |
  Create test-designs.md with concrete test cases for critical game systems:
  - **Core loop tests**: test cases verifying the moment-to-moment gameplay cycle works end-to-end. Include setup, player action sequence, expected outcomes at each step
  - **Economy balance tests**: parameterized tests verifying resource flow balance:
    - No resource can grow unbounded (test 1000 cycles of earn-spend)
    - No resource can go negative
    - Exchange rates produce expected values across all currency pairs
    - Inflation/deflation stays within designed bounds over extended play
  - **Progression gate tests**: verify every progression gate:
    - Player meets prerequisites → gate opens
    - Player lacks prerequisites → gate blocks with correct feedback
    - No skip/bypass exists (unless intentional)
    - Progression state survives save/load round-trip
  - **Save/load round-trip tests**: for each persistent data type, verify:
    - Save → load → compare produces identical game state
    - Save format versioning handles old saves correctly
    - Corrupted save detection works (truncated file, wrong version, tampered data)
  - **Boundary conditions**: test extreme values for every numeric game parameter:
    - Zero, one, max for inventories, currencies, stats
    - Timer at zero, negative, overflow
    - Maximum simultaneous entities on screen
  - **Regression scenarios**: test cases for common game bugs:
    - Double-input (pressing attack twice in one frame)
    - State transition during animation (die while opening chest)
    - Resource operation during loading (spend currency while scene transitions)

  Each test case must have: ID, preconditions, action sequence, expected result, and the system being tested.

### Antithesis
role: rigor-verifier
instruction: |
  Verify test designs catch the bugs that actually ship in games:
  - **Exploit vector coverage**: do balance tests check for exploit vectors? Common ones: sell-buy arbitrage, duplicate items via timing, negative cost transactions, overflow to max value
  - **Progression gate completeness**: is every gate tested in both directions (can pass, can't pass)? Are gates tested after save/load?
  - **Save/load thoroughness**: do round-trip tests cover ALL persistent state types? Are mid-action saves tested (save during combat, save during transition)?
  - **Multiplayer desync** (if applicable): are there tests for state divergence between clients? Common desync sources: floating-point determinism, unordered event processing, client-side prediction rollback
  - **Regression realism**: do regression scenarios cover the actual failure modes of the game's architecture? (e.g., if using ECS, test for component query order sensitivity; if using state machines, test for missing transitions)
  - **Test case specificity**: does each test case have concrete values, not placeholders? "Player has 100 gold" not "player has some gold"

  For each rigor gap, write the specific test case that is missing.

### Convergence
target: output-quality
model: standard
weight: medium

### Pass Criteria
- Core loop has at least 3 end-to-end test cases
- Economy tests check for at least 2 exploit vectors (arbitrage, duplication, overflow, negative)
- Every progression gate has both pass and block test cases
- Save/load tests cover all persistent data types with round-trip verification
- Boundary tests cover zero, one, and max for at least the 5 most critical game parameters
- Each test case has concrete values (no placeholders)

### Output
path: P3-technical/S06-test-designs.md
sections:
  - Core Loop Tests
  - Economy Balance Tests
  - Progression Gate Tests
  - Save/Load Round-Trip Tests
  - Boundary Condition Tests
  - Regression Scenarios

last_step: true

---

## Exit Contract

The following must be present in the DELIVERABLE.md for Phase 4 to begin:

- Architecture summary (components, interfaces, data model)
- Story index with dependency order
- Parallel execution plan (batches of independent stories)
- Per-story estimated LOC and complexity
- Project context document
- Test strategy and critical test cases
