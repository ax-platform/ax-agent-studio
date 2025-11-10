#!/usr/bin/env python3
"""
E2E Test 3: Ollama Monitor with gpt-oss Model

Test flow:
1. Deploy Ollama monitor on lunar_ray_510
2. Have ghost_ray_363 send @mention to it
3. Verify Ollama responds with AI-generated content

Usage:
    python test_03_ollama.py
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.e2e.helpers.dashboard_api import DashboardAPI
from tests.e2e.test_config import TEST_AGENTS

VALIDATION_SCRIPT = Path(__file__).parent / "validate-agent-response.js"


def test_ollama_monitor() -> bool:
    """Deploy Ollama on lunar_ray_510, send @mention from ghost_ray_363, verify AI response"""

    target_agent = "lunar_ray_510"
    sender_agent = "ghost_ray_363"

    print(f"\n{'=' * 80}")
    print("TEST 3: Ollama Monitor with gpt-oss")
    print("=" * 80)
    print(f"Target Agent: {target_agent} (will run Ollama)")
    print(f"Sender Agent: {sender_agent} (will send test message)")
    print("Model: gpt-oss:latest (local Ollama)")
    print("=" * 80)

    target_config = TEST_AGENTS[target_agent]

    with DashboardAPI() as api:
        try:
            # 1. Clean slate
            print("\n📦 Cleanup...")
            api.cleanup_all()

            # 2. Deploy Ollama monitor
            print(f"\n🚀 Deploying Ollama (gpt-oss:latest) on {target_agent}...")
            result = api.start_monitor(
                agent_name=target_agent,
                config_path=target_config["config_path"],
                monitor_type="ollama",
                provider="ollama",
                model="gpt-oss:latest",
            )
            print(f"  ✓ Monitor started: {result['monitor_id']}")

            # 3. Wait for monitor to be fully ready
            print("\n⏳ Waiting for Ollama monitor to initialize...")
            print("   (This takes longer than Echo - need to load model)")
            if not api.wait_for_monitor_ready(target_agent, timeout=30):
                print("  ❌ Monitor failed to initialize")
                return False
            print("  ✓ Monitor is READY")

            # 4. Send @mention and wait for AI response
            print(f"\n💬 Sending @mention from {sender_agent} → {target_agent}...")
            print("   Using wait=true, wait_mode='mentions' (timeout=60s)")
            print("   Question: 'What is the capital of France?'")

            result = subprocess.run(
                [
                    "node",
                    str(VALIDATION_SCRIPT),
                    target_agent,
                    sender_agent,
                    "What is the capital of France?",
                    "60",  # AI needs time to respond
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
                print(f"\n✅ {target_agent} PASSED - AI responded!")
                return True
            else:
                print(f"\n❌ {target_agent} FAILED")
                if result.stderr:
                    print("Error:", result.stderr)
                return False

        except Exception as e:
            print(f"\n❌ {target_agent} ERROR: {e}")
            return False


def main():
    """Run Ollama test"""
    print("\n" + "=" * 80)
    print("E2E TEST 3: Ollama Monitor with gpt-oss")
    print("=" * 80)

    success = test_ollama_monitor()

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
        print("  ✅ Ollama monitor works!")
        print("  🤖 AI model successfully responded to question")
    else:
        print("  ❌ Ollama test failed")
    print("=" * 80)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
