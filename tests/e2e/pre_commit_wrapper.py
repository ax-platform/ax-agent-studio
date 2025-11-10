#!/usr/bin/env python3
"""
Pre-commit wrapper for E2E tests

Checks prerequisites and skips gracefully if not met.
Allows main developers to run E2E tests on every commit,
while not blocking external contributors.
"""

import os
import sys
from pathlib import Path

import httpx

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load .env file if it exists
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def check_prerequisites():
    """Check if E2E test environment is ready"""
    issues = []

    # Check if dashboard backend is running
    try:
        response = httpx.get("http://127.0.0.1:8000/api/monitors", timeout=1.0)
        if response.status_code != 200:
            issues.append("Dashboard backend not responding correctly (port 8000)")
    except (httpx.ConnectError, httpx.TimeoutException):
        issues.append("Dashboard backend not running (port 8000)")

    # Check for required API keys (at least one AI provider needed)
    has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))
    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    has_gemini = bool(os.getenv("GEMINI_API_KEY"))

    if not (has_anthropic or has_openai or has_gemini):
        issues.append(
            "No AI provider API keys found (need at least one: ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY)"
        )

    return issues


def main():
    """Run E2E tests if environment is ready, skip gracefully otherwise"""
    print("\n" + "=" * 80)
    print("E2E Test Pre-commit Hook")
    print("=" * 80)

    # Check prerequisites
    issues = check_prerequisites()

    if issues:
        print("\n⚠️  Skipping E2E tests - Prerequisites not met:")
        for issue in issues:
            print(f"   - {issue}")
        print("\n💡 To enable E2E tests:")
        print(
            "   1. Start dashboard: cd src/ax_agent_studio/dashboard && uv run python -m backend.main"
        )
        print("   2. Set API keys in .env file")
        print("   3. Commit again\n")
        print("✓ Commit allowed (E2E tests skipped)")
        print("=" * 80)
        return 0

    # Prerequisites met, run tests
    print("\n✓ Prerequisites met, running E2E tests...")
    print("=" * 80)

    # Import and run test
    try:
        from tests.e2e.test_all_agent_types import main as run_tests

        exit_code = run_tests()
        if exit_code == 0:
            print("\n✅ E2E tests passed")
        else:
            print("\n❌ E2E tests failed")
        return exit_code
    except Exception as e:
        print(f"\n❌ Error running E2E tests: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
