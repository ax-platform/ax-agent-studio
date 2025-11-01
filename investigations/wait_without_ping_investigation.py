#!/usr/bin/env python3
"""
Test: What happens to wait=true WITHOUT heartbeat pings?

This test compares:
1. Wait WITH pings (control group) - should stay connected
2. Wait WITHOUT pings (test group) - does it disconnect?

This will help us understand if pings are keeping the connection alive
or if the disconnect is caused by something else (Cloud Run timeout, etc).

Usage:
    PYTHONPATH=src uv run python tests/test_wait_without_ping.py <agent_name>
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from ax_agent_studio.mcp_manager import MCPServerManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


async def test_with_pings(agent_name: str, duration_seconds: int = 300):
    """
    Test wait=true WITH concurrent pings.

    This is the control group - pings should keep connection alive.
    """
    logger.info("=" * 80)
    logger.info(" TEST 1: WAIT WITH PINGS (Control Group)")
    logger.info(f"   Duration: {duration_seconds}s")
    logger.info("=" * 80)

    start_time = datetime.now()
    ping_count = 0

    try:
        async with MCPServerManager(agent_name) as mcp_manager:
            session = mcp_manager.get_session("ax-gcp")
            if not session:
                logger.error(" No ax-gcp session found")
                return

            logger.info(" Connected to MCP server")

            # Ping task
            async def pinger():
                nonlocal ping_count
                while True:
                    await asyncio.sleep(30)
                    try:
                        result = await session.send_ping()
                        ping_count += 1
                        logger.info(f" PING #{ping_count}: {result.status}")
                    except Exception as e:
                        logger.error(f" PING FAILED: {e}")
                        raise

            # Wait task
            async def waiter():
                logger.info(f" Starting wait (timeout={duration_seconds}s)...")
                wait_start = datetime.now()

                try:
                    result = await session.call_tool("messages", {
                        "action": "check",
                        "filter_agent": agent_name,
                        "wait": True,
                        "timeout": duration_seconds,
                        "mark_read": False
                    })

                    wait_duration = (datetime.now() - wait_start).total_seconds()
                    logger.info(f" Wait returned after {wait_duration:.1f}s")
                    logger.info(f"   Result: {str(result.content)[:100]}")

                except Exception as e:
                    logger.error(f" WAIT FAILED: {e}")
                    raise

            # Run both tasks with timeout
            try:
                await asyncio.wait_for(
                    asyncio.gather(pinger(), waiter()),
                    timeout=duration_seconds + 10
                )
            except asyncio.TimeoutError:
                logger.info("⏰ Test timeout reached")

    except Exception as e:
        logger.error(f" Test failed: {e}")
    finally:
        uptime = (datetime.now() - start_time).total_seconds()
        logger.info(f"\n RESULTS:")
        logger.info(f"   Uptime: {uptime:.1f}s")
        logger.info(f"   Pings sent: {ping_count}")
        logger.info(f"   Test: {' PASSED' if uptime >= duration_seconds * 0.9 else ' FAILED'}")


async def test_without_pings(agent_name: str, duration_seconds: int = 300):
    """
    Test wait=true WITHOUT pings.

    This is the test group - will it disconnect?
    """
    logger.info("\n" + "=" * 80)
    logger.info(" TEST 2: WAIT WITHOUT PINGS (Test Group)")
    logger.info(f"   Duration: {duration_seconds}s")
    logger.info("   ️  NO PINGS - Will connection survive?")
    logger.info("=" * 80)

    start_time = datetime.now()

    try:
        async with MCPServerManager(agent_name) as mcp_manager:
            session = mcp_manager.get_session("ax-gcp")
            if not session:
                logger.error(" No ax-gcp session found")
                return

            logger.info(" Connected to MCP server")
            logger.info(f" Starting wait (timeout={duration_seconds}s)...")
            logger.info("   ⏳ No pings will be sent - pure wait test")

            wait_start = datetime.now()

            try:
                result = await session.call_tool("messages", {
                    "action": "check",
                    "filter_agent": agent_name,
                    "wait": True,
                    "timeout": duration_seconds,
                    "mark_read": False
                })

                wait_duration = (datetime.now() - wait_start).total_seconds()
                logger.info(f" Wait returned after {wait_duration:.1f}s")
                logger.info(f"   Result: {str(result.content)[:100]}")

            except Exception as e:
                wait_duration = (datetime.now() - wait_start).total_seconds()
                logger.error(f" WAIT FAILED after {wait_duration:.1f}s: {e}")
                raise

    except Exception as e:
        logger.error(f" Test failed: {e}")
    finally:
        uptime = (datetime.now() - start_time).total_seconds()
        logger.info(f"\n RESULTS:")
        logger.info(f"   Uptime: {uptime:.1f}s")
        logger.info(f"   Expected: {duration_seconds}s")
        logger.info(f"   Test: {' PASSED' if uptime >= duration_seconds * 0.9 else ' FAILED'}")

        if uptime < duration_seconds * 0.5:
            logger.warning(f"   ️  CONNECTION DROPPED EARLY!")
            logger.warning(f"   This suggests wait=true needs pings to stay alive")


async def run_comparison(agent_name: str):
    """Run both tests back-to-back for comparison"""
    logger.info("\n" + "=" * 80)
    logger.info(" PING VS NO-PING COMPARISON TEST")
    logger.info(f"   Agent: @{agent_name}")
    logger.info(f"   Server: Production GCP")
    logger.info("=" * 80)

    # Test 1: With pings (should work)
    await test_with_pings(agent_name, duration_seconds=180)  # 3 minutes

    await asyncio.sleep(5)  # Brief pause between tests

    # Test 2: Without pings (might fail)
    await test_without_pings(agent_name, duration_seconds=180)  # 3 minutes

    logger.info("\n" + "=" * 80)
    logger.info(" CONCLUSION:")
    logger.info("   If Test 1 (with pings) succeeds and Test 2 (no pings) fails,")
    logger.info("   then pings are REQUIRED to keep the connection alive!")
    logger.info("=" * 80)


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_wait_without_ping.py <agent_name>")
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
        print("  PYTHONPATH=src uv run python tests/test_wait_without_ping.py agile_cipher_956")
        sys.exit(1)

    agent_name = sys.argv[1]
    asyncio.run(run_comparison(agent_name))


if __name__ == "__main__":
    main()
