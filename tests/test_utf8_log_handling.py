#!/usr/bin/env python3
"""Test UTF-8 character handling in log files."""

import asyncio
from pathlib import Path

import pytest

from ax_agent_studio.dashboard.backend.log_streamer import LogStreamer


class FakeWebSocket:
    """Minimal WebSocket stub that captures payloads."""

    def __init__(self):
        self.messages = []

    async def send_json(self, payload):
        self.messages.append(payload)


@pytest.mark.asyncio
async def test_utf8_characters_in_logs(tmp_path: Path):
    """Test that UTF-8 characters (emoji, unicode) are properly handled."""
    # Setup
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    log_file = log_dir / "test_monitor.log"

    # Write log with various UTF-8 characters
    log_content = """=== Test Log ===
Hello World! 🚀
Testing Unicode: こんにちは (Japanese)
Emojis: ✅ 🎉 💻 🔥
Special chars: © ® ™ € £ ¥
Math symbols: ∑ ∫ ∂ ∞ √
"""
    log_file.write_text(log_content, encoding="utf-8")

    # Create streamer and fake websocket
    streamer = LogStreamer(log_dir)
    websocket = FakeWebSocket()

    # Stream the logs
    await streamer.stream_logs(websocket, "test_monitor")

    # Verify: should have received the log content
    assert len(websocket.messages) > 0
    log_messages = [msg for msg in websocket.messages if msg.get("type") == "log"]
    assert len(log_messages) == 1

    received_content = log_messages[0]["content"]

    # Verify all special characters are preserved
    assert "🚀" in received_content
    assert "こんにちは" in received_content
    assert "✅" in received_content
    assert "©" in received_content
    assert "∑" in received_content


@pytest.mark.asyncio
async def test_utf8_with_replacement_on_invalid_bytes(tmp_path: Path):
    """Test that invalid UTF-8 bytes are replaced, not crashed."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    log_file = log_dir / "test_monitor.log"

    # Write valid UTF-8 content first
    log_file.write_text("Valid content\n", encoding="utf-8")

    # Append some invalid UTF-8 bytes (not through write_text)
    with open(log_file, "ab") as f:
        f.write(b"Invalid bytes: \xff\xfe\n")
        f.write("More valid content\n".encode("utf-8"))

    streamer = LogStreamer(log_dir)
    websocket = FakeWebSocket()

    # Should not crash, should handle with errors="replace"
    await streamer.stream_logs(websocket, "test_monitor")

    assert len(websocket.messages) > 0
    log_messages = [msg for msg in websocket.messages if msg.get("type") == "log"]
    assert len(log_messages) == 1

    # Content should be present (invalid bytes replaced with � or similar)
    received_content = log_messages[0]["content"]
    assert "Valid content" in received_content
    assert "More valid content" in received_content


@pytest.mark.asyncio
async def test_utf8_in_tail_mode(tmp_path: Path):
    """Test that UTF-8 characters work in tail/streaming mode."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    log_file = log_dir / "test_monitor.log"

    # Start with initial content
    log_file.write_text("Initial log\n", encoding="utf-8")

    streamer = LogStreamer(log_dir)
    websocket = FakeWebSocket()

    # Start tailing in background
    tail_task = asyncio.create_task(
        streamer._tail_log_file(websocket, log_file, "test_monitor")
    )

    # Give it time to start
    await asyncio.sleep(0.2)

    # Append UTF-8 content
    with open(log_file, "a", encoding="utf-8") as f:
        f.write("New line with emoji: 🎯\n")
        f.flush()

    # Give it time to read
    await asyncio.sleep(0.3)

    # Cancel the tail task
    tail_task.cancel()
    try:
        await tail_task
    except asyncio.CancelledError:
        pass

    # Verify we received the new content
    log_messages = [msg for msg in websocket.messages if msg.get("type") == "log"]
    assert len(log_messages) > 0

    # Check if emoji was received
    all_content = "".join(msg["content"] for msg in log_messages)
    assert "🎯" in all_content
