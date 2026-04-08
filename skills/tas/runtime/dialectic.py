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
]


def parse_verdict(response: str) -> str:
    """Extract verdict (ACCEPT/REFINE/COUNTER/HALT) from antithesis response."""
    for pattern in _VERDICT_PATTERNS:
        m = pattern.search(response)
        if m:
            return m.group(1).upper()
    return "UNKNOWN"


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
    log_dir = Path(config["log_dir"])
    log_dir.mkdir(parents=True, exist_ok=True)

    step_id = config["step_id"]
    step_goal = config["step_goal"]
    model = config.get("model", "claude-opus-4-6")
    project_root = config["project_root"]
    query_timeout = config.get("query_timeout", 600)
    language = config.get("language", "English")

    # Load assembled system prompts (written by MetaAgent)
    thesis_prompt = Path(config["thesis_prompt_path"]).read_text(encoding="utf-8")
    antithesis_prompt = Path(config["antithesis_prompt_path"]).read_text(
        encoding="utf-8"
    )

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

            verdict = parse_verdict(anti_msg)
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

            if verdict == "HALT":
                final_msg = (
                    f"# HALTED at Round {round_num}\n\n"
                    f"## Last Thesis Position\n\n{thesis_msg}\n\n"
                    f"## Halt Signal\n\n{anti_msg}"
                )
                write_log(log_dir, round_num, "halt", final_msg)
                break

            if verdict == "UNKNOWN":
                print(
                    f"  Warning: could not parse verdict, treating as REFINE",
                    file=sys.stderr,
                    flush=True,
                )
                verdict = "REFINE"

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

        result: dict[str, Any] = {
            "status": "completed" if verdict == "ACCEPT" else "halted",
            "rounds": round_num,
            "verdict": verdict,
            "deliverable_path": str(deliverable_path),
        }
        if verdict == "HALT":
            result["halt_reason"] = "convergence_failure"

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
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)

    logging.basicConfig(
        level=logging.WARNING,
        format="%(name)s %(levelname)s: %(message)s",
        stream=sys.stderr,
    )

    result = asyncio.run(run_dialectic(config))

    # Last line of stdout MUST be JSON (MetaAgent output contract)
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
