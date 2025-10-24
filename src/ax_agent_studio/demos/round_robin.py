#!/usr/bin/env python3
"""
Multi-Agent Loop - N-way autonomous agent conversation
Creates a round-robin conversation loop between N agents.

Usage:
    python multi_agent_loop.py <agent1> <agent2> [agent3] ... [max_loops] [--delay N]

Example:
    python multi_agent_loop.py rigelz_334 lunar_craft_128 orion_344 --loops 10 --delay 8

Flow:
    Agent 1 → Agent 2 → Agent 3 → ... → Agent N → Agent 1 (loop)

Safety features:
- Ctrl+C to stop gracefully
- Max iteration limit (default: 10)
- Configurable delay between messages (default: 8s for more agents)
"""

import asyncio
import sys
import signal
from datetime import datetime
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Global flag for graceful shutdown
running = True
total_messages = 0

def signal_handler(sig, frame):
    global running
    print("\n\n🛑 Stopping multi-agent loop...")
    running = False

signal.signal(signal.SIGINT, signal_handler)

async def send_message(session, from_agent, to_agent, content):
    """Send a message from one agent to another"""
    global total_messages
    try:
        result = await session.call_tool("messages", {
            "action": "send",
            "content": content
        })
        total_messages += 1
        print(f"✅ @{from_agent} → @{to_agent}: {content[:60]}...")
        return True
    except Exception as e:
        print(f"❌ Error sending from @{from_agent} to @{to_agent}: {e}")
        return False

async def multi_agent_loop(agents, max_loops=10, delay=8):
    """Create a round-robin conversation loop between N agents"""

    if len(agents) < 2:
        print("❌ Need at least 2 agents for a conversation loop")
        return

    oauth_server = "http://localhost:8001"

    print(f"🔄 Starting multi-agent loop")
    print(f"   Agents: {' → '.join([f'@{a}' for a in agents])} → @{agents[0]} (loop)")
    print(f"   Max loops: {max_loops}")
    print(f"   Delay: {delay}s")
    print(f"   Press Ctrl+C to stop\n")

    # Conversation prompts - each agent asks the next one
    prompts = [
        "What's your perspective on {topic}?",
        "Can you build on what was just said about {topic}?",
        "What would you add to this discussion about {topic}?",
        "Share your thoughts on {topic} - anything to add?",
        "How do you see {topic} evolving? Pass it on!",
    ]

    topics = [
        "AI creativity and art",
        "the future of human-AI collaboration",
        "ethical considerations in AI development",
        "the role of AI in scientific discovery",
        "how AI agents can work together effectively",
        "the intersection of AI and human emotions",
        "what makes a good conversation",
        "the nature of intelligence itself",
    ]

    try:
        # Create MCP sessions for all agents
        sessions = []
        connections = []

        for agent in agents:
            server_url = f"http://localhost:8002/mcp/agents/{agent}"
            server_params = StdioServerParameters(
                command="npx",
                args=[
                    "-y", "mcp-remote@0.1.29",
                    server_url,
                    "--transport", "http-only",
                    "--allow-http",
                    "--oauth-server", oauth_server
                ]
            )

            read, write = await stdio_client(server_params).__aenter__()
            session = await ClientSession(read, write).__aenter__()
            await session.initialize()

            connections.append((read, write))
            sessions.append(session)
            print(f"✅ Connected to @{agent}")

        print()

        loop_count = 0
        topic_idx = 0
        prompt_idx = 0

        while running and loop_count < max_loops:
            loop_count += 1
            print(f"\n{'='*70}")
            print(f"🔁 Loop {loop_count}/{max_loops} - {datetime.now().strftime('%H:%M:%S')}")

            # Pick a topic for this round
            topic = topics[topic_idx % len(topics)]
            print(f"📋 Topic: {topic}")
            print(f"{'='*70}\n")
            topic_idx += 1

            # Each agent sends to the next one (round-robin)
            for i in range(len(agents)):
                if not running:
                    break

                from_agent = agents[i]
                to_agent = agents[(i + 1) % len(agents)]
                session = sessions[i]

                # Create the message
                prompt = prompts[prompt_idx % len(prompts)]
                message = f"@{to_agent} {prompt.format(topic=topic)}"
                prompt_idx += 1

                # Send message
                success = await send_message(session, from_agent, to_agent, message)
                if not success:
                    print(f"⚠️  Failed to send message, continuing...")

                # Wait between messages to avoid overwhelming the system
                if i < len(agents) - 1:  # Don't wait after last message in round
                    await asyncio.sleep(delay)

            # Extra wait before starting next loop
            if running and loop_count < max_loops:
                print(f"\n⏳ Waiting {delay}s before next loop...\n")
                await asyncio.sleep(delay)

        print(f"\n{'='*70}")
        print(f"🏁 Multi-agent loop completed!")
        print(f"   Total loops: {loop_count}")
        print(f"   Total messages sent: {total_messages}")
        print(f"   Stopped: {'User interrupt' if not running else 'Max loops reached'}")
        print(f"{'='*70}\n")

    except Exception as e:
        print(f"\n❌ Error in multi-agent loop: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python multi_agent_loop.py <agent1> <agent2> [agent3] ... [--loops N] [--delay N]")
        print("\nExample:")
        print("  python multi_agent_loop.py rigelz_334 lunar_craft_128 --loops 10 --delay 8")
        print("  python multi_agent_loop.py rigelz_334 lunar_craft_128 orion_344 --loops 5 --delay 10")
        sys.exit(1)

    # Parse arguments
    agents = []
    max_loops = 10
    delay = 8

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--loops" and i + 1 < len(sys.argv):
            max_loops = int(sys.argv[i + 1])
            i += 2
        elif arg == "--delay" and i + 1 < len(sys.argv):
            delay = int(sys.argv[i + 1])
            i += 2
        else:
            agents.append(arg)
            i += 1

    if len(agents) < 2:
        print("❌ Need at least 2 agents!")
        sys.exit(1)

    asyncio.run(multi_agent_loop(agents, max_loops, delay))
