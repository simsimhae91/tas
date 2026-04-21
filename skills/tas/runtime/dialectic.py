#!/usr/bin/env python3
"""
tas dialectic engine — PingPong loop for thesis-antithesis dialogue.

Manages stateful ClaudeSDKClient sessions for both agents,
routing messages between them until convergence (ACCEPT) or HALT.

Usage:
    python3 dialectic.py <step-config.json>

Input:  step-config.json with prompt paths, assignment, and settings
Output: Round logs in log_dir, deliverable.md, JSON result on last stdout line
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger("tas.dialectic")

# ---------------------------------------------------------------------------
# Degeneration detection constants
# ---------------------------------------------------------------------------

# If both agents produce responses shorter than this (chars), the round is "degenerate"
DEGENERATE_RESPONSE_MIN_CHARS = 50

# HALT after this many consecutive rounds where BOTH agents are degenerate
DEGENERATE_HALT_AFTER = 3

# HALT after this many consecutive rounds with unparseable verdict (UNKNOWN)
UNKNOWN_VERDICT_HALT_AFTER = 5

# Rate-limit indicator phrases (case-insensitive substring match).
# If EITHER agent's response contains any of these AND the response is short
# (< RATE_LIMIT_MAX_RESPONSE_LEN), HALT immediately — rate limiting is
# unrecoverable within a dialogue session.
RATE_LIMIT_PATTERNS: list[str] = [
    "hit your limit",
    "hit my limit",
    "rate limit",
    "usage limit",
    "too many requests",
    "over capacity",
    "throttled",
]

# Responses longer than this are treated as substantive dialogue — rate-limit
# error messages are typically 50-200 chars, while technical discussion about
# rate limiting runs into hundreds or thousands of chars.
RATE_LIMIT_MAX_RESPONSE_LEN = 500


# ---------------------------------------------------------------------------
# YAML frontmatter stripping
# ---------------------------------------------------------------------------

def _strip_frontmatter(text: str) -> str:
    """Strip YAML frontmatter (--- ... ---) from agent template files."""
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            return text[end + 3:].lstrip("\n")
    return text


# ---------------------------------------------------------------------------
# SDK imports (deferred to avoid top-level crash if SDK not installed)
# ---------------------------------------------------------------------------

def _check_sdk():
    """Verify claude-agent-sdk is installed, give actionable error if not."""
    try:
        import claude_agent_sdk  # noqa: F401
    except ImportError:
        print(
            "ERROR: claude-agent-sdk is not installed.\n"
            "Run: pip install claude-agent-sdk",
            file=sys.stderr,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Response collection
# ---------------------------------------------------------------------------

async def collect_response(client: Any) -> str:
    """Collect full text response from streaming SDK messages.

    Pattern from bmad-orchestrator sdk_utils.py — accumulates TextBlocks
    from AssistantMessage stream, falls back to ResultMessage.result.
    """
    from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock

    text_parts: list[str] = []
    result_text: str = ""

    try:
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        text_parts.append(block.text)
            elif isinstance(message, ResultMessage):
                result_text = getattr(message, "result", "") or ""
    except Exception as exc:
        # If we already collected data, log warning and return it
        # (handles CLI exit after successful conversation)
        if text_parts or result_text:
            logger.warning("CLI error after collecting response: %s", exc)
        else:
            raise

    return "".join(text_parts) if text_parts else result_text


async def query_and_collect(
    client: Any, prompt: str, timeout: int = 600
) -> str:
    """Send a query and collect the full response with timeout."""

    async def _raw() -> str:
        await client.query(prompt)
        return await collect_response(client)

    return await asyncio.wait_for(_raw(), timeout=timeout)


# ---------------------------------------------------------------------------
# CLI death detection & reconnection
# ---------------------------------------------------------------------------

def _is_cli_dead(exc: BaseException) -> bool:
    """Return True if the exception indicates the CLI subprocess terminated."""
    try:
        from claude_agent_sdk._errors import CLIConnectionError
    except ImportError:
        return False
    return isinstance(exc, CLIConnectionError)


async def query_with_reconnect(
    client: Any,
    prompt: str,
    agent_name: str,
    timeout: int = 600,
) -> str:
    """Query with one reconnect attempt on CLI death."""
    try:
        return await query_and_collect(client, prompt, timeout)
    except Exception as exc:
        if not _is_cli_dead(exc):
            raise
        logger.warning("%s CLI died, reconnecting once...", agent_name)
        try:
            await client.disconnect()
        except Exception:
            pass
        await client.connect()
        return await query_and_collect(client, prompt, timeout)


# ---------------------------------------------------------------------------
# Verdict parsing
# ---------------------------------------------------------------------------

_VERDICT_PATTERNS = [
    re.compile(r"##\s*Response:\s*(ACCEPT|REFINE|COUNTER|HALT)", re.IGNORECASE),
    re.compile(
        r"###\s*Updated Assessment\s*\n+\s*(ACCEPT|REFINE|COUNTER|HALT)",
        re.IGNORECASE,
    ),
    re.compile(r"\*\*Response\*\*:\s*(ACCEPT|REFINE|COUNTER|HALT)", re.IGNORECASE),
    re.compile(r"Response:\s*(ACCEPT|REFINE|COUNTER|HALT)", re.IGNORECASE),
    # Inverted-mode judgment (검증/테스트): antithesis.md outputs "## Judgment: PASS/FAIL"
    re.compile(r"##\s*Judgment:\s*(PASS|FAIL)", re.IGNORECASE),
    re.compile(r"\*\*Judgment\*\*:\s*(PASS|FAIL)", re.IGNORECASE),
    # Korean verdict phrasing (e.g., "판정: ACCEPT", "## 판정: PASS")
    re.compile(r"판정:\s*(ACCEPT|REFINE|COUNTER|HALT|PASS|FAIL)", re.IGNORECASE),
    # Standalone bold verdict on its own line (e.g., "**ACCEPT**")
    re.compile(
        r"^\*\*(ACCEPT|REFINE|COUNTER|HALT)\*\*\s*$",
        re.MULTILINE | re.IGNORECASE,
    ),
]

# Standard-mode aliases (inverted mode bypasses these for PASS/FAIL)
_VERDICT_ALIASES: dict[str, str] = {
    "PASS": "ACCEPT",
    "FAIL": "REFINE",
}


def parse_verdict(response: str, convergence_model: str = "standard") -> str:
    """Extract verdict from antithesis response.

    Standard mode: PASS→ACCEPT, FAIL→REFINE (backward compat)
    Inverted mode: PASS and FAIL returned as-is (both terminal verdicts)
    Also handles Korean phrasings (판정:) and standalone bold verdicts.
    """
    for pattern in _VERDICT_PATTERNS:
        m = pattern.search(response)
        if m:
            raw = m.group(1).upper()
            # ISSUE-01: In inverted mode, PASS/FAIL are terminal — don't alias
            if convergence_model == "inverted" and raw in ("PASS", "FAIL"):
                return raw
            return _VERDICT_ALIASES.get(raw, raw)
    return "UNKNOWN"


# ---------------------------------------------------------------------------
# Inverted-mode helpers (ISSUE-01, ISSUE-07)
# ---------------------------------------------------------------------------


def _extract_blockers(response: str) -> list[str]:
    """Extract blocker items from an inverted-mode FAIL response."""
    blockers: list[str] = []
    in_blockers = False
    for line in response.splitlines():
        if re.match(r"###?\s*Blockers", line, re.IGNORECASE):
            in_blockers = True
            continue
        if in_blockers:
            if line.startswith("#"):
                break
            m = re.match(r"\s*\d+[.)]\s*(.+)", line)
            if m:
                blockers.append(m.group(1).strip())
            elif line.startswith("- "):
                blockers.append(line[2:].strip())
    return blockers


_HALT_REASON_KEYWORDS: dict[str, str] = {
    "circular": "circular_argumentation",
    "contradiction": "external_contradiction",
    "missing information": "missing_information",
    "scope escalation": "scope_escalation",
    "scope": "scope_escalation",
}


def _parse_halt_reason(response: str) -> str:
    """Extract structured halt reason from an antithesis HALT response."""
    lower = response.lower()
    for keyword, reason in _HALT_REASON_KEYWORDS.items():
        if keyword in lower:
            return reason
    return "convergence_failure"


def _is_rate_limited(response: str) -> bool:
    """Check if a response indicates API rate limiting.

    Length gate: responses longer than RATE_LIMIT_MAX_RESPONSE_LEN are
    treated as substantive dialogue (not error messages), even if they
    contain rate-limit terminology as part of technical discussion.
    """
    if len(response.strip()) > RATE_LIMIT_MAX_RESPONSE_LEN:
        return False
    lower = response.lower()
    return any(p in lower for p in RATE_LIMIT_PATTERNS)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def write_log(log_dir: Path, round_num: int, label: str, content: str) -> None:
    """Write a round log file."""
    path = log_dir / f"round-{round_num}-{label}.md"
    path.write_text(content, encoding="utf-8")


def append_dialogue(
    log_dir: Path, round_num: int, speaker: str, verdict: str | None, content: str
) -> None:
    """Append a turn to the unified dialogue log.

    Produces a single file that reads like a conversation transcript:
      ## Round 1 — 正 ThesisAgent
      ...
      ## Round 1 — 反 AntithesisAgent [REFINE]
      ...
    """
    path = log_dir / "dialogue.md"
    labels = {"thesis": "正 ThesisAgent", "antithesis": "反 AntithesisAgent", "final": "正 ThesisAgent (Final)"}
    speaker_label = labels.get(speaker, speaker)
    verdict_tag = f" [{verdict}]" if verdict else ""

    header = f"\n\n---\n\n## Round {round_num} — {speaker_label}{verdict_tag}\n\n"

    # Create file with title on first write
    if not path.exists():
        path.write_text(f"# Dialectic Dialogue Log\n{header}{content}", encoding="utf-8")
    else:
        with path.open("a", encoding="utf-8") as f:
            f.write(f"{header}{content}")


# ---------------------------------------------------------------------------
# Client factory
# ---------------------------------------------------------------------------

def _make_client(
    system_prompt_text: str,
    *,
    model: str,
    project_root: str,
    role: str,
) -> Any:
    """Create a ClaudeSDKClient for a thesis or antithesis agent."""
    from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
    from claude_agent_sdk.types import SystemPromptPreset

    # Thesis gets write tools (produces deliverables, modifies code);
    # antithesis is read-only (evaluates only).
    if role == "thesis":
        allowed = ["Read", "Write", "Edit", "Bash", "Grep", "Glob"]
        disallowed: list[str] = []
    else:
        allowed = ["Read", "Grep", "Glob"]
        disallowed = ["Write", "Edit", "NotebookEdit"]

    # ISSUE-20: bypassPermissions for both agents — thesis needs it for 구현 Write/Edit;
    # antithesis is restricted to read-only via allowed_tools above. Uniform permission
    # mode avoids per-step session reconfiguration complexity.
    options = ClaudeAgentOptions(
        model=model,
        system_prompt=SystemPromptPreset(
            type="preset",
            preset="claude_code",
            append=system_prompt_text,
        ),
        permission_mode="bypassPermissions",
        allowed_tools=allowed,
        **({"disallowed_tools": disallowed} if disallowed else {}),
        cwd=project_root,
        max_turns=50,
    )

    return ClaudeSDKClient(options=options)


# ---------------------------------------------------------------------------
# Main dialectic loop
# ---------------------------------------------------------------------------

async def run_dialectic(config: dict[str, Any]) -> dict[str, Any]:
    """Execute the PingPong dialectic loop.

    Returns a result dict with status, rounds, verdict, and deliverable_path.
    """
    # ISSUE-12: Validate required config fields
    required_fields = [
        "log_dir", "step_id", "step_goal", "project_root",
        "thesis_prompt_path", "antithesis_prompt_path",
        "step_assignment", "antithesis_briefing",
    ]
    missing = [f for f in required_fields if f not in config]
    if missing:
        return {
            "status": "halted",
            "rounds": 0,
            "verdict": "HALT",
            "halt_reason": "invalid_config",
            "missing_fields": missing,
        }

    log_dir = Path(config["log_dir"])
    log_dir.mkdir(parents=True, exist_ok=True)

    step_id = config["step_id"]
    step_goal = config["step_goal"]
    model = config.get("model", "claude-sonnet-4-6")
    project_root = config["project_root"]
    query_timeout = config.get("query_timeout", 600)
    language = config.get("language", "English")
    # ISSUE-01: Read convergence model to handle inverted-mode terminal verdicts
    convergence_model = config.get("convergence_model", "standard")

    # Load step-specific system prompts (written by MetaAgent — role/goal/criteria only)
    thesis_step_prompt = Path(config["thesis_prompt_path"]).read_text(encoding="utf-8")
    antithesis_step_prompt = Path(config["antithesis_prompt_path"]).read_text(
        encoding="utf-8"
    )

    # Prepend full agent templates if paths provided (structural guarantee
    # that verdict format, review lenses, etc. are always included — even if
    # MetaAgent truncated or summarized the instructions)
    if config.get("thesis_template_path"):
        template = _strip_frontmatter(
            Path(config["thesis_template_path"]).read_text(encoding="utf-8")
        )
        thesis_prompt = template + "\n\n" + thesis_step_prompt
    else:
        thesis_prompt = thesis_step_prompt

    if config.get("antithesis_template_path"):
        template = _strip_frontmatter(
            Path(config["antithesis_template_path"]).read_text(encoding="utf-8")
        )
        antithesis_prompt = template + "\n\n" + antithesis_step_prompt
    else:
        antithesis_prompt = antithesis_step_prompt

    # Inject language instruction into system prompts
    lang_instruction = f"\n\n---\nIMPORTANT: Respond in {language}. All output — position, reasoning, evaluation, self-assessment — must be written in {language}.\n"
    thesis_prompt += lang_instruction
    antithesis_prompt += lang_instruction

    # Create stateful clients
    thesis = _make_client(
        thesis_prompt, model=model, project_root=project_root, role="thesis"
    )
    antithesis = _make_client(
        antithesis_prompt, model=model, project_root=project_root, role="antithesis"
    )

    try:
        # Parallel connect (~12s cold start mitigated)
        print(f"{step_id}: Connecting agents — {step_goal}", flush=True)
        await asyncio.gather(thesis.connect(), antithesis.connect())

        # Round 1: Thesis proposes
        print(f"{step_id}: Thesis producing initial position...", flush=True)
        thesis_msg = await query_with_reconnect(
            thesis, config["step_assignment"], "thesis", query_timeout
        )
        write_log(log_dir, 1, "thesis", thesis_msg)
        append_dialogue(log_dir, 1, "thesis", None, thesis_msg)

        round_num = 1
        verdict = "UNKNOWN"
        final_msg = ""
        consecutive_unknown = 0
        consecutive_degenerate = 0
        rate_limited = False

        while True:
            # Antithesis evaluates
            if round_num == 1:
                anti_input = (
                    f"{config['antithesis_briefing']}\n\n---\n\n"
                    f"## Thesis Position (Round 1)\n\n{thesis_msg}"
                )
            else:
                anti_input = f"## Thesis Response (Round {round_num})\n\n{thesis_msg}"

            anti_msg = await query_with_reconnect(
                antithesis, anti_input, "antithesis", query_timeout
            )
            write_log(log_dir, round_num, "antithesis", anti_msg)

            verdict = parse_verdict(anti_msg, convergence_model)
            append_dialogue(log_dir, round_num, "antithesis", verdict, anti_msg)
            print(f"{step_id}: Round {round_num}, {verdict}", flush=True)

            if verdict == "ACCEPT":
                # Ask thesis for final converged deliverable
                final_prompt = (
                    f"## Antithesis Response (Round {round_num})\n\n{anti_msg}\n\n"
                    "---\n\n"
                    "Antithesis has ACCEPTED your position. Produce the **final "
                    "converged deliverable** incorporating all agreed changes from "
                    "the dialogue."
                )
                final_msg = await query_with_reconnect(
                    thesis, final_prompt, "thesis", query_timeout
                )
                write_log(log_dir, round_num, "final", final_msg)
                append_dialogue(log_dir, round_num, "final", "CONVERGED", final_msg)
                break

            # ISSUE-01: In inverted mode, PASS and FAIL are terminal verdicts
            if verdict == "PASS":
                # Inverted mode: antithesis confirmed 0 blockers — judgment is the deliverable
                final_msg = anti_msg
                write_log(log_dir, round_num, "final", final_msg)
                append_dialogue(log_dir, round_num, "final", "PASS", final_msg)
                break

            if verdict == "FAIL":
                # Inverted mode: blockers confirmed by judge — judgment is the deliverable
                final_msg = anti_msg
                write_log(log_dir, round_num, "final", final_msg)
                append_dialogue(log_dir, round_num, "final", "FAIL", final_msg)
                break

            if verdict == "HALT":
                final_msg = (
                    f"# HALTED at Round {round_num}\n\n"
                    f"## Last Thesis Position\n\n{thesis_msg}\n\n"
                    f"## Halt Signal\n\n{anti_msg}"
                )
                write_log(log_dir, round_num, "halt", final_msg)
                break

            # --- Rate-limit detection (before other degeneration checks) ---
            # Rate-limit responses may be short (<50 chars) and/or unparseable,
            # so check this FIRST to avoid misclassifying as dialogue_degeneration
            # or unparseable_verdicts.  Length gate prevents false positives from
            # technical discussions that mention "rate limit" as a domain concept.
            if _is_rate_limited(thesis_msg) or _is_rate_limited(anti_msg):
                limited_agent = "thesis" if _is_rate_limited(thesis_msg) else "antithesis"
                print(
                    f"  HALT: {limited_agent} hit API rate limit",
                    file=sys.stderr,
                    flush=True,
                )
                rate_limited = True
                verdict = "HALT"
                final_msg = (
                    f"# HALTED — Rate Limit\n\n"
                    f"Agent `{limited_agent}` produced a response indicating "
                    f"API rate limiting. The dialogue cannot continue.\n\n"
                    f"## Last Thesis Position\n\n{thesis_msg}\n\n"
                    f"## Last Antithesis Response\n\n{anti_msg}"
                )
                write_log(log_dir, round_num, "halt", final_msg)
                break

            # --- Degeneration detection ---

            # Track consecutive unparseable verdicts
            if verdict == "UNKNOWN":
                consecutive_unknown += 1
                if consecutive_unknown >= UNKNOWN_VERDICT_HALT_AFTER:
                    print(
                        f"  HALT: {consecutive_unknown} consecutive UNKNOWN verdicts "
                        f"— antithesis is not producing parseable verdicts",
                        file=sys.stderr,
                        flush=True,
                    )
                    verdict = "HALT"
                    final_msg = (
                        f"# HALTED — Unparseable Verdicts\n\n"
                        f"Antithesis produced {consecutive_unknown} consecutive "
                        f"responses with no parseable verdict "
                        f"(expected: ## Response: ACCEPT/REFINE/COUNTER).\n\n"
                        f"## Last Thesis Position\n\n{thesis_msg}\n\n"
                        f"## Last Antithesis Response\n\n{anti_msg}"
                    )
                    write_log(log_dir, round_num, "halt", final_msg)
                    break
                print(
                    f"  Warning: could not parse verdict ({consecutive_unknown}/"
                    f"{UNKNOWN_VERDICT_HALT_AFTER}), treating as REFINE",
                    file=sys.stderr,
                    flush=True,
                )
                verdict = "REFINE"
            else:
                consecutive_unknown = 0

            # Track degenerate (near-empty) responses from both agents
            thesis_short = len(thesis_msg.strip()) < DEGENERATE_RESPONSE_MIN_CHARS
            anti_short = len(anti_msg.strip()) < DEGENERATE_RESPONSE_MIN_CHARS
            if thesis_short and anti_short:
                consecutive_degenerate += 1
                if consecutive_degenerate >= DEGENERATE_HALT_AFTER:
                    print(
                        f"  HALT: {consecutive_degenerate} consecutive degenerate "
                        f"rounds (both responses <{DEGENERATE_RESPONSE_MIN_CHARS} chars)",
                        file=sys.stderr,
                        flush=True,
                    )
                    verdict = "HALT"
                    final_msg = (
                        f"# HALTED — Dialogue Degeneration\n\n"
                        f"Both agents produced degenerate responses "
                        f"(<{DEGENERATE_RESPONSE_MIN_CHARS} chars) for "
                        f"{consecutive_degenerate} consecutive rounds.\n\n"
                        f"## Last Thesis Position\n\n{thesis_msg}\n\n"
                        f"## Last Antithesis Response\n\n{anti_msg}"
                    )
                    write_log(log_dir, round_num, "halt", final_msg)
                    break
            else:
                consecutive_degenerate = 0

            # --- End degeneration detection ---

            # Thesis responds to counter/refine
            thesis_input = (
                f"## Antithesis Response (Round {round_num})\n\n{anti_msg}"
            )
            thesis_msg = await query_with_reconnect(
                thesis, thesis_input, "thesis", query_timeout
            )
            round_num += 1
            write_log(log_dir, round_num, "thesis", thesis_msg)
            append_dialogue(log_dir, round_num, "thesis", None, thesis_msg)

        # Write deliverable
        deliverable_path = log_dir / "deliverable.md"
        deliverable_path.write_text(final_msg, encoding="utf-8")

        # ISSUE-01: PASS and FAIL are terminal "completed" verdicts in inverted mode
        result: dict[str, Any] = {
            "status": "completed" if verdict in ("ACCEPT", "PASS", "FAIL") else "halted",
            "rounds": round_num,
            "verdict": verdict,
            "deliverable_path": str(deliverable_path),
        }
        # ISSUE-01: Extract blockers from inverted-mode FAIL for MetaAgent retry logic
        if verdict == "FAIL":
            result["blockers"] = _extract_blockers(final_msg)
        # ISSUE-07: Parse structured HALT reason from antithesis response
        if verdict == "HALT":
            if rate_limited:
                result["halt_reason"] = "rate_limit"
            elif consecutive_degenerate >= DEGENERATE_HALT_AFTER:
                result["halt_reason"] = "dialogue_degeneration"
            elif consecutive_unknown >= UNKNOWN_VERDICT_HALT_AFTER:
                result["halt_reason"] = "unparseable_verdicts"
            else:
                result["halt_reason"] = _parse_halt_reason(anti_msg)

        return result

    finally:
        # Always disconnect — order matters (LIFO for cancel scope safety)
        for agent, name in [(antithesis, "antithesis"), (thesis, "thesis")]:
            try:
                await agent.disconnect()
            except Exception:
                logger.debug("Error disconnecting %s", name, exc_info=True)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: dialectic.py <step-config.json>", file=sys.stderr)
        sys.exit(1)

    _check_sdk()

    config_path = sys.argv[1]
    # ISSUE-11: Structured JSON error output on config load failure
    try:
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "error": f"Config load failed: {exc}"}), flush=True)
        sys.exit(1)

    logging.basicConfig(
        level=logging.WARNING,
        format="%(name)s %(levelname)s: %(message)s",
        stream=sys.stderr,
    )

    # ISSUE-11: Structured JSON error output on engine crash
    try:
        result = asyncio.run(run_dialectic(config))
    except Exception as exc:
        logger.error("Dialectic engine crashed: %s", exc, exc_info=True)
        print(json.dumps({"status": "error", "error": str(exc)}), flush=True)
        sys.exit(1)

    # Last line of stdout MUST be JSON (MetaAgent output contract)
    print(json.dumps(result), flush=True)


def _self_test() -> None:
    """Regression tests for parse_verdict, _strip_frontmatter, and checkpoint schema. Run via: python3 dialectic.py --self-test"""

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

    # --- parse_verdict tests ---
    cases: list[tuple[str, str]] = [
        # Standard verdicts
        ("## Response: ACCEPT", "ACCEPT"),
        ("## Response: REFINE", "REFINE"),
        ("## Response: COUNTER", "COUNTER"),
        ("## Response: HALT", "HALT"),
        # Bold response
        ("**Response**: ACCEPT", "ACCEPT"),
        # Plain response
        ("Response: REFINE", "REFINE"),
        # Standard-mode aliasing of inverted patterns (PASS→ACCEPT, FAIL→REFINE)
        ("## Judgment: PASS", "ACCEPT"),
        ("**Judgment**: FAIL", "REFINE"),
        # Korean phrasing
        ("판정: ACCEPT", "ACCEPT"),
        ("판정: PASS", "ACCEPT"),
        ("판정: FAIL", "REFINE"),
        # Standalone bold
        ("**ACCEPT**", "ACCEPT"),
        ("**HALT**", "HALT"),
        # Case insensitivity
        ("## Response: accept", "ACCEPT"),
        ("## Judgment: pass", "ACCEPT"),
        # No verdict → UNKNOWN
        ("This is just a regular message with no verdict.", "UNKNOWN"),
        ("Some discussion about the code.", "UNKNOWN"),
        # Verdict embedded in longer text
        ("I think the code is good.\n\n## Response: ACCEPT\n\nGreat work.", "ACCEPT"),
    ]

    passed = 0
    failed = 0
    for text, expected in cases:
        result = parse_verdict(text)
        if result == expected:
            passed += 1
        else:
            failed += 1
            preview = text[:60].replace("\n", "\\n")
            print(f"  FAIL: parse_verdict({preview!r}...) = {result!r}, expected {expected!r}")

    # --- parse_verdict inverted-mode tests (ISSUE-01) ---
    inv_cases: list[tuple[str, str]] = [
        ("## Judgment: PASS", "PASS"),
        ("## Judgment: FAIL", "FAIL"),
        ("**Judgment**: PASS", "PASS"),
        ("**Judgment**: FAIL", "FAIL"),
        ("판정: PASS", "PASS"),
        ("판정: FAIL", "FAIL"),
        # Standard verdicts unchanged in inverted mode
        ("## Response: ACCEPT", "ACCEPT"),
        ("## Response: REFINE", "REFINE"),
        ("## Response: COUNTER", "COUNTER"),
    ]
    inv_passed = 0
    inv_failed = 0
    for text, expected in inv_cases:
        result = parse_verdict(text, "inverted")
        if result == expected:
            inv_passed += 1
        else:
            inv_failed += 1
            preview = text[:60].replace("\n", "\\n")
            print(f"  FAIL: parse_verdict({preview!r}, 'inverted') = {result!r}, expected {expected!r}")

    # --- _is_rate_limited tests ---
    rl_cases: list[tuple[str, bool]] = [
        # True: short responses with rate-limit indicators
        ("You've hit your limit for the day", True),
        ("Rate limit exceeded, please try again", True),
        ("Too many requests in a short period", True),
        ("I've hit my limit and cannot continue", True),
        ("The server is over capacity", True),
        ("Usage limit reached for this API key", True),
        ("Request throttled. Please wait.", True),
        # False: no rate-limit patterns
        ("This is a normal response about code design", False),
        # False: rate-limit patterns in LONG responses (technical discussion)
        (
            "For the rate limit middleware, I propose using a sliding window "
            "approach with Redis as the backing store. The rate limit should "
            "be configurable per endpoint with different tiers for "
            "authenticated vs unauthenticated requests. Implementation plan: "
            "1. Create a RateLimiter class that wraps Redis MULTI/EXEC "
            "operations. 2. Add middleware to Express router. 3. Configure "
            "per-route limits in the route definitions. This approach handles "
            "distributed rate limiting across multiple server instances. "
            "We should also add monitoring dashboards to track rate limit "
            "hit counts per endpoint.",
            False,
        ),
        (
            "The usage limit configuration needs to support both per-user "
            "and per-IP throttling strategies. Here is my detailed proposal "
            "covering the implementation of rate limit headers, retry-after "
            "semantics, and graceful degradation patterns for the API gateway "
            "layer. The architecture should cleanly separate rate limit "
            "policy from enforcement mechanism to allow future extension. "
            "Additionally, we need to consider how the rate limit state is "
            "shared across horizontally scaled instances using a distributed "
            "cache layer with consistent hashing for partition tolerance.",
            False,
        ),
    ]
    rl_passed = 0
    rl_failed = 0
    for text, expected in rl_cases:
        result = _is_rate_limited(text)
        if result == expected:
            rl_passed += 1
        else:
            rl_failed += 1
            preview = text[:60].replace("\n", "\\n")
            print(f"  FAIL: _is_rate_limited({preview!r}...) = {result!r}, expected {expected!r}")

    # --- checkpoint schema regression tests (VERIFY-02) ---
    import importlib.util
    import shutil as _shutil
    import tempfile as _tempfile

    _ck_path = Path(__file__).parent / "checkpoint.py"
    _spec = importlib.util.spec_from_file_location("checkpoint", _ck_path)
    if _spec is None or _spec.loader is None:
        raise RuntimeError(f"checkpoint.py not loadable at {_ck_path}")
    _ck = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_ck)

    ck_cases_passed = 0
    ck_cases_failed = 0

    _tmp_ws = Path(_tempfile.mkdtemp())
    try:
        payload = {
            "schema_version": 1,
            "workspace": str(_tmp_ws),
            "plan_hash": "a" * 64,
            "current_step": "1",
            "completed_steps": [],
            "current_chunk": None,
            "completed_chunks": [],
            "status": "running",
            "updated_at": "2026-04-21T00:00:00+00:00",
        }
        _ck.write_checkpoint(_tmp_ws, **payload)
        restored = _ck.read_checkpoint(_tmp_ws)
        if restored == payload:
            ck_cases_passed += 1
        else:
            ck_cases_failed += 1
            print(f"  FAIL: checkpoint round-trip diff: {restored!r}")

        required = {"schema_version", "workspace", "plan_hash", "current_step",
                    "completed_steps", "current_chunk", "completed_chunks", "status", "updated_at"}
        if restored is not None and required.issubset(restored.keys()) and restored.get("schema_version") == 1:
            ck_cases_passed += 1
        else:
            ck_cases_failed += 1
            missing = required - set(restored.keys() if restored else set())
            sv = restored.get("schema_version") if restored else None
            print(f"  FAIL: checkpoint missing fields: {missing} or schema_version != 1 (got {sv!r})")

        plan_a = {"steps": [{"id": "1", "name": "기획"}], "loop_count": 2}
        plan_b = {"loop_count": 2, "steps": [{"id": "1", "name": "기획"}]}
        if _ck.compute_plan_hash(plan_a) == _ck.compute_plan_hash(plan_b):
            ck_cases_passed += 1
        else:
            ck_cases_failed += 1
            print("  FAIL: plan_hash is not key-order-stable")

        plan_c = dict(plan_a, loop_count=3)
        if _ck.compute_plan_hash(plan_a) != _ck.compute_plan_hash(plan_c):
            ck_cases_passed += 1
        else:
            ck_cases_failed += 1
            print("  FAIL: plan_hash did not change on semantic diff")
    finally:
        _shutil.rmtree(_tmp_ws, ignore_errors=True)

    total = passed + failed + fm_passed + fm_failed + inv_passed + inv_failed + rl_passed + rl_failed + ck_cases_passed + ck_cases_failed
    all_failed = failed + fm_failed + inv_failed + rl_failed + ck_cases_failed
    if all_failed:
        print(f"FAIL: {total - all_failed}/{total} passed, {all_failed} failed")
        sys.exit(1)
    else:
        print(f"PASS: {total}/{total} tests passed")


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--self-test":
        _self_test()
    else:
        main()
