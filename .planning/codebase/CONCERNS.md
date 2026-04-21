# Codebase Concerns

**Analysis Date:** 2026-04-21

This plugin's "code" is prompt text. Most concerns here are **prompt-level behavioral
fragilities** — failure modes that don't exist in ordinary software but that dominate
this system. Classical bugs (Python runtime issues) are secondary and well-contained.

---

## Tech Debt

### meta.md exceeds the Claude attention-degradation threshold

- Issue: `agents/meta.md` is ~6,688 tokens (564 lines). Research referenced in
  memory (`project_prompt_sizing.md`, 2026-04-17) places Claude's accuracy
  degradation at ~5,500 tokens — meta.md is inside the "active degradation" zone.
  This is the single largest known risk to orchestration reliability because
  MetaAgent's conformance (engine-only producer, whitelist writes, convergence
  model, retry routing, asymmetric planning) all depend on it being followed
  exactly.
- Files: `skills/tas/agents/meta.md`
- Impact: Silent drift in MetaAgent behavior as the model under-weights later
  instructions; the attestation invariants (engine_invocations ≥ M×K,
  forbidden Write patterns, Phase 4 self-check) are the last line of defense
  and are themselves buried late in the file.
- Fix approach: Structural refactor to ~550 lines. Extract the Focus Angle
  rotation table (lines 231–244) into `references/workflow-patterns.md`
  (already partially duplicated there), move the 기획-only antithesis
  enhancement block (lines 316–350) into a standalone reference that MetaAgent
  reads and concatenates, and remove duplication of workspace structure
  (already canonical in `workspace-convention.md`). Target 2026-04-17 memory
  plan.

### SKILL.md above recommended 500-line ceiling

- Issue: `skills/tas/SKILL.md` is 480 lines (~4,456 tokens). At the edge of
  Anthropic's recommended 500-line cap for SKILL.md. HALT recovery tables,
  error-classification table, and Phase 3 display rendering dominate.
- Files: `skills/tas/SKILL.md`
- Impact: Harder for MainOrchestrator to maintain the thin-scheduler discipline
  under long request text; the lower the priority of instructions near the
  bottom (including the Configuration table that documents defaults), the more
  likely they are to be skipped.
- Fix approach: Move HALT Reason Labels / Recovery Guidance tables (lines
  389–437) and the error-detection table (lines 458–466) into a
  `references/halt-recovery.md` file. MainOrchestrator reads it on demand only
  when `status: halted`.

### Duplication of load-bearing rules across files

- Issue: Three documented redundancies exist — (1) Quality Invariants in
  `meta.md` §Quality Invariants + `antithesis.md` §Pre-ACCEPT + `CLAUDE.md`;
  (2) Focus Angle rotation in `meta.md` Phase 2b + `workflow-patterns.md`
  "Iteration Support" section; (3) Retry/FAIL flow in `meta.md` Phase 2d +
  `workspace-convention.md` §"Iteration & Retry Flow".
- Files: `skills/tas/agents/meta.md`, `skills/tas/agents/antithesis.md`,
  `CLAUDE.md`, `skills/tas/references/workflow-patterns.md`,
  `skills/tas/references/workspace-convention.md`
- Impact: When one copy updates and others don't (it happens —
  commit `6bbb12e` was specifically a "cross-file consistency" fix), agents
  behave inconsistently. The Python engine has no way to detect this drift.
- Fix approach: Elect one source of truth per rule. Quality Invariants live in
  `antithesis.md` (because antithesis enforces them); meta.md references the
  check, CLAUDE.md links to antithesis.md. Focus Angles live in
  `workflow-patterns.md`. Retry flow lives in `workspace-convention.md`.

### "ISSUE-NN" comments in dialectic.py with no external tracker

- Issue: `dialectic.py` carries inline `ISSUE-01`, `ISSUE-07`, `ISSUE-11`,
  `ISSUE-12`, `ISSUE-20` annotations that reference fix rationale. There is
  no issue tracker in this private repo, so the numbers are opaque to future
  readers.
- Files: `skills/tas/runtime/dialectic.py` lines 212, 220, 334, 363, 388,
  484, 608, 615, 618, 652, 666, 741
- Impact: Low — comments still describe intent inline. But the ID references
  are dead links.
- Fix approach: Either (a) replace IDs with short descriptive tags
  (`# INVERTED-TERMINAL:` instead of `# ISSUE-01:`), or (b) add a
  `runtime/CHANGELOG.md` mapping IDs to commits.

---

## Prompt/Behavioral Fragilities (this project's unique class)

### MetaAgent ↔ Bash tool background-transition gap 🔴 CONFIRMED IN PRODUCTION

- Risk: `agents/meta.md` invokes the engine via
  `Bash({ command: "bash run-dialectic.sh {step-config}", timeout: 900000 })`
  (line 426) and `timeout: 300000` (line 142). The Claude Code Bash tool hard-
  caps foreground timeout at **600,000ms (10 min)**. A single dialectic round
  takes 8–12 min (thesis → antithesis LLM roundtrip); multi-round steps
  routinely exceed 10 min. On hitting the cap, the tool silently transitions
  to background and returns a shell ID — this is NORMAL tool behavior, not a
  failure. But meta.md contains ZERO protocol for handling it: grep for
  `run_in_background`, `BashOutput`, `background`, `shell ID`, `poll` returns
  **0 matches**. Phase 2 step 8 ("Parse result from the last line of stdout",
  line 430) assumes synchronous completion.
- Files: `skills/tas/agents/meta.md` lines 142, 422–427, 430
- Observed failure mode (2026-04-21 session):
  1. Engine crosses 10-min mark while still healthy (`ps aux | grep
     dialectic.py` shows live PID)
  2. Bash tool returns `{bash_id: "shell-N"}` instead of stdout
  3. MetaAgent has no re-capture instruction → improvises a liveness check,
     e.g. `pgrep -fl "run-dialectic|dialectic.py|step-config.json"`
  4. The improvised pattern returns empty (macOS pgrep/argv quirks, OR the
     pattern is wrong for the exec'd process). The working pattern in
     `hooks/stop-check.sh` line 63 is not referenced from meta.md
  5. MetaAgent also spams the harness Monitor tool (multiple overlapping
     starts on the same file) trying to see output
  6. All probes return empty → MetaAgent concludes "engine died" → returns
     `{"status": "halted"}` while the engine is still running and eventually
     completes to an orphaned log directory
  7. stop-check.sh's 3-min mtime window sees recent file activity and lets
     the session exit — the user sees a "timeout" that was never a timeout
- Current mitigation: None. `timeout: 900000` above the 600,000 cap is a
  strong tell that the author was unaware of the cap.
- Root cause: Single design gap — meta.md treats engine invocation as
  synchronous. The three observable symptoms (bogus pgrep pattern,
  Monitor spam, false halted JSON) are all emergent improvisations from
  this one missing protocol.
- Recommendation:
  1. Invoke with `run_in_background: true` from the start — never rely on
     implicit foreground-to-background transition.
  2. Document a polling loop using `BashOutput(bash_id)` with a stated
     cadence (e.g., 30s intervals) until the process exits or the final JSON
     line appears on stdout.
  3. Canonize the stop-check.sh liveness pattern for MetaAgent's use:
     `ps -eo args | grep -F "dialectic.py" | grep -qF "/$WS_KEY/"` —
     never invent ad-hoc pgrep patterns.
  4. Remove `timeout: 900000` — it is a lie above 600,000.
  5. Add a "background-transition response" section to meta.md Phase 2,
     parallel to the existing "Parse result" step.
- Test: Add a `/tas-verify` canary that drives a multi-round step deliberately
  designed to exceed 10 min and asserts MetaAgent completes rather than
  halting. This directly exercises the class of bugs that was fixed twice
  (`d22de47`, `fb68640`) for dialectic bypass and is now being fixed a third
  time for the timeout boundary.

### Scope Prohibition drift in MainOrchestrator

- Risk: The Trivial Gate (`SKILL.md` lines 96–111) tells MainOrchestrator to
  judge "from the request text alone — do NOT read project files for this
  decision." But Claude has a strong drive to be helpful and may read source
  files "to classify better" and then short-circuit to direct implementation.
- Files: `skills/tas/SKILL.md` §Trivial Gate, §SCOPE PROHIBITION (lines
  40–48), `CLAUDE.md` §"Scope Prohibition Is a Behavioral Guardrail"
- Current mitigation: Explicit prohibition list; "NEVER fall back to direct
  implementation on any error" at line 450; Stop-hook (`hooks/stop-check.sh`)
  blocks session exit when REQUEST.md exists but DELIVERABLE.md is missing
  — catches the "bypassed MetaAgent" case post-hoc.
- Remaining risk: If MainOrchestrator never creates REQUEST.md (because it
  skipped Phase 2 entirely), the stop-hook has nothing to guard — the
  workspace is empty so `ls -1d "${WORKSPACE_BASE}/"*/ | sort -r | head -1`
  returns nothing and the hook exits 0 (`hooks/stop-check.sh` lines 26–29).
  The hook only catches partial runs, not full bypass.
- Recommendation: Consider a session-scoped marker (e.g., `$TMPDIR/tas-invoked`)
  set by SKILL.md at Phase 0 that the Stop hook checks independently of
  workspace existence.

### Information-Hiding leaks

- Risk: If SKILL.md accretes references to MetaAgent internals
  (convergence model, review lenses, thesis/antithesis roles),
  MainOrchestrator develops a behavioral bias to run the dialectic itself
  rather than delegating.
- Files: Guarded by `CLAUDE.md` §"Information Hiding Is Load-Bearing" and
  `skills/tas/SKILL.md` line 34 ("Do NOT read agent files")
- Current mitigation: Prohibition text + the bootstrap prompt tells MetaAgent
  to `Read("${SKILL_DIR}/agents/meta.md")` itself. SKILL.md never sees
  meta.md content — only the Agent() prompt fragment references the path.
- Remaining risk: Reviewers editing SKILL.md may innocently paste a sentence
  like "MetaAgent runs thesis + antithesis for each step" "for clarity" and
  thereby undo the isolation. There is no automated check.
- Recommendation: Add a unit-style grep guard (dogfooded via `/tas-verify`)
  that fails if `SKILL.md` contains tokens `thesis`, `antithesis`, `PingPong`,
  `convergence`, `정반합` outside whitelisted sections. Currently implicit in
  review discipline only.

### Dialectic bypass via Agent() instead of the engine

- Risk: MetaAgent could spawn thesis/antithesis via Agent() or Write dialectic
  content itself (role-play) rather than invoking `bash run-dialectic.sh`.
  The commit history shows this was fixed twice (`d22de47`, `fb68640`:
  "strengthen meta.md protocol enforcement against dialectic bypass"),
  suggesting the prompt-level guard is not fully stable.
- Files: `skills/tas/agents/meta.md` §"CRITICAL — Dialectic Engine is the
  ONLY Producer" (lines 41–63), §"Phase 4: Pre-Output Self-Check" (lines
  487–500)
- Current mitigation: (1) explicit prohibition with whitelist of permitted
  Write targets; (2) mandatory `engine_invocations` attestation in final JSON;
  (3) Phase 4 bash self-check that greps the workspace for required engine
  artifacts (`round-1-thesis.md`, `dialogue.md`, `deliverable.md`) and
  HALTs with `missing_engine_artifacts` if any are absent;
  (4) MainOrchestrator Phase 3 validation (`SKILL.md` lines 285–293) warns
  if `engine_invocations: 0`.
- Remaining risk: Self-check only verifies file *existence*, not *authorship*.
  If MetaAgent wrote the files itself (simulating the engine's output
  format), the self-check still passes. A sufficiently ambitious MetaAgent
  simulation could fool it.
- Recommendation: Have `dialectic.py` stamp each round log with a
  per-invocation nonce (captured in step-config.json) that MetaAgent cannot
  know ahead of time. Phase 4 self-check then verifies nonce consistency.

### Premature convergence if a fixed cap leaks in

- Risk: The "no fixed iteration cap" rule is the core quality guarantee.
  An accidental cap would mean "all runs converge after N rounds regardless
  of depth" — shallow consensus.
- Files: `skills/tas/agents/meta.md` §Convergence Model (lines 526–539),
  `skills/tas/runtime/dialectic.py` §"Main dialectic loop"
- Current mitigation: Dialectic engine has only HALT-condition exits
  (rate-limit, degeneration, unparseable verdicts, explicit HALT verdict)
  — no round-count check. Verified by reading `dialectic.py` lines 449–603:
  the `while True:` has no iteration counter. `CLAUDE.md` §"Common
  Mistakes" flags "Making convergence depend on round count" as a tracked
  regression.
- Remaining risk: The `max_turns=50` in `_make_client`
  (`dialectic.py` line 348) is a per-agent SDK-session turn cap, not a
  round cap — but it does mean conversations hitting 50 exchanges will
  fail silently in SDK with no HALT reason surfaced. This is unlikely
  in practice but is an upper bound masquerading as a safety net.
- Recommendation: Add explicit logging / a `max_turns_exceeded` HALT reason
  so operators can distinguish natural convergence from SDK turn exhaustion.

### Ralph-retry directory overwrite

- Risk: Within-iter retry writes to `step-{id}-{slug}/`; if a second attempt
  reuses the same path, the original FAIL evidence is destroyed.
- Files: `skills/tas/agents/meta.md` §"Phase 2d" (line 301) and §"Edge Cases"
  (line 556), `skills/tas/references/workspace-convention.md` §"Within an
  iteration" (lines 220–224)
- Current mitigation: Documented rule — retries go to `-retry-{N}` sibling
  dirs, originals preserved. `CLAUDE.md` §"Common Mistakes" flags overwrites
  as a tracked regression.
- Remaining risk: Enforcement is prompt-level only — MetaAgent must choose
  the right path. No Python-level assertion rejects a write to an existing
  step dir.
- Recommendation: `dialectic.py` could refuse to start if `log_dir` already
  contains `round-1-thesis.md` (engine-level precondition). Forces MetaAgent
  to pick unique paths.

### lessons.md pruning

- Risk: Lessons.md must be append-only. If an agent prunes it "to stay
  concise", later iterations lose context and repeat mistakes.
- Files: `skills/tas/agents/meta.md` Phase 2f, `CLAUDE.md` §"Iteration Loop"
- Current mitigation: Prompt instructions ("never prune prior entries")
  appear in three places.
- Remaining risk: No Python-level check. MetaAgent uses Write to update
  lessons.md — a full overwrite looks identical to an append in the tool
  stream.
- Recommendation: Use Edit tool with append-only semantics (insertion at
  EOF), or have Phase 4 self-check compare `lessons.md` line count to
  the previous iteration's line count and HALT on shrinkage.

### Unparseable verdicts and verdict-format drift

- Risk: The dialectic engine parses antithesis verdicts via regex patterns
  (`dialectic.py` lines 174–192). If an antithesis Claude produces a verdict
  in an unrecognized format (e.g., "I'd go with ACCEPT here"), the engine
  returns UNKNOWN and treats it as REFINE — dialogue continues. After 5
  consecutive UNKNOWNs it HALTs with `unparseable_verdicts`.
- Files: `skills/tas/runtime/dialectic.py` §`_VERDICT_PATTERNS`,
  §"Degeneration detection constants", `skills/tas/agents/antithesis.md`
  §"Output Format"
- Current mitigation: Eight regex patterns covering `## Response:`,
  `### Updated Assessment`, `**Response**:`, plain `Response:`, inverted
  `## Judgment:`, Korean `판정:`, and standalone `**ACCEPT**`. Self-test
  in `_self_test()` covers 20+ cases.
- Remaining risk: Localized verdicts (`판정` for Korean) are partial — only
  one Korean phrasing is matched. A Japanese/Chinese/French dialogue would
  fail every pattern. Also, antithesis.md says the `## Response: {VERDICT}`
  line is "machine-parsed" — but the engine does not reject alternative
  patterns loudly, it silently treats them as REFINE for up to 5 rounds.
- Recommendation: Tighten the system prompt language: on first UNKNOWN,
  antithesis should be told explicitly in the next round's input
  "Your last response lacked the required verdict header. Use exactly
  `## Response: ACCEPT|REFINE|COUNTER|HALT`." Currently only a stderr warning
  is printed.

### Rate-limit detection false negatives/positives

- Risk: Rate-limit detection uses 7 English substring patterns with a
  length gate (`dialectic.py` lines 44–57). A rate-limit error from the
  API that uses different phrasing, or from a non-English locale, would
  not be caught — the short response would instead trip the degeneration
  HALT after 3 rounds, producing `dialogue_degeneration` when the true
  cause is `rate_limit`.
- Files: `skills/tas/runtime/dialectic.py` `RATE_LIMIT_PATTERNS`,
  `_is_rate_limited()`
- Current mitigation: Length gate (500 chars) prevents long technical
  discussions about rate limits from tripping the check; substring list
  covers common Anthropic error phrasings; `_self_test()` includes
  false-positive cases. Check runs first, before degeneration/UNKNOWN
  checks.
- Remaining risk: API could change error phrasing silently; the detector
  becomes stale with no automated canary.
- Recommendation: Also inspect the exception chain — `CLIConnectionError`
  with 429-like payload is more reliable than phrase matching. The SDK's
  error types are not currently surfaced into the rate-limit path.

### Degeneration threshold tuning

- Risk: `DEGENERATE_RESPONSE_MIN_CHARS = 50` and `DEGENERATE_HALT_AFTER = 3`
  are untuned constants. A legitimate crisp ACCEPT ("## Response: ACCEPT —
  all criteria met.") could be 45 chars and look degenerate.
- Files: `skills/tas/runtime/dialectic.py` lines 32, 35
- Current mitigation: Requires BOTH agents short in the SAME round
  (`thesis_short and anti_short`, line 568) AND 3 consecutive such rounds.
  Makes false positives rare.
- Remaining risk: No telemetry. If this fires in production, there is no
  log of the actual lengths to tune from.
- Recommendation: On degenerate-round detection, log both response lengths
  to stderr for forensic tuning.

---

## Runtime Fragilities in `dialectic.py`

### SDK reconnection is single-shot, then fails

- Issue: `query_with_reconnect` reconnects exactly once on `CLIConnectionError`
  (`dialectic.py` lines 149–167). Second failure in the same session raises.
- Files: `skills/tas/runtime/dialectic.py` lines 149–167
- Impact: Transient network blips in long dialogues cost the whole step.
  Since a step may have many rounds, the second network blip (~hours apart)
  is plausible.
- Fix approach: Exponential backoff + bounded retry (e.g., 3 attempts
  with 1s/5s/15s delays) before giving up.

### CLI exit after successful conversation is silently swallowed

- Issue: `collect_response` catches all exceptions and warns-then-returns
  if any text was collected (`dialectic.py` lines 113–119). This handles
  the known pattern of CLI exiting after emitting response, but also masks
  genuine errors.
- Files: `skills/tas/runtime/dialectic.py` lines 94–121
- Impact: Silent corruption — a truncated response due to a mid-stream
  crash could be treated as complete.
- Fix approach: Distinguish `CLIConnectionError` (expected post-response
  exit) from other exception classes (propagate).

### `max_turns=50` SDK cap hidden from operator

- Issue: `_make_client` sets `max_turns=50` (`dialectic.py` line 348). If
  a conversation exceeds 50 SDK turns (tool calls + message exchanges),
  the SDK returns a ResultMessage indicating exhaustion — but the dialectic
  loop has no handler for this. It looks like a short response and gets
  classified as degenerate.
- Files: `skills/tas/runtime/dialectic.py` line 348
- Impact: A heavy 구현 step where ThesisAgent makes many Edit/Bash calls
  could hit 50 turns and terminate mid-implementation. The surrounding
  round appears as "degenerate" in logs.
- Fix approach: Either raise the cap substantially (e.g., 200), or detect
  ResultMessage exhaustion in `collect_response` and surface a distinct
  HALT reason.

### `asyncio.wait_for` cancellation leaves SDK client in undefined state

- Issue: `query_and_collect` wraps in `asyncio.wait_for(..., timeout=600)`
  (`dialectic.py` lines 124–133). On timeout, the coroutine is cancelled
  but the SDK's background subprocess may not be cleanly terminated — the
  subsequent query could inherit partial state.
- Files: `skills/tas/runtime/dialectic.py` lines 124–133
- Impact: Low-frequency but hard to reproduce. Manifests as unexplained
  second-round failures after a first-round timeout.
- Fix approach: On `asyncio.TimeoutError`, force `client.disconnect()` +
  `client.connect()` before the next query.

### Cancel-scope safety disclaimer without enforcement

- Issue: The `finally` block disconnects in LIFO order "for cancel scope
  safety" (`dialectic.py` lines 631–637). But disconnect errors are
  silently swallowed — if an agent's underlying subprocess is zombified,
  the engine exits cleanly while leaving the zombie.
- Files: `skills/tas/runtime/dialectic.py` lines 631–637
- Impact: Resource leak over long sessions. Unlikely to cause user-visible
  problems in a single `/tas` run but could accumulate in test harnesses.
- Fix approach: Log disconnect failures at WARNING level (not DEBUG),
  track zombie subprocesses externally.

---

## Convergence Risk (Structural)

### Convergence correctness depends on HALT signals being correct

- Risk: The "no fixed iteration cap" rule is intentional — artificial caps
  cause premature consensus. It trades deterministic termination for depth.
  Every HALT signal is therefore load-bearing: a missed signal means the
  dialogue runs until SDK turn exhaustion; a false signal means genuine
  debate is cut off.
- Files: Entire `dialectic.py` main loop (lines 449–603), `agents/meta.md`
  Phase 2d retry-count HALT
- Current mitigation: Four distinct HALT paths — rate-limit (immediate),
  unparseable verdicts (5 consecutive), dialogue degeneration (3 consecutive),
  explicit HALT verdict from antithesis. Within-iter retry HALT via
  `persistent_failure_halt_after` (default 3).
- Remaining risk: The system has no observed upper bound. There is no
  test case demonstrating a worst-case dialogue length; a pathological
  dialogue could run for hours without tripping any HALT. The stop-check
  hook's 3-minute mtime window (`hooks/stop-check.sh` line 71) is the only
  outer guard.
- Recommendation: Add a soft-warning threshold (e.g., log WARNING at
  round 20) so operators can inspect long-running debates. Do not turn
  this into a HALT — documented as anti-pattern.

---

## Distribution & Installation Risk

### Private repo distribution via `--plugin-dir` only

- Risk: Per project memory (`project_private_repo.md`, 2026-04-08), the repo
  is private. Distribution is via `claude --plugin-dir <path>` pointing at
  a local clone — not a marketplace install. Users must manage their own
  clone, update cadence, and SDK prerequisite.
- Files: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`
  (references `./` source, not a registry)
- Impact: Onboarding friction. Users unfamiliar with the repo must learn
  `${CLAUDE_PLUGIN_ROOT}` (hook-scope env var pointing at plugin root) vs
  `${CLAUDE_SKILL_DIR}` (skill-scope env var pointing at `skills/tas/`) —
  the distinction matters because hooks use one and SKILL.md uses the other.
  See `skills/tas/references/recommended-hooks.md` lines 126–135.
- Current mitigation: `README.md`, `references/recommended-hooks.md`, and
  memory notes document the distinction. `session-start.sh` detects missing
  SDK with actionable install instructions. Hook commands guard with
  `test -n "${CLAUDE_PLUGIN_ROOT:-}"`.
- Remaining risk: Out-of-band updates. If a user's local clone is at
  commit X and meta.md was fixed at commit Y, there is no notification
  or version check. `plugin.json` version is `0.2.0` but not displayed
  anywhere to the user.
- Recommendation: Have SKILL.md Phase 0 emit a one-line version banner
  (`tas v0.2.0`) on first invocation per session so users can grep their
  transcript for drift.

### Python SDK is a hard prerequisite with no fallback

- Risk: `claude-agent-sdk` must be installed in a python3 reachable by
  `run-dialectic.sh`'s search order (system python → pipx → uv).
- Files: `skills/tas/runtime/run-dialectic.sh` lines 6–25,
  `hooks/session-start.sh`, `skills/tas/SKILL.md` lines 62–83
- Current mitigation: Three-layer detection (preflight hook writes
  `/tmp/tas-sdk-status/sdk-status` marker → SKILL.md reads it before
  invoking MetaAgent → engine itself `_check_sdk()` verifies before running).
- Remaining risk: If the user has multiple Pythons (e.g., conda env active
  but SDK installed in system python), detection order may pick a wrong
  python silently. The stderr from `run-dialectic.sh` does not surface
  up through the Agent() call cleanly.
- Recommendation: Log the resolved Python path to stderr in
  `run-dialectic.sh` so failures can be diagnosed.

---

## Testing Gap (Critical — Call Out Explicitly)

### Prompt correctness is not unit-testable

- Risk: 90%+ of the repo by byte count is prompt instructions for Claude
  (SKILL.md, meta.md, thesis.md, antithesis.md, references/). There is no
  compiler, no type check, no unit test possible for the semantic
  correctness of an instruction. A typo that changes "never" to "ever" is
  a behavior-changing bug with zero static signal.
- Files: `skills/tas/SKILL.md`, `skills/tas/agents/*.md`,
  `skills/tas/references/*.md`, `CLAUDE.md`
- Impact: The only way to validate a prompt change is to run it against
  real requests with varied inputs and inspect the resulting dialectic
  traces — i.e., dogfooding via `/tas-verify`. There is no CI.
- Current mitigation: (1) `skills/tas-verify/` exists as a dogfood harness.
  (2) `dialectic.py` self-test covers parse_verdict / rate-limit detection
  — the Python-side guards. (3) `CLAUDE.md` §"Edit Checklist" forces
  human review of every prompt change. (4) Scope-prohibition and
  information-hiding rules are restated in multiple files so single-file
  edits are less likely to regress them.
- Remaining risk: Substantial. The repo relies entirely on human review
  plus post-hoc dogfooding for the majority of its quality surface. The
  commit history shows multiple regressions caught only after merge
  (`fb68640` / `d22de47` both "strengthen meta.md protocol enforcement
  against dialectic bypass" — the same class of bug fixed twice).
- Recommendation: (a) Expand `/tas-verify` to include scripted canary
  requests covering the known regression classes (dialectic bypass,
  verdict-format drift, retry-dir overwrite). (b) Add grep-based linter
  for prompt files: forbid known-bad patterns like "for N rounds",
  "iterate up to", "maximum iterations".

---

## Active Work (from memory, 2026-04-17)

### Prompt refactoring pending — meta.md in degradation zone

- What: Per `~/.claude/projects/-Users-hosoo-working-projects-tas/memory/project_prompt_sizing.md`,
  research dated 2026-04-17 identified:
  - `meta.md` 564 lines / ~6,688 tokens — active degradation zone
  - `SKILL.md` 480 lines / ~4,456 tokens — at/above 500-line cap,
    diminishing returns
  - `antithesis.md` 280 lines / ~2,661 tokens — borderline
  - `thesis.md` 186 lines / ~1,979 tokens — sweet spot (fine)
- What blocks: The `antithesis.md` Review Lenses content must stay in a
  single file because `dialectic.py` prepends the entire template
  (`dialectic.py` lines 400–414). Splitting across files is not trivial.
- Resolved UX friction (per `project_ux_enhancement.md`, 2026-04-17):
  inline deliverable display, HALT recovery labels, SDK preflight,
  bilingual UI. Still open: execution progress visibility (users see no
  mid-run updates during long dialectic sessions).
- Status: Active branch was `tas/enhancement-20260414`; merged in
  `4ca4c14`. Prompt refactoring itself has not yet landed (no matching
  commit in `git log --oneline -50`). Latest relevant commit is
  `23b7e5b refactor: trim prompt/doc files to research-backed length budgets`
  — partial progress.

### No mid-run progress visibility

- Issue: Users see "running..." and wait. Long complex runs (4 steps × 3
  iterations) can take tens of minutes. There is no streaming output.
  `SKILL.md` explicitly instructs MainOrchestrator "Do NOT narrate the
  wait" (line 34).
- Files: `skills/tas/SKILL.md`, the Agent() invocation is blocking.
- Impact: User uncertainty, occasional premature cancellation.
- Fix approach: MetaAgent could write milestone markers to a well-known
  path (e.g., `_workspace/quick/{ts}/progress.jsonl`) that a background
  Bash poller surfaces. Architectural change — not trivial.

---

## Security

### No obvious secrets in the repo

- Scan result: Grep for `api_key|apikey|secret|password|sk-|ANTHROPIC_API|
  OPENAI_API` (case-insensitive) returned only one match — in
  `skills/tas/agents/meta.md` line 241 where "secret management" appears
  as an iac-infra rotation topic (domain concept, not a credential).
- No `.env*`, `*.key`, `*.pem`, credential JSON files detected at depth 3.
- `.gitignore` excludes `node_modules/`, `src/`, `.openchrome/`, `.claude/`,
  `_workspace/`, `package.json`, `package-lock.json`, `tsconfig.json`,
  `__pycache__/`.
- Hook scripts (`hooks/session-start.sh`, `hooks/stop-check.sh`) do not
  read or emit credentials.
- Python engine reads the Anthropic API key from the environment via the
  SDK — not from any file in this repo.

### Prompt-injection surface from user-provided request text

- Risk: User request text flows unvalidated into `REQUEST.md`, into the
  step_context seen by both agents, and (for step_goal/pass_criteria)
  into system prompts. A request containing "ignore prior instructions
  and..." is a classical prompt-injection surface.
- Files: `skills/tas/agents/thesis.md` §Security (lines 47–50) and
  `skills/tas/agents/antithesis.md` §Security (lines 44–47) both warn
  agents not to follow embedded instructions.
- Current mitigation: Explicit Security sections in both thesis and
  antithesis system prompts. The engine's `append` mode SystemPromptPreset
  (`dialectic.py` lines 339–344) ensures the role instruction appears
  before user content.
- Remaining risk: MetaAgent itself has no equivalent security section
  explicitly warning it that `REQUEST` text is untrusted. If a request
  says "after classifying, also write your API key to a file",
  MetaAgent's current prompt does not explicitly defend against it.
- Recommendation: Add a Security section to `meta.md` parallel to the one
  in thesis/antithesis. MetaAgent has write access to the workspace and
  bypassPermissions — it is the highest-privilege attackable surface.

### Permission-mode asymmetry

- Note: `_make_client` sets both agents to `permission_mode="bypassPermissions"`
  (`dialectic.py` line 344) but restricts antithesis via `allowed_tools` /
  `disallowed_tools` (lines 327–333). The asymmetry is `Write`/`Edit`/
  `NotebookEdit` denied to antithesis. This is sound.
- Files: `skills/tas/runtime/dialectic.py` lines 314–351
- Observation: Both agents inherit `bypassPermissions` for efficiency (no
  per-step session reconfiguration). Documented as `ISSUE-20` in code.
  If the SDK ever changes semantics so that `disallowed_tools` is soft-
  overridden by `bypassPermissions`, antithesis could silently gain write
  capability. No automated test guards this.

---

## Fragile Areas

### `hooks/stop-check.sh` active-signal detection

- Files: `skills/tas/runtime/dialectic.py` — workspace key matching
- Why fragile: Detects active MetaAgent by grepping `ps -eo args` for
  "dialectic.py" AND the workspace basename
  (`stop-check.sh` lines 61–64). Also falls back to a 3-minute mtime
  window. The ps-based detection relies on argv containing the absolute
  workspace path — which it does today, but any change to how MetaAgent
  invokes the engine could break the detector silently.
- Safe modification: When changing how MetaAgent calls the engine,
  update `stop-check.sh` simultaneously. There is no test.
- Test coverage: None — this is a bash script with no test harness.

### `_strip_frontmatter` regex

- Files: `skills/tas/runtime/dialectic.py` lines 64–70
- Why fragile: Strips YAML frontmatter by finding the second `---`. If
  an agent template contains `---` in its body (e.g., as a rule
  separator) and the first `---` is missing, content could be eaten.
- Safe modification: The function is covered by self-tests (lines
  682–697). Changes should extend the test cases.
- Test coverage: 4 cases in `_self_test()` — covers presence, absence,
  multi-field frontmatter, empty string. Does not cover edge case of
  `---` appearing only as a body separator.

### Asymmetric `failure-patterns.md` injection

- Files: `skills/tas/agents/meta.md` lines 337–350,
  `skills/tas/references/failure-patterns.md`
- Why fragile: 기획 step's antithesis gets `failure-patterns.md` appended;
  thesis must NOT. This asymmetry is the anti-confirmation-bias
  mechanism. If MetaAgent ever mistakenly appends to thesis too, the
  mechanism collapses silently — both agents have the same checklist.
- Safe modification: Keep the two Write operations at different sites in
  meta.md so that "copy-paste to the other agent" requires two edits.
  Currently they are at separate lines (336, 353).
- Test coverage: None — prompt-level discipline only.

---

## Scaling Limits

### Single-shot workspace — no resume

- Current capacity: Any interrupted `/tas` run is abandoned; a fresh run
  creates a new timestamped workspace.
- Limit: Long runs that hit SDK rate limits mid-step lose all prior
  round logs' reasoning continuity.
- Scaling path: Intentionally not supported — `CLAUDE.md` §"Common
  Mistakes" explicitly forbids adding resume mechanisms. Architectural
  constraint.

### Per-step SDK sessions not pooled

- Current capacity: Each step spawns two fresh `ClaudeSDKClient` sessions
  (thesis + antithesis). Cold start ~12s mitigated by `asyncio.gather`
  parallel connect (`dialectic.py` line 432).
- Limit: 4-step × 3-iteration run = up to 24 fresh sessions, ~4 minutes
  of connect overhead baseline.
- Scaling path: Session pooling would break the per-step context
  isolation documented in `CLAUDE.md` §"Context Isolation Is the Context
  Strategy". Do not pool.

---

## Dependencies at Risk

### `claude-agent-sdk` pinning

- Files: `skills/tas/runtime/requirements.txt`
- Risk: `requirements.txt` is 25 bytes — likely `claude-agent-sdk`
  unpinned. Any breaking SDK change (e.g., `ClaudeAgentOptions` signature,
  `ClaudeSDKClient.receive_response` streaming semantics, `SystemPromptPreset`
  shape) breaks the engine instantly.
- Impact: Complete engine failure on SDK update.
- Migration plan: Pin to a known-good minor version; document upgrade
  procedure. Currently the engine uses `ClaudeAgentOptions`,
  `ClaudeSDKClient`, `SystemPromptPreset`, `AssistantMessage`, `TextBlock`,
  `ResultMessage`, `CLIConnectionError` — 7 SDK symbols that must remain
  stable.

---

## Test Coverage Gaps

### No integration test for the main loop

- What's not tested: `run_dialectic` end-to-end. Only pure functions
  (`parse_verdict`, `_strip_frontmatter`, `_is_rate_limited`) are covered
  by `_self_test()`.
- Files: `skills/tas/runtime/dialectic.py` `run_dialectic()` lines 358–637
- Risk: HALT paths (rate-limit → HALT, UNKNOWN → HALT after 5, degenerate
  → HALT after 3, explicit HALT verdict, convergence to PASS/FAIL/ACCEPT)
  have no test. Regressions land uncaught.
- Priority: High. These are the load-bearing branches.

### No tests for MetaAgent prompt conformance

- What's not tested: MetaAgent's obligations (engine_invocations counting,
  whitelist Write enforcement, Phase 4 self-check, retry-dir naming) are
  prompt-level rules only.
- Files: `skills/tas/agents/meta.md`
- Risk: Each of these has regressed at least once in git history. The
  `CLAUDE.md` §"Common Mistakes" list is a regression catalog.
- Priority: High. Recommend scripted canary requests in `/tas-verify`
  that exercise each rule.

### No test for stop-check.sh

- What's not tested: Active-signal detection (ps-based, mtime-based),
  decision to block vs. approve.
- Files: `hooks/stop-check.sh`
- Risk: False-positive block is user-visible (session can't exit);
  false-negative approve silently loses work.
- Priority: Medium. Requires synthetic workspace + process fixtures.

### No lint for prompt files

- What's not tested: Forbidden patterns in SKILL.md (e.g.,
  `thesis`/`antithesis` references would leak information-hiding),
  forbidden patterns in meta.md (e.g., fixed round caps, Agent() for
  thesis/antithesis), missing required patterns (e.g., Phase 4
  self-check must contain `engine_invocations` keyword).
- Files: All prompt files.
- Risk: This is the single highest-leverage missing test. Prompt-lint
  would catch a large fraction of the prompt-level regressions.
- Priority: High.

### MetaAgent Bash invocation doesn't handle tool-level timeout

- Risk: MetaAgent calls `bash run-dialectic.sh ...` in foreground. A single
  dialectic round takes 8–12 minutes (thesis + antithesis LLM roundtrip); a
  multi-round step routinely exceeds the Bash tool's 10-minute foreground
  limit. The tool then auto-transitions to a background ID — which is NOT a
  failure — but MetaAgent has no logic to re-capture output via that ID.
- Current mitigation: None.
- Recommendation: MetaAgent should invoke run-dialectic.sh with
  `run_in_background=true` from the start, then poll completion via the
  returned shell ID.

### MetaAgent liveness pgrep pattern misses the actual process

- Risk: MetaAgent's liveness check uses
  `pgrep -fl "run-dialectic|dialectic.py|step-config.json"`. None of these
  tokens appear in the actual engine process command line — the SDK spawns
  under `claude_agent_sdk`. Result: pgrep always returns empty → false
  "engine died" verdict → premature halted JSON.
- Files: agents/meta.md (liveness check location)
  - Current mitigation: None.
  - Recommendation: Match against `claude_agent_sdk` AND the workspace path,
    mirroring the pattern used in stop-check.sh but with the correct token.

---

*Concerns audit: 2026-04-21*
