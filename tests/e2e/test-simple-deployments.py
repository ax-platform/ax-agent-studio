#!/usr/bin/env python3
"""
Simple E2E Test: Just verify each monitor type deploys successfully
No complex validation - just deploy and check status
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tests.e2e.helpers.dashboard_api import DashboardAPI

# Simple test configs - just what we need to deploy
TESTS = [
    ("Echo", "ghost_ray_363", "configs/agents/local_ghost.json", "echo", None, None),
    (
        "Ollama",
        "lunar_ray_510",
        "configs/agents/local_lunar_ray.json",
        "ollama",
        "ollama",
        "gptoss",
    ),
    (
        "Claude SDK",
        "ghost_ray_363",
        "configs/agents/local_ghost.json",
        "claude_agent_sdk",
        "anthropic",
        "claude-sonnet-4-5",
    ),
    (
        "OpenAI SDK",
        "lunar_ray_510",
        "configs/agents/local_lunar_ray.json",
        "openai_agents_sdk",
        "openai",
        "gpt-5-mini",
    ),
    (
        "LangGraph",
        "lunar_ray_510",
        "configs/agents/local_lunar_ray.json",
        "langgraph",
        "google",
        "gemini-2.5-pro",
    ),
]


def main():
    print("\n" + "=" * 80)
    print("SIMPLE DEPLOYMENT TEST")
    print("=" * 80)
    print(f"\nTesting {len(TESTS)} monitor types")
    print("Goal: Verify each monitor type can deploy and reach RUNNING status")
    print("=" * 80)

    results = {}

    for name, agent, config, monitor_type, provider, model in TESTS:
        print(f"\n{'─' * 80}")
        print(f"TEST: {name}")
        print("─" * 80)

        with DashboardAPI() as api:
            try:
                # Clean up first
                api.cleanup_all()

                # Deploy
                print(f"🚀 Deploying {agent} with {monitor_type}...")
                result = api.start_monitor(
                    agent_name=agent,
                    config_path=config,
                    monitor_type=monitor_type,
                    provider=provider,
                    model=model,
                )
                print(f"  ✓ Monitor started: {result['monitor_id']}")

                # Wait for RUNNING
                print("⏳ Waiting for RUNNING status...")
                if api.wait_for_monitor_running(agent, timeout=10):
                    print("  ✅ SUCCESS: Monitor is RUNNING")
                    results[name] = True
                else:
                    print("  ❌ FAILED: Monitor did not reach RUNNING")
                    results[name] = False

            except Exception as e:
                print(f"  ❌ ERROR: {e}")
                results[name] = False

    # Cleanup
    print("\n" + "=" * 80)
    print("🧹 Cleanup")
    print("=" * 80)
    with DashboardAPI() as api:
        api.cleanup_all()
        print("✓ All agents cleaned up")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    for name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {status}: {name}")

    passed_count = sum(1 for p in results.values() if p)
    total = len(results)
    print(f"\n{passed_count}/{total} tests passed")
    print("=" * 80 + "\n")

    sys.exit(0 if all(results.values()) else 1)


if __name__ == "__main__":
    main()
