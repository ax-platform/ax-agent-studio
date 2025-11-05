"""
LLM Factory - Provider-agnostic LLM initialization
Creates LLM clients for any provider: Gemini, Anthropic, OpenAI, Bedrock, Ollama
"""

import os
from typing import Any

from dotenv import load_dotenv

from ax_agent_studio.dashboard.backend.providers_loader import get_provider_config

# Load environment variables
load_dotenv()


class LLMFactory:
    """Factory for creating LLM clients based on provider"""

    @staticmethod
    def create_llm(provider: str, model: str, **kwargs) -> Any:
        """
        Create an LLM client for the specified provider

        Args:
            provider: Provider ID (e.g., 'gemini', 'anthropic', 'openai', 'bedrock', 'ollama')
            model: Model ID (e.g., 'gemini-2.0-flash', 'claude-3-5-haiku-latest')
            **kwargs: Additional provider-specific parameters

        Returns:
            LLM client instance

        Raises:
            ValueError: If provider is not supported or missing dependencies
        """
        provider_config = get_provider_config(provider)

        if not provider_config:
            raise ValueError(f"Unknown provider: {provider}")

        # Get provider details
        package = provider_config.get("package")
        class_name = provider_config.get("class")
        model_kwargs = provider_config.get("model_kwargs", {})

        # Merge provider model_kwargs with user kwargs
        merged_kwargs = {**model_kwargs, **kwargs}

        # Initialize based on provider
        if provider == "gemini":
            return LLMFactory._create_gemini(model, merged_kwargs)
        elif provider == "anthropic":
            return LLMFactory._create_anthropic(model, merged_kwargs)
        elif provider == "openai":
            return LLMFactory._create_openai(model, merged_kwargs)
        elif provider == "bedrock":
            return LLMFactory._create_bedrock(model, merged_kwargs)
        elif provider == "ollama":
            return LLMFactory._create_ollama(model, merged_kwargs)
        else:
            raise ValueError(f"Provider '{provider}' not yet implemented")

    @staticmethod
    def _create_gemini(model: str, kwargs: dict[str, Any]) -> Any:
        """Create Google Gemini LLM"""
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY not found in environment")

            return ChatGoogleGenerativeAI(model=model, google_api_key=api_key, **kwargs)
        except ImportError:
            raise ValueError(
                "langchain-google-genai not installed. Install with: uv add langchain-google-genai"
            )

    @staticmethod
    def _create_anthropic(model: str, kwargs: dict[str, Any]) -> Any:
        """Create Anthropic Claude LLM"""
        try:
            from langchain_anthropic import ChatAnthropic

            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not found in environment")

            return ChatAnthropic(model=model, anthropic_api_key=api_key, **kwargs)
        except ImportError:
            raise ValueError(
                "langchain-anthropic not installed. Install with: uv add langchain-anthropic"
            )

    @staticmethod
    def _create_openai(model: str, kwargs: dict[str, Any]) -> Any:
        """Create OpenAI LLM"""
        try:
            from langchain_openai import ChatOpenAI

            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment")

            return ChatOpenAI(model=model, openai_api_key=api_key, **kwargs)
        except ImportError:
            raise ValueError(
                "langchain-openai not installed. Install with: uv add langchain-openai"
            )

    @staticmethod
    def _create_bedrock(model: str, kwargs: dict[str, Any]) -> Any:
        """Create AWS Bedrock LLM"""
        try:
            from langchain_aws import ChatBedrockConverse

            # AWS credentials from environment or ~/.aws/credentials
            return ChatBedrockConverse(model_id=model, **kwargs)
        except ImportError:
            raise ValueError("langchain-aws not installed. Install with: uv add langchain-aws")

    @staticmethod
    def _create_ollama(model: str, kwargs: dict[str, Any]) -> Any:
        """Create Ollama LLM (via OpenAI SDK)"""
        try:
            from openai import OpenAI

            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")

            # Return OpenAI-compatible client
            # Note: For LangChain, wrap in ChatOpenAI pointing to Ollama
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=model,
                base_url=base_url,
                api_key="ollama",  # Required but unused
                **kwargs,
            )
        except ImportError:
            raise ValueError(
                "langchain-openai not installed. Install with: uv add langchain-openai"
            )


def create_llm(provider: str, model: str, **kwargs) -> Any:
    """
    Convenience function to create an LLM client

    Args:
        provider: Provider ID (gemini, anthropic, openai, bedrock, ollama)
        model: Model ID
        **kwargs: Provider-specific parameters

    Returns:
        LLM client instance
    """
    return LLMFactory.create_llm(provider, model, **kwargs)
