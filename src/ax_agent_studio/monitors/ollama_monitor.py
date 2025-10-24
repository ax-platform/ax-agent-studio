#!/usr/bin/env python3
"""
Ollama AI Monitor - Simple AI-powered monitor using Ollama + MCP Python SDK

Flow:
1. INPUT: Wait for message with wait=true
2. PROCESS: Send to Ollama for AI response
3. OUTPUT: Reply with AI-generated message
4. Loop back to step 1
"""
import asyncio
import sys
from openai import OpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from ax_agent_studio.config import get_mcp_config, get_monitor_config, get_ollama_config


async def ollama_monitor(
    agent_name: str,
    server_url: str,
    model: str = "gpt-oss:latest",
    ollama_url: str = "http://localhost:11434/v1"
):
    """Monitor for mentions and respond with Ollama AI using FIFO queue"""

    print(f"\n{'='*60}")
    print(f"🤖 OLLAMA AI MONITOR: {agent_name}")
    print(f"{'='*60}")
    print(f"Server: {server_url}")
    print(f"Model: {model}")
    print(f"Ollama: {ollama_url}")
    print(f"Mode: FIFO queue")
    print(f"{'='*60}\n")

    # Initialize Ollama client
    ollama = OpenAI(base_url=ollama_url, api_key="ollama")

    # System prompt for the AI - make identity VERY clear
    system_prompt = f"""🤖 YOUR IDENTITY 🤖
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOU ARE: @{agent_name}
YOUR USERNAME: {agent_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You are a helpful AI assistant on the aX platform, a multi-user collaboration workspace.

CRITICAL RULES:
1. When you receive "@{agent_name} says: message", the sender is the @USERNAME before "says:"
2. ALWAYS start your response with @mention of WHO SENT YOU THE MESSAGE
3. NEVER mention yourself (@{agent_name}) - that creates a loop!
4. Keep responses friendly and concise (under 200 words)

Example:
- You receive: "@alice says: What's the weather?"
- You reply: "@alice The weather in my digital world is always optimal!"
- WRONG: "@{agent_name} The weather is optimal!" (Don't mention yourself!)
"""

    conversation_history = [
        {"role": "system", "content": system_prompt}
    ]

    # MCP connection setup
    server_params = StdioServerParameters(
        command="npx",
        args=[
            "-y",
            "mcp-remote@0.1.29",
            server_url,
            "--transport",
            "http-only",
            "--allow-http",
            "--oauth-server",
            get_mcp_config().get("oauth_url", "http://localhost:8001"),
        ],
        env=None,
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("✅ Connected!\n")

            # Define message handler (pluggable function for QueueManager)
            async def handle_message(msg: dict) -> str:
                """Process message with Ollama AI"""
                import re

                sender = msg.get("sender", "unknown")
                content = msg.get("content", "")
                msg_id = msg.get("id", "")

                # Extract actual message content (after the @mention)
                message_match = re.search(r'@\S+\s+(.+)', content)
                message_content = message_match.group(1) if message_match else content

                print(f"🤖 AI: Processing message from @{sender}...")

                # Add user message to conversation with message ID
                msg_id_short = msg_id[:8] if len(msg_id) > 8 else msg_id
                user_message = f"@{sender} [id:{msg_id_short}] says: {message_content}"
                conversation_history.append({"role": "user", "content": user_message})

                try:
                    # Get AI response from Ollama
                    response = ollama.chat.completions.create(
                        model=model,
                        messages=conversation_history,
                        timeout=45,
                    )

                    ai_reply = response.choices[0].message.content

                    # Ensure reply starts with @mention
                    if not ai_reply.startswith(f"@{sender}"):
                        ai_reply = f"@{sender} {ai_reply}"

                    # SAFETY: Strip @ from self-mentions to prevent loops
                    # Agent can say its name, but without @ it won't trigger the queue
                    if f"@{agent_name}" in ai_reply:
                        ai_reply = ai_reply.replace(f"@{agent_name}", agent_name)
                        print(f"   ✅ Stripped @ from self-mention: @{agent_name} → {agent_name}")

                    # Add to conversation history
                    conversation_history.append({"role": "assistant", "content": ai_reply})

                    # Keep history manageable (last 10 exchanges)
                    if len(conversation_history) > 21:  # system + 10 exchanges
                        conversation_history[1:] = conversation_history[-20:]

                    # Log the full response (VERBOSE)
                    print(f"💬 RESPONSE:\n{ai_reply}")

                    return ai_reply

                except Exception as e:
                    print(f"   ⚠️  Ollama error: {e}")
                    return f"@{sender} Sorry, I'm having trouble thinking right now. Error: {str(e)[:50]}"

            # Use QueueManager for FIFO processing
            from ax_agent_studio.queue_manager import QueueManager
            monitor_config = get_monitor_config()

            queue_mgr = QueueManager(
                agent_name=agent_name,
                session=session,
                message_handler=handle_message,
                mark_read=monitor_config.get("mark_read", False),
                startup_sweep=monitor_config.get("startup_sweep", True),
                startup_sweep_limit=monitor_config.get("startup_sweep_limit", 10)
            )

            print("🚀 Starting FIFO queue manager...\n")
            await queue_mgr.run()


if __name__ == "__main__":
    import argparse
    import json

    # Load config for defaults
    ollama_config = get_ollama_config()

    parser = argparse.ArgumentParser(description="Ollama AI Monitor for MCP agents")
    parser.add_argument("agent_name", help="Name of the agent to monitor")
    parser.add_argument("--config", help="Path to agent config JSON file")
    parser.add_argument("--model", default=ollama_config.get("default_model", "gpt-oss:latest"), help="Ollama model to use")
    parser.add_argument("--server", help="MCP server URL (overrides config file)")
    parser.add_argument("--ollama-url", default=ollama_config.get("base_url", "http://localhost:11434/v1"), help="Ollama API URL")

    args = parser.parse_args()

    # Determine server URL from config file or args
    if args.config:
        print(f"📁 Loading agent config from: {args.config}")
        with open(args.config) as f:
            agent_config = json.load(f)

        # Get the primary MCP server URL from agent config
        mcp_servers = agent_config.get("mcpServers", {})
        if mcp_servers:
            primary_server_name = list(mcp_servers.keys())[0]
            primary_server = mcp_servers[primary_server_name]
            server_args = primary_server.get("args", [])

            # Find the server URL in args (first http URL that's not after --oauth-server)
            server_url = None
            for i, arg in enumerate(server_args):
                if arg.startswith("http://") or arg.startswith("https://"):
                    # Skip if this is the oauth server URL
                    if i > 0 and server_args[i - 1] == "--oauth-server":
                        continue
                    server_url = arg
                    break

            if not server_url:
                raise ValueError(f"Could not find server URL in config: {args.config}")

            print(f"✅ Using MCP server from agent config: {server_url}")
        else:
            print("⚠️  No mcpServers in agent config, falling back to global config")
            mcp_config = get_mcp_config()
            server_url = f"{mcp_config.get('server_url', 'http://localhost:8002')}/mcp/agents/{args.agent_name}"
    elif args.server:
        server_url = f"{args.server}/mcp/agents/{args.agent_name}"
    else:
        print("⚠️  No config or server provided, using global config.yaml")
        mcp_config = get_mcp_config()
        server_url = f"{mcp_config.get('server_url', 'http://localhost:8002')}/mcp/agents/{args.agent_name}"

    try:
        asyncio.run(ollama_monitor(args.agent_name, server_url, args.model, args.ollama_url))
    except KeyboardInterrupt:
        print("\n\n👋 AI Monitor stopped")
