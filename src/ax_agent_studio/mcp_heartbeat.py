"""
MCP Connection Heartbeat Utility

This module provides a reusable heartbeat function that keeps MCP connections alive
by sending periodic pings. Use this for ANY MCP session that needs to stay connected
for longer than 5 minutes.

Usage:
    async with ClientSession(read, write) as session:
        # Start heartbeat task
        heartbeat_task = asyncio.create_task(
            keep_alive(session, interval=240, name="my_agent")
        )

        # Your long-running work here...

        # Cleanup
        heartbeat_task.cancel()
"""

import asyncio
import logging
from datetime import datetime
from mcp import ClientSession
from typing import Optional

logger = logging.getLogger(__name__)


async def keep_alive(
    session: ClientSession,
    interval: int = 240,
    name: Optional[str] = None,
    stop_event: Optional[asyncio.Event] = None
) -> None:
    """
    Keep MCP connection alive with periodic pings.

    MCP servers (especially Cloud Run) disconnect after ~5 minutes of inactivity.
    This function sends pings every N seconds to prevent disconnections.

    Args:
        session: MCP ClientSession to keep alive
        interval: Seconds between pings (default: 240 = 4 minutes)
        name: Optional name for logging (e.g., agent name)
        stop_event: Optional event to signal task should stop

    Example:
        async with ClientSession(read, write) as session:
            heartbeat = asyncio.create_task(keep_alive(session, name="agent_123"))
            try:
                # Your work here
                await do_something()
            finally:
                heartbeat.cancel()
    """
    if interval <= 0:
        logger.info(f" Heartbeat disabled (interval=0) for {name or 'session'}")
        return

    ping_count = 0
    ping_failures = 0
    prefix = f"[{name}] " if name else ""

    logger.info(f" {prefix}Heartbeat started (interval: {interval}s)")

    while not (stop_event and stop_event.is_set()):
        try:
            # Wait before next ping
            await asyncio.sleep(interval)

            # Send ping
            ping_start = datetime.now()
            result = await session.send_ping()
            ping_duration = (datetime.now() - ping_start).total_seconds()

            ping_count += 1
            logger.info(
                f" {prefix}PING #{ping_count}: {result.status} "
                f"(took {ping_duration:.2f}s, server time: {result.timestamp})"
            )

        except asyncio.CancelledError:
            logger.info(f" {prefix}Heartbeat cancelled")
            break
        except Exception as e:
            ping_failures += 1
            logger.error(f" {prefix}PING FAILURE #{ping_failures}: {type(e).__name__}: {e}")
            logger.error("   Connection may be lost - consider restarting")
            # Continue trying - don't crash
            await asyncio.sleep(5)  # Brief pause before retry

    # Log final stats
    if ping_count > 0 or ping_failures > 0:
        logger.info(
            f" {prefix}Heartbeat stopped: "
            f"{ping_count} pings sent, {ping_failures} failures"
        )


class HeartbeatManager:
    """
    Manager for tracking multiple heartbeat tasks.

    Use this when you have multiple MCP sessions and want to manage
    their heartbeats together.

    Example:
        manager = HeartbeatManager(interval=240)

        async with stdio_client(...) as (read, write):
            async with ClientSession(read, write) as session:
                await manager.start(session, name="agent_1")
                # Your work here...

        await manager.stop_all()
    """

    def __init__(self, interval: int = 240):
        """
        Initialize heartbeat manager.

        Args:
            interval: Default seconds between pings for all sessions
        """
        self.interval = interval
        self.tasks: dict[str, asyncio.Task] = {}
        logger.info(f" HeartbeatManager initialized (interval: {interval}s)")

    async def start(
        self,
        session: ClientSession,
        name: str,
        interval: Optional[int] = None
    ) -> asyncio.Task:
        """
        Start heartbeat for a session.

        Args:
            session: MCP ClientSession
            name: Unique name for this session
            interval: Optional override for this session

        Returns:
            The heartbeat task
        """
        if name in self.tasks:
            logger.warning(f"  Heartbeat already running for {name}, stopping old one")
            await self.stop(name)

        task = asyncio.create_task(
            keep_alive(session, interval or self.interval, name)
        )
        self.tasks[name] = task
        logger.info(f" Heartbeat started for {name}")
        return task

    async def stop(self, name: str) -> None:
        """Stop heartbeat for a specific session."""
        task = self.tasks.pop(name, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            logger.info(f" Heartbeat stopped for {name}")

    async def stop_all(self) -> None:
        """Stop all heartbeats."""
        for name in list(self.tasks.keys()):
            await self.stop(name)

    def get_stats(self) -> dict[str, int]:
        """Get statistics about active heartbeats."""
        return {
            "active_heartbeats": len(self.tasks),
            "task_names": list(self.tasks.keys())
        }
