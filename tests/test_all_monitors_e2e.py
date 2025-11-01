#!/usr/bin/env python3
"""
All Monitors End-to-End Test
Tests deployment and functionality of all 4 monitor types:
- Echo (simple passthrough)
- Ollama (local LLM)
- Claude Agent SDK (Claude subscription)
- LangGraph (multi-provider)
"""

import asyncio
import sys
import os
import time
from pathlib import Path
import httpx

# Add src to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Dashboard API base URL
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://localhost:8000")

# Test configuration
TEST_AGENT = "lunar_craft_128"
TEST_CONFIG_PATH = str(PROJECT_ROOT / "configs" / "agents" / "lunar_craft_128.json")


class MonitorTester:
    """Helper class for testing monitors"""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url, timeout=30.0)
        self.started_monitors = []

    async def cleanup(self):
        """Clean up all started monitors"""
        print("\n Cleaning up test monitors...")
        for monitor_id in self.started_monitors:
            try:
                await self.client.post("/api/monitors/kill", json={"monitor_id": monitor_id})
                await self.client.delete(f"/api/monitors/{monitor_id}")
                print(f"    Cleaned up {monitor_id}")
            except Exception as e:
                print(f"   ️  Failed to clean up {monitor_id}: {e}")

        await self.client.aclose()

    async def start_monitor(self, monitor_type: str, provider: str = None, model: str = None):
        """Start a monitor and return its ID"""
        config = {
            "agent_name": TEST_AGENT,
            "config_path": TEST_CONFIG_PATH,
            "monitor_type": monitor_type,
            "provider": provider,
            "model": model,
            "system_prompt": None,
            "system_prompt_name": None,
            "history_limit": 25
        }

        response = await self.client.post("/api/monitors/start", json={"config": config})
        assert response.status_code == 200, f"Failed to start {monitor_type}: {response.text}"

        data = response.json()
        assert data["success"] is True

        monitor_id = data["monitor_id"]
        self.started_monitors.append(monitor_id)

        print(f"    Started {monitor_type} (ID: {monitor_id})")
        return monitor_id

    async def wait_for_monitor(self, monitor_id: str, timeout: int = 10):
        """Wait for monitor to be running"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            response = await self.client.get("/api/monitors")
            data = response.json()

            monitor = next((m for m in data["monitors"] if m["id"] == monitor_id), None)
            if monitor and monitor["status"] == "running":
                return True

            await asyncio.sleep(0.5)

        return False

    async def send_test_message(self, to_agent: str, message: str):
        """Send a test message to an agent"""
        response = await self.client.post("/api/messages/send", json={
            "from_agent": "test_sender",
            "to_agent": to_agent,
            "message": message
        })
        assert response.status_code == 200
        return response.json()

    async def stop_monitor(self, monitor_id: str):
        """Stop a running monitor"""
        response = await self.client.post("/api/monitors/stop", json={"monitor_id": monitor_id})
        assert response.status_code == 200
        print(f"    Stopped {monitor_id}")


async def test_echo_monitor(tester: MonitorTester):
    """Test Echo monitor (no provider, no model)"""
    print("\n" + "="*60)
    print(" Testing Echo Monitor")
    print("="*60)
    print("Requirements: No provider, no model (simple passthrough)")

    try:
        # Start echo monitor
        monitor_id = await tester.start_monitor(
            monitor_type="echo",
            provider=None,  # Echo doesn't need provider
            model=None      # Echo doesn't need model
        )

        # Wait for it to be running
        is_running = await tester.wait_for_monitor(monitor_id, timeout=10)
        assert is_running, "Echo monitor failed to start"

        print("    Echo monitor is running")

        # Test sending a message
        result = await tester.send_test_message(TEST_AGENT, "Echo test message")
        print(f"    Message sent successfully")

        # Stop the monitor
        await tester.stop_monitor(monitor_id)

        print("\n Echo monitor test PASSED")
        return True

    except Exception as e:
        print(f"\n Echo monitor test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_ollama_monitor(tester: MonitorTester):
    """Test Ollama monitor (no provider, requires model)"""
    print("\n" + "="*60)
    print(" Testing Ollama Monitor")
    print("="*60)
    print("Requirements: No provider (implicit), requires model")

    try:
        # Get available Ollama models
        response = await tester.client.get("/api/providers/ollama/models")
        models = response.json()["models"]

        if not models:
            print("   ️  No Ollama models available, skipping test")
            return None  # Skip test

        # Use first available model
        test_model = models[0]["id"]
        print(f"   Using model: {test_model}")

        # Start Ollama monitor
        monitor_id = await tester.start_monitor(
            monitor_type="ollama",
            provider=None,      # Ollama doesn't need provider (implicit)
            model=test_model    # Ollama requires model
        )

        # Wait for it to be running
        is_running = await tester.wait_for_monitor(monitor_id, timeout=15)
        assert is_running, "Ollama monitor failed to start"

        print("    Ollama monitor is running")

        # Stop the monitor (don't send test message to save time)
        await tester.stop_monitor(monitor_id)

        print("\n Ollama monitor test PASSED")
        return True

    except Exception as e:
        print(f"\n Ollama monitor test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_claude_agent_sdk_monitor(tester: MonitorTester):
    """Test Claude Agent SDK monitor (no provider, requires Claude model)"""
    print("\n" + "="*60)
    print(" Testing Claude Agent SDK Monitor")
    print("="*60)
    print("Requirements: No provider (uses Anthropic SDK), requires Claude model")

    try:
        # Verify Claude models are available
        response = await tester.client.get("/api/providers/anthropic/models")
        models = response.json()["models"]

        # Find Sonnet 4.5 (should be default)
        sonnet = next((m for m in models if m["id"] == "claude-sonnet-4-5"), None)
        assert sonnet is not None, "Claude Sonnet 4.5 not found"
        assert sonnet.get("default") is True, "Sonnet 4.5 should be default"

        print(f"   Using model: claude-sonnet-4-5 (default)")

        # Start Claude Agent SDK monitor
        monitor_id = await tester.start_monitor(
            monitor_type="claude_agent_sdk",
            provider=None,              # Claude SDK doesn't need provider
            model="claude-sonnet-4-5"   # Claude SDK requires Claude model
        )

        # Wait for it to be running
        is_running = await tester.wait_for_monitor(monitor_id, timeout=20)
        assert is_running, "Claude Agent SDK monitor failed to start"

        print("    Claude Agent SDK monitor is running")

        # Stop the monitor
        await tester.stop_monitor(monitor_id)

        print("\n Claude Agent SDK monitor test PASSED")
        return True

    except Exception as e:
        print(f"\n Claude Agent SDK monitor test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_langgraph_monitor(tester: MonitorTester):
    """Test LangGraph monitor (requires provider and model)"""
    print("\n" + "="*60)
    print(" Testing LangGraph Monitor")
    print("="*60)
    print("Requirements: Requires provider + model (multi-provider support)")

    try:
        # Get providers list
        response = await tester.client.get("/api/providers")
        providers = response.json()["providers"]

        # Find a configured provider (prefer Gemini for speed)
        configured_provider = None
        for provider in providers:
            if provider["configured"] and provider["id"] == "gemini":
                configured_provider = provider
                break

        if not configured_provider:
            # Fall back to any configured provider
            configured_provider = next((p for p in providers if p["configured"]), None)

        if not configured_provider:
            print("   ️  No providers configured, skipping test")
            return None

        provider_id = configured_provider["id"]
        print(f"   Using provider: {provider_id}")

        # Get models for this provider
        response = await tester.client.get(f"/api/providers/{provider_id}/models")
        models = response.json()["models"]

        # Use default or first model
        test_model = next((m["id"] for m in models if m.get("default")), models[0]["id"])
        print(f"   Using model: {test_model}")

        # Start LangGraph monitor
        monitor_id = await tester.start_monitor(
            monitor_type="langgraph",
            provider=provider_id,  # LangGraph requires provider
            model=test_model       # LangGraph requires model
        )

        # Wait for it to be running
        is_running = await tester.wait_for_monitor(monitor_id, timeout=20)
        assert is_running, "LangGraph monitor failed to start"

        print("    LangGraph monitor is running")

        # Stop the monitor
        await tester.stop_monitor(monitor_id)

        print("\n LangGraph monitor test PASSED")
        return True

    except Exception as e:
        print(f"\n LangGraph monitor test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all monitor E2E tests"""
    print("\n" + "="*60)
    print(" All Monitors E2E Test Suite")
    print("="*60)
    print(f"Testing against: {DASHBOARD_URL}")
    print("Make sure the dashboard is running: uv run dashboard")

    # Check if dashboard is running
    tester = MonitorTester(DASHBOARD_URL)
    try:
        response = await tester.client.get("/api/health")
        if response.status_code != 200:
            print("\n Dashboard is not responding")
            return 1
    except Exception as e:
        print(f"\n Cannot connect to dashboard: {e}")
        return 1

    print(" Dashboard is running\n")

    # Run all tests
    results = {}

    try:
        results["Echo"] = await test_echo_monitor(tester)
        results["Ollama"] = await test_ollama_monitor(tester)
        results["Claude Agent SDK"] = await test_claude_agent_sdk_monitor(tester)
        results["LangGraph"] = await test_langgraph_monitor(tester)

    finally:
        # Always cleanup
        await tester.cleanup()

    # Summary
    print("\n" + "="*60)
    print(" Test Results Summary")
    print("="*60)

    for test_name, result in results.items():
        if result is True:
            status = " PASS"
        elif result is False:
            status = " FAIL"
        else:
            status = "⏭️  SKIP"
        print(f"{status}: {test_name}")

    # Check if all tests that ran passed
    ran_tests = [r for r in results.values() if r is not None]
    all_passed = all(ran_tests) if ran_tests else False

    if all_passed:
        print("\n All monitor tests passed!")
        return 0
    else:
        print("\n️  Some tests failed or were skipped")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
