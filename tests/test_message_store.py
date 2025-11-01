#!/usr/bin/env python3
"""
Unit tests for MessageStore - Multi-Agent Message Handling

Tests verify that multiple agents can store and process the same message ID
independently, which is critical for multi-agent @mention scenarios.
"""

import sqlite3
import tempfile
import time
from pathlib import Path

import pytest

from ax_agent_studio.message_store import MessageStore, StoredMessage


class TestMessageStoreMultiAgent:
    """Test MessageStore with multiple agents sharing message IDs."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        yield db_path
        # Cleanup
        Path(db_path).unlink(missing_ok=True)

    @pytest.fixture
    def store(self, temp_db):
        """Create a MessageStore instance with temp database."""
        return MessageStore(db_path=temp_db)

    def test_same_message_multiple_agents(self, store):
        """Test that multiple agents can store the same message ID."""
        msg_id = "test-msg-123"
        content = "@agent1 @agent2 @agent3 Hey team!"

        # Store same message for 3 different agents
        assert store.store_message(msg_id, "agent1", "user1", content)
        assert store.store_message(msg_id, "agent2", "user1", content)
        assert store.store_message(msg_id, "agent3", "user1", content)

        # Each agent should have the message in their queue
        agent1_msgs = store.get_pending_messages("agent1")
        agent2_msgs = store.get_pending_messages("agent2")
        agent3_msgs = store.get_pending_messages("agent3")

        assert len(agent1_msgs) == 1
        assert len(agent2_msgs) == 1
        assert len(agent3_msgs) == 1

        # All should have the same message ID but different agent fields
        assert agent1_msgs[0].id == msg_id
        assert agent1_msgs[0].agent == "agent1"
        assert agent2_msgs[0].id == msg_id
        assert agent2_msgs[0].agent == "agent2"
        assert agent3_msgs[0].id == msg_id
        assert agent3_msgs[0].agent == "agent3"

    def test_processing_one_agent_doesnt_affect_others(self, store):
        """Test that processing a message for one agent doesn't affect others."""
        msg_id = "shared-msg-456"
        content = "@lunar @orion @rigelz Work together!"

        # Store for 3 agents
        store.store_message(msg_id, "lunar_craft_128", "coordinator", content)
        store.store_message(msg_id, "orion_344", "coordinator", content)
        store.store_message(msg_id, "rigelz_334", "coordinator", content)

        # Process for lunar only
        store.mark_processing_started(msg_id, "lunar_craft_128")
        store.mark_processed(msg_id, "lunar_craft_128")

        # lunar's queue should be empty now
        lunar_msgs = store.get_pending_messages("lunar_craft_128")
        assert len(lunar_msgs) == 0

        # orion and rigelz should still have the message
        orion_msgs = store.get_pending_messages("orion_344")
        rigelz_msgs = store.get_pending_messages("rigelz_334")

        assert len(orion_msgs) == 1
        assert len(rigelz_msgs) == 1
        assert orion_msgs[0].id == msg_id
        assert rigelz_msgs[0].id == msg_id

    def test_duplicate_insert_ignored(self, store):
        """Test that duplicate inserts for same (id, agent) are ignored."""
        msg_id = "duplicate-test"

        # Insert same message twice for same agent
        result1 = store.store_message(msg_id, "agent1", "user", "content")
        result2 = store.store_message(msg_id, "agent1", "user", "content")

        assert result1 is True
        assert result2 is True  # Returns true but doesn't duplicate

        # Should only have one message
        messages = store.get_pending_messages("agent1")
        assert len(messages) == 1

    def test_backlog_count_per_agent(self, store):
        """Test backlog counting is accurate per agent."""
        # Store 3 messages for agent1
        store.store_message("msg1", "agent1", "user", "content1")
        store.store_message("msg2", "agent1", "user", "content2")
        store.store_message("msg3", "agent1", "user", "content3")

        # Store 2 of the same messages for agent2
        store.store_message("msg1", "agent2", "user", "content1")
        store.store_message("msg2", "agent2", "user", "content2")

        # Check backlog counts
        assert store.get_backlog_count("agent1") == 3
        assert store.get_backlog_count("agent2") == 2
        assert store.get_backlog_count("agent3") == 0

    def test_fifo_ordering_per_agent(self, store):
        """Test that messages are retrieved in FIFO order per agent."""
        # Insert messages with slight delays to ensure different timestamps
        store.store_message("msg1", "agent1", "user", "first")
        time.sleep(0.01)
        store.store_message("msg2", "agent1", "user", "second")
        time.sleep(0.01)
        store.store_message("msg3", "agent1", "user", "third")

        # Get all messages
        messages = store.get_pending_messages("agent1", limit=10)

        assert len(messages) == 3
        assert messages[0].content == "first"
        assert messages[1].content == "second"
        assert messages[2].content == "third"

    def test_stats_per_agent(self, store):
        """Test that statistics are calculated correctly per agent."""
        # Add some messages for agent1
        store.store_message("m1", "agent1", "user", "test")
        store.store_message("m2", "agent1", "user", "test")

        # Process one
        store.mark_processing_started("m1", "agent1")
        store.mark_processed("m1", "agent1")

        # Get stats
        stats = store.get_stats("agent1")

        assert stats['pending'] == 1
        assert stats['completed'] == 1
        assert stats['avg_processing_time'] > 0

    def test_composite_primary_key_schema(self, store):
        """Test that the database schema uses composite primary key (id, agent)."""
        # Query the schema directly
        with store._conn() as conn:
            cursor = conn.execute("""
                SELECT sql FROM sqlite_master
                WHERE type='table' AND name='messages'
            """)
            schema = cursor.fetchone()[0]

        # Verify composite primary key exists
        assert "PRIMARY KEY (id, agent)" in schema or "PRIMARY KEY(id, agent)" in schema

        # Verify we can insert same ID for different agents
        # This would fail with old schema (id as sole primary key)
        with store._conn() as conn:
            # Insert same ID for two agents - should succeed
            conn.execute(
                "INSERT INTO messages (id, agent, sender, content, timestamp) VALUES (?, ?, ?, ?, ?)",
                ("same-id", "agent1", "user", "content", time.time())
            )
            conn.execute(
                "INSERT INTO messages (id, agent, sender, content, timestamp) VALUES (?, ?, ?, ?, ?)",
                ("same-id", "agent2", "user", "content", time.time())
            )
            conn.commit()

            # Query to verify both exist
            cursor = conn.execute(
                "SELECT COUNT(*) FROM messages WHERE id = ?",
                ("same-id",)
            )
            count = cursor.fetchone()[0]
            assert count == 2  # Both agents have the message


class TestMessageStoreBasicFunctionality:
    """Test basic MessageStore operations."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        yield db_path
        Path(db_path).unlink(missing_ok=True)

    @pytest.fixture
    def store(self, temp_db):
        """Create a MessageStore instance with temp database."""
        return MessageStore(db_path=temp_db)

    def test_store_and_retrieve(self, store):
        """Test basic store and retrieve operations."""
        msg_id = "test-123"
        agent = "test-agent"
        sender = "test-sender"
        content = "test content"

        # Store message
        success = store.store_message(msg_id, agent, sender, content)
        assert success is True

        # Retrieve message
        messages = store.get_pending_messages(agent)
        assert len(messages) == 1
        assert messages[0].id == msg_id
        assert messages[0].agent == agent
        assert messages[0].sender == sender
        assert messages[0].content == content

    def test_mark_processing(self, store):
        """Test marking messages as processing and completed."""
        msg_id = "process-test"
        agent = "agent1"

        store.store_message(msg_id, agent, "user", "content")

        # Mark as processing
        store.mark_processing_started(msg_id, agent)

        # Should still appear in pending (processing_started but not completed)
        messages = store.get_pending_messages(agent)
        assert len(messages) == 1
        assert messages[0].processing_started_at is not None

        # Mark as completed
        store.mark_processed(msg_id, agent)

        # Should no longer appear in pending
        messages = store.get_pending_messages(agent)
        assert len(messages) == 0


def test_mark_processing_methods():
    """Test that mark_processing methods accept agent parameter."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        store = MessageStore(db_path=db_path)

        # Store a message
        store.store_message("msg1", "agent1", "user", "content")

        # These should work with agent parameter (for composite key)
        store.mark_processing_started("msg1", "agent1")
        store.mark_processed("msg1", "agent1")

    finally:
        Path(db_path).unlink(missing_ok=True)


if __name__ == "__main__":
    import sys

    # Run with pytest if available, otherwise basic test
    try:
        import pytest
        sys.exit(pytest.main([__file__, "-v"]))
    except ImportError:
        print("pytest not found, running basic tests...")

        # Run a basic smoke test
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        try:
            store = MessageStore(db_path=db_path)

            # Test multi-agent scenario
            msg_id = "demo-msg"
            content = "@lunar @orion @rigelz Build an app!"

            print(" Testing multi-agent message storage...")
            store.store_message(msg_id, "lunar_craft_128", "coordinator", content)
            store.store_message(msg_id, "orion_344", "coordinator", content)
            store.store_message(msg_id, "rigelz_334", "coordinator", content)

            lunar_msgs = store.get_pending_messages("lunar_craft_128")
            orion_msgs = store.get_pending_messages("orion_344")
            rigelz_msgs = store.get_pending_messages("rigelz_334")

            assert len(lunar_msgs) == 1, f"Expected 1 message for lunar, got {len(lunar_msgs)}"
            assert len(orion_msgs) == 1, f"Expected 1 message for orion, got {len(orion_msgs)}"
            assert len(rigelz_msgs) == 1, f"Expected 1 message for rigelz, got {len(rigelz_msgs)}"

            print(" All 3 agents received the message!")

            # Test processing independence
            print(" Testing processing independence...")
            store.mark_processing_started(msg_id, "lunar_craft_128")
            store.mark_processed(msg_id, "lunar_craft_128")

            lunar_msgs = store.get_pending_messages("lunar_craft_128")
            orion_msgs = store.get_pending_messages("orion_344")
            rigelz_msgs = store.get_pending_messages("rigelz_334")

            assert len(lunar_msgs) == 0, "lunar should have 0 messages after processing"
            assert len(orion_msgs) == 1, "orion should still have 1 message"
            assert len(rigelz_msgs) == 1, "rigelz should still have 1 message"

            print(" Processing one agent doesn't affect others!")
            print("\n All basic tests passed!")

        finally:
            Path(db_path).unlink(missing_ok=True)
