#!/usr/bin/env python3
"""
E2E Test 8: OpenAI Agents SDK

Test flow:
1. Deploy OpenAI Agents SDK monitor on agent
2. Send question to OpenAI
3. Verify OpenAI responds with AI-generated content

This tests cloud AI (OpenAI GPT)

Usage:
    python test_08_openai_sdk.py
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.e2e.helpers.dashboard_api import DashboardAPI
from tests.e2e.test_config import TEST_AGENTS

VALIDATION_SCRIPT = Path(__file__).parent / "validate-agent-response.js"


def test_openai_sdk() -> bool:
    """Deploy OpenAI SDK on agent, verify AI response"""

    target_agent = "lunar_ray_510"
    sender_agent = "ghost_ray_363"

    print(f"\n{'=' * 80}")
    print(f"TEST 8: OpenAI Agents SDK")
    print('=' * 80)
    print(f"Target Agent: {target_agent} (will run OpenAI SDK)")
    print(f"Sender Agent: {sender_agent} (will send test message)")
    print(f"Model: gpt-4o-mini (cloud AI)")
    print('=' * 80)

    target_config = TEST_AGENTS[target_agent]

    with DashboardAPI() as api:
        try:
            # 1. Clean slate
            print("\n📦 Cleanup...")
            api.cleanup_all()

            # 2. Deploy OpenAI SDK monitor
            print(f"\n🚀 Deploying OpenAI Agents SDK on {target_agent}...")
            result = api.start_monitor(
                agent_name=target_agent,
                config_path=target_config["config_path"],
                monitor_type="openai_agents_sdk",
                provider="openai",
                model="gpt-4o-mini",  # Updated to real model name
            )
            print(f"  ✓ Monitor started: {result['monitor_id']}")

            # 3. Wait for monitor to be fully ready
            print(f"\n⏳ Waiting for OpenAI SDK to initialize...")
            if not api.wait_for_monitor_ready(target_agent, timeout=30):
                print("  ❌ Monitor failed to initialize")
                return False
            print("  ✓ Monitor is READY")

            # 4. Send question and wait for OpenAI's response
            print(f"\n💬 Sending question to OpenAI...")
            print(f"   Question: 'What is the largest ocean on Earth?'")

            result = subprocess.run(
                [
                    "node",
                    str(VALIDATION_SCRIPT),
                    target_agent,
                    sender_agent,
                    "What is the largest ocean on Earth?",
                    "60",  # Cloud AI timeout
                ],
                capture_output=True,
                text=True,
                timeout=90,
            )

            # Print validation output
            if result.stdout:
                for line in result.stdout.split("\n"):
                    if line.strip():
                        print(f"   {line}")

            if result.returncode == 0:
                print(f"\n✅ OpenAI SDK PASSED - AI responded!")
                return True
            else:
                print(f"\n❌ OpenAI SDK FAILED")
                if result.stderr:
                    print("Error:", result.stderr)
                return False

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback

            traceback.print_exc()
            return False


def main():
    """Run OpenAI SDK test"""
    print("\n" + "=" * 80)
    print("E2E TEST 8: OpenAI Agents SDK")
    print("=" * 80)

    success = test_openai_sdk()

    print("\n" + "=" * 80)
    print("🧹 Cleanup")
    print("=" * 80)
    with DashboardAPI() as api:
        api.cleanup_all()
        print("✓ Cleaned up")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    if success:
        print("  ✅ OpenAI Agents SDK works!")
        print("  🤖 Cloud AI successfully responded")
    else:
        print("  ❌ OpenAI SDK test failed")
    print("=" * 80)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
