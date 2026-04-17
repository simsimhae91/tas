# Common Failure Patterns for Planning Review

MetaAgent reads this file and injects its contents into the antithesis system prompt
during 기획 (planning) steps ONLY. ThesisAgent does not receive this information —
this asymmetry is intentional to reduce confirmation bias.

## Architectural Failure Patterns

- **Over-abstraction**: Interfaces/abstractions introduced for a single implementation.
  Watch for: generic factories, strategy patterns, or plugin systems when only one
  variant exists or is planned.
- **Leaky layering**: Lower layer assumes knowledge of upper layer's behavior.
  Watch for: utility functions that check caller-specific state, shared mutable state
  across module boundaries.
- **Missing error boundary**: Happy-path design without considering where errors
  originate and who is responsible for handling them. Watch for: error propagation
  that crosses trust boundaries without transformation.

## Design Decision Failure Patterns

- **Premature technology lock-in**: Choosing a framework/library before confirming
  it supports all stated requirements. Watch for: enthusiasm for a specific tool
  without checking edge-case support.
- **Scope creep disguised as thoroughness**: Adding "nice-to-have" capabilities
  framed as requirements. Watch for: pass criteria that weren't in the original
  request but appear in the design.
- **Under-scoping critical paths**: Deferring hard decisions (data migration,
  backward compatibility, concurrent access) to implementation. Watch for:
  "we'll handle that in 구현" for issues that affect the design shape.

## Compositional Failure Patterns

- **Type-contract divergence**: Interface types that don't match runtime values
  (e.g., `string` declared but `null` possible, `number` declared but `NaN` flows).
- **Ordering dependency**: Design that implicitly requires operations in a specific
  sequence but doesn't enforce it structurally.
- **Naming-behavior mismatch**: Function/variable names that promise one thing but
  the described behavior does another (e.g., `getUser` that also creates on miss).
