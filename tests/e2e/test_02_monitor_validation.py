#!/usr/bin/env python3
"""
E2E Test 2: Monitor Validation

Test flow for each monitor type:
1. Deploy monitor on target_agent
2. Send message FROM sender_agent TO target_agent with @mention
3. Use wait=true, wait_mode='mentions' to get response
4. Verify target_agent responded

Usage:
    python test_02_monitor_validation.py              # Run all
    python test_02_monitor_validation.py Echo         # Run just Echo
    python test_02_monitor_validation.py --list       # List available
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.e2e.helpers.dashboard_api import DashboardAPI
from tests.e2e.test_config import MONITOR_TYPES, TEST_AGENTS

# Reuse the validation script
VALIDATION_SCRIPT = Path(__file__).parent / "validate-agent-response.js"


def validate_monitor(config: dict) -> bool:
    """Test a monitor type: deploy, send @mention, verify response"""
    print(f"\n{'=' * 80}")
    print(f"TEST: {config['name']}")
    print(f"  Monitor on: {config['target_agent']}")
    print(f"  Message from: {config['sender_agent']}")
    if config["model"]:
        print(f"  Model: {config['model']}")
    print(f"  Timeout: {config['timeout']}s")
    print("=" * 80)

    target = config["target_agent"]
    sender = config["sender_agent"]
    target_config = TEST_AGENTS[target]

    with DashboardAPI() as api:
        try:
            # 1. Clean slate
            print("📦 Cleanup...")
            api.cleanup_all()

            # 2. Deploy monitor on target_agent
            print(f"🚀 Deploying {config['monitor_type']} on {target}...")
            result = api.start_monitor(
                agent_name=target,
                config_path=target_config["config_path"],
                monitor_type=config["monitor_type"],
                provider=config["provider"],
                model=config["model"],
            )
            print(f"  ✓ Monitor started: {result['monitor_id'][:16]}...")

            # 3. Wait for RUNNING
            print("⏳ Waiting for RUNNING status...")
            if not api.wait_for_monitor_running(target, timeout=10):
                print("  ❌ Monitor failed to reach RUNNING")
                return False
            print("  ✓ Monitor is RUNNING")

            # 4. Send message FROM sender TO target with @mention + wait for response
            print(f"💬 Sending @mention from {sender} → {target}...")
            print(f"   Using wait=true, wait_mode='mentions' (timeout={config['timeout']}s)")

            import subprocess

            result = subprocess.run(
                [
                    "node",
                    str(VALIDATION_SCRIPT),
                    target,
                    sender,
                    f"Test 2: Validating {config['name']}",
                    str(config["timeout"]),
                ],
                capture_output=True,
                text=True,
                timeout=config["timeout"] + 20,
            )

            # Print validation output
            if result.stdout:
                for line in result.stdout.split("\n"):
                    if line.strip():
                        print(f"   {line}")
            if result.stderr and "Shutting down" not in result.stderr:
                stderr_lines = [
                    line
                    for line in result.stderr.split("\n")
                    if line
                    and not any(
                        x in line for x in ["[", "Using", "Connected", "Proxy", "Press", "Shutting"]
                    )
                ]
                if stderr_lines:
                    for line in stderr_lines:
                        print(f"   {line}")

            if result.returncode == 0:
                print(f"\n✅ {config['name']} PASSED")
                return True
            else:
                print(f"\n❌ {config['name']} FAILED")
                return False

        except subprocess.TimeoutExpired:
            print(f"\n❌ {config['name']} TIMEOUT")
            return False
        except Exception as e:
            print(f"\n❌ {config['name']} ERROR: {e}")
            import traceback

            traceback.print_exc()
            return False


def main():
    """Run monitor validation tests"""
    parser = argparse.ArgumentParser(
        description="E2E Test 2: Monitor validation with @mention responses",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    Run all monitor validation tests
  %(prog)s Echo               Test only Echo monitor
  %(prog)s Echo Ollama        Test Echo and Ollama
  %(prog)s --list             List available monitor types

Available Monitor Types:
"""
        + "\n".join(f"  {c['name']:15} - {c['description']}" for c in MONITOR_TYPES),
    )

    parser.add_argument("monitor_types", nargs="*", help="Monitor types to test")
    parser.add_argument("--list", action="store_true", help="List and exit")

    args = parser.parse_args()

    # Handle --list
    if args.list:
        print("\nAvailable Monitor Types:")
        print("=" * 80)
        for c in MONITOR_TYPES:
            print(f"\n{c['name']}")
            print(f"  Type:   {c['monitor_type']}")
            print(f"  Target: {c['target_agent']}")
            print(f"  Sender: {c['sender_agent']}")
            if c["model"]:
                print(f"  Model:  {c['model']}")
            print(f"  Desc:   {c['description']}")
        print("\n" + "=" * 80)
        return 0

    # Filter tests
    if args.monitor_types:
        names = set(args.monitor_types)
        available = {c["name"] for c in MONITOR_TYPES}
        invalid = names - available
        if invalid:
            print(f"\n❌ Invalid: {', '.join(invalid)}")
            print(f"\nAvailable: {', '.join(sorted(available))}")
            return 1
        tests = [c for c in MONITOR_TYPES if c["name"] in names]
    else:
        tests = MONITOR_TYPES

    # Run tests
    print("\n" + "=" * 80)
    print("TEST 2: Monitor Validation (Deploy + @Mention + Response)")
    print("=" * 80)
    print(f"\nTesting {len(tests)} monitor type(s)")
    print("=" * 80)

    results = {}
    for config in tests:
        results[config["name"]] = validate_monitor(config)

    # Cleanup
    print("\n" + "=" * 80)
    print("🧹 Cleanup")
    print("=" * 80)
    with DashboardAPI() as api:
        api.cleanup_all()
        print("✓ Cleaned up")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    for name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {status}: {name}")

    passed = sum(1 for p in results.values() if p)
    total = len(results)
    print(f"\n{passed}/{total} tests passed")
    print("=" * 80 + "\n")

    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
