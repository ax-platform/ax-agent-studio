#!/usr/bin/env python3
"""
E2E Test 9: LangGraph with Tool Support

Test flow:
1. Deploy LangGraph monitor on agent
2. Send question to Gemini via LangGraph
3. Verify Gemini responds with AI-generated content

This tests LangGraph framework with Google Gemini 2.5 Pro (supports tools)

Usage:
    python test_09_langgraph.py
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.e2e.helpers.dashboard_api import DashboardAPI
from tests.e2e.test_config import TEST_AGENTS

VALIDATION_SCRIPT = Path(__file__).parent / "validate-agent-response.js"


def run_langgraph_test() -> bool:
    """Deploy LangGraph on agent, verify AI response"""

    target_agent = "lunar_ray_510"
    sender_agent = "ghost_ray_363"

    print(f"\n{'=' * 80}")
    print("TEST 9: LangGraph with Gemini")
    print("=" * 80)
    print(f"Target Agent: {target_agent} (will run LangGraph)")
    print(f"Sender Agent: {sender_agent} (will send test message)")
    print("Model: gemini-2.5-pro (with tool support)")
    print("=" * 80)

    target_config = TEST_AGENTS[target_agent]

    with DashboardAPI() as api:
        try:
            # 1. Clean slate
            print("\n📦 Cleanup...")
            api.cleanup_all()

            # 2. Deploy LangGraph monitor
            print(f"\n🚀 Deploying LangGraph on {target_agent}...")
            result = api.start_monitor(
                agent_name=target_agent,
                config_path=target_config["config_path"],
                monitor_type="langgraph",
                provider="gemini",  # Fixed: should be "gemini" not "google"
                model="gemini-2.5-pro",
            )
            print(f"  ✓ Monitor started: {result['monitor_id']}")

            # 3. Wait for monitor to be fully ready
            print("\n⏳ Waiting for LangGraph to initialize...")
            print("   (LangGraph + tools may take longer to initialize)")
            if not api.wait_for_monitor_ready(target_agent, timeout=45):
                print("  ❌ Monitor failed to initialize")
                return False
            print("  ✓ Monitor is READY")

            # 4. Send question and wait for Gemini's response
            print("\n💬 Sending question to Gemini via LangGraph...")
            print("   Question: 'What is the tallest mountain in the world?'")

            result = subprocess.run(
                [
                    "node",
                    str(VALIDATION_SCRIPT),
                    target_agent,
                    sender_agent,
                    "What is the tallest mountain in the world?",
                    "90",  # LangGraph + tools need more time
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )

            # Print validation output
            if result.stdout:
                for line in result.stdout.split("\n"):
                    if line.strip():
                        print(f"   {line}")

            if result.returncode == 0:
                print("\n✅ LangGraph PASSED - AI responded!")
                return True
            else:
                print("\n❌ LangGraph FAILED")
                if result.stderr:
                    print("Error:", result.stderr)
                return False

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback

            traceback.print_exc()
            return False


def main():
    """Run LangGraph test"""
    print("\n" + "=" * 80)
    print("E2E TEST 9: LangGraph with Gemini")
    print("=" * 80)

    success = run_langgraph_test()

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
        print("  ✅ LangGraph works!")
        print("  🤖 Gemini AI with tool support successfully responded")
    else:
        print("  ❌ LangGraph test failed")
    print("=" * 80)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
