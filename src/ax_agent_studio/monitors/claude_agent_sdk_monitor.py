#!/usr/bin/env python3
"""Claude Agent SDK Monitor

Security-first monitor that runs agents with Anthropic's Claude Agent SDK.
Automatically discovers MCP tools, builds an explicit allowlist, and streams
responses back through the aX Agent Factory queue manager.
"""

from __future__ import annotations

import argparse
import asyncio
import inspect
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from ax_agent_studio.config import get_monitor_config, resolve_agent_config
from ax_agent_studio.mcp_manager import MCPServerManager
from ax_agent_studio.queue_manager import QueueManager

try:
    from claude_agent_sdk import ClaudeAgentOptions, query
except ImportError:  # pragma: no cover - dependency is optional for some test runs
    print("❌ Missing dependency: claude-agent-sdk")
    print("   Install with: pip install claude-agent-sdk")
    sys.exit(1)

# Configure logging for the monitor if no handlers are registered yet.
if not logging.getLogger().hasHandlers():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-sonnet-4-5"
_HISTORY_LIMIT = 12  # Store 6 message/response pairs




async def _discover_allowed_tools(manager: MCPServerManager) -> List[str]:
    """Create a Claude allowlist of the form mcp__<server>__<tool>."""
    allowlist: List[str] = []

    for server_name, session in manager.sessions.items():
        try:
            response = await session.list_tools()
            tools = getattr(response, "tools", None)
            if tools is None and isinstance(response, dict):
                tools = response.get("tools", [])

            if not tools:
                logger.warning("No tools reported by MCP server '%s'", server_name)
                continue

            for tool in tools:
                tool_name = getattr(tool, "name", None)
                if not tool_name and isinstance(tool, dict):
                    tool_name = tool.get("name")
                if tool_name:
                    allowlist.append(f"mcp__{server_name}__{tool_name}")
        except Exception as exc:  # pragma: no cover - network errors
            logger.error("Failed to list tools for %s: %s", server_name, exc)

    # Deduplicate while preserving alphabetical order for readability.
    return sorted(set(allowlist))


def _format_allowed_tools(tools: Iterable[str]) -> str:
    """Format allowed tools for prompt output."""
    formatted = list(tools)
    if not formatted:
        return "(none discovered)"
    return "\n".join(f"- {tool}" for tool in formatted)


def _extract_message_body(raw_content: str) -> str:
    """Extract the human-authored portion from an MCP mention payload."""
    if not raw_content:
        return ""

    # Common format: "• sender: @agent message" or "@agent message"
    mention_match = re.search(r"@\S+\s+(.+)", raw_content)
    if mention_match:
        return mention_match.group(1).strip()

    return raw_content.strip()


def _event_text(event) -> Optional[str]:
    """Pull text out of Claude streaming events."""
    if event is None:
        return None

    event_type = getattr(event, "type", None)
    if isinstance(event, dict):
        event_type = event.get("type", event_type)

    if event_type in {"message_stop", "message_end"}:
        return None

    # Delta payloads (most common streaming structure)
    delta = getattr(event, "delta", None)
    if delta is None and isinstance(event, dict):
        delta = event.get("delta")
    if delta is not None:
        text = getattr(delta, "text", None)
        if text:
            return text
        if isinstance(delta, dict):
            text = delta.get("text")
            if text:
                return text

    # Direct text attribute
    text_attr = getattr(event, "text", None)
    if text_attr:
        return text_attr
    if isinstance(event, dict) and isinstance(event.get("text"), str):
        return event["text"]

    # Message content array
    content = getattr(event, "content", None)
    if content is None and isinstance(event, dict):
        content = event.get("content")
    if content:
        pieces: List[str] = []
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and isinstance(item.get("text"), str):
                    pieces.append(item["text"])
                elif hasattr(item, "text") and isinstance(getattr(item, "text"), str):
                    pieces.append(getattr(item, "text"))
        elif hasattr(content, "text") and isinstance(content.text, str):
            pieces.append(content.text)
        if pieces:
            return "".join(pieces)

    return None


async def _run_claude(prompt: str, options: ClaudeAgentOptions) -> str:
    """Execute a single-turn Claude Agent SDK query and collect the streamed text."""
    fragments: List[str] = []

    async for event in query(prompt=prompt, options=options):
        text = _event_text(event)
        if text:
            fragments.append(text)

    return "".join(fragments).strip()


async def claude_agent_sdk_monitor(
    agent_name: str,
    config_path: Optional[str] = None,
    model: str = DEFAULT_MODEL,
) -> None:
    """Run the Claude Agent SDK monitor for an MCP agent."""

    # Use shared DRY config resolver
    agent_config = resolve_agent_config(agent_name, config_path)
    base_dir = Path(__file__).resolve().parent.parent.parent

    print(f"\n{'=' * 60}")
    print(f"🛡 CLAUDE AGENT SDK MONITOR: {agent_name}")
    print(f"{'=' * 60}")
    print(f"Model: {model}")

    mcp_servers: Dict[str, Dict] = agent_config.get("mcpServers", {})
    if not mcp_servers:
        raise ValueError(
            "Agent configuration is missing 'mcpServers'. Add at least one MCP server."
        )

    print(f"MCP Servers: {', '.join(mcp_servers.keys())}")

    # Build Claude Agent SDK server definitions (command/args/env)
    claude_servers: Dict[str, Dict] = {}
    for server_name, server_cfg in mcp_servers.items():
        entry = {
            "command": server_cfg.get("command", "npx"),
            "args": server_cfg.get("args", []),
        }
        if server_cfg.get("env"):
            entry["env"] = server_cfg["env"]
        claude_servers[server_name] = entry

    # Read security permissions from agent config
    permissions_config = agent_config.get("permissions", {})
    allowed_builtin_tools = permissions_config.get("allowedTools", [])
    permission_mode = permissions_config.get("permissionMode")
    working_dir = permissions_config.get("workingDir")

    if permissions_config:
        print(f"Security Config:")
        print(f"  Allowed built-in tools: {allowed_builtin_tools or 'None'}")
        print(f"  Permission mode: {permission_mode or 'default'}")
        print(f"  Working directory: {working_dir or 'unrestricted'}")
        print()

    system_prompt_override = os.getenv("AGENT_SYSTEM_PROMPT")
    conversation_history: List[str] = []

    async with MCPServerManager(agent_name, base_dir=base_dir, config_path=config_path) as manager:
        primary_session = manager.get_primary_session()
        allowlist = await _discover_allowed_tools(manager)

        print("MCP Tools Discovered:")
        print(_format_allowed_tools(allowlist))
        print()

        if not allowlist:
            logger.warning(
                "MCP allowlist is empty. Claude will not be able to call MCP tools until tools are available."
            )

        # Merge MCP tools with allowed built-in tools
        combined_allowlist = allowlist + allowed_builtin_tools

        print("Final Tool Allowlist:")
        print(_format_allowed_tools(combined_allowlist))
        print()

        options_kwargs: Dict[str, object] = {
            "allowed_tools": combined_allowlist,
            "mcp_servers": claude_servers,
        }

        # Apply permission mode if configured
        if permission_mode:
            options_kwargs["permission_mode"] = permission_mode

        # Apply working directory restriction if configured
        if working_dir:
            options_kwargs["cwd"] = working_dir

        try:
            options_signature = inspect.signature(ClaudeAgentOptions)
        except (TypeError, ValueError):  # pragma: no cover - signature introspection edge cases
            options_signature = None

        if options_signature is not None:
            if "model" in options_signature.parameters and model:
                options_kwargs["model"] = model
            if "system_prompt" in options_signature.parameters and system_prompt_override:
                options_kwargs["system_prompt"] = system_prompt_override

        options = ClaudeAgentOptions(**options_kwargs)

        identity_prompt_template = (
            "You are @{agent_name}, an Anthropic Claude agent deployed in the aX Agent Studio.\n"
            "Follow these rules strictly:\n"
            "1. Always start replies with @{sender} but never mention @{agent_name}.\n"
            "2. Keep responses helpful, friendly, and under 180 words.\n"
            "3. Use MCP tools only from the provided allowlist.\n"
            "4. Reference message IDs when they are supplied (format id:XXXXXXXX)."
        ).format(agent_name=agent_name, sender="{sender}")

        async def handle_message(message: Dict) -> str:
            sender = message.get("sender", "unknown")
            if sender == agent_name:
                logger.info("Ignoring self-mention for %s", agent_name)
                return ""

            raw_content = message.get("content", "")
            msg_id = message.get("id", "")
            msg_id_short = msg_id[:8] if isinstance(msg_id, str) else ""

            user_text = _extract_message_body(raw_content)
            logger.info("Processing message %s from %s", msg_id_short or "(no id)", sender)

            history_text = "\n".join(conversation_history[-_HISTORY_LIMIT:])
            prompt_sections: List[str] = [identity_prompt_template.replace("{sender}", sender)]
            if system_prompt_override:
                prompt_sections.append(system_prompt_override)
            if history_text:
                prompt_sections.append("Conversation history:\n" + history_text)

            prompt_sections.append(
                f"Incoming message from @{sender} [id:{msg_id_short or 'unknown'}]:\n{user_text}\n\n"
                f"Respond as @{agent_name} while following all rules."
            )

            prompt = "\n\n".join(section for section in prompt_sections if section)

            try:
                response_text = await _run_claude(prompt, options)
            except Exception as exc:  # pragma: no cover - network errors
                logger.error("Claude Agent SDK query failed: %s", exc)
                return f"@{sender} I'm having trouble thinking right now. Error: {exc}"[:240]

            if not response_text:
                logger.warning("Empty response from Claude for message %s", msg_id_short)
                response_text = "I'm still processing this request. Could you rephrase or provide more detail?"

            response_text = response_text.strip()
            if not response_text.startswith(f"@{sender}"):
                response_text = f"@{sender} {response_text}"

            if f"@{agent_name}" in response_text:
                response_text = response_text.replace(f"@{agent_name}", agent_name)
                logger.info("Stripped self-mention for %s", agent_name)

            conversation_history.append(f"@{sender}: {user_text}")
            conversation_history.append(f"@{agent_name}: {response_text}")
            if len(conversation_history) > _HISTORY_LIMIT:
                conversation_history[:] = conversation_history[-_HISTORY_LIMIT:]

            logger.info("Response:\n%s", response_text)
            return response_text

        monitor_config = get_monitor_config()
        queue_manager = QueueManager(
            agent_name=agent_name,
            session=primary_session,
            message_handler=handle_message,
            mark_read=monitor_config.get("mark_read", False),
            startup_sweep=monitor_config.get("startup_sweep", True),
            startup_sweep_limit=monitor_config.get("startup_sweep_limit", 10),
        )

        print("🚀 Starting FIFO queue manager...\n")
        await queue_manager.run()


def main() -> None:
    parser = argparse.ArgumentParser(description="Claude Agent SDK MCP Monitor")
    parser.add_argument("agent_name", help="Agent name to monitor")
    parser.add_argument("--config", help="Path to agent config JSON file")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="Claude model to use for responses",
    )

    args = parser.parse_args()
    asyncio.run(claude_agent_sdk_monitor(args.agent_name, config_path=args.config, model=args.model))


if __name__ == "__main__":
    main()
