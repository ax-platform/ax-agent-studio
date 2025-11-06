"""
Configuration loader for aX Agent Studio.

Loads settings from config.yaml in the project root.
"""

import json
from pathlib import Path
from typing import Any

import yaml

# Find the project root (where config.yaml lives)
PROJECT_ROOT = Path(__file__).parent.parent.parent


def load_config() -> dict[str, Any]:
    """Load configuration from config.yaml."""
    config_path = PROJECT_ROOT / "config.yaml"

    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}\n"
            "Please create config.yaml in the project root."
        )

    with open(config_path) as f:
        config = yaml.safe_load(f)

    return config


# Load config on module import
config = load_config()


# Convenience accessors
def get_mcp_config() -> dict[str, str]:
    """Get MCP server configuration."""
    return config.get("mcp", {})


def get_monitor_config() -> dict[str, Any]:
    """Get monitor configuration."""
    return config.get("monitors", {})


def get_ollama_config() -> dict[str, str]:
    """Get Ollama configuration."""
    return config.get("ollama", {})


def get_dashboard_config() -> dict[str, Any]:
    """Get dashboard configuration."""
    return config.get("dashboard", {})


def resolve_agent_config(agent_name: str, config_path: str | None = None) -> dict[str, Any]:
    """
    Resolve agent configuration file dynamically.

    This function removes the requirement for config filenames to match agent names.
    Instead, it searches all .json files in configs/agents/ and matches by the agent
    name found in the URL inside the config file.

    Args:
        agent_name: The agent name to search for
        config_path: Optional explicit config path. If provided, validates it contains
                    the correct agent name. If None, searches configs/agents/*.json

    Returns:
        Dict containing the agent configuration

    Raises:
        FileNotFoundError: If no matching config is found
        ValueError: If explicit config_path doesn't match agent_name
    """
    configs_dir = PROJECT_ROOT / "configs" / "agents"

    # Case 1: Explicit config path provided
    if config_path:
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_file) as f:
            agent_config = json.load(f)

        # Validate that this config matches the agent_name
        mcp_servers = agent_config.get("mcpServers", {})
        if mcp_servers:
            for server_config in mcp_servers.values():
                args = server_config.get("args", [])
                for arg in args:
                    if arg.startswith("http"):
                        # Extract agent name from URL like https://mcp.paxai.app/mcp/agents/Aurora
                        if "/agents/" in arg:
                            url_agent_name = arg.split("/agents/")[1].split("/")[0].split("?")[0]
                            if url_agent_name != agent_name:
                                raise ValueError(
                                    f"Config file {config_path} is for agent '{url_agent_name}', "
                                    f"but you requested '{agent_name}'. Agent name mismatch!"
                                )

        return agent_config

    # Case 2: Search for config by agent name in URL
    if not configs_dir.exists():
        raise FileNotFoundError(f"Configs directory not found: {configs_dir}")

    # Search all .json files
    for config_file in configs_dir.glob("*.json"):
        try:
            with open(config_file) as f:
                agent_config = json.load(f)

            # Check if this config is for our agent
            mcp_servers = agent_config.get("mcpServers", {})
            for server_config in mcp_servers.values():
                args = server_config.get("args", [])
                for arg in args:
                    if arg.startswith("http") and "/agents/" in arg:
                        url_agent_name = arg.split("/agents/")[1].split("/")[0].split("?")[0]
                        if url_agent_name == agent_name:
                            print(f" Found config for {agent_name} in: {config_file.name}")
                            return agent_config
        except (json.JSONDecodeError, KeyError):
            # Skip invalid JSON files
            continue

    raise FileNotFoundError(
        f"No config found for agent '{agent_name}' in {configs_dir}\n"
        f"Searched all .json files for URL containing '/agents/{agent_name}'"
    )
