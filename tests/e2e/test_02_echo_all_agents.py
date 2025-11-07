#!/usr/bin/env python3
"""
E2E Test 2: Echo Monitor on All Agents

Test flow for each agent:
1. Deploy Echo monitor on agent
2. Have a DIFFERENT agent send @mention to it
3. Verify Echo monitor responds

Usage:
    python test_02_echo_all_agents.py
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.e2e.helpers.dashboard_api import DashboardAPI
from tests.e2e.test_config import TEST_AGENTS

VALIDATION_SCRIPT = Path(__file__).parent / "validate-agent-response.js"


def test_echo_on_agent(target_agent: str, sender_agent: str) -> bool:
    """Deploy Echo on target_agent, send @mention from sender_agent, verify response"""
    print(f"\n{'=' * 80}")
    print(f"Testing Echo on: {target_agent}")
    print(f"  Message from: {sender_agent}")
    print("=" * 80)

    target_config = TEST_AGENTS[target_agent]

    with DashboardAPI() as api:
        try:
            # 1. Clean slate
            print("📦 Cleanup...")
            api.cleanup_all()

            # 2. Deploy Echo monitor
            print(f"🚀 Deploying Echo on {target_agent}...")
            result = api.start_monitor(
                agent_name=target_agent,
                config_path=target_config["config_path"],
                monitor_type="echo",
                provider=None,
                model=None,
            )
            print(f"  ✓ Monitor started: {result['monitor_id'][:16]}...")

            # 3. Wait for monitor to be fully ready (checks log for init markers)
            print("⏳ Waiting for monitor to initialize...")
            if not api.wait_for_monitor_ready(target_agent, timeout=15):
                print("  ❌ Monitor failed to initialize")
                return False
            print("  ✓ Monitor is READY (queue manager started)")

            # 4. Send @mention and wait for response
            print(f"💬 Sending @mention from {sender_agent} → {target_agent}...")
            print("   Using wait=true, wait_mode='mentions' (timeout=10s)")

            result = subprocess.run(
                [
                    "node",
                    str(VALIDATION_SCRIPT),
                    target_agent,
                    sender_agent,
                    f"Test 2: Echo test for {target_agent}",
                    "10",  # Echo responds instantly
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            # Print validation output
            if result.stdout:
                for line in result.stdout.split("\n"):
                    if line.strip():
                        print(f"   {line}")

            if result.returncode == 0:
                print(f"\n✅ {target_agent} PASSED")
                return True
            else:
                print(f"\n❌ {target_agent} FAILED")
                return False

        except subprocess.TimeoutExpired:
            print(f"\n❌ {target_agent} TIMEOUT")
            return False
        except Exception as e:
            print(f"\n❌ {target_agent} ERROR: {e}")
            import traceback

            traceback.print_exc()
            return False


def main():
    """Test Echo monitor on all agents"""
    print("\n" + "=" * 80)
    print("TEST 2: Echo Monitor on All Agents")
    print("=" * 80)
    print(f"\nTesting Echo on {len(TEST_AGENTS)} agents")
    print("Each agent will have Echo deployed, then receive @mention from another agent")
    print("=" * 80)

    # Create pairs: (target_agent, sender_agent)
    # Make sure sender is different from target
    agent_names = list(TEST_AGENTS.keys())
    test_pairs = []
    for i, target in enumerate(agent_names):
        # Use the next agent as sender (wrap around)
        sender = agent_names[(i + 1) % len(agent_names)]
        test_pairs.append((target, sender))

    results = {}
    for target, sender in test_pairs:
        results[target] = test_echo_on_agent(target, sender)

    # Cleanup
    print("\n" + "=" * 80)
    print("🧹 Cleanup")
    print("=" * 80)
    with DashboardAPI() as api:
        api.cleanup_all()
        print("✓ Cleaned up")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    for name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {status}: {name}")

    passed = sum(1 for p in results.values() if p)
    total = len(results)
    print(f"\n{passed}/{total} agents can receive Echo")
    print("=" * 80 + "\n")

    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
