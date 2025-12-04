#!/usr/bin/env python3
"""
MCP Multi-Server Manager
Manages connections to multiple MCP servers and provides unified tool access
"""

import json
import logging
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from ax_agent_studio.mcp_heartbeat import HeartbeatManager

logger = logging.getLogger(__name__)


class MCPServerManager:
    """Manages multiple MCP server connections with automatic heartbeat"""

    def __init__(
        self,
        agent_name: str,
        base_dir: Path | None = None,
        config_path: Path | None = None,
        heartbeat_interval: int = 240,
    ):
        """
        Initialize MCP Server Manager.

        Args:
            agent_name: Name of the agent
            base_dir: Base directory for configs (default: project root)
            config_path: Path to agent config JSON (default: configs/agents/{agent_name}.json)
            heartbeat_interval: Seconds between heartbeat pings (default: 240 = 4 min, 0 = disabled)
        """
        self.agent_name = agent_name
        self.base_dir = base_dir or Path(__file__).parent.parent.parent
        if config_path is not None:
            self.config_path = Path(config_path)
        else:
            self.config_path = self.base_dir / "configs" / "agents" / f"{agent_name}.json"

        # Multi-server state
        self.sessions: dict[str, ClientSession] = {}
        self.exit_stack = None
        self.config = None

        # Heartbeat manager for keeping connections alive
        self.heartbeat_manager = HeartbeatManager(interval=heartbeat_interval)
        logger.info(f"MCPServerManager initialized with heartbeat interval: {heartbeat_interval}s")

    async def __aenter__(self):
        """Async context manager entry - connect to all servers"""
        await self.connect_all()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup all connections"""
        await self.disconnect_all()

    def load_config(self) -> dict:
        """Load agent configuration from the specified config_path"""
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Agent config not found: {self.config_path}\n"
                f"The config file does not exist at the specified path."
            )

        with open(self.config_path) as f:
            self.config = json.load(f)

        if "mcpServers" not in self.config:
            raise ValueError(
                f"Invalid config format. Expected 'mcpServers' key in {self.config_path}"
            )

        return self.config

    def _build_server_params(self, server_name: str, server_config: dict) -> StdioServerParameters:
        """Build StdioServerParameters from config"""
        command = server_config.get("command", "npx")
        args = server_config.get("args", [])
        env = server_config.get("env")

        # Auto-detect python command and use current interpreter
        if command == "python":
            import sys
            command = sys.executable

        # Auto-fix Node.js path on Windows if npx is missing
        if command == "npx" or command == "npx.cmd":
            import shutil
            import os
            
            # Check if npx is in PATH
            if not shutil.which("npx") and not shutil.which("npx.cmd"):
                node_path = Path(r"C:\Program Files\nodejs")
                if node_path.exists():
                    logger.info(f"Adding {node_path} to PATH for {server_name}")
                    # Create copy of env or use os.environ
                    env = env.copy() if env else os.environ.copy()
                    env["PATH"] = str(node_path) + os.pathsep + env.get("PATH", "")
                    
                    # If command is npx, try to resolve full path to npx.cmd
                    if (node_path / "npx.cmd").exists():
                        command = str(node_path / "npx.cmd")

        return StdioServerParameters(command=command, args=args, env=env)

    async def connect_all(self):
        """Connect to all MCP servers defined in config"""
        if self.config is None:
            self.load_config()

        self.exit_stack = AsyncExitStack()
        await self.exit_stack.__aenter__()

        mcp_servers = self.config.get("mcpServers", {})

        print(f"\n Connecting to {len(mcp_servers)} MCP server(s)...")

        for server_name, server_config in mcp_servers.items():
            try:
                print(f"   • {server_name}...", end=" ")

                # Build server parameters
                server_params = self._build_server_params(server_name, server_config)

                # Connect to server
                read, write = await self.exit_stack.enter_async_context(stdio_client(server_params))

                # Create session
                session = await self.exit_stack.enter_async_context(ClientSession(read, write))

                # Initialize session
                await session.initialize()

                # Store session
                self.sessions[server_name] = session

                # Start heartbeat ONLY for remote aX servers (not local filesystem/memory/etc)
                # Local servers don't have Cloud Run timeouts, only remote aX server needs pings
                if server_name.startswith("ax-") or "mcp-remote" in str(
                    server_config.get("args", [])
                ):
                    await self.heartbeat_manager.start(
                        session, name=f"{self.agent_name}/{server_name}"
                    )
                    logger.info(f"Started heartbeat for remote server: {server_name}")
                else:
                    logger.debug(f"Skipping heartbeat for local server: {server_name}")

                # Get available tools
                tools_response = await session.list_tools()
                tool_count = len(tools_response.tools) if hasattr(tools_response, "tools") else 0

                print(f" ({tool_count} tools)")
                logger.info(f"Connected to {server_name} with {tool_count} tools")

            except Exception as e:
                print("")
                logger.error(f"Failed to connect to {server_name}: {e}")
                # Continue with other servers even if one fails

        print(f" Connected to {len(self.sessions)}/{len(mcp_servers)} servers\n")

    async def disconnect_all(self):
        """Disconnect from all MCP servers and stop heartbeats"""
        # Stop all heartbeats
        await self.heartbeat_manager.stop_all()

        # Disconnect sessions
        if self.exit_stack:
            await self.exit_stack.__aexit__(None, None, None)
            self.sessions.clear()

    def get_session(self, server_name: str) -> ClientSession | None:
        """Get a specific MCP session by server name"""
        return self.sessions.get(server_name)

    def get_primary_session(self) -> ClientSession:
        """Get the primary session (ax-gcp for messaging)"""
        # Try ax-gcp first
        if "ax-gcp" in self.sessions:
            return self.sessions["ax-gcp"]

        # Fallback to first available session
        if self.sessions:
            return next(iter(self.sessions.values()))

        raise RuntimeError("No MCP sessions available")

    async def list_all_tools(self) -> dict[str, list[Any]]:
        """List all available tools from all servers"""
        all_tools = {}

        for server_name, session in self.sessions.items():
            try:
                response = await session.list_tools()
                tools = response.tools if hasattr(response, "tools") else []
                all_tools[server_name] = tools
            except Exception as e:
                logger.error(f"Failed to list tools for {server_name}: {e}")
                all_tools[server_name] = []

        return all_tools

    async def call_tool(self, server_name: str, tool_name: str, arguments: dict) -> Any:
        """Call a tool on a specific server"""
        session = self.get_session(server_name)
        if not session:
            raise ValueError(f"Server '{server_name}' not connected")

        return await session.call_tool(tool_name, arguments)

    def print_summary(self):
        """Print a summary of connected servers and available tools"""
        print("\n MCP Servers Summary:")
        print(f"   Agent: {self.agent_name}")
        print(f"   Config: {self.config_path}")
        print(f"   Servers: {len(self.sessions)}")

        for server_name, session in self.sessions.items():
            print(f"      • {server_name}")

    async def create_langchain_tools(self):
        """
        Create LangChain-compatible tools from all MCP servers using official adapter
        Returns list of async LangChain tools
        """
        from langchain_mcp_adapters.tools import load_mcp_tools

        all_tools = []

        for server_name, session in self.sessions.items():
            logger.info(f"Loading tools from {server_name}...")

            # Use official MCP adapter to load tools
            server_tools = await load_mcp_tools(session)

            # Prefix tool names with server name for clarity
            for tool in server_tools:
                # Store original name if not already prefixed
                if not tool.name.startswith(f"{server_name}_"):
                    tool.name = f"{server_name}_{tool.name}"
                all_tools.append(tool)
                logger.info(f"Created tool: {tool.name}")

        return all_tools
