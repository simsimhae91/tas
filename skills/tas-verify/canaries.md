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
grep -nE 'dialogue\.md|round-[0-9]+-(thesis|antithesis)\.md|deliverable\.md|lessons\.md|heartbeat\.txt' "$SKILL_PATH"
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

## Canary #5 — Layer A stdout-stall (VERIFY-01 a)

**Guards**: `.planning/phases/03-2-layer-hang-watchdog/03-CONTEXT.md` D-07 Canary #5;
WATCH-01; WATCH-02 (last_heartbeat read path). Catches the regression class where
`dialectic.py`'s outer try/except fails to emit a halted JSON with
`halt_reason=sdk_session_hang` + `watchdog_layer=A` + 4-field `last_heartbeat` after
a TimeoutError fires inside `query_and_collect` (Layer A asyncio.timeout).

**Exercise**: subprocess-spawn `dialectic.py` with a PYTHONPATH-injected mock
ClaudeSDKClient whose `receive_response` stalls longer than `query_timeout`.
stdlib-only. Target wall-clock ≤ 10s.

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-.}/skills/tas/runtime/tests/simulate_stdout_stall.py"
```

**Pass criteria**:
- Command exit code **0** and stdout contains the line `PASS: canary #5`
- Under the hood: spawned dialectic.py subprocess exit is non-zero (TimeoutError re-raise
  surfaces as sys.exit(1) in `__main__`)
- Among the last non-empty stdout lines of the spawned dialectic.py, one parses
  as JSON with `status == "halted"`, `halt_reason == "sdk_session_hang"`,
  `watchdog_layer == "A"`, and a 4-field `last_heartbeat` object
  (timestamp, round_n, speaker, phase). Note: dialectic.py's `main()` emits
  a trailing `{"status":"error"}` line after re-raise (ISSUE-11); the canary
  scans the last 5 lines for the halted JSON.

**Fail signals (regression)**:
- Exit code 1 with any `FAIL:` line → dialectic.py's Layer A halt emit regressed
  (missing field, wrong halt_reason, or no halted JSON at all)
- Wall-clock > 30s → Layer A may not be tripping; check that `_sdk_timeout` branch
  still uses `asyncio.timeout` on 3.11+ / `asyncio.wait_for` on 3.10

---

## Canary #6 — Layer B step-transition hang (VERIFY-01 b)

**Guards**: `.planning/phases/03-2-layer-hang-watchdog/03-CONTEXT.md` D-07 Canary #6;
WATCH-03; WATCH-04 (classification path). Catches regressions in the Bash watchdog
wrapper (`run-dialectic.sh` missing `--kill-after` or env var detection broken) and
in MetaAgent's classification of exit 0 + no-JSON → `step_transition_hang`.

**Exercise**: two parts. PART A drives Layer B SIGTERM/SIGKILL end-to-end (requires
coreutils `timeout` or `gtimeout` — SKIP on absent hosts per D-03 graceful degrade).
PART B unit-tests the classification function that mirrors meta.md D-05.

```bash
# PART A — end-to-end Layer B kill (SKIP on no-coreutils macOS)
bash "${CLAUDE_PLUGIN_ROOT:-.}/skills/tas/runtime/tests/simulate_step_transition.sh"

# PART B — classification table unit mirror
python3 "${CLAUDE_PLUGIN_ROOT:-.}/skills/tas/runtime/tests/simulate_step_transition_unit.py"
```

**Pass criteria**:
- PART A exit 0 with stdout `PASS: canary #6` OR `SKIP:` (SKIP only on hosts without
  `timeout`/`gtimeout` — SKIP is explicitly NOT a regression per D-03)
- PART A wall-clock ≤ 17s (TIMEOUT_SEC=5 + KILL_GRACE=2 + ~10s startup margin)
- Spawned `run-dialectic.sh` exit code must be 124 (SIGTERM) or 137 (SIGKILL)
- PART B: all 8 `unittest` test methods pass (exit 0 from `python3 ...simulate_step_transition_unit.py`)

**Fail signals (regression)**:
- PART A exit 1 with `FAIL:` line → Layer B wrapper or `--kill-after` broke; check
  `run-dialectic.sh` lines that detect `timeout`/`gtimeout` and the wrapped-exec
  branch
- PART A exit code not in {0, 124, 137} with coreutils installed → preflight
  regression (check `command -v` idiom)
- PART B unittest failure → MetaAgent classification drift (03-CONTEXT.md D-05);
  reconcile with the meta.md table the canary mirrors

---

## Canary #7 — Subagent-spawned orphan survival (VERIFY-TOPO-01)

**Guards**: `.planning/phases/03.1-engine-invocation-topology-refactor/03.1-CONTEXT.md`
D-VERIFY-TOPO-01; TOPO-01 (EXIT trap); TOPO-02 (nohup spawn); TOPO-03
(MetaAgent polling); TOPO-06 (invocation protocol); **Plan Review Issue #1**
(`exec` keyword suppression of EXIT trap). Catches regressions where
subagent-spawned `nohup` processes are reaped at subagent return (Claude Code
harness `bash_id` lifecycle — original halt: FINDINGS §7) **and** regressions
where `run-dialectic.sh` reintroduces `exec` on the final invocation lines
(Issue #1 close-out).

**Exercise (two Phases):**

**Phase 1 — orphan survival (synthetic mock):** synthesize a subagent that
runs `nohup bash -c 'sleep $T; echo survived > $MARKER' > $LOG 2>&1 & echo $!`,
return the PID, then verify the PID survives for $T seconds with PPID=1
and the marker file is written. Uses stdlib subprocess — no real Agent()
harness dependency.

**Phase 2 — real exec chain integration (sed-copy mock injection):** take
the real `skills/tas/runtime/run-dialectic.sh`, sed-rewrite it so
`find_python` succeeds without `claude_agent_sdk` and the final Python
invocation is replaced by a no-op mock script that prints a
`{"status":"completed","verdict":"ACCEPT"}` JSON and exits 0. Invoke the
modified script directly with `bash`, then assert `engine.done` exists and
`engine.exit` contains `0`. Skips (with explicit reason) if the sed-copy
cannot be built (script structure drift, bash -n failure, etc.) — this
preserves the signal rather than silently passing. Plan 07 invariant 6
(static `grep -c '^[[:space:]]*exec ' skills/tas/runtime/run-dialectic.sh`
equals `0`) backs up Phase 2 when it SKIPs.

```bash
# Default CI mode (T=120s; ~135s wall-clock including Phase 2)
python3 "${CLAUDE_PLUGIN_ROOT:-.}/skills/tas/runtime/tests/simulate_subagent_orphan.py"

# Or via the bash wrapper
bash "${CLAUDE_PLUGIN_ROOT:-.}/skills/tas/runtime/tests/simulate_subagent_orphan.sh"

# Smoke mode (T=10s; ~40s wall-clock) — for quick regression checks
TAS_VERIFY_TOPO_DURATION_SEC=10 python3 \
  "${CLAUDE_PLUGIN_ROOT:-.}/skills/tas/runtime/tests/simulate_subagent_orphan.py"

# Extended manual mode (T=1800s; ~30min wall-clock) — nightly only
TAS_VERIFY_TOPO_DURATION_SEC=1800 python3 \
  "${CLAUDE_PLUGIN_ROOT:-.}/skills/tas/runtime/tests/simulate_subagent_orphan.py"
```

**Pass criteria (Phase 1 — mandatory):**
- Mock subagent bash call returns in < 10 seconds (fire-and-forget contract;
  `nohup` + `&` + `echo $!` all load-bearing)
- PPID == 1 within 2s of spawn (init reparenting confirms session detach)
- Marker content == `survived` after $T seconds elapse

**Pass criteria (Phase 2 — mandatory if not SKIP):**
- `engine.done` exists after real-chain invocation (EXIT trap fired)
- `engine.exit` content equals `0` (mock dialectic exit code recorded)
- If sed-copy strategy fails for environmental reasons (script structure
  drift, modified script fails `bash -n`, `run-dialectic.sh` not found),
  SKIP with explicit reason is acceptable — static fallback guard lives in
  Plan 07 Task 2 invariant 6.

**PASS stdout:**
`PASS: canary #7 (subagent orphan survived ${DURATION}s, PPID=1; real-chain integration: <PASS|SKIP (...)>)`

**Fail signals (regression):**
- `FAIL: Phase 1 mock subagent duration <N>s >= 10s` → one of
  `nohup` / `&` / `echo $!` removed or substituted; fire-and-forget contract
  broken (TOPO-02 regression)
- `FAIL: Phase 1 PID <P> died within 2s of spawn` → harness `bash_id` reap
  returned (original Phase 3 close blocker reappeared) or SIGHUP
  propagation broke
- `FAIL: Phase 1 PPID=<N> for PID <P>, expected 1` → `nohup` detach failed
  to trigger init reparenting; possible macOS launchd or Linux
  systemd-user drift
- `FAIL: Phase 1 marker content = '<X>', expected 'survived'` → orphan ran
  but wrote wrong payload; bash `-c` argument substitution regression
- `FAIL: Phase 1 PID <P> did not produce marker within <N>s` → orphan was
  killed mid-run (partial reap) or bash shell crashed
- `FAIL: Phase 2 engine.done missing after real-chain exit rc=<N>` → **Plan
  Review Issue #1 regression — `exec` keyword reintroduced to
  `run-dialectic.sh`, suppressing EXIT trap firing.** Cross-check with
  `grep -c "^[[:space:]]*exec " skills/tas/runtime/run-dialectic.sh` (must
  be `0`).
- `FAIL: Phase 2 engine.exit = '<X>', expected '0'` → trap fired but
  captured wrong exit code; trap string or mock script drift

---

## Canary #8 — 2-chunk merge + integrated verify (VERIFY-01 c)

**STATUS:** Wave 5 complete — Phase 4 shipped. Harness: `skills/tas/runtime/tests/simulate_chunk_integration.py` (stdlib-only, 2-Phase).

**Guards**: `.planning/phases/04-chunk-decomposition/04-CONTEXT.md` D-09; CHUNK-03 (worktree orphan prevention); CHUNK-05 (cherry-pick + apply fallback + HALT); CHUNK-06 (integrated verify synthesis); CHUNK-07 (within-chunk failure handling); **Pitfall 15** (integrated verify missing regression at chunk boundary). Catches regressions where: chunk sub-loop leaves orphan worktrees, cherry-pick failure path skips `git reset --hard PRE_MERGE_SHA`, verify step_assignment loses Synthesis Context injection, chunk 1 FAIL path triggers a forbidden re-Classify, or `implementation_chunks[]` schema drifts from the D-02 6-field contract.

**Exercise (two Phases):**

**Phase 1 — 2-chunk happy path (synthetic mock, CI-default, ~30s):** Construct a minimal PROJECT_ROOT fixture inside `tempfile.mkdtemp(prefix="tas-canary-8-")` via `git init` + initial commit with 3 source files (`src/schema.py`, `src/api.py`, `src/ui.py`). Build a 2-chunk `plan.json` with D-02 schema (chunk 1 scope = "schema layer", deps = []; chunk 2 scope = "api + ui layer", deps = ["1"]). Replay the meta.md Phase 2d.5 orchestration:
1. `git worktree add --detach {WORKSPACE}/chunks/chunk-{c.id} HEAD` per chunk.
2. Mock dialectic writes `deliverable.md` + modifies one source file per chunk (pure Python — no real engine spawn).
3. `git add -A && git commit -m "chunk-{c.id}: {title}"` (MetaAgent ownership — D-06).
4. `git cherry-pick {CHUNK_SHA}` into PROJECT_ROOT (primary path — D-05).
5. `git worktree remove --force {CHUNK_PATH}` post-merge.
6. Build a mock integrated verify step-config.json with the D-07 Synthesis Context section injected.

**Phase 2 — chunk 1 regression detection (opt-in, `TAS_VERIFY_CHUNK_MODE=full`, ~300s):** Same fixture as Phase 1 BUT `_mock_dialectic(..., regression=True)` for chunk 1 only — chunk 1's deliverable embeds "SIGNATURE_MISMATCH: expected return type `int` but delivers `str`" which chunk 2 implicitly relies on. After merges complete, `_mock_integrated_verify(..., regression_mode=True)` returns `{"verdict": "FAIL", "reason": "synthesis boundary detected: chunk 1 regression — ..."}`. The canary asserts the FAIL verdict is surfaced AND no second Classify invocation path is taken (re-Classify 금지 structural check per D-10).

```bash
# Default CI mode (fast, ~30s)
python3 "${CLAUDE_PLUGIN_ROOT:-.}/skills/tas/runtime/tests/simulate_chunk_integration.py"

# Explicit fast mode
TAS_VERIFY_CHUNK_MODE=fast python3 "${CLAUDE_PLUGIN_ROOT:-.}/skills/tas/runtime/tests/simulate_chunk_integration.py"

# Extended mode (full, ~300s — regression sub-canary)
TAS_VERIFY_CHUNK_MODE=full python3 "${CLAUDE_PLUGIN_ROOT:-.}/skills/tas/runtime/tests/simulate_chunk_integration.py"
```

**Pass criteria (Phase 1 — mandatory):**
- **Assertion 1**: `git worktree add --detach` succeeds for both chunks (exit 0 + chunk path exists during iteration).
- **Assertion 2**: each chunk worktree has exactly 1 commit with `chunk-{N}:` subject prefix (verified via `git log --oneline HEAD~..HEAD` before cherry-pick removes the worktree).
- **Assertion 3**: cherry-pick succeeds for both chunks (primary path, no fallback triggered in happy-path fixture); post-merge `git log --oneline HEAD~2..HEAD` on PROJECT_ROOT shows both `chunk-1:` and `chunk-2:` commits in order.
- **Assertion 4**: the mock integrated verify `step-config.json` has a `step_assignment` string containing all 6 Synthesis Context substrings: `"## Synthesis Context"`, `"Public API"`, `"Shared file"`, `"Value flow"`, `"Regression"`, `"Not to be re-audited"` (D-07 proof).
- **Assertion 5**: post-cleanup `git worktree list --porcelain` on PROJECT_ROOT returns a list with zero entries matching `/chunks/chunk-` (all chunk worktrees removed — CHUNK-07 orphan prevention).

**Pass criteria (Phase 2 — mandatory if MODE=full):**
- **Assertion 6**: All Phase 1 assertions still hold against the regression-mode fixture.
- **Assertion 7**: `_mock_integrated_verify(..., regression_mode=True)` returns `verdict == "FAIL"`.
- **Assertion 8**: FAIL reason matches the regex `/synthesis|boundary|regression|chunk.1/i` (4 keyword alternatives — any match passes; covers D-07 focus items 1/3/4 + chunk id reference).
- **Assertion 9**: Structural — the canary maintains a `re_classify_called = False` boolean; nothing in the Phase 2 code path flips it to True. At exit, assertion requires `re_classify_called is False`. This proves re-Classify is NOT invoked on chunk 1 FAIL (CHUNK-07 + D-10 "no re-chunking / no re-Classify" regression guard).

**PASS stdout:**
- Fast mode: `PASS: canary #8 (2-chunk merge + integrated verify; Phase 2: SKIP (fast mode))`
- Full mode: `PASS: canary #8 (2-chunk merge + integrated verify; Phase 2: PASS)`

**Fail signals (regression):**
- `FAIL: Phase 1 assertion 1: <reason>` → **CHUNK-03 regression**: `git worktree add --detach` fails; check `{WORKSPACE}/chunks/` parent dir creation + stale-worktree pre-flight (meta.md Phase 2d.5 + Bash Sketch 1).
- `FAIL: Phase 1 assertion 2: <reason>` → **D-06 regression**: chunk commit is missing or has wrong prefix; check that MetaAgent commit step 7b (meta.md Phase 2d.5) runs `git add -A && git commit -m "chunk-{c.id}: ..."`; verify thesis/antithesis is NOT committing.
- `FAIL: Phase 1 assertion 3: <reason>` → **CHUNK-05 regression**: cherry-pick fails on clean fixture — check PROJECT_ROOT HEAD state before cherry-pick; Bash Sketch 2's PRE_MERGE_SHA capture may be broken.
- `FAIL: Phase 1 assertion 4: <reason>` → **D-07 regression**: Synthesis Context section missing from verify step_assignment; check meta.md Prepare Dialectic Config `Synthesis Context injection` block (Plan 05) + condition gate `S.name in {"검증", "테스트"} AND cumulative_chunk_context is non-empty`.
- `FAIL: Phase 1 assertion 5: <reason>` → **CHUNK-07 / Pitfall 9 regression**: orphan worktrees remain after canary exits; check `git worktree remove --force {CHUNK_PATH}` call site in meta.md Phase 2d.5 step 7e + Bash Sketch 4 cleanup sequence.
- `FAIL: Phase 2 assertion 6: <reason>` → Phase 1 broken under regression-mode fixture; same as Phase 1 FAIL signals above (regression fixture should not change the structural merge path — only deliverable content).
- `FAIL: Phase 2 assertion 7: <reason>` → **D-07 regression (depth)**: mock integrated verify returned non-FAIL under regression mode; check that `_mock_integrated_verify(regression_mode=True)` returns FAIL and that the verdict propagates.
- `FAIL: Phase 2 assertion 8: <reason>` → FAIL reason doesn't contain synthesis keywords; check `_mock_integrated_verify` reason string and `FAIL_KEYWORDS_RE` regex.
- `FAIL: Phase 2 assertion 9: <reason>` → **CHUNK-07 / D-10 / Pitfall 3 regression**: `re_classify_called` flipped to True — the canary detected a re-Classify path from Execute Mode. This is a HARD failure; chunk FAIL/HALT must never re-invoke Classify. Check meta.md Phase 2d.5 Verdict branch (FAIL/HALT path) + Within-Iteration FAIL Handling chunk branch sub-section.

**Integration with other canaries:**
- Canary #5/#6 guard watchdog topology (Phase 3 Layer A / Layer B).
- Canary #7 guards subagent orphan survival + real-chain integration (Phase 3.1 Scenario B).
- **Canary #8 guards the chunk sub-loop wiring** (this canary) — topology is covered by #7, sub-loop control flow is covered here. Failure of #8 does NOT imply #5/#6/#7 are compromised; they exercise different invariants.

---

## Canary #9 — Prompt Slim Behavioral Diff (SLIM-04)

**STATUS:** Wave 4 complete — Phase 5 shipped. Harness: `skills/tas/runtime/tests/simulate_prompt_slim_diff.py` (stdlib-only, 3 sub-canary, deterministic mock).

**Guards:** `.planning/phases/05-prompt-slim/05-CONTEXT.md` D-05; SLIM-04; meta.md → meta-classify.md / meta-execute.md split behavioral invariance. Catches regressions where:
- Classify Mode Phase 2 heuristic (complexity / steps / step names) drifts after split (sub-canary a)
- Classify Mode Phase 2c `implementation_chunks[]` 6-field schema or dependency structure drifts after split (sub-canary b)
- Execute Mode Phase 3 Final Aggregate (iterations / rounds_total / engine_invocations) or Phase 5 JSON Response (status / execution_mode / references_read) drifts after split (sub-canary c)
- Mode-bound Reference Load (added in Plan 05-03) fails to populate `references_read` at Read-time (sub-canary c Assertion 6, Pitfall 5)
- Baseline fixtures are deleted or corrupted (Assertion 9)

**Exercise:** Three independent sub-canaries each diff a deterministic pure-Python mock MetaAgent output against a committed baseline JSON in `skills/tas-verify/fixtures/canary-9-baseline-{a,b,c}.json`. Baselines were captured pre-slim in Plan 05-02 against the unsplit meta.md (see each baseline's `_meta.captured_from` for the pre-split git SHA). Baselines are **immutable references** — do not regenerate unless intentionally changing the behavioral contract (reviewed in PR).

```bash
# Default fast mode (~1s; all 3 sub-canaries, shallow + Assertion 6 references_read check)
python3 "${CLAUDE_PLUGIN_ROOT:-.}/skills/tas/runtime/tests/simulate_prompt_slim_diff.py"

# Explicit fast mode
TAS_VERIFY_SLIM_MODE=fast python3 "${CLAUDE_PLUGIN_ROOT:-.}/skills/tas/runtime/tests/simulate_prompt_slim_diff.py"

# Full mode (~2-3s; fast-mode assertions + deeper aggregate check on sub-canary c)
TAS_VERIFY_SLIM_MODE=full python3 "${CLAUDE_PLUGIN_ROOT:-.}/skills/tas/runtime/tests/simulate_prompt_slim_diff.py"
```

**Pass criteria (sub-canary a — trivial classify, fixture: typo fix):**
- **Assertion 1**: `complexity` matches baseline-a (expected `"simple"`)
- **Assertion 2**: `len(steps)` matches baseline-a `steps_count` (expected `1`)
- **Assertion 3**: `[s["name"] for s in steps]` matches baseline-a `steps_names_ordered` (expected `["구현"]`)
- **Assertion 4**: `implementation_chunks is None` matches baseline-a `implementation_chunks_is_null` (expected `True`)

**Pass criteria (sub-canary b — chunked classify, fixture: 3-layer auth):**
- **Assertion 1**: `complexity` matches baseline-b (expected `"complex"`)
- **Assertion 2**: `len(implementation_chunks)` matches baseline-b `implementation_chunks_count` (expected `3`)
- **Assertion 3**: `[c["id"] for c in chunks]` matches baseline-b `implementation_chunks_ids_ordered` (expected `["1", "2", "3"]`)
- **Assertion 4**: `[c["dependencies_from_prev_chunks"] for c in chunks]` matches baseline-b `implementation_chunks_deps_structure` (expected `[[], ["1"], ["1", "2"]]`)

**Pass criteria (sub-canary c — full execute, fixture: 1-step deterministic ACCEPT):**
- **Assertion 1**: `status` matches baseline-c (expected `"completed"`)
- **Assertion 2**: `iterations` matches baseline-c (expected `1`)
- **Assertion 3**: `rounds_total` matches baseline-c (expected `1`)
- **Assertion 4**: `engine_invocations` matches baseline-c (expected `1`)
- **Assertion 5**: `execution_mode` matches baseline-c (expected `"pingpong"`)
- **Assertion 6**: post-slim `references_read` contains a path ending with `/meta-execute.md` (baseline-c was captured pre-slim with `references_read_structure: []`; post-slim must populate per Pitfall 5 Read-time append rule — this is the asymmetric check per D-05)

**Pass criteria (fail-loud on missing baseline):**
- **Assertion 9**: Removing `skills/tas-verify/fixtures/canary-9-baseline-{a,b,c}.json` causes exit 1 with stderr `FAIL: baseline missing — <path>` and guidance on how to recover

**PASS stdout:**
- Fast mode: `PASS: canary #9 (prompt slim behavioral diff; a=PASS, b=PASS, c=PASS; mode=fast; PASS)`
- Full mode: `PASS: canary #9 (prompt slim behavioral diff; a=PASS, b=PASS, c=PASS; mode=full; PASS+PASS)`

**Fail signals:**

| FAIL prefix | Regression class | Fix pointer |
|-------------|------------------|-------------|
| `FAIL: sub-canary a complexity:` | Classify Mode Phase 2 Complexity Heuristic drifted | meta-classify.md §Phase 2 Classification — restore complexity rule for "fix" request_type |
| `FAIL: sub-canary a steps_names_ordered:` | Phase 2 Step Template Selection produces different names | meta-classify.md §Phase 2 — restore 구현 / 기획 labels |
| `FAIL: sub-canary a implementation_chunks_is_null:` | Trivial request produces non-null chunks (over-chunking regression) | meta-classify.md §Phase 2c — verify chunk sizing trigger heuristic |
| `FAIL: sub-canary b implementation_chunks_count:` | Phase 2c chunk count wrong for 3-layer fixture | meta-classify.md §Phase 2c — restore vertical-layer slicing |
| `FAIL: sub-canary b implementation_chunks_ids_ordered:` | chunk id sequencing changed | meta-classify.md §Phase 2c CHUNK-02 6-field schema |
| `FAIL: sub-canary b implementation_chunks_deps_structure:` | sequential relay dependency rule drifted (CHUNK-04) | meta-classify.md §Phase 2c — restore deps: chunk_N depends on chunks_1..N-1 |
| `FAIL: sub-canary c engine_invocations:` | Execute Mode engine counting changed (SSOT-1 surface regression detectable via behavioral diff before SSOT-1 grep fires) | meta.md §Final JSON Contract + meta-execute.md §Phase 5 JSON Response |
| `FAIL: sub-canary c iterations:` / `rounds_total:` | Phase 3 Final Aggregate tally rule changed | meta-execute.md §Phase 3 Final Aggregate |
| `FAIL: sub-canary c references_read:` / `post-slim array is empty` | Mode-bound Reference Load (meta.md Plan 05-03) not populating references_read at Read-time | meta.md §Mode-bound Reference Load + meta-{classify,execute}.md Phase 1 Attestation first step |
| `FAIL: baseline missing` | Baseline JSON deleted / moved | `git checkout HEAD -- skills/tas-verify/fixtures/canary-9-baseline-*.json` |

**Integration with other canaries:**
- Canary #4 guards info-hiding (SKILL.md does not read agent/dialectic artifact files). Preserved across Phase 5 (Plan 05-03 SKILL.md edit did not leak filenames into Agent() prompts).
- Canary #5/#6 guard watchdog topology (Phase 3 Layer A / B). Unaffected by Phase 5 (runtime code unchanged per D-08).
- Canary #7 guards subagent orphan survival + real-chain integration (Phase 3.1 Scenario B). Unaffected by Phase 5 (run-dialectic.sh + meta-execute.md Phase 2d nohup spawn preserved).
- Canary #8 guards chunk sub-loop wiring (Phase 4 CHUNK-01..07). Unaffected by Phase 5 (meta-execute.md Phase 2d.5 preserved byte-identical across Wave 1 split).
- **Canary #9 guards prompt slim behavioral invariance** (this canary) — Phase 5 extract faithfulness across split.
- **SSOT-1/2/3 lint** (co-located in this file §SSOT Invariants) guards structural single-source of engine_invocations / convergence verdict / references_read normative definitions.
- Canary #9 + SSOT lint are complementary: #9 catches behavior drift regardless of where sentences live; SSOT lint catches duplication regardless of whether behavior is preserved. Both must pass for Phase 5 close.

---

## SSOT Invariants (SLIM-03)

**STATUS:** Wave 3 complete — Phase 5 shipped. These 3 bash grep invariants guarantee that each load-bearing normative sentence appears in exactly 1 file. Failure of any invariant indicates drift: a definition was copied into a reference file instead of being anchored in its single source-of-truth location.

**Guards:** `.planning/phases/05-prompt-slim/05-CONTEXT.md` D-03; Phase 4 D-12 14-invariant lint precedent extended for Phase 5 SSOT-1/2/3.

**Exercise:** Run the following bash block from repo root. `/tas-verify` invokes it as part of the post-canary lint sweep.

```bash
# === SSOT Invariants (SLIM-03) — each pattern must match in exactly 1 file ===

# SSOT-1: engine_invocations JSON schema definition (anchor in meta.md §Final JSON Contract)
PATTERN_1='"engine_invocations" counts `bash run-dialectic.sh` calls'
COUNT_1=$(grep -rFln -- "$PATTERN_1" skills/tas/ 2>/dev/null | grep -v "_workspace/" | wc -l | tr -d ' ')
if [ "$COUNT_1" != "1" ]; then
  echo "SSOT-1 FAIL: engine_invocations schema sentence matched in $COUNT_1 files (expected 1)" >&2
  grep -rFln -- "$PATTERN_1" skills/tas/ 2>/dev/null | grep -v "_workspace/" >&2
  exit 1
fi

# SSOT-2: convergence verdict normative definition (anchor in meta.md §Convergence Model OR meta-execute.md — SSOT chosen per D-03)
PATTERN_2='^- `검증` uses \*\*inverted model\*\*'
COUNT_2=$(grep -rn -E -- "$PATTERN_2" skills/tas/ 2>/dev/null | grep -v "_workspace/" | wc -l | tr -d ' ')
if [ "$COUNT_2" != "1" ]; then
  echo "SSOT-2 FAIL: convergence verdict normative sentence matched in $COUNT_2 places (expected 1)" >&2
  grep -rn -E -- "$PATTERN_2" skills/tas/ 2>/dev/null | grep -v "_workspace/" >&2
  exit 1
fi

# SSOT-3: references_read attestation schema (anchor in meta.md §Final JSON Contract)
PATTERN_3='references_read: ["${SKILL_DIR}/references/meta-'
COUNT_3=$(grep -rFln -- "$PATTERN_3" skills/tas/ 2>/dev/null | grep -v "_workspace/" | wc -l | tr -d ' ')
if [ "$COUNT_3" != "1" ]; then
  echo "SSOT-3 FAIL: references_read schema fragment matched in $COUNT_3 files (expected 1)" >&2
  grep -rFln -- "$PATTERN_3" skills/tas/ 2>/dev/null | grep -v "_workspace/" >&2
  exit 1
fi

echo "SSOT-1/2/3 PASS: all load-bearing contracts are single-source"
```

**Pass criteria (each invariant independently mandatory):**
- **SSOT-1**: `grep -rFln` count of the engine_invocations schema sentence == 1 (anchor: `skills/tas/agents/meta.md` §Final JSON Contract)
- **SSOT-2**: `grep -rn -E` count of the convergence verdict regex == 1 (anchor: single file, currently `skills/tas/references/meta-execute.md` per Wave 1 split; D-03 accepts either meta.md or meta-execute.md as the single location)
- **SSOT-3**: `grep -rFln` count of the references_read schema fragment == 1 (anchor: `skills/tas/agents/meta.md` §Final JSON Contract)
- All 3 PASS → block echoes `SSOT-1/2/3 PASS: all load-bearing contracts are single-source` with exit 0

**Fail signals:**
- **SSOT-1 FAIL** → `engine_invocations` definition was copied into `meta-classify.md` or `meta-execute.md` or SKILL.md. Remove the duplicate; replace with a pointer like "(See `${SKILL_DIR}/agents/meta.md` §Final JSON Contract.)"
- **SSOT-2 FAIL** → `검증` inverted-model sentence was copied out of its single location (into meta.md or a second references file, for example). Return the sentence to a single anchor location; reword downstream usages as pointers.
- **SSOT-3 FAIL** → `references_read: ["${SKILL_DIR}/references/meta-` JSON literal appears in a references file or SKILL.md. SKILL.md may mention the field conceptually but must NOT use this exact fragment (use a different quoting style — e.g., single-line inline JSON that does NOT match the literal pattern). References files must use prose pointers, never this JSON literal.

**Integration with other canaries:**
- Canary #9 guards behavioral invariance across the split; SSOT-1/2/3 guard structural uniqueness of load-bearing definitions — complementary. A split that changes Classify/Execute behavior but keeps single-source definitions passes Canary #9 (structural diff) but might still be a conceptual regression elsewhere; a split that keeps behavior identical but duplicates definitions passes Canary #9 but fails SSOT lint. Both must pass for Phase 5 close.

---

## When to add a new canary

Add one whenever:
1. A regression is merged and fixed (commit the canary alongside the fix)
2. A class of failure affects the MetaAgent protocol that Python cannot check
3. A `CLAUDE.md` "Common Mistakes" bullet is added — should have a canary
   that would catch the next occurrence
