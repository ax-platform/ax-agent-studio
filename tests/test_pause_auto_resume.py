#!/usr/bin/env python3
"""
Simple unit test for pause auto-resume and message clearing.
Tests action=stop functionality with auto-clear when reason starts with "Done:".
No pytest required - just run with: uv run python tests/test_pause_auto_resume.py
"""

import tempfile
import time
from pathlib import Path

from ax_agent_studio.message_store import MessageStore


def test_done_clears_messages_on_resume():
    """Test that pause with 'Done:' reason clears pending messages on auto-resume."""
    print("\n" + "=" * 80)
    print("TEST: Pause with 'Done:' reason clears messages on auto-resume")
    print("=" * 80)

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        store = MessageStore(db_path=db_path)
        agent = "test_agent"

        # Store some messages
        print("\n1. Storing initial messages...")
        store.store_message("msg1", agent, "user", "Message 1")
        store.store_message("msg2", agent, "user", "Message 2")
        pending = store.get_pending_messages(agent)
        assert len(pending) == 2, f"Expected 2 messages, got {len(pending)}"
        print(f"   ✓ {len(pending)} messages stored")

        # Pause with reason starting with "Done:" (triggers auto-clear)
        print("\n2. Pausing with 'Done:' reason (auto-resume in 1 second)...")
        resume_at = time.time() + 1
        store.pause_agent(agent, reason="Done: Auto-resuming", resume_at=resume_at)
        assert store.is_agent_paused(agent) is True
        print("   ✓ Agent paused")

        # Add more messages while paused
        print("\n3. Adding messages while paused...")
        store.store_message("msg3", agent, "user", "Message 3")
        store.store_message("msg4", agent, "user", "Message 4")
        pending = store.get_pending_messages(agent)
        assert len(pending) == 4, f"Expected 4 messages, got {len(pending)}"
        print(f"   ✓ {len(pending)} messages total (including paused period)")

        # Wait for auto-resume time
        print("\n4. Waiting for auto-resume...")
        time.sleep(1.2)

        # check_auto_resume should resume AND clear messages
        print("5. Checking auto-resume (should clear messages)...")
        was_resumed = store.check_auto_resume(agent)
        assert was_resumed is True, "Expected agent to auto-resume"
        print("   ✓ Agent auto-resumed")

        # Messages should be cleared now
        pending = store.get_pending_messages(agent)
        assert len(pending) == 0, (
            f"Expected 0 messages after auto-resume with Done: reason, got {len(pending)}"
        )
        print(f"   ✓ Messages cleared: {len(pending)} pending")

        # Agent should be active again
        assert store.is_agent_paused(agent) is False
        print("   ✓ Agent is active again")

        print("\n" + "=" * 80)
        print("✅ TEST PASSED: Pause with 'Done:' reason clears messages on auto-resume")
        print("=" * 80 + "\n")

    finally:
        Path(db_path).unlink(missing_ok=True)


def test_regular_pause_keeps_messages():
    """Test that regular pause (without 'Done:' reason) preserves messages on resume."""
    print("\n" + "=" * 80)
    print("TEST: Regular pause preserves messages")
    print("=" * 80)

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        store = MessageStore(db_path=db_path)
        agent = "test_agent"

        # Store some messages
        print("\n1. Storing initial messages...")
        store.store_message("msg1", agent, "user", "Message 1")
        store.store_message("msg2", agent, "user", "Message 2")
        print("   ✓ 2 messages stored")

        # Pause with regular reason (not starting with "Done:")
        print("\n2. Pausing with regular reason (auto-resume in 1 second)...")
        resume_at = time.time() + 1
        store.pause_agent(agent, reason="Self-paused: taking a break", resume_at=resume_at)
        print("   ✓ Agent paused")

        # Add more messages while paused
        print("\n3. Adding message while paused...")
        store.store_message("msg3", agent, "user", "Message 3")
        print("   ✓ 3 messages total")

        # Wait and resume
        print("\n4. Waiting for auto-resume...")
        time.sleep(1.2)
        was_resumed = store.check_auto_resume(agent)
        assert was_resumed is True
        print("   ✓ Agent auto-resumed")

        # Messages should NOT be cleared for regular pause
        pending = store.get_pending_messages(agent)
        assert len(pending) == 3, f"Expected 3 messages after regular pause, got {len(pending)}"
        print(f"   ✓ Messages preserved: {len(pending)} pending")

        print("\n" + "=" * 80)
        print("✅ TEST PASSED: Regular pause preserves messages")
        print("=" * 80 + "\n")

    finally:
        Path(db_path).unlink(missing_ok=True)


if __name__ == "__main__":
    try:
        test_done_clears_messages_on_resume()
        test_regular_pause_keeps_messages()
        print("\n" + "🎉 " * 20)
        print("ALL TESTS PASSED!")
        print("🎉 " * 20 + "\n")
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        exit(1)
    except Exception as e:
        print(f"\n💥 ERROR: {e}\n")
        import traceback

        traceback.print_exc()
        exit(1)
