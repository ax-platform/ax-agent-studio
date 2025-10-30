"""
Conversation Memory Utilities

Stateless conversation memory - always fetch fresh context from server.
This approach (inspired by chirpy) ensures agents have up-to-date conversation
context without maintaining stale in-memory history.

Key principle: Each time agent receives a message, fetch last N messages
from server to understand conversation context, then reply to current message.
"""

import re
import logging
from typing import List, Dict, Optional
from mcp import ClientSession

logger = logging.getLogger(__name__)


async def fetch_conversation_context(
    session: ClientSession,
    agent_name: str,
    limit: int = 25
) -> List[Dict[str, str]]:
    """
    Fetch recent messages for conversation context.

    Args:
        session: MCP ClientSession
        agent_name: Agent name (for filtering)
        limit: Number of recent messages to fetch (default: 25)

    Returns:
        List of messages in chronological order (oldest first)
        Each message: {"sender": "alice", "content": "Hello!", "id": "abc123"}
    """
    try:
        # Fetch recent messages (single API call)
        # NOTE: Gets all messages in the conversation/channel for full context
        # This includes messages TO the agent and messages FROM the agent
        result = await session.call_tool("messages", {
            "action": "check",
            "mode": "latest",  # Get latest messages, not unread
            "limit": limit,
            "wait": False,
            "mark_read": False  # Don't mark as read, just fetching for context
        })

        messages = []

        # Parse messages from result
        content = result.content
        if not content:
            return messages

        # Extract text from content
        if hasattr(content, 'text'):
            messages_data = content.text
        else:
            messages_data = str(content[0].text) if content else ""

        if not messages_data:
            return messages

        # Skip status messages
        if "No mentions" in messages_data or "WAIT SUCCESS" in messages_data:
            return messages

        # Parse each message from the formatted text
        # Format: • sender: @agent_name message_content [id:abc123]
        pattern = r'• ([^:]+): @\S+\s+(.+?)\s+\[id:([a-f0-9-]+)\]'
        matches = re.finditer(pattern, messages_data, re.MULTILINE | re.DOTALL)

        for match in matches:
            sender = match.group(1).strip()
            content = match.group(2).strip()
            msg_id = match.group(3).strip()

            messages.append({
                "sender": sender,
                "content": content,
                "id": msg_id
            })

        logger.info(f"📚 Fetched {len(messages)} messages for conversation context")
        return messages

    except Exception as e:
        logger.error(f"❌ Failed to fetch conversation context: {e}")
        return []


def format_conversation_for_llm(
    messages: List[Dict[str, str]],
    current_message: Dict[str, str],
    agent_name: str,
    system_prompt: str
) -> List[Dict[str, str]]:
    """
    Format conversation messages for LLM (OpenAI chat format).

    Args:
        messages: List of past messages for context
        current_message: The message agent is responding to
        agent_name: Agent's name
        system_prompt: System prompt for the agent

    Returns:
        List in OpenAI chat format: [{"role": "system|user|assistant", "content": "..."}]
    """
    conversation = [
        {"role": "system", "content": system_prompt}
    ]

    # Add past messages for context
    for msg in messages:
        sender = msg["sender"]
        content = msg["content"]
        msg_id = msg["id"][:8] if len(msg["id"]) > 8 else msg["id"]

        # Messages TO this agent are user messages
        if f"@{agent_name}" in content:
            # Extract message content (remove the @mention)
            clean_content = re.sub(r'@\S+\s+', '', content).strip()
            conversation.append({
                "role": "user",
                "content": f"@{sender} [id:{msg_id}] says: {clean_content}"
            })

        # Messages FROM this agent are assistant messages
        elif sender == agent_name:
            conversation.append({
                "role": "assistant",
                "content": content
            })

    # Add current message as the final user message
    current_sender = current_message["sender"]
    current_content = current_message["content"]
    current_id = current_message["id"][:8] if len(current_message["id"]) > 8 else current_message["id"]

    # Extract clean content
    clean_current = re.sub(r'@\S+\s+', '', current_content).strip()
    conversation.append({
        "role": "user",
        "content": f"@{current_sender} [id:{current_id}] says: {clean_current}"
    })

    return conversation


def get_conversation_summary(messages: List[Dict[str, str]]) -> str:
    """Get a human-readable summary of conversation context."""
    if not messages:
        return "No conversation history"

    participants = set(msg["sender"] for msg in messages)
    return f"{len(messages)} messages from {len(participants)} participants: {', '.join(sorted(participants))}"
