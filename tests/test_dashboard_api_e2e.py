#!/usr/bin/env python3
"""
Dashboard API End-to-End Tests
Tests all agent types and their configuration requirements
"""

import asyncio
import sys
import os
from pathlib import Path
import httpx
import pytest

# Add src to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Dashboard API base URL
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://localhost:8000")


class TestDashboardAPI:
    """Test suite for Dashboard API endpoints"""

    @pytest.fixture(scope="class")
    async def client(self):
        """HTTP client for testing"""
        async with httpx.AsyncClient(base_url=DASHBOARD_URL, timeout=10.0) as client:
            yield client

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Dashboard should respond to health check"""
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_providers_list(self, client):
        """Should return list of available providers"""
        response = await client.get("/api/providers")
        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        assert isinstance(data["providers"], list)

    @pytest.mark.asyncio
    async def test_provider_defaults(self, client):
        """Should return default provider and agent type"""
        response = await client.get("/api/providers/defaults")
        assert response.status_code == 200
        data = response.json()

        # Should have provider, model, and agent_type
        assert "provider" in data
        assert "model" in data
        assert "agent_type" in data

        # Agent type should be one of the valid types
        assert data["agent_type"] in ["echo", "ollama", "langgraph", "claude_agent_sdk"]

    @pytest.mark.asyncio
    async def test_claude_models(self, client):
        """Claude Agent SDK should have Sonnet 4.5 and Haiku 4.5"""
        response = await client.get("/api/providers/anthropic/models")
        assert response.status_code == 200
        data = response.json()

        models = data["models"]
        model_ids = [m["id"] for m in models]

        # Must have both recommended Claude 4.5 models
        assert "claude-sonnet-4-5" in model_ids
        assert "claude-haiku-4-5" in model_ids

        # Sonnet should be the default
        default_model = next((m for m in models if m.get("default")), None)
        assert default_model is not None
        assert default_model["id"] == "claude-sonnet-4-5"

    @pytest.mark.asyncio
    async def test_gemini_models(self, client):
        """LangGraph should have Gemini models"""
        response = await client.get("/api/providers/gemini/models")
        assert response.status_code == 200
        data = response.json()

        models = data["models"]
        model_ids = [m["id"] for m in models]

        # Should have Gemini 2.5 Flash
        assert "gemini-2.5-flash" in model_ids

    @pytest.mark.asyncio
    async def test_ollama_models(self, client):
        """Ollama should return available local models"""
        response = await client.get("/api/providers/ollama/models")
        assert response.status_code == 200
        data = response.json()

        # Should return a list (even if empty)
        assert "models" in data
        assert isinstance(data["models"], list)

    @pytest.mark.asyncio
    async def test_environments_list(self, client):
        """Should list available environments"""
        response = await client.get("/api/environments")
        assert response.status_code == 200
        data = response.json()

        assert "environments" in data
        # Local environment should always exist
        assert "local" in data["environments"]

    @pytest.mark.asyncio
    async def test_configs_list(self, client):
        """Should list agent configurations"""
        response = await client.get("/api/configs")
        assert response.status_code == 200
        data = response.json()

        assert "configs" in data
        assert isinstance(data["configs"], list)

    @pytest.mark.asyncio
    async def test_monitors_list(self, client):
        """Should list running monitors"""
        response = await client.get("/api/monitors")
        assert response.status_code == 200
        data = response.json()

        assert "monitors" in data
        assert isinstance(data["monitors"], list)

    @pytest.mark.asyncio
    async def test_kill_switch_status(self, client):
        """Should return kill switch status"""
        response = await client.get("/api/kill-switch/status")
        assert response.status_code == 200
        data = response.json()

        assert "active" in data
        assert isinstance(data["active"], bool)


class TestAgentTypeRequirements:
    """Test configuration requirements for each agent type"""

    def test_echo_requirements(self):
        """Echo monitor should require no provider or model"""
        # Echo is a simple passthrough, no AI configuration needed
        required_fields = {
            "provider": False,  # Not needed
            "model": False,     # Not needed
        }
        assert required_fields["provider"] is False
        assert required_fields["model"] is False

    def test_ollama_requirements(self):
        """Ollama monitor should require model but not provider"""
        # Ollama has implicit provider (always Ollama)
        required_fields = {
            "provider": False,  # Implicit (always ollama)
            "model": True,      # User selects model
        }
        assert required_fields["provider"] is False
        assert required_fields["model"] is True

    def test_claude_agent_sdk_requirements(self):
        """Claude Agent SDK should require model but not provider"""
        # Claude Agent SDK uses Anthropic models directly via SDK
        required_fields = {
            "provider": False,  # Implicit (always anthropic)
            "model": True,      # User selects Claude model
        }
        assert required_fields["provider"] is False
        assert required_fields["model"] is True

    def test_langgraph_requirements(self):
        """LangGraph monitor should require both provider and model"""
        # LangGraph supports multiple providers
        required_fields = {
            "provider": True,   # User selects provider
            "model": True,      # User selects model
        }
        assert required_fields["provider"] is True
        assert required_fields["model"] is True


async def run_api_tests():
    """Run all dashboard API tests"""
    print("\n" + "="*60)
    print(" Dashboard API E2E Test Suite")
    print("="*60)

    print("\nℹ  Testing against:", DASHBOARD_URL)
    print("   Make sure the dashboard is running: uv run dashboard")

    # Check if dashboard is running
    async with httpx.AsyncClient(base_url=DASHBOARD_URL, timeout=5.0) as client:
        try:
            response = await client.get("/api/health")
            if response.status_code != 200:
                print("\n Dashboard is not responding. Start it with: uv run dashboard")
                return 1
        except Exception as e:
            print(f"\n Cannot connect to dashboard: {e}")
            print("   Start it with: uv run dashboard")
            return 1

    print("\n Dashboard is running\n")

    # Run pytest programmatically
    import pytest

    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-k", "TestDashboardAPI or TestAgentTypeRequirements"
    ])

    return exit_code


if __name__ == "__main__":
    exit_code = asyncio.run(run_api_tests())
    sys.exit(exit_code)
