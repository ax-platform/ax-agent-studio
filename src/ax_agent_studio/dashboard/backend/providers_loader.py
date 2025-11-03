"""
Providers Loader - Load LLM provider configurations
"""

import yaml
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent


def load_providers() -> Dict[str, Any]:
    """Load provider configurations from providers.yaml"""
    providers_path = PROJECT_ROOT / "configs" / "providers.yaml"

    if not providers_path.exists():
        return {"providers": {}, "defaults": {"provider": "gemini", "model": "gemini-2.5-flash"}}

    try:
        with open(providers_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading providers: {e}")
        return {"providers": {}, "defaults": {"provider": "gemini", "model": "gemini-2.5-flash"}}


def is_provider_configured(provider_id: str, provider_data: Dict[str, Any]) -> bool:
    """Check if a provider is configured and available"""

    # Ollama is always available (local)
    if provider_id == "ollama":
        return True

    # Anthropic: Available if API key OR subscription mode
    # When USE_CLAUDE_SUBSCRIPTION=true, the API key may be temporarily unset
    # but Claude Agent SDK can still use subscription authentication
    if provider_id == "anthropic":
        has_api_key = bool(os.getenv("ANTHROPIC_API_KEY"))
        has_subscription = os.getenv("USE_CLAUDE_SUBSCRIPTION", "").lower() == "true"
        return has_api_key or has_subscription

    # Check for API key
    if provider_data.get("requires_api_key"):
        env_var = provider_data.get("env_var")
        if env_var and os.getenv(env_var):
            return True
        return False

    # Check for AWS Bedrock
    if provider_data.get("uses_aws_credentials"):
        # Check if AWS credentials exist or aws_bedrock flag is set
        has_aws_keys = bool(os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"))
        has_aws_profile = Path.home() / ".aws" / "credentials"
        bedrock_enabled = os.getenv("AWS_BEDROCK_ENABLED", "").lower() in ("true", "1", "yes")

        return has_aws_keys or has_aws_profile.exists() or bedrock_enabled

    return False


def get_providers_list(include_unavailable: bool = False) -> List[Dict[str, Any]]:
    """Get list of available providers with metadata

    Args:
        include_unavailable: If True, include providers that aren't configured
    """
    config = load_providers()
    providers = config.get("providers", {})

    result = []
    for provider_id, provider_data in providers.items():
        is_configured = is_provider_configured(provider_id, provider_data)

        # Skip unconfigured providers unless requested
        if not is_configured and not include_unavailable:
            continue

        result.append({
            "id": provider_id,
            "name": provider_data.get("name", provider_id),
            "description": provider_data.get("description", ""),
            "requires_api_key": provider_data.get("requires_api_key", False),
            "env_var": provider_data.get("env_var"),
            "uses_aws_credentials": provider_data.get("uses_aws_credentials", False),
            "configured": is_configured
        })

    return result


async def get_models_for_provider(provider_id: str) -> List[Dict[str, Any]]:
    """Get available models for a specific provider

    For Ollama: Dynamically loads models from `ollama list` command
    For others: Returns static list from providers.yaml
    """
    # Special case: Ollama uses dynamic model discovery
    if provider_id == "ollama":
        from .config_loader import ConfigLoader
        config_loader = ConfigLoader(PROJECT_ROOT)
        ollama_models = await config_loader.get_ollama_models()

        # Format Ollama models to match expected structure
        return [
            {
                "id": model,
                "name": model,
                "description": f"Ollama model: {model}",
                "recommended": False,
                "default": False  # Could check against config.yaml default_model
            }
            for model in ollama_models
        ]

    # Standard case: Load from providers.yaml
    config = load_providers()
    providers = config.get("providers", {})

    if provider_id not in providers:
        return []

    provider = providers[provider_id]
    models = provider.get("models", [])
    default_model = provider.get("default_model")

    return [
        {
            "id": model.get("id"),
            "name": model.get("name"),
            "description": model.get("description", ""),
            "recommended": model.get("recommended", False),
            "default": model.get("id") == default_model if default_model else False
        }
        for model in models
    ]


def get_provider_config(provider_id: str) -> Optional[Dict[str, Any]]:
    """Get full configuration for a specific provider"""
    config = load_providers()
    providers = config.get("providers", {})
    return providers.get(provider_id)


def get_defaults() -> Dict[str, str]:
    """Get default provider, model, and agent type"""
    import os
    config = load_providers()
    defaults = config.get("defaults", {"provider": "gemini", "model": "gemini-2.5-flash"})

    # Add default agent type from environment (defaults to claude_agent_sdk)
    default_agent_type = os.getenv("DEFAULT_AGENT_TYPE", "claude_agent_sdk")
    defaults["agent_type"] = default_agent_type

    return defaults
