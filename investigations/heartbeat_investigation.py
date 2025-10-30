#!/usr/bin/env python3
"""
Test MCP Heartbeat/Ping Mechanism

This script demonstrates how to use the MCP session.send_ping() method
to detect connection health and handle disconnections.
"""

import asyncio
import logging
from mcp import StdioServerParameters, ClientSession
from mcp.client.stdio import stdio_client

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def heartbeat_monitor(session: ClientSession, interval: int = 30):
    """
    Monitor connection health with periodic pings.

    Args:
        session: MCP ClientSession
        interval: Seconds between heartbeat checks (default: 30)

    Raises:
        Exception: When ping fails, indicating connection lost
    """
    logger.info(f"💓 Heartbeat monitor started (interval: {interval}s)")

    while True:
        try:
            await asyncio.sleep(interval)

            logger.info("💓 Sending heartbeat ping...")
            result = await session.send_ping()

            logger.info(f"✅ Heartbeat OK - {result.status} at {result.timestamp}")

        except Exception as e:
            logger.error(f"❌ Heartbeat FAILED: {e}")
            logger.error("🔌 Connection lost - monitor should reconnect")
            raise


async def test_with_heartbeat():
    """
    Test monitor with heartbeat detection.
    Simulates a monitor that uses wait=true for messages while
    concurrently checking connection health with pings.
    """
    agent_name = "orion_344"

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
                logger.info(f"🔌 Connected to MCP server for @{agent_name}")

                # Run heartbeat and message polling concurrently
                async def message_poller():
                    """Simulate the message polling task (wait=true)"""
                    logger.info("📥 Message poller started")

                    while True:
                        try:
                            logger.info("📥 Waiting for messages (wait=true)...")

                            # This blocks until a message arrives or timeout
                            result = await session.call_tool("messages", {
                                "action": "check",
                                "wait": True,
                                "timeout": 60,  # 60 second timeout for testing
                            })

                            logger.info(f"📨 Received: {result.content}")

                        except Exception as e:
                            logger.error(f"❌ Poller error: {e}")
                            raise

                # Run both tasks concurrently
                # If heartbeat fails, it will cancel the message poller
                await asyncio.gather(
                    heartbeat_monitor(session, interval=15),  # Ping every 15 seconds
                    message_poller()
                )

    except KeyboardInterrupt:
        logger.info("🛑 Stopped by user")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        logger.info("🔄 Monitor should reconnect here...")


async def quick_ping_test():
    """Quick test to verify ping works"""
    agent_name = "orion_344"

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
            print("✅ Connected to MCP server")

            # Send 3 pings
            for i in range(3):
                result = await session.send_ping()
                print(f"💓 Ping {i+1}: {result.status} at {result.timestamp}")
                await asyncio.sleep(2)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "quick":
        print("🔧 Running quick ping test...")
        asyncio.run(quick_ping_test())
    else:
        print("🔧 Running full heartbeat monitor test...")
        print("📝 This will ping every 15s while waiting for messages")
        print("💡 Send a test message to @orion_344 to see both tasks working")
        asyncio.run(test_with_heartbeat())
