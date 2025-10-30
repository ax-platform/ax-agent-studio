#!/usr/bin/env python3
"""
Test MCP Timeout Options - Finding the Right Configuration

This test investigates different timeout strategies:
1. Default timeout (no args) - what's the baseline?
2. Extended timeout (read_timeout_seconds) - does this help?
3. Progress callback - does this reset the timer?
4. Concurrent pings - does this keep connection alive?

Goal: Find the optimal configuration to prevent disconnects during long waits.

Usage:
    PYTHONPATH=src uv run python tests/test_timeout_options.py <agent_name>
"""

import asyncio
import logging
import sys
from datetime import timedelta, datetime
from pathlib import Path
from ax_agent_studio.mcp_manager import MCPServerManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


async def test_default_timeout(agent_name: str):
    """Test 1: Default timeout (no custom timeout specified)"""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 TEST 1: DEFAULT TIMEOUT")
    logger.info("=" * 80)

    async with MCPServerManager(agent_name) as mcp_manager:
        session = mcp_manager.get_session("ax-gcp")

        logger.info("📥 Calling messages tool with default timeout...")
        start = datetime.now()

        try:
            result = await session.call_tool("messages", {
                "action": "check",
                "filter_agent": agent_name,
                "wait": True,
                "timeout": 180,  # Server-side timeout: 3 minutes
                "mark_read": False
            })

            duration = (datetime.now() - start).total_seconds()
            logger.info(f"✅ Completed after {duration:.1f}s")

        except Exception as e:
            duration = (datetime.now() - start).total_seconds()
            logger.error(f"❌ Failed after {duration:.1f}s: {e}")


async def test_extended_timeout(agent_name: str):
    """Test 2: Extended client-side timeout"""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 TEST 2: EXTENDED CLIENT TIMEOUT")
    logger.info("   read_timeout_seconds = 10 minutes")
    logger.info("=" * 80)

    async with MCPServerManager(agent_name) as mcp_manager:
        session = mcp_manager.get_session("ax-gcp")

        logger.info("📥 Calling messages tool with 10-minute client timeout...")
        start = datetime.now()

        try:
            result = await session.call_tool(
                name="messages",
                arguments={
                    "action": "check",
                    "filter_agent": agent_name,
                    "wait": True,
                    "timeout": 180,  # Server-side: 3 minutes
                    "mark_read": False
                },
                read_timeout_seconds=timedelta(minutes=10)  # ← Extended client timeout
            )

            duration = (datetime.now() - start).total_seconds()
            logger.info(f"✅ Completed after {duration:.1f}s")

        except Exception as e:
            duration = (datetime.now() - start).total_seconds()
            logger.error(f"❌ Failed after {duration:.1f}s: {e}")


async def test_progress_callback(agent_name: str):
    """Test 3: Progress callback to reset timeout"""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 TEST 3: PROGRESS CALLBACK")
    logger.info("   Callback should reset timeout on progress updates")
    logger.info("=" * 80)

    async with MCPServerManager(agent_name) as mcp_manager:
        session = mcp_manager.get_session("ax-gcp")

        progress_count = 0

        def progress_callback(progress):
            nonlocal progress_count
            progress_count += 1
            logger.info(f"📊 Progress update #{progress_count}: {progress}")

        logger.info("📥 Calling messages tool with progress callback...")
        start = datetime.now()

        try:
            result = await session.call_tool(
                name="messages",
                arguments={
                    "action": "check",
                    "filter_agent": agent_name,
                    "wait": True,
                    "timeout": 180,
                    "mark_read": False
                },
                progress_callback=progress_callback  # ← Progress callback
            )

            duration = (datetime.now() - start).total_seconds()
            logger.info(f"✅ Completed after {duration:.1f}s")
            logger.info(f"   Progress updates received: {progress_count}")

        except Exception as e:
            duration = (datetime.now() - start).total_seconds()
            logger.error(f"❌ Failed after {duration:.1f}s: {e}")
            logger.info(f"   Progress updates received: {progress_count}")


async def test_concurrent_pings(agent_name: str):
    """Test 4: Concurrent pings to keep connection alive"""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 TEST 4: CONCURRENT PINGS")
    logger.info("   Ping every 30s while wait is blocking")
    logger.info("=" * 80)

    async with MCPServerManager(agent_name) as mcp_manager:
        session = mcp_manager.get_session("ax-gcp")

        ping_count = 0
        stop_pinging = False

        async def pinger():
            nonlocal ping_count
            while not stop_pinging:
                await asyncio.sleep(30)
                if stop_pinging:
                    break
                try:
                    result = await session.send_ping()
                    ping_count += 1
                    logger.info(f"💓 PING #{ping_count}: {result.status}")
                except Exception as e:
                    logger.error(f"❌ Ping failed: {e}")

        async def waiter():
            logger.info("📥 Calling messages tool (3 minute timeout)...")
            start = datetime.now()

            try:
                result = await session.call_tool("messages", {
                    "action": "check",
                    "filter_agent": agent_name,
                    "wait": True,
                    "timeout": 180,
                    "mark_read": False
                })

                duration = (datetime.now() - start).total_seconds()
                logger.info(f"✅ Completed after {duration:.1f}s")

            except Exception as e:
                duration = (datetime.now() - start).total_seconds()
                logger.error(f"❌ Failed after {duration:.1f}s: {e}")

        # Run both tasks
        try:
            await asyncio.gather(pinger(), waiter())
        finally:
            stop_pinging = True
            logger.info(f"   Total pings sent: {ping_count}")


async def run_all_tests(agent_name: str):
    """Run all timeout configuration tests"""
    logger.info("=" * 80)
    logger.info("🔬 MCP TIMEOUT OPTIONS TEST SUITE")
    logger.info(f"   Agent: @{agent_name}")
    logger.info(f"   Server: Production GCP")
    logger.info("=" * 80)
    logger.info("\n💡 Testing different strategies to prevent timeout disconnects:")
    logger.info("   1. Baseline (default timeout)")
    logger.info("   2. Extended client timeout")
    logger.info("   3. Progress callback")
    logger.info("   4. Concurrent pings")

    await test_default_timeout(agent_name)
    await asyncio.sleep(2)

    await test_extended_timeout(agent_name)
    await asyncio.sleep(2)

    await test_progress_callback(agent_name)
    await asyncio.sleep(2)

    await test_concurrent_pings(agent_name)

    logger.info("\n" + "=" * 80)
    logger.info("🎯 RECOMMENDATIONS:")
    logger.info("   Based on the results above:")
    logger.info("   • If all tests passed: Connection is stable!")
    logger.info("   • If only ping test passed: Use concurrent pings in production")
    logger.info("   • If extended timeout helped: Increase read_timeout_seconds")
    logger.info("   • If progress callback helped: Ensure server sends updates")
    logger.info("=" * 80)


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_timeout_options.py <agent_name>")
        print("\nAvailable GCP agents:")
        agents_dir = Path(__file__).parent.parent / "configs" / "agents"
        for config_file in sorted(agents_dir.glob("*.json")):
            if config_file.stem.startswith("_"):
                continue
            import json
            with open(config_file) as f:
                data = json.load(f)
                if "ax-gcp" in data.get("mcpServers", {}):
                    print(f"  • {config_file.stem}")
        print("\nExample:")
        print("  PYTHONPATH=src uv run python tests/test_timeout_options.py agile_cipher_956")
        sys.exit(1)

    agent_name = sys.argv[1]
    asyncio.run(run_all_tests(agent_name))


if __name__ == "__main__":
    main()
