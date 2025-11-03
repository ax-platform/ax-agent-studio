#!/usr/bin/env python3
"""Quick test to send message to lunar_craft_128 via docker"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ax_agent_studio.mcp_manager import MCPServerManager


async def send_test_message():
    """Send test message to lunar_craft_128 via docker environment"""

    base_dir = Path(__file__).parent

    # Connect as orion_344 (which uses ax-docker)
    async with MCPServerManager("orion_344", base_dir=base_dir) as manager:
        session = manager.get_primary_session()

        print("✅ Connected to ax-docker via orion_344")
        print("📤 Sending message to @lunar_craft_128...\n")

        # Send message to lunar_craft_128
        result = await session.call_tool("messages", {
            "action": "send",
            "content": "@lunar_craft_128 Hello! This is a test of the OpenAI Agents SDK integration. Please confirm you received this message and tell me what model you're using.",
            "wait": True,
            "wait_mode": "mentions",
            "timeout": 60
        })

        print("✅ Message sent!")
        print(f"Response: {result.content[0].text if result.content else 'No response'}")


if __name__ == "__main__":
    asyncio.run(send_test_message())
