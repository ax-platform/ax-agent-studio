#!/usr/bin/env python3
"""
End-to-end test script for multi-provider support
Tests each provider with LLMFactory to ensure they work before UI integration
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ax_agent_studio.llm_factory import create_llm


async def test_provider(provider: str, model: str):
    """Test a single provider"""
    print(f"\n{'='*60}")
    print(f"Testing: {provider} / {model}")
    print(f"{'='*60}")

    try:
        # Create LLM
        print(f"Creating LLM...")
        llm = create_llm(provider=provider, model=model)
        print(f" LLM created successfully")

        # Simple test message
        print(f"Sending test message...")
        from langchain_core.messages import HumanMessage
        messages = [HumanMessage(content="Say 'Hello from {provider}!' in exactly those words.")]

        response = llm.invoke(messages)
        print(f" Response received:")
        print(f"   {response.content[:200]}...")

        return True

    except Exception as e:
        print(f" Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run tests for all configured providers"""
    print("\n" + "="*60)
    print(" Multi-Provider End-to-End Test Suite")
    print("="*60)

    tests = [
        # Gemini (fastest to test)
        ("gemini", "gemini-2.5-flash"),

        # Bedrock (if AWS credentials configured)
        ("bedrock", "us.anthropic.claude-haiku-4-5-20251001-v1:0"),

        # Ollama (local fallback)
        ("ollama", "gpt-oss:latest"),
    ]

    results = {}

    for provider, model in tests:
        success = await test_provider(provider, model)
        results[f"{provider}/{model}"] = success

        # Small delay between tests
        await asyncio.sleep(1)

    # Summary
    print("\n" + "="*60)
    print(" Test Results Summary")
    print("="*60)

    for test_name, success in results.items():
        status = " PASS" if success else " FAIL"
        print(f"{status}: {test_name}")

    all_passed = all(results.values())

    if all_passed:
        print("\n All tests passed! Multi-provider support is working!")
        return 0
    else:
        print("\n️  Some tests failed. Check errors above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
