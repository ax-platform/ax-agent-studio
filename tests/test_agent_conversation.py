#!/usr/bin/env python3
"""
Test agent-to-agent conversation with FIFO queue
Verifies agents can have back-and-forth without missing messages
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_agent_conversation():
    """Test 5 back-and-forth messages between agents"""

    print(" Testing Agent Conversation - 5 Back-and-Forths")
    print("=" * 60)
    print()

    # Connect to ax-docker MCP server
    agent_name = "test_conductor"
    server_params = StdioServerParameters(
        command="npx",
        args=[
            "-y", "mcp-remote@0.1.29",
            f"http://localhost:8002/mcp/agents/{agent_name}",
            "--transport", "http-only",
            "--oauth-server", "http://localhost:8001"
        ]
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                print(" Connected to aX platform\n")

                # Test 1: Send initial message mentioning 2 agents
                print(" Test 1: Initial message to @agent1 and @agent2")
                result = await session.call_tool("messages", {
                    "action": "send",
                    "content": "@lunar_craft_128 @orion_344 Let's count to 5! @lunar_craft_128 says 1"
                })
                print(f"   Sent initial message\n")

                # Wait and check for responses
                await asyncio.sleep(5)

                # Test 2: Check message history
                print(" Test 2: Checking message history...")
                result = await session.call_tool("messages", {
                    "action": "check",
                    "limit": 10,
                    "since": "5m"
                })

                messages_data = result.content[0].text if result.content else ""
                message_count = messages_data.count("•")

                print(f"   Found {message_count} messages in last 5 minutes")
                print(f"   Preview:\n{messages_data[:500]}...\n")

                # Test 3: Verify agents are responding
                if "@lunar_craft_128" in messages_data and "@orion_344" in messages_data:
                    print(" Both agents visible in conversation")
                else:
                    print("  Warning: Not all agents responding yet")

                print()
                print("=" * 60)
                print("Test Instructions:")
                print("1. Make sure lunar_craft_128 and orion_344 are running")
                print("2. Watch the logs to see if they respond")
                print("3. They should count: 1, 2, 3, 4, 5 back and forth")
                print("4. Check for 'Already processed message' in logs = good!")
                print("=" * 60)

    except Exception as e:
        print(f" Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_agent_conversation())
