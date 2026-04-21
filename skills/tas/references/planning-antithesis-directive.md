# Planning-Phase Antithesis Directive (기획-only)

MetaAgent reads this file and injects its contents into the **antithesis
system prompt** during 기획 (planning) steps ONLY. Thesis does NOT receive it.
The asymmetry is intentional — it reduces confirmation bias without biasing
the proposer.

## When to apply

- `S.name == "기획"` → append this directive AND the contents of
  `failure-patterns.md` (also read in Phase 1) to the antithesis system prompt
- Any other step name → do not append

## What to append verbatim

Append the following block to `{LOG_DIR}/antithesis-system-prompt.md` after the
standard `STEP ROLE` / `STEP GOAL` / `PASS CRITERIA` block:

```
---
## Planning-Phase Directive

When evaluating the thesis's design proposal, go beyond verifying completeness
within the proposed approach. Actively consider:

1. **Alternative framework**: Could a fundamentally different architectural pattern,
   library choice, or structural approach better serve the stated requirements?
   If yes, present it as a COUNTER with concrete trade-off comparison.
2. **Assumption challenge**: What implicit assumptions does the thesis make about
   the problem space? Are any of these assumptions worth questioning?
3. **Scope tension**: Is the proposed scope genuinely minimal, or does it include
   speculative abstractions? Conversely, does it under-scope and defer critical
   decisions that will be harder to fix later?

---
## Historical Failure Patterns (Asymmetric — thesis does not have this information)

{failure_patterns content}

Use these patterns as a checklist when evaluating the thesis's design proposal.
Flag any matches as specific refinement items in your evaluation.
```

Substitute `{failure_patterns content}` with the full text of
`references/failure-patterns.md` (read once in Phase 1).

## What NOT to do

- ❌ Append any part of this block to `thesis-system-prompt.md` — symmetry
  defeats the anti-confirmation-bias mechanism
- ❌ Summarize or reword the directive — it is calibrated; rewording shifts
  antithesis behavior in hard-to-trace ways
- ❌ Apply this directive to non-기획 steps — the review lenses for
  구현/검증/테스트 are different and live in `antithesis.md`
