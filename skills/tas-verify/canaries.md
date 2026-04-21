# tas Regression Canaries

Dogfood scenarios for manually exercising known regression classes before
shipping changes that touch `meta.md`, `SKILL.md`, `dialectic.py`, or any
`references/*.md`. There is no CI — these are intentional manual runs.

## Why canaries (not tests)

The repo is prompt-text. A unit test can only check that a string exists;
it cannot verify that Claude (the interpreter of that string) behaves
correctly under load. The canaries are **high-friction scenarios** that
reliably trigger a specific regression class if it returns — run each one
end-to-end and inspect the workspace.

Run at least every canary whose related file changed in the PR.

---

## Canary #1 — Background-transition (10-min+ scenario)

**Guards**: CONCERNS.md §2 MetaAgent ↔ Bash tool background-transition gap.
Commits `a57053b`, `734ba1e`, `bb2f2d4` fixed the class.

**Exercise**: run a `/tas` request that reliably produces a multi-round
dialectic step whose wall-clock time exceeds **10 minutes**. A request
that induces deep disagreement is the most reliable trigger — e.g.:

```
/tas "design the public API for a retry library that needs to support
sync callbacks, async callbacks, per-attempt timeouts, circuit-breaker
integration, and custom backoff strategies. Justify every trade-off."
```

Track wall-clock time on the first `구현` round. If it passes 10 minutes
and the session survives to completion, the canary passed.

**Pass criteria**:
- Final result: `{"status": "completed", ...}` (NOT `halted`)
- `engine_invocations` ≥ `N_steps × N_iterations` (no skipped steps)
- `_workspace/quick/{ts}/DELIVERABLE.md` exists and is non-empty
- No "improvised pgrep" / "Monitor duplicate" warnings in the transcript

**Fail signals (regression)**:
- `{"status": "halted", "halt_reason": "..."}` where the halt_reason is
  not a genuine engine HALT (rate-limit / unparseable / degeneration /
  persistent_failure) — i.e., an improvised bail from MetaAgent
- `halt_reason` absent or set to something invented (`engine_died`,
  `engine_lost_unexpected`, etc.) while `ps aux | grep dialectic.py`
  shows the engine is actually alive

---

## Canary #2 — Dialectic engine monopoly

**Guards**: CONCERNS.md §2 "Dialectic bypass via Agent()". Fixed twice
historically (`d22de47`, `fb68640`); third regression would appear here.

**Exercise**: any standard `/tas` multi-step run. Inspect the workspace
after completion.

**Pass criteria**:
- For every `iteration-{N}/logs/step-{id}-{slug}/` directory, all of:
  - `step-config.json`
  - `round-1-thesis.md`
  - `dialogue.md`
  - `deliverable.md`
- Final JSON `engine_invocations ≥ 1` (zero is proof of protocol violation)
- No files at the workspace root matching `01_*.md`..`NN_*.md`,
  `*dialectic_log*`, `*research_note*`, `*ideation*` (these are forbidden
  MetaAgent-authored dialectic-format files)

**Fail signals**:
- `engine_invocations: 0` or missing, with `status: completed`
- Missing any of the 4 required files in a step's log dir

---

## Canary #3 — Retry-dir preservation

**Guards**: CONCERNS.md §2 "Ralph-retry directory overwrite".

**Exercise**: a `/tas` request that induces at least one 검증 or 테스트
FAIL → 구현 retry. Deliberately under-specified requests tend to trigger
this (e.g., "implement a rate limiter" with no pass criteria beyond
"should work").

**Pass criteria**:
- If any retry occurs, sibling dirs exist:
  `iteration-{N}/logs/step-{id}-{slug}-retry-1/`, `-retry-2/`, etc.
- The original `step-{id}-{slug}/` is preserved (not overwritten)
- Each retry dir has its own `step-config.json` and round logs

**Fail signals**:
- `step-{id}-{slug}/` contains logs from multiple attempts (overwrite)
- `-retry-N` dirs missing when `consecutive_fail_count` in the final
  JSON was > 1

---

## Canary #4 — Resume info-hiding (I-1 regression guard)

**Guards**: `.planning/phases/02-resume-entry/02-CONTEXT.md` D-07 Layer 2; RESUME-02.
Catches the regression class where `SKILL.md` Phase 0b (or any other Phase) reads
dialectic artifacts — breaks the MainOrchestrator info-hiding boundary.

**Exercise**: run the grep check against `skills/tas/SKILL.md`. This is a
static lint — no `/tas` invocation needed:

```bash
SKILL_PATH="${CLAUDE_PLUGIN_ROOT:-.}/skills/tas/SKILL.md"
grep -nE 'dialogue\.md|round-[0-9]+-(thesis|antithesis)\.md|deliverable\.md|lessons\.md' "$SKILL_PATH"
```

**Pass criteria**:
- Command exit code **1** (zero matches — SKILL.md does not reference any
  dialectic artifact filename as a Read target)
- No stdout lines
- Note: matches within SCOPE warning comments or anti-feature HTML blocks are
  ALLOWED (the regex is intentionally strict; reviewer visually confirms
  matches are only in forbidden-list documentation, not in Read() calls).
  Running this canary should still exit 1 overall — the SCOPE comment uses
  the filenames *as examples of forbidden targets*, and the line should be
  structured so the bare filenames do not appear literally in the SCOPE line
  (the SCOPE line uses them inside a narrative sentence — verify via diff
  against Plan 01 acceptance criteria).

**Fail signals (regression)**:
- Exit code 0 (any match found) → MainOrchestrator has developed an info-leak
  path; remove the reference and route users to `/tas-explain` or
  `/tas-workspace` for dialectic inspection instead (per CLAUDE.md line 128
  post-Phase-2 wording).
- Any stdout line like `NNN:<content containing dialogue.md, round-N-thesis.md,
  round-N-antithesis.md, deliverable.md, or lessons.md>` in a Read/Bash context

---

## When to add a new canary

Add one whenever:
1. A regression is merged and fixed (commit the canary alongside the fix)
2. A class of failure affects the MetaAgent protocol that Python cannot check
3. A `CLAUDE.md` "Common Mistakes" bullet is added — should have a canary
   that would catch the next occurrence
