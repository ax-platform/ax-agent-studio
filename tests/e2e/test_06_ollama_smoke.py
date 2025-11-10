#!/usr/bin/env python3
"""
E2E Test 6: Ollama Smoke Test (for pre-commit hooks)

Lightweight test that verifies Ollama monitor can respond to a simple question.
Perfect for pre-commit hooks - fast and validates AI functionality.

Test flow:
1. Deploy Ollama on 1 agent
2. Send simple question
3. Verify AI responds

Usage:
    python test_06_ollama_smoke.py
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.e2e.helpers.dashboard_api import DashboardAPI
from tests.e2e.test_config import TEST_AGENTS

VALIDATION_SCRIPT = Path(__file__).parent / "validate-agent-response.js"


def test_ollama_smoke() -> bool:
    """Lightweight Ollama test - just verify it responds"""

    target_agent = "ghost_ray_363"
    sender_agent = "lunar_ray_510"

    print(f"\n{'=' * 80}")
    print("TEST 6: Ollama Smoke Test")
    print('=' * 80)
    print(f"Target: {target_agent} (Ollama AI)")
    print(f"Sender: {sender_agent}")
    print(f"Model: gpt-oss:latest")
    print(f"Question: 'Hi!'")
    print('=' * 80)

    target_config = TEST_AGENTS[target_agent]

    with DashboardAPI() as api:
        try:
            # 1. Clean slate
            print("\n📦 Cleanup...")
            api.cleanup_all()

            # 2. Deploy Ollama monitor
            print(f"\n🚀 Deploying Ollama on {target_agent}...")
            result = api.start_monitor(
                agent_name=target_agent,
                config_path=target_config["config_path"],
                monitor_type="ollama",
                provider="ollama",
                model="gpt-oss:latest",
            )
            print(f"  ✓ Monitor started: {result['monitor_id'][:16]}...")

            # 3. Wait for ready
            print(f"\n⏳ Waiting for monitor to initialize...")
            if not api.wait_for_monitor_ready(target_agent, timeout=30):
                print("  ❌ Monitor failed to initialize")
                return False
            print("  ✓ Monitor is READY")

            # 4. Send simple message
            print(f"\n💬 Sending simple greeting...")

            result = subprocess.run(
                [
                    "node",
                    str(VALIDATION_SCRIPT),
                    target_agent,
                    sender_agent,
                    "Hi!",
                    "30",  # Short timeout for simple greeting
                ],
                capture_output=True,
                text=True,
                timeout=45,
            )

            if result.returncode == 0:
                print(f"  ✅ AI responded successfully!")
                return True
            else:
                print(f"  ❌ AI failed to respond")
                return False

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            return False


def main():
    """Run Ollama smoke test"""
    print("\n" + "=" * 80)
    print("E2E TEST 6: Ollama Smoke Test (Pre-Commit)")
    print("=" * 80)

    success = test_ollama_smoke()

    print("\n" + "=" * 80)
    print("🧹 Cleanup")
    print("=" * 80)
    with DashboardAPI() as api:
        api.cleanup_all()
        print("✓ Cleaned up")

    print("\n" + "=" * 80)
    print("RESULT")
    print("=" * 80)
    if success:
        print("  ✅ Ollama smoke test PASSED")
        print("  🤖 AI is working correctly")
    else:
        print("  ❌ Ollama smoke test FAILED")
    print("=" * 80)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
