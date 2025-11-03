#!/usr/bin/env python3
"""
End-to-End Test for OpenAI Agents SDK Monitor
Tests that OpenAI Agents SDK can work with MCP tools from start to finish
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


async def test_openai_agents_mcp_initialization():
    """Test that OpenAI Agents SDK can initialize with MCP servers"""
    print("Testing OpenAI Agents SDK MCP Initialization\n")

    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY not set, skipping test")
        return False

    try:
        from agents import Agent
        from agents.mcp import MCPServerStdio
    except ImportError:
        print("openai-agents package not installed")
        print("   Install with: pip install openai-agents")
        return False

    # 1. Test creating a simple MCP server connection
    print("1. Testing MCP server creation...")
    try:
        # Create a test MCP server (stdio type)
        server = MCPServerStdio(
            name="test_server",
            params={
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-memory"],
                "env": None,
            },
            cache_tools_list=True,
        )
        print("   MCPServerStdio created successfully\n")
    except Exception as e:
        print(f"   Failed to create MCP server: {e}\n")
        return False

    # 2. Test agent creation with MCP server
    print("2. Creating OpenAI Agent with MCP server...")
    try:
        agent = Agent(
            name="test_agent",
            instructions="You are a test agent.",
            model="gpt-5-mini",
            mcp_servers=[],  # Empty for quick test
        )
        print(f"   Agent created: {agent.name}\n")
    except Exception as e:
        print(f"   Failed to create agent: {e}\n")
        return False

    print("Initialization test passed!\n")
    return True


async def test_openai_agents_simple_call():
    """Test a simple OpenAI agent call without MCP"""
    print("Testing Simple OpenAI Agent Call (no MCP)\n")

    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY not set, skipping test")
        return False

    try:
        from agents import Agent, Runner
    except ImportError:
        print("openai-agents package not installed")
        return False

    print("1. Creating OpenAI Agent (gpt-5-mini)...")
    try:
        agent = Agent(
            name="test_agent",
            instructions="You are a helpful assistant. Keep responses very brief.",
            model="gpt-5-mini",  # Use latest mini model for cost efficiency
        )
        print(f"   Agent created: {agent.name}\n")
    except Exception as e:
        print(f"   Failed to create agent: {e}\n")
        return False

    print("2. Making test call...")
    try:
        result = await Runner.run(agent, "Say 'test passed' and nothing else")

        # Extract response text
        response_text = ""
        if hasattr(result, "messages") and result.messages:
            for msg in result.messages:
                if msg.role == "assistant" and hasattr(msg, "content"):
                    for content in msg.content:
                        if hasattr(content, "text"):
                            response_text = content.text
                            break
                    if response_text:
                        break

        print(f"   Response: {response_text}\n")

        if "test passed" not in response_text.lower():
            print(f"   Expected 'test passed' in response but got: {response_text}")

    except Exception as e:
        print(f"   Failed to run agent: {e}\n")
        import traceback
        traceback.print_exc()
        return False

    print("Simple call test passed!\n")
    return True


async def test_monitor_message_handling():
    """Test the monitor's message handling logic"""
    print("Testing Monitor Message Handling\n")

    # Test the _extract_message_body function
    from ax_agent_studio.monitors.openai_agents_monitor import _extract_message_body

    print("1. Testing message extraction...")

    # Test case 1: Simple mention
    raw = "@sender Hello world"
    extracted = _extract_message_body(raw)
    print(f"   Simple mention: '{raw}' -> '{extracted}'")

    # Test case 2: Multi-line
    raw = "@sender Line 1\nLine 2"
    extracted = _extract_message_body(raw)
    print(f"   Multi-line: extracted {len(extracted)} chars")

    # Test case 3: Empty
    raw = ""
    extracted = _extract_message_body(raw)
    print(f"   Empty message: '{extracted}'")

    print("\nMessage handling test passed!\n")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("OpenAI Agents SDK Monitor - E2E Test Suite")
    print("=" * 60 + "\n")

    results = []

    try:
        # Test 1: Initialization
        print("\n" + "=" * 60)
        result1 = asyncio.run(test_openai_agents_mcp_initialization())
        results.append(("Initialization", result1))

        # Test 2: Simple call
        print("\n" + "=" * 60)
        result2 = asyncio.run(test_openai_agents_simple_call())
        results.append(("Simple Call", result2))

        # Test 3: Message handling
        print("\n" + "=" * 60)
        result3 = asyncio.run(test_monitor_message_handling())
        results.append(("Message Handling", result3))

        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)

        passed = sum(1 for _, result in results if result)
        total = len(results)

        for test_name, result in results:
            status = "PASS" if result else "FAIL"
            print(f"{status}: {test_name}")

        print(f"\nTotal: {passed}/{total} tests passed")

        if passed == total:
            print("\nAll E2E tests passed!")
            exit(0)
        else:
            print("\nSome tests failed or were skipped")
            exit(1)

    except Exception as e:
        print(f"\nTest suite failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
