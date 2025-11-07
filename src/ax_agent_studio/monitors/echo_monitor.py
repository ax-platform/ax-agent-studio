#!/usr/bin/env python3
"""
Echo Monitor - Deterministic Testing Monitor

Simple monitor that echoes back received messages with queue awareness.
Perfect for deterministic E2E tests where you need predictable output.

Usage:
    uv run python -m ax_agent_studio.monitors.echo_monitor <agent_name> --config <config_path>

Example:
    uv run python -m ax_agent_studio.monitors.echo_monitor lunar_craft_128 \
        --config configs/agents/lunar_craft_128.json
"""

import argparse
import asyncio
import json

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from ax_agent_studio.config import get_mcp_config, get_monitor_config
from ax_agent_studio.conversation_memory import (
    prepare_batch_message_context,
    prepare_message_board_context,
)
from ax_agent_studio.message_store import MessageStore
from ax_agent_studio.queue_manager import QueueManager


async def echo_monitor(
    agent_name: str,
    server_url: str,
    db_path: str = "data/message_backlog.db",
):
    """Echo monitor that returns deterministic responses with queue awareness"""

    print(f"\n{'=' * 80}")
    print(f"ECHO MONITOR: {agent_name}")
    print(f"{'=' * 80}")
    print(f"Server: {server_url}")
    print("Mode: Deterministic Echo (for testing)")
    print(f"Database: {db_path}")
    print(f"{'=' * 80}\n")

    # Initialize message store
    store = MessageStore(db_path=db_path)

    # MCP connection setup
    server_params = StdioServerParameters(
        command="npx",
        args=[
            "-y",
            "mcp-remote@0.1.29",
            server_url,
            "--transport",
            "http-only",
            "--allow-http",
            "--oauth-server",
            get_mcp_config().get("oauth_url", "http://localhost:8001"),
        ],
        env=None,
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("✓ Connected to MCP server\n")

            # Define echo message handler
            async def handle_message(msg: dict) -> str:
                """Return deterministic echo with batch/queue information"""

                sender = msg.get("sender", "unknown")

                # CRITICAL: Never process our own messages (prevents infinite loop)
                if sender == agent_name:
                    print(f"⏭  Skipping self-message from {sender}")
                    return ""  # Empty response = no action

                # Use new batch utilities
                formatted_context, is_batch, history = prepare_batch_message_context(msg, agent_name)
                content = msg.get("content", "")

                # Build deterministic response
                response_parts = []

                if is_batch:
                    # BATCH MODE: Multiple messages processed together
                    response_parts.append(f"[ECHO - BATCH MODE] Processed {len(history) + 1} messages together")
                    response_parts.append(f"[ECHO] Current message from @{sender}: {content}")
                    response_parts.append(f"[ECHO] History: {len(history)} previous messages")

                    # List history messages
                    if history:
                        response_parts.append("[ECHO] Message history:")
                        for i, h in enumerate(history, 1):
                            h_sender = h.get("sender", "unknown")
                            h_content = h.get("content", "")[:50]  # Truncate
                            response_parts.append(f"  {i}. @{h_sender}: {h_content}...")
                else:
                    # SINGLE MODE: One message
                    response_parts.append(f"[ECHO - SINGLE MODE] Received from @{sender}")
                    response_parts.append(f"[ECHO] Content: {content}")

                # Show formatted context (visual debug)
                print("\n" + formatted_context)

                return "\n".join(response_parts)

            # Use QueueManager for FIFO processing
            monitor_config = get_monitor_config()

            queue_mgr = QueueManager(
                agent_name=agent_name,
                session=session,
                message_handler=handle_message,
                store=store,
                mark_read=monitor_config.get("mark_read", False),
                startup_sweep=monitor_config.get("startup_sweep", True),
                startup_sweep_limit=monitor_config.get("startup_sweep_limit", 10),
                heartbeat_interval=monitor_config.get("heartbeat_interval", 240),
            )

            print("✓ Echo handler initialized")
            print("✓ Starting FIFO queue manager...\n")
            await queue_mgr.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Echo Monitor for deterministic testing")
    parser.add_argument("agent_name", help="Name of the agent to monitor")
    parser.add_argument("--config", required=True, help="Path to agent config JSON file")
    parser.add_argument("--db", default="data/message_backlog.db", help="Database path")

    args = parser.parse_args()

    # Load agent config to get server URL
    with open(args.config) as f:
        agent_config = json.load(f)

    # Get the primary MCP server (first one in mcpServers)
    mcp_servers = agent_config.get("mcpServers", {})
    if not mcp_servers:
        print("ERROR: No mcpServers in agent config")
        exit(1)

    # Use the first MCP server as the primary one for messaging
    primary_server_name = list(mcp_servers.keys())[0]
    primary_server = mcp_servers[primary_server_name]

    # Extract server URL from args
    server_url = None
    args_list = primary_server.get("args", [])
    for i, arg in enumerate(args_list):
        if arg.startswith("http://") or arg.startswith("https://"):
            # Skip oauth server
            if i > 0 and args_list[i - 1] == "--oauth-server":
                continue
            server_url = arg
            break

    if not server_url:
        # Fallback to global config
        mcp_config = get_mcp_config()
        base_url = mcp_config.get("server_url", "http://localhost:8002")
        server_url = f"{base_url}/mcp/agents/{args.agent_name}"

    try:
        asyncio.run(echo_monitor(args.agent_name, server_url, args.db))
    except KeyboardInterrupt:
        print("\n\n🛑 Echo monitor stopped by user")
    except Exception as e:
        print(f"\n\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        raise
