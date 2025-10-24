#!/usr/bin/env python3
"""
E2E Tests for Message Parsing and Queue Management

Tests:
1. Message parsing from MCP server format
2. Self-mention detection
3. Sender identification
4. Agent conversation flow
"""

import asyncio
import re
from dataclasses import dataclass
from typing import Optional, Tuple


# Mock the message format we get from MCP server
@dataclass
class MockMCPResult:
    """Simulates MCP server response"""
    content: str

    class Text:
        def __init__(self, text):
            self.text = text

    def __init__(self, text: str):
        self.content = [self.Text(text)]


class TestMessageParser:
    """Test the message parsing logic from queue_manager.py"""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name

    def _parse_message_from_result(self, result) -> Optional[Tuple[str, str, str]]:
        """
        Replicated from queue_manager.py to test parsing logic

        Returns:
            Tuple of (message_id, sender, content) or None if no valid message
        """
        try:
            # Extract message text
            if hasattr(result.content[0], 'text'):
                messages_data = result.content[0].text
            else:
                messages_data = str(result.content[0])

            if not messages_data:
                print("❌ Empty messages_data")
                return None

            # Skip status messages
            if "WAIT SUCCESS" in messages_data or "No mentions" in messages_data:
                print(f"⏭️  Skipping status message: {messages_data[:100]}")
                return None

            # Extract message ID from [id:xxxxxxxx] tags
            message_id_match = re.search(r'\[id:([a-f0-9-]+)\]', messages_data)
            if not message_id_match:
                print("❌ No message ID found in response")
                return None

            message_id = message_id_match.group(1)

            # Verify there's an actual mention
            mention_match = re.search(r'• ([^:]+): (@\S+)\s+(.+)', messages_data)
            if not mention_match:
                print("⏭️  No actual mentions in response")
                return None

            # Verify THIS agent is mentioned
            if f"@{self.agent_name}" not in messages_data:
                print(f"⏭️  Message doesn't mention @{self.agent_name}")
                return None

            # Extract sender
            sender = mention_match.group(1)

            # DEBUG: Print what we extracted
            print(f"🔍 DEBUG: Extracted sender='{sender}', agent_name='{self.agent_name}'")

            # Skip self-mentions (agent mentioning themselves)
            if sender == self.agent_name:
                print(f"⏭️  Skipping self-mention from {sender}")
                return None

            # Full content includes the mention pattern
            content = messages_data

            return (message_id, sender, content)

        except Exception as e:
            print(f"❌ Error parsing message: {e}")
            return None


def test_normal_message():
    """Test: Normal message from another user"""
    print("\n" + "="*60)
    print("TEST 1: Normal message from madtank to lunar_craft_128")
    print("="*60)

    parser = TestMessageParser("lunar_craft_128")

    # Simulate message from madtank to lunar_craft_128
    mock_result = MockMCPResult(
        "[id:12c95700] • madtank: @lunar_craft_128 What's the weather like?"
    )

    result = parser._parse_message_from_result(mock_result)

    if result:
        msg_id, sender, content = result
        print(f"✅ PASS: Parsed message")
        print(f"   Message ID: {msg_id}")
        print(f"   Sender: {sender}")
        print(f"   Expected sender: madtank")
        assert sender == "madtank", f"Expected sender 'madtank', got '{sender}'"
    else:
        print("❌ FAIL: Message was None (should have been parsed)")
        assert False


def test_self_mention():
    """Test: Agent mentions itself (should be skipped)"""
    print("\n" + "="*60)
    print("TEST 2: Self-mention - lunar_craft_128 mentions itself")
    print("="*60)

    parser = TestMessageParser("lunar_craft_128")

    # Simulate lunar_craft_128 mentioning itself
    mock_result = MockMCPResult(
        "[id:abc123] • lunar_craft_128: @lunar_craft_128 I'm ready!"
    )

    result = parser._parse_message_from_result(mock_result)

    if result is None:
        print("✅ PASS: Self-mention was correctly skipped")
    else:
        msg_id, sender, content = result
        print(f"❌ FAIL: Self-mention was NOT skipped!")
        print(f"   Sender: {sender}")
        assert False


def test_agent_to_agent():
    """Test: One agent mentions another agent"""
    print("\n" + "="*60)
    print("TEST 3: Agent-to-agent - orion_344 to lunar_craft_128")
    print("="*60)

    parser = TestMessageParser("lunar_craft_128")

    # Simulate orion_344 mentioning lunar_craft_128
    mock_result = MockMCPResult(
        "[id:def456] • orion_344: @lunar_craft_128 What's your favorite programming language?"
    )

    result = parser._parse_message_from_result(mock_result)

    if result:
        msg_id, sender, content = result
        print(f"✅ PASS: Parsed agent-to-agent message")
        print(f"   Sender: {sender}")
        print(f"   Expected sender: orion_344")
        assert sender == "orion_344", f"Expected sender 'orion_344', got '{sender}'"
    else:
        print("❌ FAIL: Message was None (should have been parsed)")
        assert False


def test_wrong_agent_mentioned():
    """Test: Message doesn't mention this agent (should be skipped)"""
    print("\n" + "="*60)
    print("TEST 4: Wrong agent - message for orion_344, not lunar_craft_128")
    print("="*60)

    parser = TestMessageParser("lunar_craft_128")

    # Simulate message to orion_344 (not lunar_craft_128)
    mock_result = MockMCPResult(
        "[id:xyz789] • madtank: @orion_344 Hello there!"
    )

    result = parser._parse_message_from_result(mock_result)

    if result is None:
        print("✅ PASS: Message for different agent was correctly skipped")
    else:
        msg_id, sender, content = result
        print(f"❌ FAIL: Message for different agent was NOT skipped!")
        print(f"   Content: {content}")
        assert False


def test_sender_extraction():
    """Test: Verify sender name extraction is correct"""
    print("\n" + "="*60)
    print("TEST 5: Sender extraction - various usernames")
    print("="*60)

    test_cases = [
        ("madtank", "[id:aaa] • madtank: @lunar_craft_128 test"),
        ("orion_344", "[id:bbb] • orion_344: @lunar_craft_128 test"),
        ("user_with_underscore", "[id:ccc] • user_with_underscore: @lunar_craft_128 test"),
    ]

    parser = TestMessageParser("lunar_craft_128")

    for expected_sender, message in test_cases:
        mock_result = MockMCPResult(message)
        result = parser._parse_message_from_result(mock_result)

        if result:
            msg_id, sender, content = result
            if sender == expected_sender:
                print(f"✅ PASS: Correctly extracted sender '{sender}'")
            else:
                print(f"❌ FAIL: Expected '{expected_sender}', got '{sender}'")
                assert False
        else:
            print(f"❌ FAIL: Failed to parse message: {message}")
            assert False


def run_all_tests():
    """Run all tests"""
    print("\n" + "🧪 "*20)
    print("MESSAGE PARSING E2E TESTS")
    print("🧪 "*20)

    try:
        test_normal_message()
        test_self_mention()
        test_agent_to_agent()
        test_wrong_agent_mentioned()
        test_sender_extraction()

        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)

    except AssertionError as e:
        print("\n" + "="*60)
        print("❌ TESTS FAILED!")
        print("="*60)
        raise


if __name__ == "__main__":
    run_all_tests()
