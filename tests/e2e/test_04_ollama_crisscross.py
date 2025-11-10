#!/usr/bin/env python3
"""
E2E Test 4: Ollama Crisscross - Multiple AI Agents

Test flow:
1. Deploy Ollama on 2 agents simultaneously
2. Have them send messages to each other (crisscross)
3. Verify both AI agents respond

This demonstrates multi-agent AI conversations!

Usage:
    python test_04_ollama_crisscross.py
"""

import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.e2e.helpers.dashboard_api import DashboardAPI
from tests.e2e.test_config import TEST_AGENTS

VALIDATION_SCRIPT = Path(__file__).parent / "validate-agent-response.js"


def deploy_ollama_agent(api: DashboardAPI, agent_name: str) -> bool:
    """Deploy Ollama monitor on an agent"""
    print(f"\n🚀 Deploying Ollama on {agent_name}...")

    config = TEST_AGENTS[agent_name]
    result = api.start_monitor(
        agent_name=agent_name,
        config_path=config["config_path"],
        monitor_type="ollama",
        provider="ollama",
        model="gpt-oss:latest",
    )
    print(f"  ✓ Monitor started: {result['monitor_id']}")

    print(f"⏳ Waiting for {agent_name} to initialize...")
    if not api.wait_for_monitor_ready(agent_name, timeout=30):
        print(f"  ❌ {agent_name} failed to initialize")
        return False
    print(f"  ✓ {agent_name} is READY")
    return True


def test_ai_crisscross() -> dict:
    """Deploy Ollama on 2 agents and have them message each other"""

    # Agent pairs for crisscross
    agent1 = "ghost_ray_363"
    agent2 = "lunar_ray_510"

    print(f"\n{'=' * 80}")
    print("TEST 4: Ollama AI Crisscross")
    print("=" * 80)
    print(f"Agent 1: {agent1} (Ollama AI)")
    print(f"Agent 2: {agent2} (Ollama AI)")
    print("Pattern: Each AI agent will receive and respond to a message")
    print("=" * 80)

    results = {}

    with DashboardAPI() as api:
        try:
            # 1. Clean slate
            print("\n📦 Cleanup...")
            api.cleanup_all()

            # 2. Deploy Ollama on BOTH agents
            print("\n🤖 Deploying AI monitors on both agents...")
            if not deploy_ollama_agent(api, agent1):
                return {agent1: False, agent2: False}
            if not deploy_ollama_agent(api, agent2):
                return {agent1: True, agent2: False}

            print("\n✅ Both AI agents are ready!")

            # Give them a moment to settle
            time.sleep(2)

            # 3. Crisscross test 1: agent2 → agent1
            print(f"\n{'=' * 80}")
            print(f"🔀 Test 1: {agent2} → {agent1}")
            print("=" * 80)
            print(f"💬 Sending question from {agent2} → {agent1}...")
            print("   Question: 'What is 2+2?'")

            result = subprocess.run(
                [
                    "node",
                    str(VALIDATION_SCRIPT),
                    agent1,  # target
                    agent2,  # sender
                    "What is 2+2?",
                    "60",
                ],
                capture_output=True,
                text=True,
                timeout=90,
            )

            if result.stdout:
                for line in result.stdout.split("\n"):
                    if line.strip():
                        print(f"   {line}")

            results[agent1] = result.returncode == 0

            # 4. Crisscross test 2: agent1 → agent2
            print(f"\n{'=' * 80}")
            print(f"🔀 Test 2: {agent1} → {agent2}")
            print("=" * 80)
            print(f"💬 Sending question from {agent1} → {agent2}...")
            print("   Question: 'What color is the sky?'")

            result = subprocess.run(
                [
                    "node",
                    str(VALIDATION_SCRIPT),
                    agent2,  # target
                    agent1,  # sender
                    "What color is the sky?",
                    "60",
                ],
                capture_output=True,
                text=True,
                timeout=90,
            )

            if result.stdout:
                for line in result.stdout.split("\n"):
                    if line.strip():
                        print(f"   {line}")

            results[agent2] = result.returncode == 0

            return results

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            return {agent1: False, agent2: False}


def main():
    """Run Ollama crisscross test"""
    print("\n" + "=" * 80)
    print("E2E TEST 4: Ollama AI Crisscross")
    print("=" * 80)

    results = test_ai_crisscross()

    print("\n" + "=" * 80)
    print("🧹 Cleanup")
    print("=" * 80)
    with DashboardAPI() as api:
        api.cleanup_all()
        print("✓ Cleaned up")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    for agent, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {status}: {agent}")

    passed_count = sum(1 for p in results.values() if p)
    total = len(results)
    print(f"\n{passed_count}/{total} AI agents responded successfully")

    if all(results.values()):
        print("🎉 AI Crisscross complete! Both agents responded to each other!")

    print("=" * 80)

    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
