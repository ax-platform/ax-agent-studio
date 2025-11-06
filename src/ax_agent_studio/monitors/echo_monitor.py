#!/usr/bin/env python3
"""
Echo Monitor - Simplest MCP Monitor Template
Monitors for @mentions and echoes them back - perfect for testing!

Usage:
    python echo_monitor.py <agent_name>

Example:
    python echo_monitor.py rigelz_334
"""

import asyncio
import re
from datetime import datetime

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from ax_agent_studio.config import get_mcp_config, get_monitor_config


async def echo_monitor(agent_name, config_path=None):
    """
    Simple echo monitor that responds to @mentions
    Perfect for testing and understanding the flow!
    """

    # Load configuration
    monitor_config = get_monitor_config()

    # Determine MCP server endpoint from agent config or fallback to global config
    if config_path:
        import json

        print(f" Loading agent config from: {config_path}")
        with open(config_path) as f:
            agent_config = json.load(f)

        # Get the primary MCP server (first one in mcpServers)
        mcp_servers = agent_config.get("mcpServers", {})
        if not mcp_servers:
            print("  No mcpServers in agent config, falling back to global config.yaml")
            mcp_config = get_mcp_config()
            base_url = mcp_config.get("server_url", "http://localhost:8002")
            server_url = f"{base_url}/mcp/agents/{agent_name}"
            oauth_server = mcp_config.get("oauth_url", "http://localhost:8001")
        else:
            # Use the first MCP server as the primary one for messaging
            primary_server_name = list(mcp_servers.keys())[0]
            primary_server = mcp_servers[primary_server_name]

            # Extract server URL from args (usually args[0] after npx command)
            args = primary_server.get("args", [])
            server_url = None
            oauth_server = "http://localhost:8001"  # default

            # Find the server URL in args (skip npx flags)
            # The MCP server URL is the first http(s) URL, not preceded by a flag
            for i, arg in enumerate(args):
                if arg.startswith("http://") or arg.startswith("https://"):
                    # Check if this is after --oauth-server flag
                    if i > 0 and args[i - 1] == "--oauth-server":
                        oauth_server = arg
                    elif server_url is None:  # Only take the first non-oauth URL
                        server_url = arg

            if not server_url:
                raise ValueError(f"Could not find server URL in config: {config_path}")

            print(f" Using MCP server from agent config: {server_url}")
    else:
        # Fallback to global config.yaml
        print("  No config path provided, using global config.yaml")
        mcp_config = get_mcp_config()
        base_url = mcp_config.get("server_url", "http://localhost:8002")
        server_url = f"{base_url}/mcp/agents/{agent_name}"
        oauth_server = mcp_config.get("oauth_url", "http://localhost:8001")

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
            oauth_server,
        ],
    )

    print(f" Echo Monitor starting for @{agent_name}")
    print(f"   Server: {server_url}")
    print("   Mode: FIFO queue")
    print("   Press Ctrl+C to stop\n")

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print(" Connected to MCP server\n")

                # Define message handler (pluggable function for QueueManager)
                async def handle_message(msg: dict) -> str:
                    """Echo back the message"""
                    sender = msg.get("sender", "unknown")
                    content = msg.get("content", "")
                    msg_id = msg.get("id", "")

                    try:
                        # Extract just the message text (after the @mention)
                        match = re.search(r"@\S+\s+(.+)", content)
                        if match:
                            original_msg = match.group(1).strip()
                        else:
                            original_msg = content.strip()

                        # Remove trailing "..." if present
                        if original_msg.endswith("..."):
                            original_msg = original_msg[:-3]

                        # Filter out echo responses to prevent infinite loops
                        if "Echo received at" in original_msg:
                            print("   Ignoring echo response (prevents loop)")
                            return None  # Skip this message

                        # Echo back with timestamp and message ID
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        msg_id_short = msg_id[:8] if len(msg_id) > 8 else msg_id
                        return f"Echo received at {timestamp} from @{sender} [id:{msg_id_short}]: {original_msg} "

                    except Exception as e:
                        print(f"   Error parsing message: {e}")
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        return f"Echo received at {timestamp} from @{sender}! "

                # Use QueueManager for FIFO processing
                from ax_agent_studio.queue_manager import QueueManager

                queue_mgr = QueueManager(
                    agent_name=agent_name,
                    session=session,
                    message_handler=handle_message,
                    mark_read=monitor_config.get("mark_read", False),
                    startup_sweep=monitor_config.get("startup_sweep", True),
                    startup_sweep_limit=monitor_config.get("startup_sweep_limit", 10),
                    heartbeat_interval=monitor_config.get("heartbeat_interval", 240),
                )

                print(" Starting FIFO queue manager...\n")
                await queue_mgr.run()

    except KeyboardInterrupt:
        print("\n\n Echo monitor stopped by user")
    except Exception as e:
        print(f"\n Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Echo Monitor - Simple MCP Monitor")
    parser.add_argument("agent_name", help="Agent name to monitor")
    parser.add_argument("--config", help="Path to agent config JSON file")

    args = parser.parse_args()
    asyncio.run(echo_monitor(args.agent_name, args.config))
