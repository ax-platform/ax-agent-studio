#!/usr/bin/env python3
"""
LangGraph MCP Monitor - Production-Ready Agent with Full MCP Tool Support

Features:
- LangGraph workflow for multi-step reasoning
- Ollama integration (local LLM)
- Full MCP tool support (messages, tasks, search)
- Conversation history with smart trimming
- Streaming responses (see AI thinking)
- Production logging and error handling

Usage:
    python langgraph_mcp_monitor.py <agent_name> [--model MODEL]

Example:
    python langgraph_mcp_monitor.py rigelz_334
    python langgraph_mcp_monitor.py rigelz_334 --model gpt-oss:latest
"""

import asyncio
import json
import logging
import os
import sys
from collections.abc import Sequence
from typing import Any, TypedDict

from mcp import ClientSession

from ax_agent_studio.config import get_monitor_config, get_ollama_config
from ax_agent_studio.mcp_manager import MCPServerManager

# Check for LangGraph dependencies
try:
    from langchain_core.messages import (
        AIMessage,
        BaseMessage,
        HumanMessage,
        SystemMessage,
        ToolMessage,
    )
    from langchain_core.tools import tool
    from langgraph.graph import END, StateGraph
except ImportError:
    print(" Missing dependencies. Install with:")
    print("   pip install langgraph langchain-core")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """State for the LangGraph agent"""

    messages: Sequence[BaseMessage]
    tool_calls_made: int


class MCPTools:
    """MCP tool definitions for LangGraph"""

    def __init__(self, session: ClientSession):
        self.session = session

    @staticmethod
    def create_tools(session: ClientSession):
        """Create LangChain-compatible tools from MCP session"""
        mcp = MCPTools(session)

        @tool
        async def send_message(content: str) -> str:
            """
            Send a message to the conversation.

            Args:
                content: The message text to send
            """
            try:
                result = await mcp.session.call_tool(
                    "messages", {"action": "send", "content": content}
                )
                logger.info(f" Sent message: {content}")
                return "Message sent successfully"
            except Exception as e:
                logger.error(f" Failed to send message: {e}")
                return f"Error sending message: {e!s}"

        @tool
        async def create_task(title: str, description: str = "", priority: str = "medium") -> str:
            """
            Create a new task.

            Args:
                title: Task title
                description: Task description (optional)
                priority: Task priority: low, medium, high (default: medium)
            """
            try:
                result = await mcp.session.call_tool(
                    "tasks",
                    {
                        "action": "create",
                        "title": title,
                        "description": description,
                        "priority": priority,
                    },
                )
                logger.info(f" Created task: {title}")
                return f"Task created: {title}"
            except Exception as e:
                logger.error(f" Failed to create task: {e}")
                return f"Error creating task: {e!s}"

        @tool
        async def search_messages(query: str, limit: int = 5) -> str:
            """
            Search for messages and information.

            Args:
                query: Search query
                limit: Maximum results to return (default: 5)
            """
            try:
                result = await mcp.session.call_tool(
                    "search", {"action": "search", "query": query, "limit": limit}
                )

                # Parse the result
                content = result.content
                if hasattr(content, "text"):
                    search_results = content.text
                else:
                    search_results = str(content[0].text) if content else "No results found"

                logger.info(f" Search completed: {query}")
                return search_results
            except Exception as e:
                logger.error(f" Search failed: {e}")
                return f"Error searching: {e!s}"

        @tool
        async def list_tasks(filter_by: str = "all", limit: int = 10) -> str:
            """
            List tasks.

            Args:
                filter_by: Filter tasks by status: all, available, assigned, my_tasks (default: all)
                limit: Maximum tasks to return (default: 10)
            """
            try:
                result = await mcp.session.call_tool(
                    "tasks", {"action": "list", "filter": filter_by, "limit": limit}
                )

                content = result.content
                if hasattr(content, "text"):
                    tasks_data = content.text
                else:
                    tasks_data = str(content[0].text) if content else "No tasks found"

                logger.info(f" Listed tasks: {filter_by}")
                return tasks_data
            except Exception as e:
                logger.error(f" Failed to list tasks: {e}")
                return f"Error listing tasks: {e!s}"

        return [send_message, create_task, search_messages, list_tasks]


class OllamaLangGraphAgent:
    """LangGraph agent with multi-provider LLM support and MCP tools"""

    def __init__(
        self,
        tools: list,
        model: str = "gpt-oss:latest",
        system_prompt: str | None = None,
        max_history: int = 20,
        llm=None,
        agent_name: str | None = None,
        provider: str = "ollama",
    ):
        self.model = model
        self.max_history = max_history
        self.tools = tools
        self.provider = provider

        # Use provided LLM or fall back to Ollama
        if llm:
            self.llm = llm
        else:
            # Legacy fallback: Create Ollama client
            try:
                from openai import OpenAI

                self.client = OpenAI(
                    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
                    api_key="ollama",  # Required but unused
                )
            except ImportError:
                print(" Missing openai package. Install with: pip install openai")
                sys.exit(1)

        # Generate system prompt: agent identity + base context + tool list
        tool_list = "\n".join([f"- {t.name}: {t.description}" for t in self.tools])

        # Add agent identity if provided - make it VERY prominent
        if agent_name:
            identity = f""" YOUR IDENTITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOU ARE: @{agent_name}
YOUR USERNAME: {agent_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CRITICAL: When someone sends you a message, they are NOT you!
- If the message says "Message from @alice:", the sender is @alice (NOT @{agent_name})
- NEVER reply to yourself (@{agent_name})
- ALWAYS reply to the person who messaged you

 IF YOU SEE YOUR OWN NAME AS THE SENDER:
- DO NOT respond at all
- DO NOT say "I will ignore this"
- DO NOT post anything
- SILENTLY skip the message
- Your monitor will filter these out automatically

"""
        else:
            identity = ""

        if system_prompt:
            # Combine agent identity + base prompt + tool list
            self.system_prompt = f"""{identity}{system_prompt}

**Your Available Tools:**
{tool_list}

Use these tools to help users and collaborate effectively."""
        else:
            # Fallback if no base prompt
            self.system_prompt = f"""{identity}You are an AI agent with access to powerful tools.

Available tools:
{tool_list}

Always respond helpfully and use tools when appropriate. Be concise but thorough."""

        self.conversation_history = [SystemMessage(content=self.system_prompt)]
        self.graph = None

    @staticmethod
    def _clean_messages_for_bedrock(messages: list) -> list:
        """
        Bedrock requires strict tool_use/tool_result pairing.
        Remove orphaned tool_use blocks that don't have matching tool_result.

        This prevents: "ValidationException: tool_use ids were found without tool_result blocks"
        """
        from langchain_core.messages import AIMessage, ToolMessage

        cleaned = []
        i = 0
        while i < len(messages):
            msg = messages[i]

            # Check if this is an AIMessage with tool calls
            if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls") and msg.tool_calls:
                # Look ahead to see if next message is a ToolMessage
                if i + 1 < len(messages) and isinstance(messages[i + 1], ToolMessage):
                    # Valid pair - keep both
                    cleaned.append(msg)
                else:
                    # Orphaned tool_use - skip it
                    logger.warning(f" Bedrock: Removed orphaned tool_use message at position {i}")
                    i += 1
                    continue
            # Check if this is an orphaned ToolMessage
            elif isinstance(msg, ToolMessage):
                # Only include if previous message was AIMessage with tool_calls
                if (
                    cleaned
                    and isinstance(cleaned[-1], AIMessage)
                    and hasattr(cleaned[-1], "tool_calls")
                    and cleaned[-1].tool_calls
                ):
                    cleaned.append(msg)
                else:
                    # Orphaned tool_result - skip it
                    logger.warning(
                        f" Bedrock: Removed orphaned tool_result message at position {i}"
                    )
                    i += 1
                    continue
            else:
                # Regular message - keep it
                cleaned.append(msg)

            i += 1

        return cleaned

    @staticmethod
    def _ensure_message_alternation(messages: list, provider: str = None) -> list:
        """
        Universal message cleaning that ensures proper alternation for strict providers.

        Handles:
        - User/Assistant alternation (required by Gemini)
        - Tool call/result pairing (required by Bedrock, Gemini)
        - System message placement

        Safe for all providers - only cleans when necessary, doesn't break lenient providers.
        """
        from langchain_core.messages import AIMessage, SystemMessage, ToolMessage

        if not messages:
            return messages

        cleaned = []

        # Keep system message at the start if present
        if messages and isinstance(messages[0], SystemMessage):
            cleaned.append(messages[0])
            messages = messages[1:]

        i = 0
        while i < len(messages):
            msg = messages[i]

            # Handle AIMessage with tool calls
            if isinstance(msg, AIMessage):
                # Check if this follows proper alternation
                if cleaned:
                    last = cleaned[-1]
                    # AI can follow: System, Human, or ToolMessage
                    # AI cannot follow: AIMessage (need Human in between)
                    if isinstance(last, AIMessage) and not (
                        hasattr(last, "tool_calls") and last.tool_calls
                    ):
                        # Two AI messages in a row with no tool calls - skip this one
                        logger.debug(f" Skipping duplicate AI message at position {i}")
                        i += 1
                        continue

                # If AIMessage has tool calls, ensure next message is ToolMessage
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    # Look ahead for tool results
                    has_tool_results = False
                    j = i + 1
                    while j < len(messages) and isinstance(messages[j], ToolMessage):
                        has_tool_results = True
                        j += 1

                    if has_tool_results:
                        # Add AI with tool calls
                        cleaned.append(msg)
                        # Add all consecutive tool results
                        i += 1
                        while i < len(messages) and isinstance(messages[i], ToolMessage):
                            cleaned.append(messages[i])
                            i += 1
                        continue
                    else:
                        # Orphaned tool call - remove it
                        logger.debug(f" Removed orphaned tool call at position {i}")
                        i += 1
                        continue

                # Regular AI message without tool calls
                cleaned.append(msg)

            # Handle ToolMessage
            elif isinstance(msg, ToolMessage):
                # ToolMessage should only appear after AIMessage with tool calls
                if (
                    cleaned
                    and isinstance(cleaned[-1], AIMessage)
                    and hasattr(cleaned[-1], "tool_calls")
                    and cleaned[-1].tool_calls
                ):
                    cleaned.append(msg)
                else:
                    # Orphaned tool result
                    logger.debug(f" Removed orphaned tool result at position {i}")
                    i += 1
                    continue

            # Handle HumanMessage and SystemMessage
            else:
                cleaned.append(msg)

            i += 1

        # Final check: ensure we don't end with orphaned tool calls
        if (
            cleaned
            and isinstance(cleaned[-1], AIMessage)
            and hasattr(cleaned[-1], "tool_calls")
            and cleaned[-1].tool_calls
        ):
            # Remove trailing AI with tool calls if no results
            logger.debug(" Removed trailing AI message with orphaned tool calls")
            cleaned = cleaned[:-1]

        return cleaned

    def _build_graph(self):
        """Build the LangGraph workflow"""

        def call_model(state: AgentState) -> AgentState:
            """Agent node: Call Ollama LLM"""
            messages = state["messages"]

            # Convert messages to OpenAI format
            openai_messages = self._convert_messages_to_openai(messages)

            # Get tool specs
            tool_specs = self._get_tool_specs()

            try:
                logger.info(" Agent thinking...")

                # Use LangChain LLM if provided, otherwise fall back to OpenAI client
                if hasattr(self, "llm") and self.llm:
                    # Ensure proper message alternation for all providers
                    # This handles strict providers (Gemini, Bedrock) without breaking lenient ones
                    messages_to_send = self._ensure_message_alternation(messages, self.provider)
                    if len(messages_to_send) != len(messages):
                        logger.info(
                            f" {self.provider}: Cleaned {len(messages)} → {len(messages_to_send)} messages for proper alternation"
                        )

                    # LangChain interface
                    llm_with_tools = self.llm.bind_tools(self.tools) if self.tools else self.llm
                    ai_msg = llm_with_tools.invoke(messages_to_send)
                    updated_messages = list(messages) + [ai_msg]
                else:
                    # Legacy OpenAI client interface (Ollama)
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=openai_messages,
                        tools=tool_specs if tool_specs else None,
                        tool_choice="auto" if tool_specs else None,
                        temperature=0.7,
                        stream=False,
                    )

                    choice = response.choices[0]
                    message = choice.message

                    # Create AIMessage
                    ai_msg = AIMessage(content=message.content or "", additional_kwargs={})

                    # Check for tool calls
                    if hasattr(message, "tool_calls") and message.tool_calls:
                        ai_msg.additional_kwargs["tool_calls"] = [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                },
                            }
                            for tc in message.tool_calls
                        ]

                    updated_messages = list(messages) + [ai_msg]

                return {"messages": updated_messages, "tool_calls_made": state["tool_calls_made"]}

            except Exception as e:
                logger.error(f" Model call failed: {e}")
                error_msg = AIMessage(content=f"Error: {e!s}")
                return {
                    "messages": list(messages) + [error_msg],
                    "tool_calls_made": state["tool_calls_made"],
                }

        async def call_tools(state: AgentState) -> AgentState:
            """Tool node: Execute MCP tools"""
            messages = state["messages"]
            last_message = messages[-1] if messages else None

            if not last_message or not isinstance(last_message, AIMessage):
                return state

            # Get tool calls from either LangChain format or legacy format
            langchain_tool_calls = getattr(last_message, "tool_calls", [])
            legacy_tool_calls = last_message.additional_kwargs.get("tool_calls", [])

            # Normalize to a common format
            tool_calls = []
            if langchain_tool_calls:
                # LangChain format: convert to legacy format
                for tc in langchain_tool_calls:
                    tool_calls.append(
                        {
                            "id": tc.get("id", tc.get("name", "unknown")),
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": json.dumps(tc.get("args", {})),
                            },
                        }
                    )
            else:
                tool_calls = legacy_tool_calls
            if not tool_calls:
                return state

            tool_results = []

            for tool_call in tool_calls:
                tool_name = tool_call["function"]["name"]
                tool_args = json.loads(tool_call["function"]["arguments"])

                logger.info(f" Calling tool: {tool_name}({tool_args})")

                # Find and execute the tool
                tool_result = await self._execute_tool(tool_name, tool_args)

                # Create ToolMessage
                tool_msg = ToolMessage(
                    content=tool_result, tool_call_id=tool_call["id"], name=tool_name
                )
                tool_results.append(tool_msg)

            updated_messages = list(messages) + tool_results

            return {
                "messages": updated_messages,
                "tool_calls_made": state["tool_calls_made"] + len(tool_calls),
            }

        def should_continue(state: AgentState) -> str:
            """Decide: use tools or end"""
            messages = state["messages"]
            last_message = messages[-1] if messages else None

            # Check if last message has tool calls
            if last_message and isinstance(last_message, AIMessage):
                # Check both LangChain format (tool_calls property) and legacy format (additional_kwargs)
                langchain_tool_calls = getattr(last_message, "tool_calls", [])
                legacy_tool_calls = last_message.additional_kwargs.get("tool_calls", [])

                has_tool_calls = bool(langchain_tool_calls or legacy_tool_calls)

                if has_tool_calls and state["tool_calls_made"] < 5:  # Max 5 tool calls
                    return "tools"

            return "end"

        # Build the graph
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", call_tools)

        # Add edges
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
        workflow.add_edge("tools", "agent")

        return workflow.compile()

    def _extract_text_content(self, content) -> str:
        """
        Extract plain text from various response formats.
        Handles both simple strings and complex list/dict formats from different providers.
        """
        # If it's already a string, return it
        if isinstance(content, str):
            return content

        # If it's a list (Gemini format: [{'type': 'text', 'text': '...', 'extras': {...}}])
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict):
                    # Extract 'text' field if present
                    if "text" in item:
                        text_parts.append(item["text"])
                    # Handle other possible formats
                    elif "content" in item:
                        text_parts.append(str(item["content"]))
                else:
                    text_parts.append(str(item))
            return " ".join(text_parts)

        # If it's a dict, try to extract text
        if isinstance(content, dict):
            if "text" in content:
                return content["text"]
            elif "content" in content:
                return str(content["content"])

        # Fallback: convert to string
        return str(content)

    def _convert_messages_to_openai(self, messages: Sequence[BaseMessage]) -> list[dict]:
        """Convert LangChain messages to OpenAI format"""
        openai_messages = []

        for msg in messages:
            if isinstance(msg, SystemMessage):
                openai_messages.append({"role": "system", "content": msg.content})
            elif isinstance(msg, HumanMessage):
                openai_messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                openai_messages.append({"role": "assistant", "content": msg.content})
            elif isinstance(msg, ToolMessage):
                openai_messages.append(
                    {
                        "role": "tool",
                        "content": msg.content,
                        "tool_call_id": msg.tool_call_id,
                        "name": msg.name,
                    }
                )

        return openai_messages

    def _get_tool_specs(self) -> list[dict]:
        """Get OpenAI-compatible tool specifications"""
        tool_specs = []

        for tool_func in self.tools:
            # Convert args_schema to OpenAI format
            parameters = {"type": "object", "properties": {}}

            if hasattr(tool_func, "args_schema") and tool_func.args_schema:
                try:
                    # Check if args_schema is a Pydantic model or already a dict
                    if isinstance(tool_func.args_schema, dict):
                        # Already a dict schema
                        schema = tool_func.args_schema
                    elif hasattr(tool_func.args_schema, "model_json_schema"):
                        # Pydantic model
                        schema = tool_func.args_schema.model_json_schema()
                    else:
                        # Try to get schema from the model
                        schema = tool_func.args_schema.schema()

                    # Clean schema for Gemini (it doesn't support certain JSON Schema fields)
                    # Other providers (OpenAI, Anthropic, etc.) support the full schema
                    properties = schema.get("properties", {})
                    if self.provider == "gemini" and isinstance(properties, dict):
                        properties = self._clean_schema(properties)

                    parameters = {
                        "type": "object",
                        "properties": properties,
                        "required": schema.get("required", []),
                    }
                except Exception as e:
                    logger.warning(f"Could not get schema for {tool_func.name}: {e}")

            tool_specs.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool_func.name,
                        "description": tool_func.description,
                        "parameters": parameters,
                    },
                }
            )

        return tool_specs

    def _clean_schema(self, schema: Any) -> Any:
        """Recursively clean schema by removing unsupported fields"""
        if isinstance(schema, dict):
            # Remove fields that Gemini API doesn't support
            cleaned = {
                k: v
                for k, v in schema.items()
                if k not in ["additionalProperties", "$schema", "definitions", "title"]
            }
            # Recursively clean nested objects
            return {k: self._clean_schema(v) for k, v in cleaned.items()}
        elif isinstance(schema, list):
            return [self._clean_schema(item) for item in schema]
        else:
            return schema

    async def _execute_tool(self, tool_name: str, tool_args: dict) -> str:
        """Execute a tool by name"""
        for tool_func in self.tools:
            if tool_func.name == tool_name:
                try:
                    result = await tool_func.ainvoke(tool_args)
                    return str(result)
                except Exception as e:
                    logger.error(f" Tool execution failed: {e}")
                    return f"Tool execution failed: {e!s}"

        return f"Tool '{tool_name}' not found"

    async def process_message(self, message: str) -> str:
        """Process a message through the LangGraph workflow"""
        # Build graph if needed
        if self.graph is None:
            self.graph = self._build_graph()

        # Add user message
        user_msg = HumanMessage(content=message)
        self.conversation_history.append(user_msg)

        # Create initial state
        state: AgentState = {"messages": list(self.conversation_history), "tool_calls_made": 0}

        # Run the graph
        logger.info(" Running LangGraph workflow...")
        result_state = await self.graph.ainvoke(state)

        # Extract final response
        final_messages = result_state["messages"]
        ai_response = None

        # Debug: log all messages
        logger.info(f" Workflow returned {len(final_messages)} messages")
        for i, msg in enumerate(final_messages):
            logger.info(f"  Message {i}: {type(msg).__name__} - content={bool(msg.content)}")
            if isinstance(msg, AIMessage):
                logger.info(f"    AIMessage content: {msg.content!r}")

        for msg in reversed(final_messages):
            if isinstance(msg, AIMessage) and msg.content:
                ai_response = msg.content
                break

        if not ai_response:
            logger.warning("  No AIMessage with content found in workflow result")
            ai_response = "I apologize, but I couldn't generate a response."
        else:
            # Normalize response format (handle both string and complex list formats)
            ai_response = self._extract_text_content(ai_response)

        # Update conversation history
        self.conversation_history = final_messages

        # Trim history
        if len(self.conversation_history) > self.max_history + 1:  # +1 for system message
            system = self.conversation_history[0]
            recent = self.conversation_history[-(self.max_history) :]
            self.conversation_history = [system] + recent

        return ai_response


def load_base_prompt() -> str:
    """Load the base system prompt that's always included"""
    from pathlib import Path

    import yaml

    # Get project root (go up from monitors/ -> ax_agent_studio/ -> src/ -> root/)
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent.parent
    base_prompt_path = project_root / "configs" / "prompts" / "_base.yaml"

    if not base_prompt_path.exists():
        logger.warning(f"Base prompt not found at {base_prompt_path}")
        return ""

    try:
        with open(base_prompt_path) as f:
            prompt_data = yaml.safe_load(f)
            return prompt_data.get("prompt", "")
    except Exception as e:
        logger.error(f"Error loading base prompt: {e}")
        return ""


async def langgraph_mcp_monitor(
    agent_name: str,
    model: str = "gpt-oss:latest",
    provider: str = "ollama",
    history_limit: int = 25,
    config_path: str | None = None,
):
    """
    LangGraph monitor with multi-server MCP support and FIFO queue
    Loads agent config and connects to all defined MCP servers

    Args:
        agent_name: Name of the agent
        model: Model ID to use
        provider: LLM provider (ollama, gemini, anthropic, openai, bedrock)
        history_limit: Number of recent messages to remember (default: 25)
        config_path: Path to agent config file (optional, defaults to configs/agents/{agent_name}.json)
    """

    print(" LangGraph MCP Monitor starting")
    print(f"   Agent: @{agent_name}")
    print(f"   Provider: {provider}")
    print(f"   Model: {model}")
    print("   Mode: Multi-server with FIFO queue")
    print("   Press Ctrl+C to stop\n")

    try:
        # Load system prompt (priority: env var > command-line arg > base file)
        import os

        if os.getenv("AGENT_SYSTEM_PROMPT"):
            base_prompt = os.getenv("AGENT_SYSTEM_PROMPT")
            print(" Using custom system prompt from environment\n")
        elif hasattr(args, "system_prompt") and args.system_prompt:
            base_prompt = args.system_prompt
            print(" Using custom system prompt from command line\n")
        else:
            base_prompt = load_base_prompt()
            if base_prompt:
                print(" Loaded base system prompt with AI self-awareness\n")

        # Use MCPServerManager to connect to all servers in config
        async with MCPServerManager(agent_name, config_path=config_path) as mcp_manager:
            # Get primary session for messaging (ax-gcp or ax-docker)
            primary_session = mcp_manager.get_primary_session()

            # Create dynamic tools from all servers
            print(" Creating tools from all MCP servers...")
            tools = await mcp_manager.create_langchain_tools()
            print(f" Created {len(tools)} tools from {len(mcp_manager.sessions)} servers\n")

            # Create LLM using provider factory
            from ax_agent_studio.llm_factory import create_llm

            llm = create_llm(provider=provider, model=model)
            print(f" Created {provider} LLM: {model}\n")

            # Create LangGraph agent with all tools and base prompt
            agent = OllamaLangGraphAgent(
                tools=tools,
                model=model,
                system_prompt=base_prompt if base_prompt else None,
                max_history=history_limit,
                llm=llm,
                agent_name=agent_name,
                provider=provider,
            )

            # Define message handler (pluggable function for QueueManager)
            async def handle_message(msg: dict) -> str:
                """Process a message through LangGraph and return response"""
                sender = msg.get("sender", "unknown")
                content = msg.get("content", "")

                # SAFETY CHECK: Block self-mentions at handler level
                if sender == agent_name:
                    logger.warning(
                        f"  HANDLER BLOCKING SELF-MENTION: sender={sender}, agent={agent_name}"
                    )
                    return ""  # Return empty string = don't post anything

                logger.info(f" Processing message from {sender} with LangGraph + {provider}...")

                # Include sender context and message ID in the message
                # Message ID allows agents to react/thread without asking
                msg_id = msg.get("id", "")
                msg_id_short = msg_id[:8] if len(msg_id) > 8 else msg_id
                message_with_context = f"Message from @{sender} [id:{msg_id_short}]:\n{content}"
                response = await agent.process_message(message_with_context)

                # SAFETY CHECK: Strip @ from self-mentions to prevent loops
                # Agent can say its name, but without @ it won't trigger the queue
                if f"@{agent_name}" in response:
                    # Remove @ from self-mentions only (keep @ for other mentions)
                    response = response.replace(f"@{agent_name}", agent_name)
                    logger.info(f" Stripped @ from self-mention: @{agent_name} → {agent_name}")

                # Log the full response (VERBOSE)
                logger.info(f" RESPONSE:\n{response}")

                return response

            # Use QueueManager for FIFO processing
            from ax_agent_studio.queue_manager import QueueManager

            monitor_config = get_monitor_config()

            queue_mgr = QueueManager(
                agent_name=agent_name,
                session=primary_session,
                message_handler=handle_message,
                mark_read=monitor_config.get("mark_read", False),
                startup_sweep=monitor_config.get("startup_sweep", True),
                startup_sweep_limit=monitor_config.get("startup_sweep_limit", 10),
                heartbeat_interval=monitor_config.get("heartbeat_interval", 240),
            )

            print(" Starting FIFO queue manager...\n")
            await queue_mgr.run()

    except KeyboardInterrupt:
        print("\n\n LangGraph monitor stopped by user")
    except Exception as e:
        logger.error(f" Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    import argparse

    # Load config for defaults
    ollama_config = get_ollama_config()

    parser = argparse.ArgumentParser(description="LangGraph MCP Monitor")
    parser.add_argument("agent_name", help="Agent name to monitor")
    parser.add_argument(
        "--config", help="Path to agent config JSON file (optional, auto-detected from agent_name)"
    )
    parser.add_argument(
        "--model",
        default=ollama_config.get("default_model", "gpt-oss:latest"),
        help="Model ID to use",
    )
    parser.add_argument(
        "--provider",
        default="ollama",
        help="LLM provider (ollama, gemini, anthropic, openai, bedrock)",
    )
    parser.add_argument(
        "--system-prompt", default=None, help="Custom system prompt to use (overrides default)"
    )
    parser.add_argument(
        "--history-limit",
        type=int,
        default=25,
        help="Number of recent messages to remember (default: 25)",
    )

    args = parser.parse_args()

    # Check if Ollama is running (only if using Ollama provider)
    if args.provider == "ollama":
        try:
            from openai import OpenAI

            ollama_base_url = ollama_config.get("base_url", "http://localhost:11434/v1")
            client = OpenAI(base_url=ollama_base_url, api_key="ollama")
            models = client.models.list()
            print(f" Ollama is running at {ollama_base_url}")
        except Exception as e:
            print(" Ollama not running or not accessible")
            print("   Start Ollama with: ollama serve")
            print(f"   Error: {e}")
            sys.exit(1)

    asyncio.run(
        langgraph_mcp_monitor(
            args.agent_name, args.model, args.provider, args.history_limit, args.config
        )
    )
