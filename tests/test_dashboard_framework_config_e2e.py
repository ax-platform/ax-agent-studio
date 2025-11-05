#!/usr/bin/env python3
"""
End-to-End tests for Dashboard Framework Configuration

Tests that the framework registry system correctly shows/hides UI elements
and loads the correct models for each monitor type.

Run with: PYTHONPATH=src python tests/test_dashboard_framework_config_e2e.py
"""

import requests


class DashboardFrameworkE2ETest:
    """E2E tests for framework configuration system"""

    def __init__(self, dashboard_url: str = "http://127.0.0.1:8000"):
        self.dashboard_url = dashboard_url
        self.api_base = dashboard_url + "/api"

    def test_framework_registry_api(self) -> bool:
        """Test that /api/frameworks endpoint works and returns valid data"""
        print("\n" + "=" * 70)
        print("TEST: Framework Registry API")
        print("=" * 70)

        response = requests.get(f"{self.api_base}/frameworks")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.json()
        assert "frameworks" in data, "Response missing 'frameworks' key"
        assert "ui" in data, "Response missing 'ui' key"
        assert "provider_defaults" in data, "Response missing 'provider_defaults' key"

        # Check all expected frameworks are present
        expected_frameworks = [
            "echo",
            "ollama",
            "claude_agent_sdk",
            "openai_agents_sdk",
            "langgraph",
        ]
        for fw in expected_frameworks:
            assert fw in data["frameworks"], f"Missing framework: {fw}"
            print(f"✅ Framework '{fw}' found in registry")

        print("✅ Framework Registry API working correctly\n")
        return True

    def test_framework_definitions(self) -> bool:
        """Test that each framework has correct configuration"""
        print("=" * 70)
        print("TEST: Framework Definitions")
        print("=" * 70)

        response = requests.get(f"{self.api_base}/frameworks")
        frameworks = response.json()["frameworks"]

        # Test Echo
        echo = frameworks["echo"]
        assert echo["requires_provider"] == False, "Echo should not require provider"
        assert echo["requires_model"] == False, "Echo should not require model"
        assert echo["provider"] is None, "Echo should have no provider"
        print("✅ Echo configuration correct")

        # Test Ollama
        ollama = frameworks["ollama"]
        assert ollama["requires_provider"] == False, "Ollama should not require provider selection"
        assert ollama["requires_model"] == True, "Ollama should require model"
        assert ollama["provider"] == "ollama", "Ollama should have implicit ollama provider"
        print("✅ Ollama configuration correct")

        # Test Claude Agent SDK
        claude_sdk = frameworks["claude_agent_sdk"]
        assert (
            claude_sdk["requires_provider"] == False
        ), "Claude SDK should not require provider selection"
        assert claude_sdk["requires_model"] == True, "Claude SDK should require model"
        assert (
            claude_sdk["provider"] == "anthropic"
        ), "Claude SDK should have implicit anthropic provider"
        assert claude_sdk.get("recommended") == True, "Claude SDK should be marked as recommended"
        assert (
            claude_sdk["default_model"] == "claude-sonnet-4-5"
        ), f"Claude SDK default should be claude-sonnet-4-5, got {claude_sdk.get('default_model')}"
        print("✅ Claude Agent SDK configuration correct (default: claude-sonnet-4-5)")

        # Test OpenAI Agents SDK
        openai_sdk = frameworks["openai_agents_sdk"]
        assert (
            openai_sdk["requires_provider"] == False
        ), "OpenAI SDK should not require provider selection"
        assert openai_sdk["requires_model"] == True, "OpenAI SDK should require model"
        assert openai_sdk["provider"] == "openai", "OpenAI SDK should have implicit openai provider"
        assert (
            openai_sdk["default_model"] == "gpt-5-mini"
        ), f"OpenAI SDK default should be gpt-5-mini, got {openai_sdk.get('default_model')}"
        print("✅ OpenAI Agents SDK configuration correct (default: gpt-5-mini)")

        # Test LangGraph
        langgraph = frameworks["langgraph"]
        assert langgraph["requires_provider"] == True, "LangGraph should require provider selection"
        assert langgraph["requires_model"] == True, "LangGraph should require model"
        assert langgraph["provider"] is None, "LangGraph should have no fixed provider"
        print("✅ LangGraph configuration correct")

        print("✅ All framework definitions correct\n")
        return True

    def test_provider_models(self) -> bool:
        """Test that provider defaults include correct models"""
        print("=" * 70)
        print("TEST: Provider Model Lists")
        print("=" * 70)

        response = requests.get(f"{self.api_base}/frameworks")
        provider_defaults = response.json()["provider_defaults"]

        # Test Anthropic models
        anthropic = provider_defaults["anthropic"]
        assert "default_model" in anthropic, "Anthropic missing default_model"
        assert (
            anthropic["default_model"] == "claude-sonnet-4-5"
        ), f"Anthropic default should be claude-sonnet-4-5, got {anthropic['default_model']}"
        assert "available_models" in anthropic, "Anthropic missing available_models"
        assert "claude-sonnet-4-5" in anthropic["available_models"], "Missing claude-sonnet-4-5"
        assert "claude-haiku-4-5" in anthropic["available_models"], "Missing claude-haiku-4-5"
        print(
            f"✅ Anthropic has {len(anthropic['available_models'])} Claude models (default: {anthropic['default_model']})"
        )

        # Test OpenAI models
        openai = provider_defaults["openai"]
        assert "default_model" in openai, "OpenAI missing default_model"
        assert (
            openai["default_model"] == "gpt-5-mini"
        ), f"OpenAI default should be gpt-5-mini, got {openai['default_model']}"
        assert "available_models" in openai, "OpenAI missing available_models"
        assert "gpt-5" in openai["available_models"], "Missing gpt-5"
        assert "gpt-5-mini" in openai["available_models"], "Missing gpt-5-mini"
        print(
            f"✅ OpenAI has {len(openai['available_models'])} GPT models (default: {openai['default_model']})"
        )

        # Test Google models
        google = provider_defaults["google"]
        assert (
            "gemini-2.5-flash" in google["available_models"]
            or "gemini-2.5-pro" in google["available_models"]
        ), "Missing Gemini models"
        print(f"✅ Google has {len(google['available_models'])} Gemini models")

        # Test Ollama models
        ollama = provider_defaults["ollama"]
        assert (
            "llama3.2" in ollama["available_models"] or "qwen2.5" in ollama["available_models"]
        ), "Missing Ollama models"
        print(f"✅ Ollama has {len(ollama['available_models'])} local models")

        print("✅ All provider model lists correct\n")
        return True

    def test_settings_endpoint(self) -> bool:
        """Test that /api/settings returns default values"""
        print("=" * 70)
        print("TEST: Settings Endpoint")
        print("=" * 70)

        response = requests.get(f"{self.api_base}/settings")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.json()
        assert "default_agent_type" in data, "Missing default_agent_type"
        assert "default_provider" in data, "Missing default_provider"
        assert "default_model" in data, "Missing default_model"
        assert "default_environment" in data, "Missing default_environment"

        print(f"✅ Default agent type: {data['default_agent_type']}")
        print(f"✅ Default provider: {data['default_provider']}")
        print(f"✅ Default model: {data['default_model']}")
        print(f"✅ Default environment: {data['default_environment']}")

        print("✅ Settings endpoint working correctly\n")
        return True

    def test_framework_specific_endpoint(self) -> bool:
        """Test that /api/frameworks/{type} returns specific framework data"""
        print("=" * 70)
        print("TEST: Framework-Specific Endpoints")
        print("=" * 70)

        # Test Claude Agent SDK endpoint
        response = requests.get(f"{self.api_base}/frameworks/claude_agent_sdk")
        assert response.status_code == 200, "Claude Agent SDK endpoint failed"
        claude_data = response.json()
        assert claude_data["provider"] == "anthropic", "Claude SDK should use anthropic"
        print("✅ /api/frameworks/claude_agent_sdk works")

        # Test OpenAI Agents SDK endpoint
        response = requests.get(f"{self.api_base}/frameworks/openai_agents_sdk")
        assert response.status_code == 200, "OpenAI Agents SDK endpoint failed"
        openai_data = response.json()
        assert openai_data["provider"] == "openai", "OpenAI SDK should use openai"
        print("✅ /api/frameworks/openai_agents_sdk works")

        # Test 404 for invalid framework
        response = requests.get(f"{self.api_base}/frameworks/invalid_framework")
        assert response.status_code == 404, "Should return 404 for invalid framework"
        print("✅ Returns 404 for invalid framework")

        print("✅ Framework-specific endpoints working correctly\n")
        return True

    def run_all_tests(self) -> bool:
        """Run all E2E tests"""
        print("\n" + "=" * 70)
        print("DASHBOARD FRAMEWORK CONFIGURATION E2E TESTS")
        print("=" * 70)
        print(f"Dashboard URL: {self.dashboard_url}")
        print(f"API Base: {self.api_base}")

        try:
            # Check if dashboard is running
            response = requests.get(f"{self.api_base}/health", timeout=5)
            if response.status_code != 200:
                print("❌ Dashboard not healthy, cannot run tests")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Dashboard not reachable: {e}")
            print(f"   Make sure dashboard is running on {self.dashboard_url}")
            return False

        tests = [
            self.test_framework_registry_api,
            self.test_framework_definitions,
            self.test_provider_models,
            self.test_settings_endpoint,
            self.test_framework_specific_endpoint,
        ]

        passed = 0
        failed = 0

        for test in tests:
            try:
                if test():
                    passed += 1
                else:
                    failed += 1
                    print(f"❌ Test failed: {test.__name__}")
            except AssertionError as e:
                failed += 1
                print(f"❌ Test failed: {test.__name__}")
                print(f"   Assertion: {e}")
            except Exception as e:
                failed += 1
                print(f"❌ Test error: {test.__name__}")
                print(f"   Error: {e}")

        print("=" * 70)
        print(f"RESULTS: {passed} passed, {failed} failed")
        print("=" * 70)

        return failed == 0


if __name__ == "__main__":
    import sys

    tester = DashboardFrameworkE2ETest()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
