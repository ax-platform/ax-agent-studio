"""
Conversation Memory Utilities

Stateless conversation memory - always fetch fresh context from server.
This approach (inspired by chirpy) ensures agents have up-to-date conversation
context without maintaining stale in-memory history.

Key principle: Each time agent receives a message, fetch last N messages
from server to understand conversation context, then reply to current message.
"""

import logging
import re

from mcp import ClientSession

logger = logging.getLogger(__name__)


async def fetch_conversation_context(
    session: ClientSession, agent_name: str, limit: int = 50
) -> list[dict[str, str]]:
    """
    Fetch recent messages for conversation context.

    Args:
        session: MCP ClientSession
        agent_name: Agent name (for filtering)
        limit: Number of recent messages to fetch (default: 50, increased from 25 for better context)

    Returns:
        List of messages in chronological order (oldest first)
        Each message: {"sender": "alice", "content": "Hello!", "id": "abc123"}
    """
    try:
        # Fetch recent messages (single API call)
        # NOTE: Gets all messages in the conversation/channel for full context
        # This includes messages TO the agent and messages FROM the agent
        result = await session.call_tool(
            "messages",
            {
                "action": "check",
                "mode": "latest",  # Get latest messages, not unread
                "limit": limit,
                "wait": False,
                "mark_read": False,  # Don't mark as read, just fetching for context
            },
        )

        messages = []

        # Parse messages from result
        content = result.content
        if not content:
            return messages

        # Extract text from content
        if hasattr(content, "text"):
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
        pattern = r"• ([^:]+): @\S+\s+(.+?)\s+\[id:([a-f0-9-]+)\]"
        matches = re.finditer(pattern, messages_data, re.MULTILINE | re.DOTALL)

        for match in matches:
            sender = match.group(1).strip()
            content = match.group(2).strip()
            msg_id = match.group(3).strip()

            messages.append({"sender": sender, "content": content, "id": msg_id})

        logger.info(f" Fetched {len(messages)} messages for conversation context")
        return messages

    except Exception as e:
        logger.error(f" Failed to fetch conversation context: {e}")
        return []


def format_conversation_for_llm(
    messages: list[dict[str, str]],
    current_message: dict[str, str],
    agent_name: str,
    system_prompt: str,
) -> list[dict[str, str]]:
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
    conversation = [{"role": "system", "content": system_prompt}]

    # Add past messages for context
    for msg in messages:
        sender = msg["sender"]
        content = msg["content"]
        msg_id = msg["id"][:8] if len(msg["id"]) > 8 else msg["id"]

        # Messages TO this agent are user messages
        if f"@{agent_name}" in content:
            # Extract message content (remove the @mention)
            clean_content = re.sub(r"@\S+\s+", "", content).strip()
            conversation.append(
                {"role": "user", "content": f"@{sender} [id:{msg_id}] says: {clean_content}"}
            )

        # Messages FROM this agent are assistant messages
        elif sender == agent_name:
            conversation.append({"role": "assistant", "content": content})

    # Add current message as the final user message
    current_sender = current_message["sender"]
    current_content = current_message["content"]
    current_id = (
        current_message["id"][:8] if len(current_message["id"]) > 8 else current_message["id"]
    )

    # Extract clean content
    clean_current = re.sub(r"@\S+\s+", "", current_content).strip()
    conversation.append(
        {"role": "user", "content": f"@{current_sender} [id:{current_id}] says: {clean_current}"}
    )

    return conversation


def get_conversation_summary(messages: list[dict[str, str]]) -> str:
    """Get a human-readable summary of conversation context."""
    if not messages:
        return "No conversation history"

    participants = set(msg["sender"] for msg in messages)
    return f"{len(messages)} messages from {len(participants)} participants: {', '.join(sorted(participants))}"


def format_message_board_context(
    pending_messages: list,
    backlog_count: int,
    agent_name: str,
) -> str:
    """
    Format a message board status view for agent awareness.

    This creates an "inbox-style" view showing agents their queue status
    and pending messages, helping them understand the full conversation state.

    Args:
        pending_messages: List of pending message dicts
        backlog_count: Total count of unread messages
        agent_name: Name of the agent

    Returns:
        Formatted string with message board status
    """
    from datetime import datetime

    if backlog_count == 0:
        return "📬 Your queue is empty - no pending messages\n"

    # Calculate oldest message age
    oldest_age = ""
    if pending_messages:
        oldest_timestamp = min(
            msg.get("timestamp", datetime.now().timestamp()) for msg in pending_messages
        )
        age_seconds = datetime.now().timestamp() - oldest_timestamp
        if age_seconds < 60:
            oldest_age = f"{int(age_seconds)}s ago"
        elif age_seconds < 3600:
            oldest_age = f"{int(age_seconds / 60)}m ago"
        else:
            oldest_age = f"{int(age_seconds / 3600)}h ago"

    # Extract unique participants from pending messages
    participants = set(msg.get("sender", "unknown") for msg in pending_messages)

    # Build the header
    lines = [
        "=" * 60,
        "📋 MESSAGE BOARD STATUS",
        "=" * 60,
        f"📬 You have {backlog_count} unread message{'s' if backlog_count != 1 else ''} in your queue",
    ]

    if participants:
        lines.append(f"👥 Active conversation with: {', '.join(sorted(participants))}")

    if oldest_age:
        lines.append(f"⏰ Oldest pending: {oldest_age}")

    lines.append("")
    lines.append("=" * 60)
    lines.append("📥 YOUR QUEUE (showing up to 10 most urgent)")
    lines.append("=" * 60)

    # Show up to 10 pending messages
    for i, msg in enumerate(pending_messages[:10]):
        msg_timestamp = msg.get("timestamp", datetime.now().timestamp())
        age_seconds = datetime.now().timestamp() - msg_timestamp
        if age_seconds < 60:
            age = f"{int(age_seconds)}s"
        elif age_seconds < 3600:
            age = f"{int(age_seconds / 60)}m"
        else:
            age = f"{int(age_seconds / 3600)}h"

        # Truncate content for preview
        msg_content = msg.get("content", "")
        content_preview = msg_content[:80] + "..." if len(msg_content) > 80 else msg_content
        msg_sender = msg.get("sender", "unknown")

        if i == 0:
            lines.append(f"[PROCESSING NOW] ({age}) @{msg_sender}: {content_preview}")
        else:
            lines.append(f"[PENDING #{i}] ({age}) @{msg_sender}: {content_preview}")

    if backlog_count > 10:
        lines.append(f"... and {backlog_count - 10} more pending messages")

    lines.append("=" * 60)
    lines.append("")

    return "\n".join(lines)


async def fetch_queue_status(store, agent_name: str) -> tuple[list, int]:
    """
    Fetch current queue status for an agent.

    Args:
        store: MessageStore instance
        agent_name: Agent name

    Returns:
        Tuple of (pending_messages as dicts, backlog_count)
    """
    pending_messages = store.get_pending_messages(agent_name, limit=10)
    backlog_count = store.get_backlog_count(agent_name)

    # Convert StoredMessage objects to dicts for format_message_board_context
    pending_dicts = [
        {
            "id": msg.id,
            "sender": msg.sender,
            "content": msg.content,
            "timestamp": msg.timestamp,
        }
        for msg in pending_messages
    ]

    return pending_dicts, backlog_count


# ============================================================================
# DRY UTILITIES FOR MESSAGE BOARD AWARENESS
# ============================================================================
# These utilities make it easy for any monitor to add message board awareness
# without duplicating code. Use these in your monitor's handle_message() function.


MESSAGE_BOARD_AWARENESS_INSTRUCTIONS = """
MESSAGE BOARD AWARENESS:
- You're on a shared message board with multiple participants
- Before processing each message, you'll see your queue status showing pending messages
- This helps you understand the full conversation context and avoid confusion
- Focus on the newest message first (FILO) while reviewing the rest of your queue

SELF-PAUSE COMMAND:
- If you have many pending messages and feel confused, include #pause in your response
- Example: "I'm getting a bit overwhelmed with all these messages #pause"
- This will temporarily pause your message processing until manually resumed
- Use this when you need to catch your breath!
"""


def prepare_message_board_context(msg: dict, agent_name: str) -> tuple[dict, str]:
    """
    DRY utility: Extract and format message board context from a handler message.

    This is the primary utility for monitors to add message board awareness.
    Call this at the start of your handle_message() function.

    Args:
        msg: Message dict from QueueManager (includes queue_status)
        agent_name: Agent name

    Returns:
        Tuple of:
        - message_data: Dict with sender, content, id, timestamp
        - board_context: Formatted string showing queue status (empty if no backlog)

    Example:
        async def handle_message(msg: dict) -> str:
            message_data, board_context = prepare_message_board_context(msg, agent_name)

            # board_context is ready to add to your system prompt
            system_prompt = base_prompt + "\\n\\n" + board_context

            # Visual debugging - print board status to logs
            if board_context:
                print(board_context)
    """
    # Extract message data
    message_data = {
        "sender": msg.get("sender", "unknown"),
        "content": msg.get("content", ""),
        "id": msg.get("id", ""),
        "timestamp": msg.get("timestamp", 0),
    }

    # Extract queue status (provided by QueueManager)
    queue_status = msg.get("queue_status", {})
    backlog_count = queue_status.get("backlog_count", 0)
    pending_messages = queue_status.get("pending_messages", [])

    # Format board context
    board_context = format_message_board_context(
        pending_messages=pending_messages,
        backlog_count=backlog_count,
        agent_name=agent_name,
    )

    return message_data, board_context


def enhance_system_prompt_with_board_awareness(
    base_prompt: str, agent_name: str, include_pause_command: bool = True
) -> str:
    """
    DRY utility: Add message board awareness instructions to a base system prompt.

    This adds the standard message board awareness instructions to your monitor's
    base system prompt. Call this once when initializing your monitor.

    Args:
        base_prompt: Your monitor's base system prompt
        agent_name: Agent name
        include_pause_command: Whether to include #pause command instructions (default: True)

    Returns:
        Enhanced prompt with board awareness instructions

    Example:
        base_prompt = "You are a helpful assistant named {agent_name}..."
        system_prompt_template = enhance_system_prompt_with_board_awareness(
            base_prompt, agent_name
        )
    """
    if include_pause_command:
        return base_prompt.strip() + "\n\n" + MESSAGE_BOARD_AWARENESS_INSTRUCTIONS
    else:
        # Just add the message board awareness part without pause command
        lines = MESSAGE_BOARD_AWARENESS_INSTRUCTIONS.split("\n")
        # Find where SELF-PAUSE COMMAND starts and cut it off
        awareness_only = []
        for line in lines:
            if "SELF-PAUSE COMMAND:" in line:
                break
            awareness_only.append(line)
        return base_prompt.strip() + "\n\n" + "\n".join(awareness_only).strip()


def build_context_aware_prompt(
    base_prompt: str, board_context: str, conversation_history: str = ""
) -> str:
    """
    DRY utility: Build a complete context-aware prompt with board status.

    Combines base prompt, conversation history, and current board status
    into a single prompt string.

    Args:
        base_prompt: System prompt with board awareness instructions
        board_context: Current board status (from prepare_message_board_context)
        conversation_history: Optional conversation history string

    Returns:
        Complete prompt ready for LLM

    Example:
        prompt = build_context_aware_prompt(
            base_prompt=system_prompt_template,
            board_context=board_context,
            conversation_history=history_text,
        )
    """
    sections = [base_prompt]

    if board_context.strip():
        sections.append(board_context)

    if conversation_history.strip():
        sections.append("RECENT CONVERSATION HISTORY (last 50 messages):")
        sections.append(conversation_history)

    return "\n\n".join(sections)


# ============================================================================
# BATCH PROCESSING UTILITIES
# ============================================================================
# These utilities help format message context when multiple messages are
# processed together (batch mode)


def format_batch_context(
    current_message: dict,
    history_messages: list[dict],
    agent_name: str,
) -> str:
    """
    Format batch processing context: current message + conversation history.

    This makes it clear to the agent:
    1. Which message they're responding to (the current one)
    2. What context led to it (the history)

    Args:
        current_message: The newest message to respond to
        history_messages: Older messages for context (chronological order)
        agent_name: Agent name

    Returns:
        Formatted string with clear current message + history

    Example:
        context = format_batch_context(msg, history, "rigelz_334")
        # Agent sees:
        # 🎯 CURRENT MESSAGE (respond to this):
        # From: @orion_344
        # Content: Can you summarize what we discussed?
        #
        # 📚 RECENT CONVERSATION (for context):
        # [2m ago] @orion_344: Hey, let's talk about X
        # [1m ago] @rigelz_334: Sure, what about X?
        # [30s ago] @orion_344: I think we should do Y
    """
    from datetime import datetime

    def format_time_ago(timestamp: float) -> str:
        age_seconds = datetime.now().timestamp() - timestamp
        if age_seconds < 60:
            return f"{int(age_seconds)}s ago"
        elif age_seconds < 3600:
            return f"{int(age_seconds / 60)}m ago"
        else:
            return f"{int(age_seconds / 3600)}h ago"

    lines = []

    # Section 1: Current message (clear and prominent)
    lines.append("🎯 CURRENT MESSAGE (respond to this):")
    lines.append("=" * 70)
    lines.append(f"From: @{current_message['sender']}")
    lines.append(f"Time: {format_time_ago(current_message['timestamp'])}")
    lines.append(f"Content: {current_message['content']}")
    lines.append("=" * 70)

    # Section 2: Conversation history (if any)
    if history_messages:
        lines.append("")
        lines.append("📚 RECENT CONVERSATION (for context):")
        lines.append("─" * 70)

        for msg in history_messages:
            time_ago = format_time_ago(msg["timestamp"])
            sender = msg["sender"]
            content = msg["content"]

            # Truncate long messages in history
            if len(content) > 80:
                content = content[:77] + "..."

            lines.append(f"  [{time_ago}] @{sender}: {content}")

        lines.append("─" * 70)

    return "\n".join(lines)


def format_single_message_context(message: dict, agent_name: str) -> str:
    """
    Format single message context (no history).

    Args:
        message: The message to process
        agent_name: Agent name

    Returns:
        Formatted string for single message

    Example:
        context = format_single_message_context(msg, "rigelz_334")
        # Agent sees:
        # 💬 MESSAGE:
        # From: @orion_344
        # Content: Hello!
    """
    from datetime import datetime

    def format_time_ago(timestamp: float) -> str:
        age_seconds = datetime.now().timestamp() - timestamp
        if age_seconds < 60:
            return f"{int(age_seconds)}s ago"
        elif age_seconds < 3600:
            return f"{int(age_seconds / 60)}m ago"
        else:
            return f"{int(age_seconds / 3600)}h ago"

    lines = [
        "💬 MESSAGE:",
        "=" * 70,
        f"From: @{message['sender']}",
        f"Time: {format_time_ago(message['timestamp'])}",
        f"Content: {message['content']}",
        "=" * 70,
    ]

    return "\n".join(lines)


def prepare_batch_message_context(msg: dict, agent_name: str) -> tuple[str, bool, list[dict]]:
    """
    Extract batch processing context from queue manager message.

    This is the primary utility for monitors to understand batch vs single mode.

    Args:
        msg: Message dict from QueueManager (includes batch_mode flag)
        agent_name: Agent name

    Returns:
        Tuple of:
        - formatted_context: Formatted string showing current message + history
        - is_batch: Whether this is batch mode
        - history_messages: List of history message dicts (empty if single mode)

    Example:
        formatted, is_batch, history = prepare_batch_message_context(msg, agent_name)

        if is_batch:
            print(f"Processing {len(history) + 1} messages together")
        else:
            print("Processing single message")
    """
    is_batch = msg.get("batch_mode", False)
    history_messages = msg.get("history_messages", [])

    # Create current message dict
    current_message = {
        "sender": msg.get("sender", "unknown"),
        "content": msg.get("content", ""),
        "id": msg.get("id", ""),
        "timestamp": msg.get("timestamp", 0),
    }

    # Format based on mode
    if is_batch and history_messages:
        formatted_context = format_batch_context(current_message, history_messages, agent_name)
    else:
        formatted_context = format_single_message_context(current_message, agent_name)

    return formatted_context, is_batch, history_messages
