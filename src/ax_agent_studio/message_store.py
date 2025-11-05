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
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
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

            conn.commit()

    @contextmanager
    def _conn(self):
        """Context manager for database connections."""
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
