#!/usr/bin/env python3
"""
E2E Test: All Agent Types (Data-Driven)

Tests deployment and validation of all agent types using a forEach pattern.
Each test config specifies: agent, monitor type, model, timeout.
"""

import subprocess
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.e2e.helpers.dashboard_api import DashboardAPI

# Test configurations: Each monitor type with its settings
TEST_CONFIGS = [
    {
        "name": "Echo Monitor (Simple)",
        "agent_name": "ghost_ray_363",
        "config_path": "configs/agents/local_ghost.json",
        "monitor_type": "echo",
        "provider": None,
        "model": None,
        "sender_agent": "lunar_ray_510",
        "timeout": 10,  # Echo responds instantly
    },
    {
        "name": "Ollama Monitor (AI)",
        "agent_name": "lunar_ray_510",
        "config_path": "configs/agents/local_lunar_ray.json",
        "monitor_type": "ollama",
        "provider": "ollama",
        "model": "gptoss",
        "sender_agent": "ghost_ray_363",
        "timeout": 60,  # AI needs time to process
    },
    {
        "name": "Claude Agent SDK (Secure)",
        "agent_name": "ghost_ray_363",
        "config_path": "configs/agents/local_ghost.json",
        "monitor_type": "claude_agent_sdk",
        "provider": "anthropic",
        "model": "claude-sonnet-4-5",
        "sender_agent": "lunar_ray_510",
        "timeout": 60,  # AI needs time to process
    },
    {
        "name": "OpenAI Agents SDK",
        "agent_name": "lunar_ray_510",
        "config_path": "configs/agents/local_lunar_ray.json",
        "monitor_type": "openai_agents_sdk",
        "provider": "openai",
        "model": "gpt-5-mini",
        "sender_agent": "ghost_ray_363",
        "timeout": 60,  # AI needs time to process
    },
    {
        "name": "LangGraph (Tools)",
        "agent_name": "lunar_ray_510",
        "config_path": "configs/agents/local_lunar_ray.json",
        "monitor_type": "langgraph",
        "provider": "google",
        "model": "gemini-2.5-pro",
        "sender_agent": "ghost_ray_363",
        "timeout": 90,  # AI + tools need more time
    },
]


def run_javascript_validation(agent_name: str, sender_agent: str, timeout: int = 180) -> bool:
    """Run JavaScript MCP JAM SDK validation test"""
    script_path = Path(__file__).parent / "validate-agent-response.js"
    test_message = f"E2E Test: Validating {agent_name}"

    print("  🧪 Running MCP JAM SDK validation...")
    print(f"     Script: {script_path.name}")
    print(f"     Target: {agent_name}")
    print(f"     Sender: {sender_agent}")
    print(f"     Timeout: {timeout}s")

    try:
        result = subprocess.run(
            [
                "node",
                str(script_path),
                agent_name,
                sender_agent,
                test_message,
                str(timeout),
            ],
            capture_output=True,
            text=True,
            timeout=timeout + 20,  # Process timeout = wait timeout + overhead
        )

        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)

        if result.returncode == 0:
            print("  ✅ Validation PASSED")
            return True
        else:
            print(f"  ❌ Validation FAILED (exit code {result.returncode})")
            return False

    except subprocess.TimeoutExpired:
        print(f"  ❌ Validation TIMEOUT (>{timeout}s)")
        return False
    except Exception as e:
        print(f"  ❌ Validation ERROR: {e}")
        return False


def test_monitor_type(config: dict) -> bool:
    """Generic test function for any monitor type"""
    print("\n" + "=" * 80)
    print(f"TEST: {config['name']}")
    print("=" * 80)

    with DashboardAPI() as api:
        # Clean slate
        print("\n📦 Cleaning up existing agents...")
        api.cleanup_all()

        # Deploy monitor
        print(f"🚀 Deploying {config['agent_name']} with {config['monitor_type']}...")
        result = api.start_monitor(
            agent_name=config["agent_name"],
            config_path=config["config_path"],
            monitor_type=config["monitor_type"],
            provider=config["provider"],
            model=config["model"],
        )
        print(f"  ✓ Monitor started: {result['monitor_id']}")

        # Wait for running
        print("⏳ Waiting for monitor to reach RUNNING status...")
        if api.wait_for_monitor_running(config["agent_name"], timeout=10):
            print("  ✓ Monitor is RUNNING")
        else:
            print("  ❌ Monitor failed to start")
            return False

        # Validate with MCP JAM SDK
        print("\n🧪 Validating with MCP JAM SDK...")
        return run_javascript_validation(
            config["agent_name"], config["sender_agent"], timeout=config["timeout"]
        )


def main():
    """Run all E2E tests using forEach pattern"""
    print("\n" + "=" * 80)
    print("E2E TEST SUITE: All Agent Types (Data-Driven)")
    print("=" * 80)
    print(f"\nTesting {len(TEST_CONFIGS)} monitor types")
    print("Using Dashboard API for deployment (no UI automation needed)")
    print("=" * 80)

    results = {}
    for config in TEST_CONFIGS:
        try:
            passed = test_monitor_type(config)
            results[config["name"]] = passed
        except Exception as e:
            print(f"\n💥 ERROR in {config['name']}: {type(e).__name__}: {e}")
            import traceback

            traceback.print_exc()
            results[config["name"]] = False

    # Final cleanup
    print("\n" + "=" * 80)
    print("🧹 Final Cleanup")
    print("=" * 80)
    with DashboardAPI() as api:
        api.cleanup_all()
        print("✓ All agents cleaned up")

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    for name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {status}: {name}")

    total = len(results)
    passed_count = sum(1 for p in results.values() if p)
    print(f"\nTotal: {passed_count}/{total} tests passed")
    print("=" * 80 + "\n")

    # Exit with appropriate code
    if all(results.values()):
        print("✅ ALL TESTS PASSED\n")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
