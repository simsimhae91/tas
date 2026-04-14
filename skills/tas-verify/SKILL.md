---
name: tas-verify
description: >
  Independent post-synthesis verification for tas outputs. Traces boundary values
  through produced code, audits function composition, and validates mathematical
  invariants. Use after /tas completes or on any code that needs compositional
  integrity checking. Trigger on: /tas-verify, "verify tas output", "tas 검증",
  "합성 검증", "boundary check", "trace values".
---

# tas:verify — Post-Synthesis Verification

You perform **independent verification** of code produced by a `/tas` session or any code the user points you to. You are NOT part of the dialectic loop — you run AFTER it completes, or standalone.

Your single purpose: find defects that text-based review misses by **tracing concrete values through computation chains**.

## When to Use

- After any `/tas` quick session that produced code (especially complex 4-step runs)
- When the user wants compositional integrity checking on existing code
- When reviewing functions that chain arithmetic operations with defensive measures

Note: tas's 검증 step already performs static review during the dialectic. tas-verify
complements that with **concrete-value boundary tracing** — a different technique that
catches defects text-based review misses.

## Process

### Step 1: Identify the Target

Determine what code to verify:

1. If `$ARGUMENTS` contains a file path, verify that file
2. Otherwise, auto-detect: check `_workspace/quick/` for the most recently updated
   timestamped directory (ignore `classify-*` dirs)
3. Read the final `DELIVERABLE.md` from the identified workspace
4. Identify all code files that were written or modified during the session
   (use `git log` / `git diff` since the workspace's `created` timestamp)

If no target is found, ask the user what to verify.

### Step 2: Function Inventory

For each function in the target code:

1. **Signature**: name, parameters (with types and defaults), return type
2. **Numeric parameters**: list every parameter that participates in arithmetic
3. **Call chain**: which functions call which, and what values flow between them
4. **Defensive measures**: any caps, clamps, guards, and WHERE they are applied (inside the function or in the caller)

Present this as a table before proceeding.

### Step 3: Boundary Value Tracing

For each numeric parameter, select boundary values:

| Category | Values |
|----------|--------|
| Zero boundary | 0, -1, 1 |
| Type boundary | Number.MAX_SAFE_INTEGER, Infinity, NaN |
| Domain boundary | the default value, the declared max (e.g., maxDelay), the cap value ± 1 |

For each meaningful combination of boundary values:

1. **Trace through the call chain** — compute the concrete intermediate value at every function boundary
2. **Record each step**: `functionName(inputs) → intermediate → next function(intermediate) → ...`
3. **Flag violations**:
   - NaN at any intermediate step
   - Infinity at any intermediate step (before a cap)
   - Negative value where positive is expected
   - Type change (number → undefined, etc.)
   - Defensive measure receiving a value it can't handle (`Math.min(NaN, cap)` = NaN)

### Step 4: Composition Audit

For each pair of functions where output(A) → input(B):

1. **Range analysis**: What is the full range of A's output? Does it fit B's expected input?
2. **Defense placement**: If B applies a cap/clamp, can A produce a value that corrupts computation BEFORE B's defense? (e.g., jitter calculated from Infinity before maxDelay cap)
3. **Order dependency**: Would moving the defense INTO function A fix the issue?

### Step 5: Contract Verification

For each public (exported) function:

1. Does it honor its documented contract for ALL valid inputs?
2. Are there inputs the type system allows but the implementation doesn't handle?
3. Does every error message accurately describe what happened for that specific code path?

## Output Format

```markdown
## tas-verify — Verification Report

### Target
- File(s): {paths}
- Session: {workspace path if applicable}

### Function Inventory
| Function | Numeric Params | Calls | Defensive Measures |
|----------|---------------|-------|-------------------|
| retry | maxRetries, baseDelay, maxDelay | computeDelay, sleep | Math.min(delay, maxDelay) in caller |
| computeDelay | base, attempt | — | none |
| sleep | ms | — | none |

### Boundary Traces

#### Trace 1: {description}
```
Input: maxRetries=1025, baseDelay=1000, strategy=exp+jitter, maxDelay=30000
→ computeDelay(1000, 1025, exp+jitter)
  → base * Math.pow(2, 1024) = 1000 * Infinity = Infinity
  → Math.random() * Infinity = NaN (when random=0) or Infinity (when random>0)
  → return NaN or Infinity
→ Math.min(NaN, 30000) = NaN  ⚠ INVALID
→ sleep(NaN) → setTimeout(fn, NaN) → fires immediately (NaN treated as 0)
```
**Verdict**: ⚠ DEFECT — cap applied at wrong layer

#### Trace 2: {description}
...

### Composition Issues
| A → B | Issue | Fix |
|-------|-------|-----|
| computeDelay → Math.min | computeDelay can return NaN/Infinity; Math.min doesn't sanitize NaN | Move cap inside computeDelay, apply before jitter multiplication |

### Contract Violations
| Function | Contract | Violation |
|----------|----------|-----------|
| retry | "maxRetries: max number of retries" | negative maxRetries → 0 loop iterations → throws undefined |

### Verdict
- **CLEAN**: No issues found — all traces produce valid values
- **DEFECTS FOUND**: {count} composition/contract issues requiring attention
```

## Principles

1. **Concrete over semantic**: Never accept "X caps all values" as evidence. Trace the actual computation
2. **Intermediate values matter**: A final result that happens to be correct doesn't excuse invalid intermediate steps — they indicate fragile composition that breaks under different inputs
3. **The type signature is the contract**: If a parameter is typed as `number`, every finite number, ±Infinity, NaN, and ±0 are valid inputs unless explicitly constrained
4. **Defense at the source**: A cap in the consumer doesn't protect the producer's internal computation
