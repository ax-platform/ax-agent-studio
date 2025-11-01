#!/usr/bin/env python3
"""
End-to-End Monitor Test for Gemini
Sends a test message and verifies the monitor responds
"""

import asyncio
import time
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def send_test_message(agent_name: str, message: str):
    """Send a message to an agent and wait for response"""

    # Connect to ax-gcp MCP server
    server_params = StdioServerParameters(
        command="npx",
        args=[
            "-y", "mcp-remote@0.1.29",
            f"http://localhost:8002/mcp/agents/{agent_name}",
            "--transport", "http-only",
            "--oauth-server", "http://localhost:8001"
        ]
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            print(f" Sending message to @{agent_name}: {message}")

            # Send message
            result = await session.call_tool("messages", {
                "action": "send",
                "content": f"@{agent_name} {message}"
            })

            print(f" Message sent\n")

            # Wait a bit for processing
            print("⏳ Waiting 10 seconds for response...")
            await asyncio.sleep(10)

            # Check for response
            print(" Checking for response...")
            result = await session.call_tool("messages", {
                "action": "check",
                "mode": "latest",
                "limit": 5
            })

            # Parse response
            if hasattr(result, 'content'):
                content = result.content
                if isinstance(content, list) and len(content) > 0:
                    text = str(content[0].text) if hasattr(content[0], 'text') else str(content[0])
                    print(f" Recent messages:\n{text}\n")

                    # Check if agent responded
                    if agent_name.lower() in text.lower():
                        print(" Agent response detected!")
                        return True
                    else:
                        print("️  No response from agent yet")
                        return False

            return False


async def test_gemini_monitor():
    """Test the Gemini monitor end-to-end"""
    print("=" * 60)
    print("Gemini Monitor End-to-End Test")
    print("=" * 60 + "\n")

    print("️  Make sure the Gemini monitor is running!")
    print("   Start it with:")
    print("   PYTHONPATH=src uv run python -m ax_agent_studio.monitors.langgraph_monitor orion_344 \\")
    print("     --config configs/agents/orion_344.json --model gemini-2.0-flash-exp --provider gemini\n")

    input("Press Enter when monitor is running...")

    # Send test message
    agent = "orion_344"
    message = "Quick test: What is 2+2? Just answer with the number."

    success = await send_test_message(agent, message)

    if success:
        print("\n End-to-end test PASSED!")
    else:
        print("\n No response detected. Check monitor logs.")
        print("   Log file should be in ./logs/")


if __name__ == "__main__":
    try:
        asyncio.run(test_gemini_monitor())
    except KeyboardInterrupt:
        print("\n\nTest cancelled")
    except Exception as e:
        print(f"\n Test failed: {e}")
        import traceback
        traceback.print_exc()
