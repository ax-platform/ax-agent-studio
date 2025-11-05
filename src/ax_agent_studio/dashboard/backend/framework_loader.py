"""Framework Registry Loader

Loads framework definitions from configs/frameworks.yaml with environment variable substitution.
"""

import os
import re
from pathlib import Path
from typing import Any

import yaml


def _substitute_env_vars(value: Any) -> Any:
    """Recursively substitute environment variables in config values.

    Supports ${VAR_NAME:-default_value} syntax.
    """
    if isinstance(value, str):
        # Pattern: ${VAR_NAME:-default}
        pattern = r"\$\{([^:}]+)(?::-([^}]+))?\}"

        def replacer(match):
            var_name = match.group(1)
            default = match.group(2) or ""
            return os.getenv(var_name, default)

        return re.sub(pattern, replacer, value)
    elif isinstance(value, dict):
        return {k: _substitute_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_substitute_env_vars(item) for item in value]
    else:
        return value


def load_frameworks() -> dict[str, Any]:
    """Load framework registry with environment variable substitution.

    Returns:
        Dict with framework definitions and UI defaults
    """
    # Path from src/ax_agent_studio/dashboard/backend/framework_loader.py -> configs/frameworks.yaml
    config_path = Path(__file__).parent.parent.parent.parent.parent / "configs" / "frameworks.yaml"

    if not config_path.exists():
        raise FileNotFoundError(f"Framework registry not found: {config_path}")

    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Substitute environment variables in the entire config
    config = _substitute_env_vars(config)

    return config


def get_framework_info(framework_type: str) -> dict[str, Any]:
    """Get configuration info for a specific framework.

    Args:
        framework_type: Framework identifier (echo, ollama, claude_agent_sdk, etc.)

    Returns:
        Framework configuration dict

    Raises:
        KeyError: If framework not found
    """
    config = load_frameworks()
    frameworks = config.get("frameworks", {})

    if framework_type not in frameworks:
        raise KeyError(f"Unknown framework: {framework_type}")

    return frameworks[framework_type]


def get_ui_defaults() -> dict[str, str]:
    """Get UI defaults with environment variable substitution.

    Returns:
        Dict with default_framework, default_provider, default_model
    """
    config = load_frameworks()
    return config.get("ui", {})


def get_provider_defaults(provider: str) -> dict[str, Any]:
    """Get default model and available models for a provider.

    Args:
        provider: Provider name (anthropic, openai, google, etc.)

    Returns:
        Dict with default_model and available_models

    Raises:
        KeyError: If provider not found
    """
    config = load_frameworks()
    provider_defaults = config.get("provider_defaults", {})

    if provider not in provider_defaults:
        raise KeyError(f"Unknown provider: {provider}")

    return provider_defaults[provider]
