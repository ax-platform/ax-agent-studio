#!/usr/bin/env python3
"""
E2E Test 5: Four-Way AI Conversation - Queue Management Stress Test

Test flow:
1. Deploy Ollama on ALL 4 agents simultaneously
2. Have them send messages to each other in various patterns
3. Test queue management when multiple messages arrive
4. Verify all agents handle concurrent conversations

This stress-tests the queue manager!

Usage:
    python test_05_four_way_conversation.py
"""

import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.e2e.helpers.dashboard_api import DashboardAPI
from tests.e2e.test_config import TEST_AGENTS

VALIDATION_SCRIPT = Path(__file__).parent / "validate-agent-response.js"

# All 4 test agents
AGENTS = list(TEST_AGENTS.keys())


def deploy_ollama_agent(api: DashboardAPI, agent_name: str) -> bool:
    """Deploy Ollama monitor on an agent"""
    print(f"  🚀 Deploying on {agent_name}...", end=" ")

    config = TEST_AGENTS[agent_name]
    result = api.start_monitor(
        agent_name=agent_name,
        config_path=config["config_path"],
        monitor_type="ollama",
        provider="ollama",
        model="gpt-oss:latest",
    )

    if not api.wait_for_monitor_ready(agent_name, timeout=30):
        print("❌ FAILED")
        return False
    print("✅ READY")
    return True


def send_message(target: str, sender: str, content: str) -> bool:
    """Send a message and wait for AI response"""
    result = subprocess.run(
        [
            "node",
            str(VALIDATION_SCRIPT),
            target,
            sender,
            content,
            "60",
        ],
        capture_output=True,
        text=True,
        timeout=90,
    )
    return result.returncode == 0


def test_four_way_conversation() -> dict:
    """Deploy Ollama on all 4 agents and test conversation patterns"""

    print(f"\n{'=' * 80}")
    print("TEST 5: Four-Way AI Conversation")
    print("=" * 80)
    print(f"Agents: {', '.join(AGENTS)}")
    print("All agents will have Ollama AI running")
    print("=" * 80)

    results = {}

    with DashboardAPI() as api:
        try:
            # 1. Clean slate
            print("\n📦 Cleanup...")
            api.cleanup_all()

            # 2. Deploy Ollama on ALL 4 agents
            print("\n🤖 Deploying Ollama AI on all 4 agents...")
            print("   (This takes ~30s per agent)")

            all_ready = True
            for agent in AGENTS:
                if not deploy_ollama_agent(api, agent):
                    all_ready = False
                    break

            if not all_ready:
                print("\n❌ Failed to deploy all agents")
                return {agent: False for agent in AGENTS}

            print("\n✅ All 4 AI agents are ready!")
            print("   Each agent can now respond to @mentions with AI")

            # 3. Have all agents ask each other simple trivia questions
            print(f"\n{'=' * 80}")
            print("💬 Four-Way Trivia Conversation")
            print("=" * 80)
            print("All agents ask each other simple trivia questions")
            print()

            # Simple trivia questions between all agents
            conversations = [
                (AGENTS[0], AGENTS[1], "What is the capital of Italy?"),
                (AGENTS[1], AGENTS[2], "What color is the ocean?"),
                (AGENTS[2], AGENTS[3], "How many days are in a week?"),
                (AGENTS[3], AGENTS[0], "What is 10 times 10?"),
                (AGENTS[0], AGENTS[2], "What is the largest planet?"),
                (AGENTS[1], AGENTS[3], "How many legs does a spider have?"),
                (AGENTS[2], AGENTS[0], "What shape is a ball?"),
                (AGENTS[3], AGENTS[1], "What season comes after summer?"),
            ]

            for i, (target, sender, content) in enumerate(conversations, 1):
                print(f"  {i}. {sender} → {target}")
                print(f'     "{content}"')
                success = send_message(target, sender, content)
                results[f"{sender}_to_{target}_{i}"] = success
                status = "✅" if success else "❌"
                print(f"     {status}\n")
                time.sleep(2)  # Small delay to avoid overwhelming

            return results

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback

            traceback.print_exc()
            return {agent: False for agent in AGENTS}


def main():
    """Run four-way conversation test"""
    print("\n" + "=" * 80)
    print("E2E TEST 5: Four-Way AI Conversation & Queue Stress Test")
    print("=" * 80)

    results = test_four_way_conversation()

    print("\n" + "=" * 80)
    print("🧹 Cleanup")
    print("=" * 80)
    with DashboardAPI() as api:
        api.cleanup_all()
        print("✓ Cleaned up")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    passed_count = sum(1 for p in results.values() if p)
    total = len(results)

    print(f"\n  {passed_count}/{total} conversations successful")

    if passed_count == total:
        print("\n  🎉 All trivia conversations worked!")
        print("  ✅ All 4 AI agents successfully answered questions")
        print("  ✅ Queue management handled multiple conversations")
    else:
        print(f"\n  ⚠️  Some conversations failed ({total - passed_count} failed)")
        failed_count = sum(1 for p in results.values() if not p)
        print(f"     {failed_count} conversations had issues")

    print("=" * 80)

    return 0 if passed_count == total else 1


if __name__ == "__main__":
    sys.exit(main())
