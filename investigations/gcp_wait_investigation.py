#!/usr/bin/env python3
"""
Test GCP Production Server: Wait Connection + Heartbeat Investigation

This test investigates:
1. How long can we keep wait=true open with concurrent heartbeat pings?
2. Does the heartbeat keep us connected to the same Cloud Run instance?
3. What happens when wait times out vs when heartbeat fails?
4. Can we detect connection drops before wait fails?

Usage:
    PYTHONPATH=src uv run python tests/test_gcp_wait_heartbeat.py <agent_name> [duration_minutes]

Examples:
    PYTHONPATH=src uv run python tests/test_gcp_wait_heartbeat.py agile_cipher_956 5
    PYTHONPATH=src uv run python tests/test_gcp_wait_heartbeat.py logic_keeper_930 10
"""

import asyncio
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from mcp import ClientSession
from ax_agent_studio.mcp_manager import MCPServerManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class ConnectionTracker:
    """Track connection statistics and health"""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.start_time = datetime.now()
        self.ping_count = 0
        self.ping_failures = 0
        self.wait_iterations = 0
        self.wait_timeouts = 0
        self.messages_received = 0
        self.last_ping_time: Optional[datetime] = None
        self.last_wait_time: Optional[datetime] = None
        self.connection_drops = 0

    def record_ping_success(self, timestamp: str):
        """Record a successful ping"""
        self.ping_count += 1
        self.last_ping_time = datetime.now()

    def record_ping_failure(self, error: str):
        """Record a ping failure"""
        self.ping_failures += 1
        self.connection_drops += 1
        logger.error(f" PING FAILURE #{self.ping_failures}: {error}")

    def record_wait_iteration(self):
        """Record a wait iteration (blocking call started)"""
        self.wait_iterations += 1
        self.last_wait_time = datetime.now()

    def record_wait_timeout(self):
        """Record a wait timeout"""
        self.wait_timeouts += 1

    def record_message(self):
        """Record a message received"""
        self.messages_received += 1

    def get_uptime(self) -> timedelta:
        """Get total uptime"""
        return datetime.now() - self.start_time

    def print_stats(self):
        """Print current statistics"""
        uptime = self.get_uptime()
        logger.info("=" * 80)
        logger.info(f" CONNECTION STATISTICS - @{self.agent_name}")
        logger.info(f"   Uptime: {uptime}")
        logger.info(f"   Pings: {self.ping_count} successful, {self.ping_failures} failed")
        logger.info(f"   Wait iterations: {self.wait_iterations}")
        logger.info(f"   Wait timeouts: {self.wait_timeouts}")
        logger.info(f"   Messages received: {self.messages_received}")
        logger.info(f"   Connection drops detected: {self.connection_drops}")
        logger.info(f"   Last ping: {self.last_ping_time.strftime('%H:%M:%S') if self.last_ping_time else 'N/A'}")
        logger.info(f"   Last wait: {self.last_wait_time.strftime('%H:%M:%S') if self.last_wait_time else 'N/A'}")
        logger.info("=" * 80)


async def heartbeat_task(
    session: ClientSession,
    tracker: ConnectionTracker,
    interval: int = 30,
    stop_event: asyncio.Event = None
):
    """
    Send periodic pings to check connection health.

    Args:
        session: MCP ClientSession
        tracker: ConnectionTracker instance
        interval: Seconds between pings
        stop_event: Event to signal task should stop
    """
    logger.info(f" Heartbeat task started (interval: {interval}s)")

    while not (stop_event and stop_event.is_set()):
        try:
            await asyncio.sleep(interval)

            ping_start = datetime.now()
            result = await session.send_ping()
            ping_duration = (datetime.now() - ping_start).total_seconds()

            tracker.record_ping_success(result.timestamp)

            logger.info(
                f" PING #{tracker.ping_count}: {result.status} "
                f"(took {ping_duration:.2f}s, server time: {result.timestamp})"
            )

        except asyncio.CancelledError:
            logger.info(" Heartbeat task cancelled")
            break
        except Exception as e:
            tracker.record_ping_failure(str(e))
            logger.error(f"   Error type: {type(e).__name__}")
            logger.error(f"   Connection likely lost - test should fail")
            # Don't raise - let wait task detect it too
            await asyncio.sleep(5)  # Brief pause before retry


async def wait_task(
    session: ClientSession,
    tracker: ConnectionTracker,
    agent_name: str,
    wait_timeout: int = 300,
    stop_event: asyncio.Event = None
):
    """
    Monitor messages with wait=true blocking calls.

    Args:
        session: MCP ClientSession
        tracker: ConnectionTracker instance
        agent_name: Agent name to filter messages
        wait_timeout: Timeout for each wait call (seconds)
        stop_event: Event to signal task should stop
    """
    logger.info(f" Wait task started (timeout: {wait_timeout}s per call)")

    while not (stop_event and stop_event.is_set()):
        try:
            tracker.record_wait_iteration()
            wait_start = datetime.now()

            logger.info(f" WAIT #{tracker.wait_iterations}: Blocking with wait=true (timeout={wait_timeout}s)...")

            result = await session.call_tool("messages", {
                "action": "check",
                "filter_agent": agent_name,
                "wait": True,
                "timeout": wait_timeout,
                "mark_read": False,
                "limit": 1
            })

            wait_duration = (datetime.now() - wait_start).total_seconds()

            # Check if we got a message or timeout
            content_str = str(result.content) if result.content else ""

            if "No mentions" in content_str or "WAIT SUCCESS: Found 0" in content_str:
                tracker.record_wait_timeout()
                logger.info(
                    f"⏰ WAIT TIMEOUT #{tracker.wait_iterations}: "
                    f"No messages after {wait_duration:.1f}s"
                )
            else:
                tracker.record_message()
                logger.info(
                    f" MESSAGE RECEIVED #{tracker.messages_received}: "
                    f"After {wait_duration:.1f}s"
                )
                logger.info(f"   Content preview: {content_str[:200]}")

        except asyncio.CancelledError:
            logger.info(" Wait task cancelled")
            break
        except Exception as e:
            logger.error(f" WAIT ERROR: {type(e).__name__}: {e}")
            logger.error(f"   Connection likely lost")
            # Brief pause before retry
            await asyncio.sleep(5)


async def stats_reporter(
    tracker: ConnectionTracker,
    interval: int = 60,
    stop_event: asyncio.Event = None
):
    """
    Periodically report statistics.

    Args:
        tracker: ConnectionTracker instance
        interval: Seconds between reports
        stop_event: Event to signal task should stop
    """
    logger.info(f" Stats reporter started (interval: {interval}s)")

    while not (stop_event and stop_event.is_set()):
        await asyncio.sleep(interval)
        tracker.print_stats()


async def run_test(agent_name: str, duration_minutes: int = 5):
    """
    Run the wait + heartbeat test.

    Args:
        agent_name: Agent to test with (must have config in configs/agents/)
        duration_minutes: How long to run the test (default: 5 minutes)
    """
    logger.info("=" * 80)
    logger.info(f" STARTING GCP WAIT + HEARTBEAT TEST")
    logger.info(f"   Agent: @{agent_name}")
    logger.info(f"   Duration: {duration_minutes} minutes")
    logger.info(f"   Server: Production GCP (mcp.paxai.app)")
    logger.info("=" * 80)

    tracker = ConnectionTracker(agent_name)
    stop_event = asyncio.Event()

    try:
        async with MCPServerManager(agent_name) as mcp_manager:
            logger.info(f" Connected to MCP server(s)")

            # Get the ax-gcp session (production server)
            session = mcp_manager.get_session("ax-gcp")
            if not session:
                logger.error(" No ax-gcp session found - check agent config")
                return

            logger.info(f" Using ax-gcp session for @{agent_name}")
            logger.info("")
            logger.info(" Starting concurrent tasks:")
            logger.info("   1. Heartbeat: Ping every 30s")
            logger.info("   2. Wait: Block for messages (5 minute timeout)")
            logger.info("   3. Stats: Report every 60s")
            logger.info("")

            # Set up test duration timeout
            async def duration_limiter():
                """Stop test after specified duration"""
                await asyncio.sleep(duration_minutes * 60)
                logger.info(f"⏰ Test duration reached ({duration_minutes} minutes)")
                stop_event.set()

            # Run all tasks concurrently
            tasks = [
                heartbeat_task(session, tracker, interval=30, stop_event=stop_event),
                wait_task(session, tracker, agent_name, wait_timeout=300, stop_event=stop_event),
                stats_reporter(tracker, interval=60, stop_event=stop_event),
                duration_limiter()
            ]

            await asyncio.gather(*tasks, return_exceptions=True)

    except KeyboardInterrupt:
        logger.info("")
        logger.info(" Test stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f" Fatal error: {type(e).__name__}: {e}")
    finally:
        logger.info("")
        logger.info(" FINAL STATISTICS:")
        tracker.print_stats()
        logger.info("")

        # Analysis
        logger.info(" ANALYSIS:")

        if tracker.ping_failures > 0:
            logger.warning(f"   ️  {tracker.ping_failures} ping failures detected - connection unstable")
        else:
            logger.info(f"    All {tracker.ping_count} pings successful - connection stable")

        if tracker.wait_timeouts > 0:
            logger.info(f"   ⏰ {tracker.wait_timeouts} wait timeouts (no messages received)")

        if tracker.messages_received > 0:
            logger.info(f"    {tracker.messages_received} messages received during test")

        uptime = tracker.get_uptime()
        if uptime.total_seconds() >= (duration_minutes * 60 * 0.9):
            logger.info(f"    Test completed full duration ({uptime})")
        else:
            logger.warning(f"   ️  Test ended early (uptime: {uptime} / {duration_minutes}m)")

        logger.info("")
        logger.info(" KEY FINDINGS:")
        logger.info(f"   • Connection uptime: {uptime}")
        logger.info(f"   • Heartbeat reliability: {tracker.ping_count - tracker.ping_failures}/{tracker.ping_count}")
        logger.info(f"   • Wait call success rate: {tracker.wait_iterations - tracker.wait_timeouts}/{tracker.wait_iterations}")

        if tracker.ping_failures == 0 and tracker.wait_iterations > 0:
            logger.info("   •  Heartbeat appears to keep connection alive!")
        elif tracker.ping_failures > 0:
            logger.warning("   • ️  Connection dropped despite heartbeat - investigate further")

        logger.info("")


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python test_gcp_wait_heartbeat.py <agent_name> [duration_minutes]")
        print("")
        print("Available GCP agents:")
        agents_dir = Path(__file__).parent.parent / "configs" / "agents"
        for config_file in sorted(agents_dir.glob("*.json")):
            if config_file.stem.startswith("_"):
                continue
            # Check if it has ax-gcp server
            import json
            with open(config_file) as f:
                data = json.load(f)
                if "ax-gcp" in data.get("mcpServers", {}):
                    print(f"  • {config_file.stem}")
        print("")
        print("Examples:")
        print("  PYTHONPATH=src uv run python tests/test_gcp_wait_heartbeat.py agile_cipher_956 5")
        print("  PYTHONPATH=src uv run python tests/test_gcp_wait_heartbeat.py logic_keeper_930 10")
        sys.exit(1)

    agent_name = sys.argv[1]
    duration_minutes = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    asyncio.run(run_test(agent_name, duration_minutes))


if __name__ == "__main__":
    main()
