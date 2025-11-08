#!/usr/bin/env python3
"""
E2E Test 7: Claude Agent SDK

Test flow:
1. Deploy Claude Agent SDK monitor on agent
2. Send question to Claude
3. Verify Claude responds with AI-generated content

This tests production-grade cloud AI (Anthropic Claude Sonnet 4.5)

Usage:
    python test_07_claude_sdk.py
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.e2e.helpers.dashboard_api import DashboardAPI
from tests.e2e.test_config import TEST_AGENTS

VALIDATION_SCRIPT = Path(__file__).parent / "validate-agent-response.js"


def test_claude_sdk() -> bool:
    """Deploy Claude SDK on agent, verify AI response"""

    target_agent = "ghost_ray_363"
    sender_agent = "lunar_ray_510"

    print(f"\n{'=' * 80}")
    print(f"TEST 7: Claude Agent SDK")
    print('=' * 80)
    print(f"Target Agent: {target_agent} (will run Claude SDK)")
    print(f"Sender Agent: {sender_agent} (will send test message)")
    print(f"Model: claude-sonnet-4-5 (cloud AI)")
    print('=' * 80)

    target_config = TEST_AGENTS[target_agent]

    with DashboardAPI() as api:
        try:
            # 1. Clean slate
            print("\n📦 Cleanup...")
            api.cleanup_all()

            # 2. Deploy Claude SDK monitor
            print(f"\n🚀 Deploying Claude Agent SDK on {target_agent}...")
            result = api.start_monitor(
                agent_name=target_agent,
                config_path=target_config["config_path"],
                monitor_type="claude_agent_sdk",
                provider="anthropic",
                model="claude-sonnet-4-5",
            )
            print(f"  ✓ Monitor started: {result['monitor_id']}")

            # 3. Wait for monitor to be fully ready
            print(f"\n⏳ Waiting for Claude SDK to initialize...")
            if not api.wait_for_monitor_ready(target_agent, timeout=30):
                print("  ❌ Monitor failed to initialize")
                return False
            print("  ✓ Monitor is READY")

            # 4. Send question and wait for Claude's response
            print(f"\n💬 Sending question to Claude...")
            print(f"   Question: 'What is the speed of light?'")

            result = subprocess.run(
                [
                    "node",
                    str(VALIDATION_SCRIPT),
                    target_agent,
                    sender_agent,
                    "What is the speed of light?",
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
                print(f"\n✅ Claude SDK PASSED - AI responded!")
                return True
            else:
                print(f"\n❌ Claude SDK FAILED")
                if result.stderr:
                    print("Error:", result.stderr)
                return False

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback

            traceback.print_exc()
            return False


def main():
    """Run Claude SDK test"""
    print("\n" + "=" * 80)
    print("E2E TEST 7: Claude Agent SDK")
    print("=" * 80)

    success = test_claude_sdk()

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
        print("  ✅ Claude Agent SDK works!")
        print("  🤖 Cloud AI successfully responded")
    else:
        print("  ❌ Claude SDK test failed")
    print("=" * 80)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
