"""
Configuration loader for aX Agent Studio.

Loads settings from config.yaml in the project root.
"""

import yaml
from pathlib import Path
from typing import Any, Dict

# Find the project root (where config.yaml lives)
PROJECT_ROOT = Path(__file__).parent.parent.parent


def load_config() -> Dict[str, Any]:
    """Load configuration from config.yaml."""
    config_path = PROJECT_ROOT / "config.yaml"

    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}\n"
            "Please create config.yaml in the project root."
        )

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    return config


# Load config on module import
config = load_config()


# Convenience accessors
def get_mcp_config() -> Dict[str, str]:
    """Get MCP server configuration."""
    return config.get("mcp", {})


def get_monitor_config() -> Dict[str, Any]:
    """Get monitor configuration."""
    return config.get("monitors", {})


def get_ollama_config() -> Dict[str, str]:
    """Get Ollama configuration."""
    return config.get("ollama", {})


def get_dashboard_config() -> Dict[str, Any]:
    """Get dashboard configuration."""
    return config.get("dashboard", {})
