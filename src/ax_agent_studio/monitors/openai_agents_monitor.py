#!/usr/bin/env python3
"""OpenAI Agents SDK Monitor

Lightweight monitor using OpenAI's Agents SDK with native MCP support.
Automatically discovers and connects to MCP servers, providing seamless
integration with OpenAI's agent framework.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv

from ax_agent_studio.config import get_monitor_config
from ax_agent_studio.mcp_manager import MCPServerManager
from ax_agent_studio.queue_manager import QueueManager

# Load environment variables from .env file
load_dotenv()

try:
    from agents import Agent, Runner
    from agents.mcp import MCPServerStdio, MCPServerStreamableHttp
except ImportError:  # pragma: no cover
    print("❌ Missing dependency: openai-agents")
    print("   Install with: pip install openai-agents")
    sys.exit(1)

# Configure logging
if not logging.getLogger().hasHandlers():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-5-mini"  # OpenAI's latest efficient model
_HISTORY_LIMIT = 10  # Recent message pairs to keep


def _resolve_config_path(agent_name: str, config_path: Optional[str], base_dir: Path) -> Path:
    """Resolve the agent config path.

    If config_path is provided, use it directly.
    Otherwise, search for a config file where the agent name in the URL matches agent_name.
    This allows flexible filename conventions (e.g., 'prod-bot.json', 'my-agent.json').
    """
    if config_path:
        resolved = Path(config_path).expanduser().resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"Agent config not found: {resolved}")
        return resolved

    # Search configs/agents/ for a file with matching agent name in URL
    agents_dir = base_dir / "configs" / "agents"
    if not agents_dir.exists():
        raise FileNotFoundError(
            f"Agents directory not found: {agents_dir}\n"
            "Create configs/agents/ and add agent configuration files."
        )

    for config_file in agents_dir.glob("*.json"):
        try:
            with open(config_file) as f:
                data = json.load(f)

            # Skip template files
            if "_comment" in data or "_instructions" in data:
                continue

            # Extract agent name from MCP server URL
            if "mcpServers" in data:
                for server_config in data["mcpServers"].values():
                    args = server_config.get("args", [])
                    for arg in args:
                        if isinstance(arg, str) and "/mcp/agents/" in arg:
                            url_agent_name = arg.split("/mcp/agents/")[-1].strip()
                            if url_agent_name == agent_name:
                                return config_file
        except Exception:
            continue  # Skip invalid JSON files

    # If no match found, suggest the issue
    raise FileNotFoundError(
        f"No agent config found with agent name '{agent_name}' in the URL.\n"
        f"Searched in: {agents_dir}\n"
        f"Make sure your config file contains:\n"
        f'  "mcpServers": {{ "ax-gcp": {{ "args": ["...mcp/agents/{agent_name}", ...] }} }}'
    )


async def _create_mcp_servers_from_config(agent_config: Dict) -> List:
    """Create OpenAI Agents SDK MCP server instances from agent config.

    IMPORTANT: Only creates stdio servers (filesystem, memory, etc).
    Skips ax-docker/ax-gcp which are handled by MCPServerManager via mcp-remote OAuth proxy.
    Direct HTTP connections fail with 401 because they bypass OAuth.
    """
    mcp_servers_config = agent_config.get("mcpServers", {})
    servers = []

    for server_name, server_cfg in mcp_servers_config.items():
        command = server_cfg.get("command", "npx")
        args = server_cfg.get("args", [])
        env = server_cfg.get("env", {})

        # Check if this server uses mcp-remote (HTTP with OAuth)
        # These must go through MCPServerManager, not OpenAI SDK direct connection
        is_mcp_remote = "mcp-remote" in str(args)
        is_http = any("http://" in str(arg) or "https://" in str(arg) for arg in args)

        if is_mcp_remote or (is_http and server_name in ["ax-docker", "ax-gcp"]):
            # SKIP ax-docker/ax-gcp - handled by MCPServerManager with OAuth
            logger.info(f"Skipping {server_name} (handled by MCPServerManager via mcp-remote OAuth)")
            continue
        elif is_http:
            # Other HTTP servers (if any) - use StreamableHTTP
            url = next((arg for arg in args if "http" in str(arg)), None)
            if url:
                server = MCPServerStreamableHttp(
                    name=server_name,
                    params={
                        "url": url,
                        "headers": {},
                        "timeout": 30,
                    },
                    cache_tools_list=True,
                )
                servers.append(server)
                logger.info(f"Configured HTTP MCP server: {server_name} ({url})")
        else:
            # Use stdio for local processes (like filesystem, memory, etc.)
            full_env = os.environ.copy()
            full_env.update(env)

            server = MCPServerStdio(
                name=server_name,
                params={
                    "command": command,
                    "args": args,
                    "env": full_env if env else None,
                },
                cache_tools_list=True,
            )
            servers.append(server)
            logger.info(f"Configured stdio MCP server: {server_name} ({command} {' '.join(args)})")

    return servers


def _extract_message_body(raw_content: str) -> str:
    """Extract human message from MCP mention payload."""
    if not raw_content:
        return ""

    # Remove @mentions pattern: @sender_name message content
    lines = raw_content.split("\n", 1)
    if len(lines) > 1:
        return lines[1].strip()
    return raw_content.strip()


async def openai_agents_monitor(
    agent_name: str,
    config_path: Optional[str] = None,
    model: str = DEFAULT_MODEL,
) -> None:
    """Run the OpenAI Agents SDK monitor for an MCP agent."""

    # Get project root (3 levels up from this file: monitors/ -> ax_agent_studio/ -> src/ -> project_root/)
    base_dir = Path(__file__).resolve().parent.parent.parent.parent
    resolved_config = _resolve_config_path(agent_name, config_path, base_dir)

    print(f"\n{'=' * 60}")
    print(f"🤖 OPENAI AGENTS SDK MONITOR: {agent_name}")
    print(f"{'=' * 60}")
    print(f"Config: {resolved_config}")
    print(f"Model: {model}")

    with resolved_config.open() as f:
        agent_config = json.load(f)

    mcp_servers_config = agent_config.get("mcpServers", {})
    if not mcp_servers_config:
        raise ValueError(
            "Agent configuration is missing 'mcpServers'. Add at least one MCP server."
        )

    print(f"MCP Servers: {', '.join(mcp_servers_config.keys())}")

    # Read permissions if configured
    permissions_config = agent_config.get("permissions", {})
    if permissions_config:
        print(f"\nPermissions Config:")
        print(f"  Note: OpenAI Agents SDK handles permissions via tool filtering")
        print()

    # API key check
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY not found in environment. "
            "Set it in your .env file: OPENAI_API_KEY=sk-..."
        )

    system_prompt_override = os.getenv("AGENT_SYSTEM_PROMPT")
    conversation_history: List[Dict] = []

    # Create MCP servers using OpenAI Agents SDK MCP classes (for agent tool access)
    mcp_server_instances = await _create_mcp_servers_from_config(agent_config)

    print(f"\n✅ Configured {len(mcp_server_instances)} MCP servers for agent")
    print()

    # Use MCPServerManager same way as LangGraph monitor - auto-loads full config
    # This connects to ALL servers for QueueManager messaging
    # (OpenAI SDK handles separate agent tool connections)
    async with MCPServerManager(agent_name, base_dir=base_dir) as manager:
        primary_session = manager.get_primary_session()
        print(f"✅ Connected messaging layer for QueueManager\n")

        # Open all MCP server connections
        # We need to use AsyncExitStack to manage multiple async context managers
        from contextlib import AsyncExitStack

        async with AsyncExitStack() as stack:
            # Connect all MCP servers
            mcp_servers = []
            for server in mcp_server_instances:
                connected_server = await stack.enter_async_context(server)
                mcp_servers.append(connected_server)

            print(f"✅ Connected {len(mcp_servers)} MCP servers for agent tool access\n")

            # Build agent instructions
            base_instructions = (
                f"You are @{agent_name}, an AI agent deployed in the aX Agent Studio.\n"
                "Follow these rules:\n"
                "1. Always start replies with @{{sender}} but never mention yourself.\n"
                "2. Keep responses helpful, friendly, and concise.\n"
                "3. Use MCP tools to complete tasks.\n"
                "4. Reference message IDs when supplied (format: id:XXXXXXXX)."
            )

            if system_prompt_override:
                instructions = f"{base_instructions}\n\nAdditional instructions:\n{system_prompt_override}"
            else:
                instructions = base_instructions

            # Create OpenAI agent with MCP servers
            # Note: We create the agent inside the context managers
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

                # Build context-aware instructions
                context_instructions = instructions.replace("{sender}", sender)

                # Add conversation history for context
                if conversation_history:
                    history_text = "\n".join(
                        f"{msg['role']}: {msg['content']}"
                        for msg in conversation_history[-_HISTORY_LIMIT:]
                    )
                    context_instructions += f"\n\nRecent conversation:\n{history_text}"

                # Add current message context
                full_prompt = (
                    f"Incoming message from @{sender} [id:{msg_id_short or 'unknown'}]:\n"
                    f"{user_text}\n\n"
                    f"Respond as @{agent_name} following all rules."
                )

                try:
                    # Create agent for this specific interaction
                    # OpenAI Agents SDK agents are lightweight and can be created per-message
                    agent = Agent(
                        name=agent_name,
                        instructions=context_instructions,
                        mcp_servers=mcp_servers,
                        model=model,
                    )

                    # Run the agent with the message
                    result = await Runner.run(agent, full_prompt)

                    # Extract response text
                    response_text = ""
                    if hasattr(result, "messages") and result.messages:
                        # Get the last assistant message
                        for msg in reversed(result.messages):
                            if msg.role == "assistant" and hasattr(msg, "content"):
                                for content in msg.content:
                                    if hasattr(content, "text"):
                                        response_text = content.text
                                        break
                                if response_text:
                                    break

                    if not response_text:
                        response_text = "I processed your request but have no text response."

                except Exception as exc:  # pragma: no cover
                    logger.error("OpenAI agent execution failed: %s", exc)
                    return f"@{sender} I encountered an error: {str(exc)[:100]}"

                # Ensure response starts with @sender
                response_text = response_text.strip()
                if not response_text.startswith(f"@{sender}"):
                    response_text = f"@{sender} {response_text}"

                # Remove self-mentions
                if f"@{agent_name}" in response_text:
                    response_text = response_text.replace(f"@{agent_name}", agent_name)

                # Update conversation history
                conversation_history.append({"role": "user", "content": f"@{sender}: {user_text}"})
                conversation_history.append({"role": "assistant", "content": response_text})

                if len(conversation_history) > _HISTORY_LIMIT * 2:
                    conversation_history[:] = conversation_history[-_HISTORY_LIMIT * 2:]

                logger.info("Response generated: %d chars", len(response_text))
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
    parser = argparse.ArgumentParser(description="OpenAI Agents SDK MCP Monitor")
    parser.add_argument("agent_name", help="Agent name to monitor")
    parser.add_argument("--config", help="Path to agent config JSON file")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"OpenAI model to use (default: {DEFAULT_MODEL})",
    )

    args = parser.parse_args()

    asyncio.run(openai_agents_monitor(args.agent_name, config_path=args.config, model=args.model))


if __name__ == "__main__":
    main()
