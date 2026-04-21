# Testing Patterns

**Analysis Date:** 2026-04-21

## Honest Summary

**This project has essentially no automated test suite.** Verification is deliberate, manual, and reasoning-based — not red/green CI. There is:

- One embedded self-test function for the Python runtime (`python3 dialectic.py --self-test`), covering three pure helpers.
- No `pytest` suite, no `unittest` module, no `tests/` directory.
- No `.github/workflows/`, no CI config, no lint/test scripts in any `package.json` (there is no `package.json`).
- Five Claude-driven "skill" commands (`/tas`, `/tas-verify`, `/tas-review`, `/tas-explain`, `/tas-workspace`) that provide the actual quality loop — via dogfooding rather than assertions.

This is intentional, not an oversight. Per `CLAUDE.md`: *"You can't test prompt changes — there's no compiler, no unit test. You must reason about how a receiving Claude will interpret your edits under diverse user inputs."* The testing gap is structural to the project's subject matter.

---

## Test Framework

**Runner (Python only):** none. The only executable test is `dialectic.py --self-test`, which is a plain function that prints PASS/FAIL and `sys.exit(1)` on any failure.

**Assertion Library:** none — bare `if result == expected` comparisons with manual pass/fail counting.

**Run Commands:**
```bash
# Python runtime self-test (three helpers only)
python3 /Users/hosoo/working/projects/tas/skills/tas/runtime/dialectic.py --self-test

# End-to-end verification via dogfooding (see workflow below)
/tas {request}          # Full dialectic run
/tas-verify [file]      # Boundary-value tracing on produced code
/tas-review [ref|diff]  # Dialectic code review
```

There is no `make test`, no `npm test`, no `pytest`, no `tox`, no `nox`.

---

## Test File Organization

**Location:** No separate test files exist.

**Naming:** N/A — the sole test function is `_self_test()` at `skills/tas/runtime/dialectic.py:678`, triggered by the `--self-test` argv guard at line 825.

**Structure:**
```
skills/tas/runtime/
  dialectic.py         # contains _self_test() as module-internal function
  run-dialectic.sh     # wrapper (no test coverage)
  requirements.txt     # pins claude-agent-sdk>=0.1.50 (no test deps)
```

No `tests/` directory exists anywhere in the repo (`find . -name 'pytest.ini' -o -name 'pyproject.toml' -o -name 'setup.py'` returns nothing).

---

## Test Structure — `_self_test()`

The self-test is a single function with three inlined case-table loops. Pattern from `skills/tas/runtime/dialectic.py` lines 678-822:

```python
def _self_test() -> None:
    """Regression tests for parse_verdict and _strip_frontmatter. Run via: python3 dialectic.py --self-test"""

    # --- _strip_frontmatter tests ---
    fm_cases: list[tuple[str, str]] = [
        ("---\nname: foo\n---\n# Hello", "# Hello"),
        ("---\nname: foo\nmodel: opus\n---\n\n# Hello", "# Hello"),
        ("# No frontmatter here", "# No frontmatter here"),
        ("", ""),
    ]
    fm_passed = 0
    fm_failed = 0
    for text, expected in fm_cases:
        result = _strip_frontmatter(text)
        if result == expected:
            fm_passed += 1
        else:
            fm_failed += 1
            preview = text[:40].replace("\n", "\\n")
            print(f"  FAIL: _strip_frontmatter({preview!r}) = {result!r}, expected {expected!r}")
    # ... similar blocks for parse_verdict (standard + inverted) and _is_rate_limited
```

**What the self-test covers:**

| Function | Cases | Location in `dialectic.py` |
|----------|-------|----------------------------|
| `_strip_frontmatter` | 4 cases (frontmatter present / absent / empty) | lines 682-697 |
| `parse_verdict` standard mode | 15 cases (all regex patterns, Korean phrasing, aliases, bold, embedded) | lines 700-739 |
| `parse_verdict` inverted mode | 9 cases (PASS/FAIL preserved, standard unchanged) | lines 742-763 |
| `_is_rate_limited` | 9 cases (short error → True, long technical discussion → False via length gate) | lines 766-813 |

Total: 37 case-table rows across 4 pure helpers.

**What the self-test does NOT cover:**

- `run_dialectic()` — the main async loop (requires SDK + live Claude sessions, unit-untestable by construction)
- `collect_response`, `query_and_collect`, `query_with_reconnect` — SDK interaction
- `_make_client` — SDK client construction
- `_is_cli_dead` — depends on SDK-internal exception class
- Any interaction with the filesystem, subprocess launching, or JSON output contract
- Any MetaAgent logic (meta.md is markdown, not code)
- Any MainOrchestrator logic (SKILL.md is markdown, not code)

**Pattern:** case tables as `list[tuple[...]]`, iterate and count pass/fail, `sys.exit(1)` if any failed. No fixtures, no setUp/tearDown, no mocking — all tested helpers are pure.

---

## Mocking

**Framework:** none.

**What to Mock:** nothing is mocked. Tested helpers are pure (string → string, string → bool). The SDK-touching code paths are not tested.

**What NOT to Mock:** the dialectic engine loop itself. `CLAUDE.md` is explicit: prompt changes cannot be unit-tested. Mocking `ClaudeSDKClient` to verify "the loop calls thesis then antithesis" would test the Python structure but not the behavior that matters (which is a property of the receiving Claude, not the Python). The project intentionally skips this.

---

## Fixtures and Factories

None. The self-test embeds literal strings inline. There is no `conftest.py`, no `fixtures/` directory, no factory module.

---

## Coverage

**Requirements:** none enforced. There is no `.coveragerc`, no coverage tool invocation, no CI gate.

**View Coverage:** N/A — no coverage tool is configured or run.

Effective coverage of `dialectic.py`: 4 of ~25 module-level functions have case-table tests, weighted heavily toward verdict parsing and rate-limit heuristics. Estimated line coverage via inspection: <15% of the 828-line file.

---

## Test Types

### Unit Tests

- **Scope:** Four pure string/regex helpers in `dialectic.py`.
- **Approach:** Inline case tables in `_self_test()`, invoked via `--self-test` argv flag.
- **Location:** `skills/tas/runtime/dialectic.py:678-822`.

### Integration Tests

- **Scope:** None as automated tests.
- **Approach:** The **dogfooding workflow** (below) substitutes for integration testing. A `/tas` run exercises MainOrchestrator → MetaAgent → `dialectic.py` → two `ClaudeSDKClient` sessions end-to-end.

### End-to-End Tests

- **Scope:** None as automated tests.
- **Approach:** Same as integration — human-initiated `/tas` invocations against real project changes.

### Prompt Correctness

**Not unit-tested.** Per `CLAUDE.md` "The Core Paradox": prompt changes are verified by reasoning about how the receiving Claude will interpret them under diverse user inputs, not by asserting on output. The `CLAUDE.md` Edit Checklist is the replacement for a test suite:

- Who executes this? (Which Claude instance reads this text.)
- What context does it have? (Only its system prompt + input parameters.)
- Does this leak across boundaries? (Information hiding intact.)
- Is the instruction falsifiable? ("Be thorough" is noise.)
- Would a fresh Claude misread this? (Read as if zero prior context.)

Failing any checklist item is a test failure in this project's sense.

---

## Dogfooding Workflow (Primary Verification Path)

The project tests itself by running itself. Two skill commands exist specifically to verify tas's own output:

### `/tas-verify [file]` — Post-Synthesis Boundary Tracing

Implemented in `skills/tas-verify/SKILL.md`. Runs AFTER a `/tas` session (or standalone on any code the user points to).

**Process** (from `skills/tas-verify/SKILL.md:27-90`):

1. **Target identification**: accept a file path, or auto-detect the most recent `_workspace/quick/{timestamp}/` directory and identify files modified during the session.
2. **Function Inventory**: tabulate every function's signature, numeric parameters, callees, and defensive measures.
3. **Boundary Value Tracing**: for each numeric parameter, select boundary values (0, -1, 1, `Number.MAX_SAFE_INTEGER`, Infinity, NaN, declared max, cap ±1). Trace concrete intermediate values through every function boundary. Flag NaN, Infinity-before-cap, negative-where-positive, or type changes.
4. **Composition Audit**: for each A→B call pair, analyze whether A's output range fits B's expected input, and whether defensive measures are placed at the right layer.
5. **Contract Verification**: for each exported function, check that every input the type system allows is handled correctly.

The report format (lines 92-135) produces a `CLEAN` or `DEFECTS FOUND` verdict with concrete boundary traces. This catches defects textual review misses — the technique is complementary to the 검증 step inside the dialectic.

### `/tas-review [ref|diff]` — Standalone Dialectic Code Review

Implemented in `skills/tas-review/SKILL.md`. Invokes `MetaAgent` with `REQUEST_TYPE: review` and passes a collected git diff (from `git diff HEAD`, `git diff <branch>...HEAD`, `git diff --cached`, or `gh pr diff #N`). MetaAgent runs the standard dialectic against the diff and produces a review document.

800-line diff cap with truncation warning (`skills/tas-review/SKILL.md:48-64`). Used on self-reviewed commits in this repo as a smoke test of the review pipeline.

### `/tas` Itself

Every `/tas` invocation on this codebase is a self-test of:
- MainOrchestrator (SKILL.md) routing correctness
- MetaAgent (meta.md) classify + execute logic
- `dialectic.py` PingPong loop end-to-end
- Hook behavior (SessionStart SDK preflight, Stop integrity guard)
- Workspace conventions (file layout under `_workspace/quick/{timestamp}/`)

Workspace evidence at `_workspace/quick/` (5 past runs as of 2026-04-21, timestamps from `20260416_143634` through `20260417_meta_refactor`) shows this workflow is the actual verification mechanism.

### `/tas-explain [run-id]` and `/tas-workspace`

Secondary tools for inspecting past runs (`skills/tas-explain/SKILL.md`, `skills/tas-workspace/SKILL.md`). Used to debug dialectic failures by reading `iteration-{N}/logs/step-{id}-{slug}/dialogue.md` transcripts. Not tests themselves, but essential to diagnosing what tas got wrong on a given run.

---

## Dynamic Testing Convention for Dialectic Outputs

When `/tas` is invoked against a user project, the **테스트 (Test) step inside the dialectic** adapts to the project's domain. This is specified in `skills/tas/references/workflow-patterns.md` §Dynamic Testing by Domain and enforced by MetaAgent's testing-context injection (`skills/tas/agents/meta.md` lines 382-399).

| Domain | 테스트 Requirements |
|--------|---------------------|
| `web-frontend` | Unit tests + Playwright CLI via Bash (`npx playwright test`, `npx playwright screenshot`) + visual/behavioral evaluation on screenshots |
| `web-backend` / `api` | Unit tests + integration tests against actual endpoints |
| `cli` | Unit tests + subprocess execution tests with real args |
| `library` | Unit tests + usage-example verification |
| `mobile` | Unit tests + (platform-specific) emulator smoke test if tooling available |
| `monorepo` | Per-package unit tests + cross-package integration tests + build isolation check |
| `data-pipeline` | Unit tests on transform functions + idempotency check (run twice, same result) + schema validation against sample data |
| `iac-infra` | `terraform validate` / `terraform plan` + `tflint` / `checkov` + dry-run showing expected resource changes |
| `unknown` | Unit tests + whatever execution the project's build tooling provides |

**Web projects — Playwright CLI, not MCP**:

> "For web projects, Playwright CLI via Bash (`npx playwright test`, `npx playwright screenshot`) is the dynamic verification channel — Playwright MCP tools are not available in dialectic agent sessions. ThesisAgent spins up the dev server and runs tests/captures screenshots via Bash; AntithesisAgent evaluates the results." — `skills/tas/references/workflow-patterns.md:69-72`

This is reinforced in three places:
- `skills/tas/agents/meta.md:384-397` (MetaAgent injects the testing-strategy context)
- `skills/tas/agents/thesis.md:165-169` (ThesisAgent attacker-mode execution instructions)
- `CLAUDE.md` §Testing Strategy by Domain

The convergence model for 테스트 is **inverted** — thesis executes tests and reports results; antithesis judges PASS (tests green + coverage adequate) or FAIL (with specific blocker list). Defined in `skills/tas/agents/antithesis.md:222-231`.

**Non-web domains** use static tests plus execution (e.g., `cargo test`, `pytest`, `go test`) — no dynamic browser step is required or injected.

---

## Common Patterns

### Async Testing

None. The async code in `dialectic.py` (`run_dialectic`, `collect_response`, `query_and_collect`, `query_with_reconnect`) is not tested. Testing would require mocking `claude_agent_sdk.ClaudeSDKClient`, which the project considers out of scope (the behavior that matters is the dialectic's emergent quality, not the Python plumbing).

### Error Testing

Not tested directly. Error paths in `main()` (lines 651-672) are exercised only during real runs when configs fail to load or the engine crashes.

### Regression Testing

The `_self_test()` function is explicitly framed as regression coverage (`"Regression tests for parse_verdict and _strip_frontmatter"` — line 679). When adding new verdict formats or rate-limit patterns, extend the case tables — this is the only enforceable regression gate in the codebase.

---

## Absence of CI

No `.github/workflows/`, no `.gitlab-ci.yml`, no `.circleci/`, no `Jenkinsfile`. No pre-commit hook enforcing tests. The only automated check is the `SessionStart` hook (`hooks/session-start.sh`) which verifies `claude-agent-sdk` is importable and writes a status marker to `$TMPDIR/tas-sdk-status/sdk-status` — this is a dependency check, not a test.

The `Stop` hook (`hooks/stop-check.sh`) enforces a workspace integrity invariant (no `REQUEST.md` without `DELIVERABLE.md`) — this is a runtime safety guard, not a test.

---

## Testing Gap Summary

| Layer | What exists | What's missing |
|-------|-------------|----------------|
| `dialectic.py` pure helpers | 37-case self-test for 4 helpers | ~20 other functions untested |
| `dialectic.py` async engine | nothing | Full `run_dialectic` loop, SDK interaction, subprocess entrypoint |
| `run-dialectic.sh` | nothing | Python discovery paths, error exit messages |
| `hooks/*.sh` | nothing | SDK preflight branches, Stop-hook block/skip logic |
| `SKILL.md` prompts | CLAUDE.md Edit Checklist (reasoning only) | No automated prompt evaluation |
| `meta.md` prompt | CLAUDE.md Edit Checklist (reasoning only) | No automated evaluation |
| `thesis.md` / `antithesis.md` | CLAUDE.md Edit Checklist (reasoning only) | No automated evaluation |
| End-to-end | Human-driven `/tas` runs + `/tas-verify` | No scripted regression corpus |
| CI | none | everything |

When extending the codebase, treat the Edit Checklist in `CLAUDE.md` as the spec against which you self-review, and use `/tas-verify` on any Python changes that produce numeric or control-flow behavior. New pure helpers added to `dialectic.py` should grow the `_self_test()` case tables; new async/SDK code does not get tests.

---

*Testing analysis: 2026-04-21*
