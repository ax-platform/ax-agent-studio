"""Persistent message store to handle mention backlogs.

When agents are busy processing and new @mentions arrive, they pile up.
This store persists them to SQLite so no messages are lost even if
the monitor restarts or crashes.
"""

import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path


@dataclass
class StoredMessage:
    """Persisted mention message."""

    id: str
    agent: str
    sender: str
    content: str
    timestamp: float
    processed: bool = False
    processing_started_at: float | None = None
    processing_completed_at: float | None = None


class MessageStore:
    """SQLite-backed message store for mention queuing."""

    def __init__(self, db_path: str = "data/message_backlog.db"):
        self.db_path = Path(db_path) if db_path != ":memory:" else db_path
        self._is_memory = (db_path == ":memory:")
        self._memory_conn = None  # Keep persistent connection for in-memory DBs

        # Only create directory for file-based databases
        if db_path != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        try:
            with self._conn() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id TEXT NOT NULL,
                        agent TEXT NOT NULL,
                        sender TEXT NOT NULL,
                        content TEXT NOT NULL,
                        timestamp REAL NOT NULL,
                        processed INTEGER DEFAULT 0,
                        processing_started_at REAL,
                        processing_completed_at REAL,
                        created_at REAL DEFAULT (strftime('%s', 'now')),
                        PRIMARY KEY (id, agent)
                    )
                """)

                # Index for efficient queries
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_agent_processed
                    ON messages(agent, processed, timestamp)
                """)

                # Agent status table for pause/resume functionality
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS agent_status (
                        agent TEXT PRIMARY KEY,
                        status TEXT NOT NULL DEFAULT 'active',
                        paused_at REAL,
                        paused_reason TEXT,
                        resume_at REAL,
                        updated_at REAL DEFAULT (strftime('%s', 'now'))
                    )
                """)

                conn.commit()
        except Exception as e:
            import logging
            logging.error(f"Failed to initialize database: {e}")
            raise

    @contextmanager
    def _conn(self):
        """Context manager for database connections."""
        # For in-memory databases, reuse the same connection
        # (otherwise each connection creates a fresh empty database)
        if self._is_memory:
            if self._memory_conn is None:
                self._memory_conn = sqlite3.connect(str(self.db_path))
                self._memory_conn.row_factory = sqlite3.Row
            yield self._memory_conn
        else:
            # For file-based databases, create new connection each time
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()

    def store_message(self, msg_id: str, agent: str, sender: str, content: str) -> bool:
        """Store a new mention message."""
        try:
            with self._conn() as conn:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO messages
                    (id, agent, sender, content, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (msg_id, agent, sender, content, time.time()),
                )
                conn.commit()
                return True
        except sqlite3.Error:
            return False

    def get_pending_messages(self, agent: str, limit: int = 10) -> list[StoredMessage]:
        """Get unprocessed messages for an agent, ordered by timestamp."""
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM messages
                WHERE agent = ? AND processed = 0
                ORDER BY timestamp ASC
                LIMIT ?
                """,
                (agent, limit),
            ).fetchall()

            return [
                StoredMessage(
                    id=row["id"],
                    agent=row["agent"],
                    sender=row["sender"],
                    content=row["content"],
                    timestamp=row["timestamp"],
                    processed=bool(row["processed"]),
                    processing_started_at=row["processing_started_at"],
                    processing_completed_at=row["processing_completed_at"],
                )
                for row in rows
            ]

    def mark_processing_started(self, msg_id: str, agent: str = None) -> bool:
        """Mark a message as being processed (prevents duplicate processing)."""
        try:
            with self._conn() as conn:
                if agent:
                    # With composite key: update only this agent's message
                    conn.execute(
                        """
                        UPDATE messages
                        SET processing_started_at = ?
                        WHERE id = ? AND agent = ?
                        """,
                        (time.time(), msg_id, agent),
                    )
                else:
                    # Backward compatibility: update by id only
                    conn.execute(
                        """
                        UPDATE messages
                        SET processing_started_at = ?
                        WHERE id = ?
                        """,
                        (time.time(), msg_id),
                    )
                conn.commit()
                return True
        except sqlite3.Error:
            return False

    def mark_processed(self, msg_id: str, agent: str = None) -> bool:
        """Mark a message as fully processed."""
        try:
            with self._conn() as conn:
                if agent:
                    # With composite key: update only this agent's message
                    conn.execute(
                        """
                        UPDATE messages
                        SET processed = 1, processing_completed_at = ?
                        WHERE id = ? AND agent = ?
                        """,
                        (time.time(), msg_id, agent),
                    )
                else:
                    # Backward compatibility: update by id only
                    conn.execute(
                        """
                        UPDATE messages
                        SET processed = 1, processing_completed_at = ?
                        WHERE id = ?
                        """,
                        (time.time(), msg_id),
                    )
                conn.commit()
                return True
        except sqlite3.Error:
            return False

    def get_backlog_count(self, agent: str) -> int:
        """Get count of unprocessed messages for an agent."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as count FROM messages WHERE agent = ? AND processed = 0",
                (agent,),
            ).fetchone()
            return row["count"] if row else 0

    def get_total_processed(self, agent: str) -> int:
        """Get count of all processed messages for an agent."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as count FROM messages WHERE agent = ? AND processed = 1",
                (agent,),
            ).fetchone()
            return row["count"] if row else 0

    def cleanup_old_messages(self, days: int = 7) -> int:
        """Delete processed messages older than N days."""
        cutoff = time.time() - (days * 86400)

        with self._conn() as conn:
            cursor = conn.execute(
                """
                DELETE FROM messages
                WHERE processed = 1 AND processing_completed_at < ?
                """,
                (cutoff,),
            )
            conn.commit()
            return cursor.rowcount

    def get_stats(self, agent: str) -> dict:
        """Get statistics for an agent."""
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN processed = 0 THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN processed = 1 THEN 1 ELSE 0 END) as completed,
                    AVG(CASE
                        WHEN processing_completed_at IS NOT NULL
                        AND processing_started_at IS NOT NULL
                        THEN processing_completed_at - processing_started_at
                        ELSE NULL
                    END) as avg_processing_time
                FROM messages
                WHERE agent = ?
                """,
                (agent,),
            ).fetchone()

            return {
                "total": row["total"] or 0,
                "pending": row["pending"] or 0,
                "completed": row["completed"] or 0,
                "avg_processing_time": row["avg_processing_time"] or 0.0,
            }

    def clear_agent(self, agent: str) -> int:
        """Delete all messages stored for an agent."""
        with self._conn() as conn:
            cursor = conn.execute(
                "DELETE FROM messages WHERE agent = ?",
                (agent,),
            )
            conn.commit()
            return cursor.rowcount

    def clear_pending_messages(self, agent: str) -> int:
        """Delete all pending (unprocessed) messages for an agent.

        This is used by #done to clear the backlog when an agent needs a break.
        Only clears unprocessed messages - keeps processed ones for history.
        """
        with self._conn() as conn:
            cursor = conn.execute(
                "DELETE FROM messages WHERE agent = ? AND processed = 0",
                (agent,),
            )
            conn.commit()
            return cursor.rowcount

    def pause_agent(self, agent: str, reason: str = "", resume_at: float | None = None) -> bool:
        """
        Pause an agent (stop processing messages).

        Args:
            agent: Agent name
            reason: Optional reason for pause (e.g., "Self-paused: overwhelmed", "Manual pause")
            resume_at: Optional timestamp for auto-resume (None = manual resume required)

        Returns:
            True if successful
        """
        try:
            with self._conn() as conn:
                conn.execute(
                    """
                    INSERT INTO agent_status (agent, status, paused_at, paused_reason, resume_at, updated_at)
                    VALUES (?, 'paused', ?, ?, ?, ?)
                    ON CONFLICT(agent) DO UPDATE SET
                        status = 'paused',
                        paused_at = excluded.paused_at,
                        paused_reason = excluded.paused_reason,
                        resume_at = excluded.resume_at,
                        updated_at = excluded.updated_at
                    """,
                    (agent, time.time(), reason, resume_at, time.time()),
                )
                conn.commit()
                return True
        except sqlite3.Error:
            return False

    def resume_agent(self, agent: str) -> bool:
        """
        Resume an agent (continue processing messages).

        Args:
            agent: Agent name

        Returns:
            True if successful
        """
        try:
            with self._conn() as conn:
                conn.execute(
                    """
                    INSERT INTO agent_status (agent, status, paused_at, paused_reason, resume_at, updated_at)
                    VALUES (?, 'active', NULL, NULL, NULL, ?)
                    ON CONFLICT(agent) DO UPDATE SET
                        status = 'active',
                        paused_at = NULL,
                        paused_reason = NULL,
                        resume_at = NULL,
                        updated_at = excluded.updated_at
                    """,
                    (agent, time.time()),
                )
                conn.commit()
                return True
        except sqlite3.Error:
            return False

    def get_agent_status(self, agent: str) -> dict:
        """
        Get current status of an agent.

        Args:
            agent: Agent name

        Returns:
            Dict with keys: status ('active'|'paused'), paused_at, paused_reason, resume_at
        """
        with self._conn() as conn:
            row = conn.execute(
                "SELECT status, paused_at, paused_reason, resume_at FROM agent_status WHERE agent = ?",
                (agent,),
            ).fetchone()

            if not row:
                # Agent not in table = active by default
                return {
                    "status": "active",
                    "paused_at": None,
                    "paused_reason": None,
                    "resume_at": None,
                }

            return {
                "status": row["status"],
                "paused_at": row["paused_at"],
                "paused_reason": row["paused_reason"],
                "resume_at": row["resume_at"],
            }

    def is_agent_paused(self, agent: str) -> bool:
        """
        Check if agent is currently paused.

        Args:
            agent: Agent name

        Returns:
            True if paused, False if active
        """
        status = self.get_agent_status(agent)
        return status["status"] == "paused"

    def check_auto_resume(self, agent: str) -> bool:
        """
        Check if agent should be auto-resumed based on resume_at timestamp.
        If resume_at is set and current time >= resume_at, automatically resume.

        Args:
            agent: Agent name

        Returns:
            True if agent was auto-resumed, False otherwise
        """
        status = self.get_agent_status(agent)

        if status["status"] == "paused" and status["resume_at"]:
            if time.time() >= status["resume_at"]:
                self.resume_agent(agent)
                return True

        return False
