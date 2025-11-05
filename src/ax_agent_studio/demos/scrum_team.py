#!/usr/bin/env python3
"""
Demo: Scrum Team with Autonomous Agents

Three agents work together like a scrum team:
- Agent 1 (Product Owner): Creates tasks and sets priorities
- Agent 2 (Developer): Works on tasks and updates status
- Agent 3 (QA/Manager): Reviews work and closes tasks

All agents have full MCP tool access and work autonomously!

Usage:
    python demo_scrum_team.py <product_owner> <developer> <qa_manager>

Example:
    python demo_scrum_team.py rigelz_334 lunar_craft_128 orion_344

Prerequisites:
    - Start LangGraph monitors for each agent first
    - Agents must be enabled in UI
"""

import asyncio
import sys
from datetime import datetime

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SCRUM_WORKFLOW = [
    # Sprint Planning
    {
        "from": "product_owner",
        "to": "developer",
        "message": "Hey {to}! Let's start our sprint. Can you create a task called 'Implement User Authentication' with priority high and description 'Add OAuth2 login flow for users'?",
        "expected_tool": "create_task",
        "phase": "Sprint Planning",
    },
    {
        "from": "product_owner",
        "to": "developer",
        "message": "{to}, also create a task 'Fix Bug in Search' with priority medium and description 'Search returns duplicate results'",
        "expected_tool": "create_task",
        "phase": "Sprint Planning",
    },
    # Development Phase
    {
        "from": "developer",
        "to": "product_owner",
        "message": "{to}, tasks created! Can you list all tasks so we can see our sprint backlog?",
        "expected_tool": "list_tasks",
        "phase": "Development",
    },
    {
        "from": "developer",
        "to": "qa_manager",
        "message": "Hey {to}! I've started working on the auth task. Can you search for any messages about 'authentication requirements'?",
        "expected_tool": "search_messages",
        "phase": "Development",
    },
    # Testing & Review
    {
        "from": "qa_manager",
        "to": "developer",
        "message": "{to}, I reviewed the search. Now can you list all current tasks to see what's in progress?",
        "expected_tool": "list_tasks",
        "phase": "Testing",
    },
    {
        "from": "qa_manager",
        "to": "product_owner",
        "message": "{to}, the auth implementation looks good! Can you create a task 'Deploy Authentication Feature' with priority high?",
        "expected_tool": "create_task",
        "phase": "Review",
    },
    # Sprint Retrospective
    {
        "from": "product_owner",
        "to": "qa_manager",
        "message": "{to}, great work! Can you list all tasks so we can review what we accomplished this sprint?",
        "expected_tool": "list_tasks",
        "phase": "Retrospective",
    },
    {
        "from": "product_owner",
        "to": "developer",
        "message": "Thanks {to}! Can you search for messages about 'next sprint' to help us plan?",
        "expected_tool": "search_messages",
        "phase": "Sprint Planning (Next)",
    },
]


async def send_scrum_message(from_agent: str, to_agent: str, message: str):
    """Send a message from one agent to another"""

    server_url = f"http://localhost:8002/mcp/agents/{from_agent}"
    oauth_server = "http://localhost:8001"

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
            oauth_server,
        ],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Format message with @mention
            full_message = f"@{to_agent} {message}"

            # Send message
            await session.call_tool("messages", {"action": "send", "content": full_message})


async def run_scrum_demo(product_owner: str, developer: str, qa_manager: str):
    """Run the scrum team demo"""

    agents = {"product_owner": product_owner, "developer": developer, "qa_manager": qa_manager}

    print("""
╔══════════════════════════════════════════════════════════════════╗
║   Scrum Team Demo: Autonomous Agents with MCP Tools           ║
╚══════════════════════════════════════════════════════════════════╝
    """)

    print(" Team Members:")
    print(f"    Product Owner: @{product_owner} (creates & prioritizes tasks)")
    print(f"    Developer: @{developer} (works on tasks)")
    print(f"    QA/Manager: @{qa_manager} (reviews & closes tasks)")
    print()

    print(" Each agent can:")
    print("   - create_task: Create new tasks")
    print("   - list_tasks: View all tasks")
    print("   - search_messages: Search for information")
    print("   - send_message: Communicate with team")
    print()

    print("  Prerequisites:")
    print(f"   1. Start: python langgraph_mcp_monitor.py {product_owner}")
    print(f"   2. Start: python langgraph_mcp_monitor.py {developer}")
    print(f"   3. Start: python langgraph_mcp_monitor.py {qa_manager}")
    print()

    input(" Press Enter when all monitors are running...")
    print()

    print(" Starting Scrum Sprint Demo...\n")

    current_phase = None

    for i, step in enumerate(SCRUM_WORKFLOW, 1):
        # Print phase header if new phase
        if step["phase"] != current_phase:
            current_phase = step["phase"]
            print(f"\n{'='*70}")
            print(f" Phase: {current_phase}")
            print(f"{'='*70}\n")

        from_agent = agents[step["from"]]
        to_agent = agents[step["to"]]
        message = step["message"].format(to=to_agent)

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Step {i}/{len(SCRUM_WORKFLOW)}")
        print(f"   From: @{from_agent} ({step['from']})")
        print(f"   To: @{to_agent}")
        print(f"   Message: {message[:80]}...")
        print(f"    Expected tool: {step['expected_tool']}")

        # Send message
        try:
            await send_scrum_message(from_agent, to_agent, message)
            print("    Message sent!")
        except Exception as e:
            print(f"    Error: {e}")

        # Wait for agent to process (adjust based on your Ollama speed)
        wait_time = 15
        print(f"   ⏳ Waiting {wait_time}s for agent to process and use tools...")
        await asyncio.sleep(wait_time)
        print()

    print("\n" + "=" * 70)
    print(" Scrum Sprint Demo Complete!")
    print("=" * 70)
    print()
    print(" Summary:")
    print(f"   - Total messages: {len(SCRUM_WORKFLOW)}")
    print(f"   - Phases completed: {len(set(s['phase'] for s in SCRUM_WORKFLOW))}")
    print(f"   - Expected tool calls: {len([s for s in SCRUM_WORKFLOW if s.get('expected_tool')])}")
    print()
    print(" What happened:")
    print("   - Product Owner created tasks with priorities")
    print("   - Developer worked on tasks and communicated status")
    print("   - QA/Manager reviewed work and searched for info")
    print("   - Team collaborated autonomously using MCP tools!")
    print()
    print(" Check your monitors' output to see:")
    print("   - LangGraph workflow execution")
    print("   - Tool calls (create_task, search_messages, list_tasks)")
    print("   - Multi-step reasoning")
    print("   - Autonomous decision making")
    print()


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python demo_scrum_team.py <product_owner> <developer> <qa_manager>")
        print()
        print("Example:")
        print("  python demo_scrum_team.py rigelz_334 lunar_craft_128 orion_344")
        print()
        print("Or use the quick start script:")
        print("  ./start_demo.sh demo_scrum_team.py rigelz_334 lunar_craft_128 orion_344")
        sys.exit(1)

    product_owner = sys.argv[1]
    developer = sys.argv[2]
    qa_manager = sys.argv[3]

    asyncio.run(run_scrum_demo(product_owner, developer, qa_manager))
