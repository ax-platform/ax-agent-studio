"""
Modular FIFO Queue Manager for MCP Monitors

This module provides a reusable queue abstraction that any monitor can plug into.
It handles the triple-task pattern (poller + processor + heartbeat) and uses SQLite for persistence.

Architecture:
- Poller Task: Continuously receives messages via MCP, stores in SQLite
- Processor Task: Pulls messages from FIFO queue, processes, sends responses
- Heartbeat Task: Keeps MCP connection alive with periodic pings (every 4 minutes)
- All tasks run concurrently via asyncio.gather()

Benefits:
- Zero message loss (SQLite buffer)
- FIFO guaranteed (ORDER BY timestamp ASC)
- Crash resilient (persistent storage)
- Connection resilient (heartbeat prevents 5-minute timeout)
- Modular (any monitor can use it)
- Pluggable handlers (monitors implement simple async function)
"""

import asyncio
import logging
import re
from typing import Callable, Awaitable, Optional
from mcp import ClientSession
from ax_agent_studio.message_store import MessageStore
from ax_agent_studio.mcp_heartbeat import keep_alive

logger = logging.getLogger(__name__)


class QueueManager:
    """
    Modular FIFO queue manager for MCP monitors.

    Usage:
        async def my_handler(content: str) -> str:
            # Your processing logic here
            return "Response"

        queue_mgr = QueueManager(agent_name, session, my_handler)
        await queue_mgr.run()  # Runs forever
    """

    def __init__(
        self,
        agent_name: str,
        session: ClientSession,
        message_handler: Callable[[str], Awaitable[str]],
        store: Optional[MessageStore] = None,
        mark_read: bool = False,
        poll_interval: float = 1.0,
        startup_sweep: bool = True,
        startup_sweep_limit: int = 10,
        heartbeat_interval: int = 240  # 4 minutes default
    ):
        """
        Initialize QueueManager.

        Args:
            agent_name: Name of the agent (e.g., "lunar_craft_128")
            session: MCP ClientSession for tool calls
            message_handler: Async function that processes message content and returns response
            store: Optional MessageStore instance (creates default if None)
            mark_read: Whether to mark messages as read (default: False for FIFO)
            poll_interval: Seconds to wait between queue checks if empty (default: 1.0)
            startup_sweep: Whether to fetch unread messages on startup (default: True)
            startup_sweep_limit: Max unread messages to fetch on startup, 0=unlimited (default: 10)
            heartbeat_interval: Seconds between heartbeat pings (default: 240 = 4 minutes, 0=disabled)
        """
        self.agent_name = agent_name
        self.session = session
        self.handler = message_handler
        self.store = store or MessageStore()
        self.mark_read = mark_read
        self.poll_interval = poll_interval
        self.startup_sweep = startup_sweep
        self.startup_sweep_limit = startup_sweep_limit
        self.heartbeat_interval = heartbeat_interval
        self._running = False

        logger.info(f"🔧 QueueManager initialized for @{agent_name}")
        logger.info(f"   Storage: {self.store.db_path}")
        logger.info(f"   Mark read: {self.mark_read}")
        logger.info(f"   Startup sweep: {self.startup_sweep} (limit: {self.startup_sweep_limit})")
        logger.info(f"   Heartbeat: {'enabled' if self.heartbeat_interval > 0 else 'disabled'} (interval: {self.heartbeat_interval}s)")

    def _parse_message(self, result) -> Optional[tuple[str, str, str]]:
        """
        Parse MCP messages tool result to extract message ID, sender, and content.

        The MCP remote server returns messages in different formats:
        - result.content: Status messages like "✅ WAIT SUCCESS: Found 1 mentions"
        - result.events: Actual message data (for some MCP implementations)
        - result.content with formatted text: Message data in text format (for others)

        Returns:
            Tuple of (message_id, sender, content) or None if no valid message
        """
        try:
            # Try result.events first (old format from some MCP servers)
            if hasattr(result, 'events') and result.events:
                event = result.events[0]
                msg_id = event.get('id', 'unknown')
                sender = event.get('sender_name', 'unknown')
                content = event.get('content', '')

                logger.info(f"📋 Found message via events: {msg_id[:8]} from {sender}")
                return (msg_id, sender, content)

            # Try result.content (current format)
            content = result.content
            if not content:
                logger.debug("📋 Empty content in result")
                return None

            # Extract message text
            if hasattr(content, 'text'):
                messages_data = content.text
            else:
                messages_data = str(content[0].text) if content else ""

            if not messages_data:
                logger.debug("📋 Empty messages_data")
                return None

            # Skip status messages like "WAIT SUCCESS"
            if "WAIT SUCCESS" in messages_data or "No mentions" in messages_data:
                logger.debug(f"📋 Skipping status message: {messages_data[:100]}")
                return None

            # Extract message ID from [id:xxxxxxxx] tags
            message_id_match = re.search(r'\[id:([a-f0-9-]+)\]', messages_data)
            if not message_id_match:
                logger.warning("⚠️  No message ID found in response")
                return None

            message_id = message_id_match.group(1)

            # Verify there's an actual mention (not just "no mentions found")
            mention_match = re.search(r'• ([^:]+): (@\S+)\s+(.+)', messages_data)
            if not mention_match:
                logger.debug("⏭️  No actual mentions in response")
                return None

            # Verify THIS agent is mentioned
            if f"@{self.agent_name}" not in messages_data:
                logger.debug(f"⏭️  Message doesn't mention @{self.agent_name}")
                return None

            # Extract sender and content
            sender = mention_match.group(1)

            # Skip self-mentions (agent mentioning themselves)
            if sender == self.agent_name:
                logger.warning(f"⏭️  SKIPPING SELF-MENTION: {sender} mentioned themselves (agent={self.agent_name})")
                return None

            # Full content includes the mention pattern
            content = messages_data

            logger.info(f"✅ VALID MESSAGE: from {sender} to {self.agent_name}")
            return (message_id, sender, content)

        except Exception as e:
            logger.error(f"❌ Error parsing message: {e}")
            return None

    async def _startup_sweep(self):
        """
        Startup sweep: Fetch unread messages before starting poller.

        This gives monitors context when they join late by catching up on
        the last N unread messages. Uses mode='unread' + wait=False to
        fetch backlog without blocking.

        Following ax_sentinel's recommendation:
        1. Fetch unread messages in loop until empty or limit reached
        2. Store each in the queue
        3. Mark them as read via up_to_id to prevent reprocessing
        """
        if not self.startup_sweep:
            logger.info("⏭️  Startup sweep disabled, starting poller...")
            return

        logger.info(f"🔍 Starting unread message sweep (limit: {self.startup_sweep_limit or 'unlimited'})")

        fetched = 0
        last_id = None

        try:
            max_iterations = 200  # Safety limit to prevent infinite loops
            iteration = 0

            while iteration < max_iterations:
                # Stop if we've reached the limit
                if self.startup_sweep_limit > 0 and fetched >= self.startup_sweep_limit:
                    logger.info(f"✅ Sweep limit reached ({fetched} messages)")
                    break

                # Fetch unread messages (non-blocking)
                # Mark as read immediately to prevent re-fetching the same message
                result = await self.session.call_tool("messages", {
                    "action": "check",
                    "filter_agent": self.agent_name,
                    "mode": "unread",
                    "wait": False,
                    "limit": 1,  # Fetch one at a time to avoid duplicates
                    "mark_read": True  # Mark read immediately
                })

                # Parse message
                parsed = self._parse_message(result)
                if not parsed:
                    # No more unread messages
                    logger.info(f"✅ Sweep complete ({fetched} messages fetched)")
                    break

                msg_id, sender, content = parsed

                # Store in queue
                success = self.store.store_message(
                    msg_id=msg_id,
                    agent=self.agent_name,
                    sender=sender,
                    content=content
                )

                if success:
                    fetched += 1
                    last_id = msg_id
                    logger.info(f"📥 Sweep [{fetched}]: {msg_id[:8]} from {sender}")

                iteration += 1

                # CRITICAL: Rate limit protection - wait between requests
                # MCP server rate limit: ~100 req/min, so 0.7s = ~85 req/min (safe)
                await asyncio.sleep(0.7)

            if iteration >= max_iterations:
                logger.warning(f"⚠️  Hit max iterations ({max_iterations}) during sweep")

        except Exception as e:
            logger.error(f"❌ Startup sweep error: {e}")
            logger.info("   Continuing with normal polling...")

    async def poll_and_store(self):
        """
        Poller Task: Continuously receive messages and store in queue.

        This task runs forever, blocking on wait=true until messages arrive.
        When a message arrives, it's immediately stored in SQLite, then we
        go back to waiting. This ensures no messages are lost while the
        processor is busy.
        """
        logger.info("📥 Poller task started")
        iteration = 0

        while self._running:
            try:
                iteration += 1
                logger.debug(f"[Poller] Waiting for messages... (iteration {iteration})")

                # Block until message arrives (wait=true)
                result = await self.session.call_tool("messages", {
                    "action": "check",
                    "wait": True,
                    "mark_read": self.mark_read
                })

                # Parse and validate message
                parsed = self._parse_message(result)
                if not parsed:
                    continue

                msg_id, sender, content = parsed

                # Store in SQLite queue
                success = self.store.store_message(
                    msg_id=msg_id,
                    agent=self.agent_name,
                    sender=sender,
                    content=content
                )

                if success:
                    backlog = self.store.get_backlog_count(self.agent_name)
                    logger.info(f"📥 Stored message {msg_id[:8]} from {sender} (backlog: {backlog})")
                else:
                    logger.warning(f"⚠️  Failed to store message {msg_id[:8]} (likely duplicate)")

            except asyncio.CancelledError:
                logger.info("📥 Poller task cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Poller error: {e}")
                await asyncio.sleep(5)  # Brief pause on error

    async def process_queue(self):
        """
        Processor Task: Pull messages from queue and process FIFO.

        This task runs forever, checking the queue for pending messages.
        When a message is found, it's processed with the handler, response
        is sent, and message is marked complete. If queue is empty, we
        sleep briefly before checking again.
        """
        logger.info("⚙️  Processor task started")

        from pathlib import Path
        kill_switch_file = Path("data/KILL_SWITCH")

        while self._running:
            try:
                # 🛑 KILL SWITCH: Check if processing should be paused
                if kill_switch_file.exists():
                    logger.warning("🛑 KILL SWITCH ACTIVE - Processing paused")
                    await asyncio.sleep(2)  # Check every 2 seconds
                    continue

                # Get next pending message (FIFO order)
                messages = self.store.get_pending_messages(self.agent_name, limit=1)

                if not messages:
                    # Queue empty - brief pause
                    await asyncio.sleep(self.poll_interval)
                    continue

                msg = messages[0]
                backlog = self.store.get_backlog_count(self.agent_name)

                logger.info(f"⚙️  Processing message {msg.id[:8]} from {msg.sender} (backlog: {backlog})")

                # Mark as processing (prevents duplicate processing)
                self.store.mark_processing_started(msg.id, self.agent_name)

                try:
                    # Call monitor's handler with full message context (pluggable!)
                    # Pass dict with sender and content so handler knows who sent the message
                    response = await self.handler({
                        "content": msg.content,
                        "sender": msg.sender,
                        "id": msg.id,
                        "timestamp": msg.timestamp
                    })

                    # Ensure response is a string
                    if not isinstance(response, str):
                        response = str(response)

                    # Only send if response is not empty (handler may return "" to skip)
                    if response and response.strip():
                        # Send response as a REPLY to the original message (creates thread)
                        await self.session.call_tool("messages", {
                            "action": "send",
                            "content": response,
                            "parent_message_id": msg.id  # Reply to the message we received
                        })
                        logger.info(f"✅ Completed message {msg.id[:8]} (threaded reply): {response[:50]}...")
                    else:
                        # Handler returned empty response (e.g., blocked self-mention)
                        logger.info(f"✅ Completed message {msg.id[:8]}: (no response - handler blocked)")

                    # Mark as processed (removes from queue)
                    self.store.mark_processed(msg.id, self.agent_name)

                except Exception as e:
                    logger.error(f"❌ Handler error for message {msg.id[:8]}: {e}")
                    logger.error(f"   Error details: {type(e).__name__}: {str(e)}")
                    # Mark as processed to prevent infinite retry loop
                    # TODO: Add retry limits and dead-letter queue for transient failures
                    self.store.mark_processed(msg.id, self.agent_name)
                    logger.warning(f"⚠️  Message {msg.id[:8]} marked as failed (won't retry)")

            except asyncio.CancelledError:
                logger.info("⚙️  Processor task cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Processor error: {e}")
                await asyncio.sleep(5)  # Brief pause on error

    async def heartbeat(self):
        """
        Heartbeat Task: Keep MCP connection alive with periodic pings.

        Uses the reusable keep_alive() utility from mcp_heartbeat module.
        This ensures DRY - all MCP connections use the same heartbeat logic.
        """
        # Use the centralized heartbeat utility
        await keep_alive(
            self.session,
            interval=self.heartbeat_interval,
            name=self.agent_name
        )

    async def run(self):
        """
        Run all tasks concurrently (poller + processor + heartbeat).

        This is the main entry point for monitors. It starts all tasks
        and runs until interrupted (Ctrl+C).
        """
        self._running = True

        try:
            # Show initial stats
            stats = self.store.get_stats(self.agent_name)
            logger.info(f"📊 Queue stats: {stats['pending']} pending, {stats['completed']} completed")

            # Do startup sweep to catch up on missed messages
            await self._startup_sweep()

            # Run all tasks concurrently (poller + processor + heartbeat)
            tasks = [
                self.poll_and_store(),
                self.process_queue(),
            ]

            # Add heartbeat if enabled
            if self.heartbeat_interval > 0:
                tasks.append(self.heartbeat())

            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("🛑 QueueManager stopped by user")
        except Exception as e:
            logger.error(f"❌ QueueManager error: {e}")
        finally:
            self._running = False

            # Show final stats
            stats = self.store.get_stats(self.agent_name)
            logger.info(f"📊 Final stats: {stats['pending']} pending, {stats['completed']} completed")
            logger.info(f"   Avg processing time: {stats['avg_processing_time']:.2f}s")
            # Note: Heartbeat stats are logged by keep_alive() utility

    async def cleanup_old_messages(self, days: int = 7) -> int:
        """
        Clean up old processed messages.

        Args:
            days: Delete messages older than this many days (default: 7)

        Returns:
            Number of messages deleted
        """
        count = self.store.cleanup_old_messages(days)
        logger.info(f"🗑️  Cleaned up {count} messages older than {days} days")
        return count
