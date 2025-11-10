#!/usr/bin/env python3
"""
E2E Test: All Agent Types

Tests deployment and validation of all agent types:
- Echo (Simple)
- Ollama (AI)
- Claude Agent SDK (Secure)
- OpenAI Agents SDK
- LangGraph (Tools)

Uses Dashboard API instead of UI automation for reliability.
"""

import subprocess
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.e2e.helpers.dashboard_api import DashboardAPI


def run_javascript_validation(
    agent_name: str, sender_agent: str, test_description: str, timeout: int = 180
) -> bool:
    """Run JavaScript MCP JAM SDK validation test

    Returns True if validation passed, False otherwise
    """
    script_path = Path(__file__).parent / "validate-agent-response.js"
    test_message = f"E2E Test: {test_description}"

    print("  🧪 Running MCP JAM SDK validation...")
    print(f"     Script: {script_path.name}")
    print(f"     Target: {agent_name}")
    print(f"     Sender: {sender_agent}")
    print(f"     Timeout: {timeout}s")

    try:
        result = subprocess.run(
            ["node", str(script_path), agent_name, sender_agent, test_message, str(timeout)],
            capture_output=True,
            text=True,
            timeout=timeout + 20,  # Process timeout = wait timeout + overhead
        )

        # Print script output
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
        print("  ❌ Validation TIMEOUT (>200s)")
        return False
    except Exception as e:
        print(f"  ❌ Validation ERROR: {e}")
        return False


def run_echo_monitor_test():
    """Test Echo monitor deployment"""
    print("\n" + "=" * 80)
    print("TEST 1: Echo Monitor (Simple)")
    print("=" * 80)

    with DashboardAPI() as api:
        # Clean slate
        print("\n📦 Cleaning up existing agents...")
        api.cleanup_all()

        # Deploy Echo
        print("🚀 Deploying ghost_ray_363 with Echo monitor...")
        result = api.start_monitor(
            agent_name="ghost_ray_363",
            config_path="configs/agents/local_ghost.json",
            monitor_type="echo",
        )
        print(f"  ✓ Monitor started: {result['monitor_id']}")

        # Wait for running
        print("⏳ Waiting for monitor to be READY...")
        if api.wait_for_monitor_ready("ghost_ray_363", timeout=15):
            print("  ✓ Monitor is READY")
        else:
            print("  ❌ Monitor failed to initialize")
            return False

        # Validate with MCP JAM SDK (Echo responds instantly, use short timeout)
        print("\n🧪 Validating with MCP JAM SDK...")
        if run_javascript_validation(
            "ghost_ray_363",
            "lunar_ray_510",
            "Echo Monitor - Testing instant echo response (no AI)",
            timeout=15,
        ):
            return True
        else:
            return False


def run_ollama_monitor_test():
    """Test Ollama monitor deployment"""
    print("\n" + "=" * 80)
    print("TEST 2: Ollama Monitor (AI)")
    print("=" * 80)

    with DashboardAPI() as api:
        # Clean slate
        print("\n📦 Cleaning up existing agents...")
        api.cleanup_all()

        # Deploy Ollama with default model (using lunar_ray_510 - local config)
        print("🚀 Deploying lunar_ray_510 with Ollama monitor...")
        result = api.start_monitor(
            agent_name="lunar_ray_510",
            config_path="configs/agents/local_lunar_ray.json",
            monitor_type="ollama",
            provider="ollama",
            model="gpt-oss:latest",  # Latest Ollama model
        )
        print(f"  ✓ Monitor started: {result['monitor_id']}")

        # Wait for running
        print("⏳ Waiting for monitor to be READY...")
        if api.wait_for_monitor_ready("lunar_ray_510", timeout=15):
            print("  ✓ Monitor is READY")
        else:
            print("  ❌ Monitor failed to initialize")
            return False

        # Validate with MCP JAM SDK (AI needs time to respond)
        print("\n🧪 Validating with MCP JAM SDK...")
        if run_javascript_validation(
            "lunar_ray_510",
            "ghost_ray_363",
            "Ollama Monitor (gpt-oss:latest) - Testing local AI response",
            timeout=60,
        ):
            return True
        else:
            return False


def run_claude_sdk_monitor_test():
    """Test Claude Agent SDK monitor deployment"""
    print("\n" + "=" * 80)
    print("TEST 3: Claude Agent SDK (Secure)")
    print("=" * 80)

    with DashboardAPI() as api:
        # Clean slate
        print("\n📦 Cleaning up existing agents...")
        api.cleanup_all()

        # Deploy Claude SDK with default model (using ghost_ray_363 - local config)
        print("🚀 Deploying ghost_ray_363 with Claude Agent SDK...")
        result = api.start_monitor(
            agent_name="ghost_ray_363",
            config_path="configs/agents/local_ghost.json",
            monitor_type="claude_agent_sdk",
            provider="anthropic",
            model="claude-sonnet-4-5",
        )
        print(f"  ✓ Monitor started: {result['monitor_id']}")

        # Wait for running
        print("⏳ Waiting for monitor to be READY...")
        if api.wait_for_monitor_ready("ghost_ray_363", timeout=15):
            print("  ✓ Monitor is READY")
        else:
            print("  ❌ Monitor failed to initialize")
            return False

        # Validate with MCP JAM SDK (AI needs time to respond)
        print("\n🧪 Validating with MCP JAM SDK...")
        if run_javascript_validation(
            "ghost_ray_363",
            "lunar_ray_510",
            "Claude Agent SDK (claude-sonnet-4-5) - Testing cloud AI with security controls",
            timeout=60,
        ):
            return True
        else:
            return False


def run_openai_sdk_monitor_test():
    """Test OpenAI Agents SDK monitor deployment"""
    print("\n" + "=" * 80)
    print("TEST 4: OpenAI Agents SDK")
    print("=" * 80)

    with DashboardAPI() as api:
        # Clean slate
        print("\n📦 Cleaning up existing agents...")
        api.cleanup_all()

        # Deploy OpenAI SDK with default model (using lunar_ray_510 - local config)
        print("🚀 Deploying lunar_ray_510 with OpenAI Agents SDK...")
        result = api.start_monitor(
            agent_name="lunar_ray_510",
            config_path="configs/agents/local_lunar_ray.json",
            monitor_type="openai_agents_sdk",
            provider="openai",
            model="gpt-5-mini",
        )
        print(f"  ✓ Monitor started: {result['monitor_id']}")

        # Wait for running
        print("⏳ Waiting for monitor to be READY...")
        if api.wait_for_monitor_ready("lunar_ray_510", timeout=15):
            print("  ✓ Monitor is READY")
        else:
            print("  ❌ Monitor failed to initialize")
            return False

        # Validate with MCP JAM SDK (AI needs time to respond)
        print("\n🧪 Validating with MCP JAM SDK...")
        if run_javascript_validation(
            "lunar_ray_510",
            "ghost_ray_363",
            "OpenAI Agents SDK (gpt-4o-mini) - Testing OpenAI cloud AI",
            timeout=60,
        ):
            return True
        else:
            return False


def run_langgraph_monitor_test():
    """Test LangGraph monitor deployment"""
    print("\n" + "=" * 80)
    print("TEST 5: LangGraph (Tools)")
    print("=" * 80)

    with DashboardAPI() as api:
        # Clean slate
        print("\n📦 Cleaning up existing agents...")
        api.cleanup_all()

        # Deploy LangGraph with default model (using lunar_ray_510 - local config)
        print("🚀 Deploying lunar_ray_510 with LangGraph...")
        result = api.start_monitor(
            agent_name="lunar_ray_510",
            config_path="configs/agents/local_lunar_ray.json",
            monitor_type="langgraph",
            provider="gemini",
            model="gemini-2.5-pro",
        )
        print(f"  ✓ Monitor started: {result['monitor_id']}")

        # Wait for running
        print("⏳ Waiting for monitor to be READY...")
        if api.wait_for_monitor_ready("lunar_ray_510", timeout=15):
            print("  ✓ Monitor is READY")
        else:
            print("  ❌ Monitor failed to initialize")
            return False

        # Validate with MCP JAM SDK (AI + tools need time to respond)
        print("\n🧪 Validating with MCP JAM SDK...")
        if run_javascript_validation(
            "lunar_ray_510",
            "ghost_ray_363",
            "LangGraph (gemini-2.5-pro) - Testing AI with tool support",
            timeout=90,
        ):
            return True
        else:
            return False


def main():
    """Run all E2E tests"""
    print("\n" + "=" * 80)
    print("E2E TEST SUITE: All Agent Types")
    print("=" * 80)
    print("\nTesting agent deployment and validation for all monitor types")
    print("Using Dashboard API for deployment (no UI automation needed)")
    print("=" * 80)

    tests = [
        ("Echo Monitor", run_echo_monitor_test),
        ("Ollama Monitor", run_ollama_monitor_test),
        ("Claude SDK Monitor", run_claude_sdk_monitor_test),
        ("OpenAI SDK Monitor", run_openai_sdk_monitor_test),
        ("LangGraph Monitor", run_langgraph_monitor_test),  # Now using lunar_ray_510 (local)
    ]

    results = {}
    for name, test_func in tests:
        try:
            passed = test_func()
            results[name] = passed
        except Exception as e:
            print(f"\n💥 ERROR in {name}: {type(e).__name__}: {e}")
            import traceback

            traceback.print_exc()
            results[name] = False

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
