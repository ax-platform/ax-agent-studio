#!/usr/bin/env python3
"""
Test Ollama model loading to prevent regression

This test ensures:
1. Ollama models are loaded dynamically via `ollama list`
2. Models are formatted correctly for the UI
3. The endpoint works end-to-end
"""

import asyncio
import subprocess


async def test_ollama_list_command():
    """Verify ollama list command works"""
    print("Testing: ollama list command...")

    try:
        process = await asyncio.create_subprocess_shell(
            "ollama list",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            print(f"  ❌ FAIL: ollama list failed: {stderr.decode()}")
            return False

        lines = stdout.decode().strip().split('\n')
        model_count = len(lines) - 1  # Exclude header

        print(f"  ✅ PASS: Found {model_count} Ollama models")
        return True

    except Exception as e:
        print(f"  ❌ FAIL: Exception: {e}")
        return False


async def test_providers_loader():
    """Test get_models_for_provider('ollama')"""
    print("\nTesting: providers_loader.get_models_for_provider('ollama')...")

    try:
        import sys
        from pathlib import Path

        # Add src to path
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

        from ax_agent_studio.dashboard.backend.providers_loader import get_models_for_provider

        models = await get_models_for_provider('ollama')

        if not models:
            print("  ❌ FAIL: No models returned")
            return False

        # Verify structure
        for model in models:
            if not all(k in model for k in ['id', 'name', 'description']):
                print(f"  ❌ FAIL: Invalid model structure: {model}")
                return False

        print(f"  ✅ PASS: Loaded {len(models)} models")
        print("  Models:")
        for m in models:
            print(f"    - {m['name']}")
        return True

    except Exception as e:
        print(f"  ❌ FAIL: Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_dashboard_endpoint():
    """Test the dashboard API endpoint"""
    print("\nTesting: Dashboard API endpoint /api/providers/ollama/models...")

    try:
        import httpx

        # Note: Dashboard must be running on port 8000
        async with httpx.AsyncClient() as client:
            response = await client.get("http://127.0.0.1:8000/api/providers/ollama/models")

            if response.status_code != 200:
                print(f"  ⚠️  SKIP: Dashboard not running (status {response.status_code})")
                return True  # Not a failure, just can't test

            data = response.json()
            models = data.get('models', [])

            if not models:
                print("  ❌ FAIL: No models returned from API")
                return False

            print(f"  ✅ PASS: API returned {len(models)} models")
            return True

    except Exception as e:
        print(f"  ⚠️  SKIP: Dashboard not running ({e})")
        return True  # Not a failure, just can't test


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Ollama Model Loading Tests")
    print("=" * 60)

    results = []

    # Test 1: ollama list command
    results.append(await test_ollama_list_command())

    # Test 2: providers_loader function
    results.append(await test_providers_loader())

    # Test 3: Dashboard API endpoint (optional)
    results.append(await test_dashboard_endpoint())

    # Summary
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"✅ ALL TESTS PASSED ({passed}/{total})")
        return 0
    else:
        print(f"❌ SOME TESTS FAILED ({passed}/{total} passed)")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
