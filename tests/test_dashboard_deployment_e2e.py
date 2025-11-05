#!/usr/bin/env python3
"""
E2E test for dashboard monitor deployment

Tests that ALL monitor types can be deployed successfully via the dashboard API.
This prevents regressions and ensures the dashboard "Start Monitor" button works.

Run: python tests/test_dashboard_deployment_e2e.py
"""

import os
import sys
import time

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class DashboardDeploymentTest:
    """Test dashboard monitor deployment for all monitor types"""

    def __init__(self):
        self.api_base = "http://localhost:8000/api"
        self.deployed_monitors = []

    def test_monitor_deployment(
        self, agent_name: str, monitor_type: str, model: str, config_file: str
    ) -> bool:
        """Test deploying a single monitor via dashboard API"""
        print(f"\n{'=' * 70}")
        print(f"Testing {monitor_type} deployment for {agent_name}")
        print(f"{'=' * 70}")

        # Get agent config to find proper config file name
        response = requests.get(f"{self.api_base}/configs")
        if response.status_code != 200:
            print(f"❌ Failed to get configs: {response.status_code}")
            return False

        configs = response.json().get("configs", [])
        agent_config = next((c for c in configs if c["agent_name"] == agent_name), None)

        if not agent_config:
            print(f"❌ Agent config not found for {agent_name}")
            return False

        actual_config_file = agent_config["filename"]
        print(f"   Using config file: {actual_config_file}")

        # Start monitor - API expects nested MonitorConfig object
        payload = {
            "config": {
                "agent_name": agent_name,
                "monitor_type": monitor_type,
                "model": model if model else None,
                "config_path": actual_config_file,
            }
        }

        print(f"   Payload: {payload}")

        response = requests.post(f"{self.api_base}/monitors/start", json=payload)

        if response.status_code != 200:
            print(f"❌ Failed to start monitor: {response.status_code}")
            print(f"   Response: {response.text}")
            return False

        data = response.json()
        monitor_id = data.get("id")
        print(f"✅ Monitor started: {monitor_id}")
        self.deployed_monitors.append(monitor_id)

        # Wait for monitor to be running
        if not self.wait_for_monitor_running(monitor_id):
            return False

        # Check logs for errors
        if not self.check_monitor_logs(monitor_id, monitor_type):
            return False

        print(f"✅ {monitor_type} deployment successful!")
        return True

    def wait_for_monitor_running(self, monitor_id: str, timeout: int = 30) -> bool:
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
                print(f"   [{i+1}s] Monitor not found")
                continue

            status = monitor.get("status")

            if status == "running":
                print(f"   ✅ Monitor running after {i+1}s")
                return True
            elif status in ["failed", "stopped"]:
                print(f"   ❌ Monitor failed: {status}")
                return False

        print("   ❌ Timeout waiting for monitor")
        return False

    def check_monitor_logs(self, monitor_id: str, monitor_type: str) -> bool:
        """Check monitor logs for critical errors"""
        print("\n   Checking logs for errors...")

        response = requests.get(f"{self.api_base}/logs/{monitor_id}")
        if response.status_code != 200:
            print(f"   ⚠️  Could not fetch logs: {response.status_code}")
            return True  # Don't fail if logs unavailable

        logs = response.text

        # Check for critical errors
        if "401 Unauthorized" in logs:
            print("   ❌ Found 401 Unauthorized error")
            return False

        if "Traceback" in logs and "Error" in logs:
            print("   ❌ Found Python traceback in logs")
            # Print last 20 lines
            lines = logs.split("\n")
            print("   Last 20 lines:")
            for line in lines[-20:]:
                print(f"     {line}")
            return False

        # Check for success indicators based on monitor type
        if monitor_type == "openai_agents_sdk":
            if "Skipping ax-docker" in logs or "Skipping ax-gcp" in logs:
                print("   ✅ OpenAI monitor correctly skipped ax-docker/ax-gcp")
            else:
                print("   ⚠️  ax-docker skip message not found (may be OK)")

        if "QueueManager initialized" in logs or "queue manager" in logs.lower():
            print("   ✅ QueueManager started")

        return True

    def cleanup_monitors(self):
        """Stop all deployed monitors"""
        print(f"\n{'=' * 70}")
        print(f"Cleaning up {len(self.deployed_monitors)} monitor(s)...")
        print(f"{'=' * 70}")

        for monitor_id in self.deployed_monitors:
            try:
                response = requests.delete(f"{self.api_base}/monitors/{monitor_id}")
                if response.status_code == 200:
                    print(f"✅ Stopped {monitor_id}")
                else:
                    print(f"⚠️  Failed to stop {monitor_id}: {response.status_code}")
            except Exception as e:
                print(f"⚠️  Error stopping {monitor_id}: {e}")

    def run_all_tests(self) -> bool:
        """Run deployment tests for all monitor types"""

        # Test cases: (agent_name, monitor_type, model, config_file)
        test_cases = [
            # Echo monitor (simplest, no API key needed)
            ("ghost_ray_363", "echo", "", "local_ghost.json"),
            # LangGraph monitor
            ("lunar_craft_128", "langgraph", "gpt-oss:latest", "lunar_craft_128.json"),
        ]

        # Only test OpenAI if API key is set
        if os.getenv("OPENAI_API_KEY"):
            test_cases.append(
                (
                    "lunar_craft_128",
                    "openai_agents_sdk",
                    "gpt-5-mini",
                    "lunar_craft_128.json",
                )
            )
        else:
            print("\n⚠️  OPENAI_API_KEY not set, skipping OpenAI Agents SDK test")

        # Only test Claude if API key is set
        if os.getenv("ANTHROPIC_API_KEY"):
            test_cases.append(
                (
                    "ghost_ray_363",
                    "claude_agent_sdk",
                    "claude-sonnet-4-5",
                    "local_ghost.json",
                )
            )
        else:
            print("\n⚠️  ANTHROPIC_API_KEY not set, skipping Claude Agent SDK test")

        try:
            results = []
            for agent_name, monitor_type, model, config_file in test_cases:
                success = self.test_monitor_deployment(agent_name, monitor_type, model, config_file)
                results.append((monitor_type, success))

                # Brief pause between tests
                if success:
                    time.sleep(2)

            # Summary
            print(f"\n{'=' * 70}")
            print("DEPLOYMENT TEST SUMMARY")
            print(f"{'=' * 70}")

            all_passed = True
            for monitor_type, success in results:
                status = "✅ PASS" if success else "❌ FAIL"
                print(f"{status}: {monitor_type}")
                if not success:
                    all_passed = False

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
    print("Dashboard Monitor Deployment E2E Test")
    print("=" * 70)
    print()
    print("This test verifies all monitor types can be deployed via dashboard API")
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
    test = DashboardDeploymentTest()
    success = test.run_all_tests()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
