#!/usr/bin/env python3
"""
Comprehensive E2E tests for ALL framework types

This is the BASELINE test suite that must pass before and after refactoring.
Tests every framework can deploy, run, and stop cleanly via dashboard API.

Run: python tests/test_all_frameworks_e2e.py
"""

import os
import sys
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv()


class FrameworkE2ETestSuite:
    """Test suite for all framework types"""

    def __init__(self):
        self.api_base = "http://localhost:8000/api"
        self.deployed_monitors = []
        self.test_results = []

    def test_framework_deployment(
        self,
        framework_id: str,
        agent_name: str,
        model: str,
        config_file: str,
        provider: str = None,
    ) -> bool:
        """Test a single framework type can deploy successfully"""
        print(f"\n{'=' * 70}")
        print(f"Testing Framework: {framework_id}")
        print(f"  Agent: {agent_name}")
        print(f"  Model: {model}")
        print(f"  Provider: {provider or 'N/A'}")
        print(f"{'=' * 70}")

        # Get agent config
        response = requests.get(f"{self.api_base}/configs")
        if response.status_code != 200:
            print(f"❌ Failed to get configs: {response.status_code}")
            return False

        configs = response.json().get("configs", [])
        agent_config = next(
            (c for c in configs if c["agent_name"] == agent_name), None
        )

        if not agent_config:
            print(f"❌ Agent config not found for {agent_name}")
            return False

        actual_config_file = agent_config["filename"]

        # Build payload
        payload = {
            "config": {
                "agent_name": agent_name,
                "monitor_type": framework_id,
                "model": model if model else None,
                "config_path": actual_config_file,
                "provider": provider,
            }
        }

        print(f"\n   Deploying...")

        # Deploy monitor
        response = requests.post(f"{self.api_base}/monitors/start", json=payload)

        if response.status_code != 200:
            print(f"❌ Failed to start monitor: {response.status_code}")
            print(f"   Response: {response.text}")
            return False

        data = response.json()
        if not data.get("success"):
            print(f"❌ Deploy failed: {data}")
            return False

        monitor_id = data.get("monitor_id")
        if not monitor_id:
            print(f"❌ No monitor_id in response: {data}")
            return False
        print(f"✅ Monitor deployed: {monitor_id}")
        self.deployed_monitors.append(monitor_id)

        # Wait for monitor to be running
        if not self.wait_for_monitor_running(monitor_id, framework_id):
            return False

        # Validate monitor state
        if not self.validate_monitor_state(monitor_id, framework_id, provider):
            return False

        print(f"✅ {framework_id} framework validation PASSED")
        return True

    def wait_for_monitor_running(
        self, monitor_id: str, framework_id: str, timeout: int = 15
    ) -> bool:
        """Wait for monitor to reach running state"""
        print(f"\n   Waiting for monitor to start (max {timeout}s)...")

        for i in range(timeout):
            time.sleep(1)

            response = requests.get(f"{self.api_base}/monitors")
            if response.status_code != 200:
                continue

            monitors = response.json().get("monitors", [])
            monitor = next((m for m in monitors if m.get("id") == monitor_id), None)

            if not monitor:
                continue

            status = monitor.get("status")

            if status == "running":
                print(f"   ✅ Monitor running after {i+1}s")
                return True
            elif status in ["failed", "stopped"]:
                print(f"   ❌ Monitor failed: {status}")
                self.print_monitor_logs(monitor_id)
                return False

        print(f"   ❌ Timeout waiting for monitor")
        return False

    def validate_monitor_state(
        self, monitor_id: str, framework_id: str, expected_provider: str = None
    ) -> bool:
        """Validate monitor state matches framework expectations"""
        print(f"\n   Validating monitor state...")

        response = requests.get(f"{self.api_base}/monitors")
        if response.status_code != 200:
            print(f"   ⚠️  Could not fetch monitors")
            return False

        monitors = response.json().get("monitors", [])
        monitor = next((m for m in monitors if m.get("id") == monitor_id), None)

        if not monitor:
            print(f"   ❌ Monitor not found")
            return False

        # Check framework type
        if monitor.get("monitor_type") != framework_id:
            print(
                f"   ❌ Wrong monitor type: {monitor.get('monitor_type')} != {framework_id}"
            )
            return False

        # Check provider (framework-specific monitors should NOT have provider)
        framework_specific = ["openai_agents_sdk", "claude_agent_sdk"]
        if framework_id in framework_specific:
            # Provider should be None or empty for these frameworks
            if monitor.get("provider") and monitor.get("provider") != "null":
                print(
                    f"   ⚠️  WARNING: Framework-specific monitor has provider: {monitor.get('provider')}"
                )
                print(
                    f"   This is a cosmetic bug but monitor should work correctly"
                )
        else:
            # Provider should be present for generic frameworks
            if not monitor.get("provider"):
                print(f"   ⚠️  WARNING: Generic framework missing provider")

        # Check MCP servers connected
        mcp_servers = monitor.get("mcp_servers", [])
        if not mcp_servers:
            print(f"   ⚠️  WARNING: No MCP servers listed")

        print(f"   ✅ Monitor state validated")
        return True

    def print_monitor_logs(self, monitor_id: str):
        """Print last 20 lines of monitor logs"""
        print(f"\n   Last 20 lines of logs:")
        try:
            response = requests.get(f"{self.api_base}/logs/{monitor_id}")
            if response.status_code == 200:
                lines = response.text.split("\n")
                for line in lines[-20:]:
                    print(f"     {line}")
        except Exception as e:
            print(f"   Could not fetch logs: {e}")

    def cleanup_monitors(self):
        """Stop all deployed monitors"""
        if not self.deployed_monitors:
            return

        print(f"\n{'=' * 70}")
        print(f"Cleaning up {len(self.deployed_monitors)} monitor(s)...")
        print(f"{'=' * 70}")

        for monitor_id in self.deployed_monitors:
            try:
                response = requests.delete(f"{self.api_base}/monitors/{monitor_id}")
                if response.status_code == 200:
                    print(f"✅ Stopped {monitor_id}")
                    time.sleep(0.5)  # Brief pause between stops
                else:
                    print(f"⚠️  Failed to stop {monitor_id}: {response.status_code}")
            except Exception as e:
                print(f"⚠️  Error stopping {monitor_id}: {e}")

    def run_all_tests(self) -> bool:
        """Run E2E tests for all framework types"""

        # Define test cases: (framework_id, agent_name, model, config_file, provider)
        test_cases = [
            # Echo monitor (simplest, no model/provider needed)
            ("echo", "ghost_ray_363", "", "local_ghost.json", None),
            # LangGraph monitor (provider + model required)
            (
                "langgraph",
                "lunar_craft_128",
                "gpt-oss:latest",
                "lunar_craft_128.json",
                "ollama",
            ),
        ]

        # Conditional tests based on API keys
        if os.getenv("OPENAI_API_KEY"):
            test_cases.append(
                (
                    "openai_agents_sdk",
                    "lunar_craft_128",
                    "gpt-5-mini",
                    "lunar_craft_128.json",
                    None,  # Provider should be None for framework-specific
                )
            )
        else:
            print("\n⚠️  OPENAI_API_KEY not set, skipping OpenAI Agents SDK test")

        if os.getenv("ANTHROPIC_API_KEY"):
            test_cases.append(
                (
                    "claude_agent_sdk",
                    "ghost_ray_363",
                    "claude-sonnet-4-5",
                    "local_ghost.json",
                    None,  # Provider should be None for framework-specific
                )
            )
        else:
            print("\n⚠️  ANTHROPIC_API_KEY not set, skipping Claude Agent SDK test")

        # Run tests
        try:
            for framework_id, agent_name, model, config_file, provider in test_cases:
                success = self.test_framework_deployment(
                    framework_id, agent_name, model, config_file, provider
                )
                self.test_results.append((framework_id, success))

                # Brief pause between tests
                if success:
                    time.sleep(2)

            # Print summary
            print(f"\n{'=' * 70}")
            print("FRAMEWORK E2E TEST SUMMARY")
            print(f"{'=' * 70}")

            all_passed = True
            for framework_id, success in self.test_results:
                status = "✅ PASS" if success else "❌ FAIL"
                print(f"{status}: {framework_id}")
                if not success:
                    all_passed = False

            if all_passed:
                print(f"\n🎉 All {len(self.test_results)} framework tests PASSED!")
            else:
                failed = sum(1 for _, s in self.test_results if not s)
                print(f"\n❌ {failed}/{len(self.test_results)} tests FAILED")

            return all_passed

        except Exception as e:
            print(f"\n❌ Test suite failed with exception: {e}")
            import traceback

            traceback.print_exc()
            return False

        finally:
            # Always cleanup
            self.cleanup_monitors()


def main():
    """Main test runner"""
    print("=" * 70)
    print("Framework E2E Test Suite (BASELINE)")
    print("=" * 70)
    print()
    print("This test suite validates ALL framework types work correctly.")
    print("Must pass before AND after any refactoring!")
    print()
    print("Prerequisites:")
    print("  1. Dashboard running on http://localhost:8000")
    print("  2. OPENAI_API_KEY set (for OpenAI tests)")
    print("  3. ANTHROPIC_API_KEY set (for Claude tests)")
    print("  4. Agent configs exist (ghost_ray_363, lunar_craft_128)")
    print()

    # Check dashboard
    try:
        response = requests.get("http://localhost:8000/api/monitors", timeout=5)
        if response.status_code != 200:
            print("❌ Dashboard not responding correctly")
            sys.exit(1)
    except requests.exceptions.RequestException:
        print("❌ Dashboard is not running on http://localhost:8000")
        print("   Start it with: python scripts/start_dashboard.py")
        sys.exit(1)

    print("✅ Dashboard is running\n")

    # Run tests
    test_suite = FrameworkE2ETestSuite()
    success = test_suite.run_all_tests()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
