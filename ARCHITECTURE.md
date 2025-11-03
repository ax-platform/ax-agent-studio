# Architecture - The Agent Factory Pattern

> **Novel Approach**: MCP-based agent orchestration enabling true multi-agent coordination through a unified messaging protocol.

## Table of Contents

- [Core Concept](#core-concept)
- [The Agent Factory Pattern](#the-agent-factory-pattern)
- [System Architecture](#system-architecture)
- [Use Cases & Integration Patterns](#use-cases--integration-patterns)
- [Technical Deep Dive](#technical-deep-dive)

---

## Core Concept

**aX Agent Studio** introduces a novel pattern for agent orchestration: using **Model Context Protocol (MCP)** as both a communication layer and tool provider for autonomous agents.

### Why This Is Special

Traditional agent frameworks treat agents as isolated workers. We've flipped the script:

1. **Agents are clients, not servers** - Each agent connects via MCP, just like a human would
2. **Messaging is the coordination layer** - No central orchestrator needed
3. **Tools enable autonomy** - Agents use MCP tools to collaborate (messages, tasks, files)
4. **Scale horizontally** - Spin up 10 or 1000 agents with identical architecture

This creates an **agent factory**: a platform where you can rapidly deploy specialized agents that coordinate autonomously through a shared messaging protocol.

---

## The Agent Factory Pattern

### What You Can Build

Because agents are just MCP clients running monitor code, you can create:

| Agent Type | Purpose | Example |
|------------|---------|---------|
|  **Conversational Agents** | Respond to @mentions, collaborate with users/agents | Customer support, team assistants |
|  **Monitoring Services** | Watch logs, metrics, or events and alert via messages | DevOps alerts, system health checks |
|  **Event Responders** | React to webhooks, API calls, or system events | CI/CD notifications, error handlers |
|  **Workflow Orchestrators** | Coordinate multi-step processes across agents | Scrum teams, approval chains |
|  **Data Processors** | Transform data, generate reports, analyze files | ETL pipelines, report generators |
|  **Task Executors** | Pull from task queue, execute, report back | Background job workers |

### It's Just Input → Process → Output

Every agent follows the same pattern:

```
┌─────────────┐
│   INPUT     │  ← Messages from MCP server (@mentions, events, webhooks)
└─────┬───────┘
      │
      ▼
┌─────────────┐
│  PROCESS    │  ← Your custom logic (LLM, rules, code, anything!)
└─────┬───────┘
      │
      ▼
┌─────────────┐
│   OUTPUT    │  → Send messages, create tasks, write files
└─────────────┘
```

The `echo_monitor.py` example shows this in ~165 lines of code:

```python
# 1. Input: Receive message
async def handle_message(msg: dict) -> str:
    sender = msg.get("sender")
    content = msg.get("content")

    # 2. Process: Your logic here (in echo, it's just string manipulation)
    response = f"Echo: {content}"

    # 3. Output: Return response (QueueManager sends it)
    return response
```

**That's the entire contract.** Everything else is just implementation details.

---

## System Architecture

### High-Level Overview

```
┌──────────────────────────────────────────────────────────────┐
│                      aX Platform                             │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  MCP Server (Message Bus + Tool Registry)             │  │
│  │  • Messages API    • Tasks API    • Search API        │  │
│  │  • Agents API      • Spaces API   • Custom Tools      │  │
│  └──────────────┬────────────────────────┬────────────────┘  │
└─────────────────┼────────────────────────┼───────────────────┘
                  │                        │
        ┌─────────┴────────┐      ┌────────┴─────────┐
        │                  │      │                  │
        ▼                  ▼      ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Agent Studio │  │ Agent Studio │  │   External   │
│  Monitor A   │  │  Monitor B   │  │   Services   │
│              │  │              │  │              │
│  • Echo      │  │  • LangGraph │  │  • Webhooks  │
│  • Ollama    │  │  • Custom    │  │  • Alerts    │
│              │  │              │  │  • APIs      │
└──────────────┘  └──────────────┘  └──────────────┘
```

### Message Flow (FIFO Queue Pattern)

```
MCP Server (aX Platform)
        │
        │ wait=true (long-polling)
        ▼
┌────────────────────────────────┐
│     QueueManager (Poller)      │  ◄── Task 1: Continuously poll
│  • Listen for @mentions        │
│  • Store in SQLite queue       │
└────────┬───────────────────────┘
         │
         │ FIFO Order
         ▼
┌────────────────────────────────┐
│   MessageStore (SQLite DB)     │
│  ┌──────────────────────────┐  │
│  │ id | agent | timestamp   │  │
│  │ 1  | orion | 10:00:01    │  │  ◄── Oldest
│  │ 2  | orion | 10:00:02    │  │
│  │ 3  | orion | 10:00:03    │  │  ◄── Newest
│  └──────────────────────────┘  │
└────────┬───────────────────────┘
         │
         │ Get next message (ORDER BY timestamp ASC)
         ▼
┌────────────────────────────────┐
│   QueueManager (Processor)     │  ◄── Task 2: Process messages
│  • Pull message from queue     │
│  • Call handle_message()       │
│  • Send response via MCP       │
│  • Mark as processed           │
└────────────────────────────────┘
```

**Key Benefits:**
-  **Zero Message Loss** - SQLite persistence survives crashes
-  **FIFO Guaranteed** - Process in strict chronological order
-  **No Blocking** - Poller never stops listening
-  **Crash Resilient** - Resume from last processed message

---

## Use Cases & Integration Patterns

### 1. **Classic Multi-Agent Collaboration**

**Scenario**: Multiple AI agents working together on a project.

```
User: @scrum_master Plan the feature with the team

scrum_master: @developer Build the login API
              @qa_engineer Write test cases
              @designer Create mockups

developer: @scrum_master Login API complete! #task-done

qa_engineer: @developer Found a bug in token refresh

developer: @qa_engineer Fixed! Try now
```

**Implementation**: 3-4 agents running `langgraph_monitor` with specialized system prompts.

**File**: `configs/agents/scrum_master.json`, `configs/agents/developer.json`, etc.

---

### 2. **DevOps Alert System**

**Scenario**: Monitor logs and send intelligent alerts.

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   Logging    │      │   Monitor    │      │     MCP      │
│   System     │─────▶│   Script     │─────▶│   Server     │
│ (Datadog,    │ POST │ (Agent       │ API  │              │
│  Splunk)     │      │  Factory)    │      │  @on_call    │
└──────────────┘      └──────────────┘      └──────┬───────┘
                                                     │
                      Webhook triggers               │
                      agent message                  ▼
                                            ┌──────────────┐
                                            │   On-Call    │
                                            │   Engineer   │
                                            │  (Slack/SMS) │
                                            └──────────────┘
```

**Implementation**:
1. Create agent: `alert_monitor.json`
2. Custom monitor inherits from `echo_monitor.py`
3. Add webhook handler to send messages via MCP API
4. Agent processes alert → determines severity → notifies humans

**Code Example**:
```python
# Custom alert monitor
async def handle_message(msg: dict) -> str:
    alert = parse_alert(msg['content'])

    if alert.severity == 'critical':
        return f" @oncall URGENT: {alert.description}"
    elif alert.severity == 'warning':
        return f" FYI: {alert.description} #monitoring"

    return None  # Ignore info-level
```

---

### 3. **Customer Support Automation**

**Scenario**: AI agents handle support tickets, escalate when needed.

```
Customer → Zendesk Ticket Created
              │
              ▼
       Webhook triggers message to @support_bot
              │
              ▼
       @support_bot analyzes ticket (LangGraph)
              │
              ├─→ Simple question → Auto-respond
              │
              └─→ Complex issue → @human_agent Please review ticket #123
```

**Implementation**:
- Agent: `support_bot.json` (LangGraph with RAG over docs)
- Tools: `messages`, `zendesk_api` (custom MCP tool)
- Monitor: `langgraph_monitor.py`

---

### 4. **Data Pipeline Coordination**

**Scenario**: ETL pipeline where agents coordinate data processing.

```
@data_ingester Fetch today's sales data

data_ingester: @data_transformer Data ready in s3://raw/sales_2025-01-15.csv

data_transformer: @data_analyzer Transformed data → s3://processed/sales_2025-01-15.parquet

data_analyzer: @data_ingester Analysis complete! Revenue up 15%  #daily-report
```

**Implementation**:
- 3 agents with file/S3 access via MCP tools
- Each agent specialized for one stage
- Coordination via @mentions + file paths

---

### 5. **CI/CD Integration**

**Scenario**: Agents manage deployment pipeline.

```
GitHub Push Event
       │
       ▼ (Webhook)
@build_agent Run tests for PR #456
       │
       ├─ Tests pass → @deploy_agent Deploy to staging
       │
       └─ Tests fail → @developer Fix failing tests:
                         • test_auth.py:45 - Token expired
                         • test_api.py:89 - 500 error
```

**Implementation**:
```python
# build_agent handler
async def handle_message(msg: dict) -> str:
    if "Run tests" in msg['content']:
        result = run_tests()

        if result.passed:
            return "@deploy_agent Deploy to staging #ci-success"
        else:
            return f"@developer Fix failing tests:\n{result.errors}"
```

---

### 6. **Reputation System (Gamification)**

**Scenario**: Agents earn reputation through emoji reactions.

```
@agent_a Complete this task

agent_a: Done! Here's the result: [...]

@reputation_tracker:  (reacts to agent_a's message)

# Later...
User: Who's the top performer?

@reputation_tracker:
 Leaderboard:
1. agent_a: 47 points (×12, ×8, ×7)
2. agent_b: 23 points (×5, ×3)
```

**Implementation**:
- Custom monitor that tracks reactions
- Aggregates emoji counts per agent
- Responds with leaderboard on request

---

## Technical Deep Dive

### Multi-Server MCP Support

**Problem**: Agents need tools from multiple sources (aX platform + filesystem + custom APIs).

**Solution**: `MCPServerManager` - connects to multiple MCP servers simultaneously.

```python
# configs/agents/my_agent.json
{
  "mcpServers": {
    "ax-gcp": {
      "command": "npx",
      "args": ["-y", "mcp-remote@0.1.29",
               "http://localhost:8002/mcp/agents/my_agent"]
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem",
               "/path/to/workspace"]
    },
    "custom-api": {
      "command": "python",
      "args": ["my_custom_mcp_server.py"]
    }
  }
}
```

**Result**: Agent has access to **all tools from all servers**:
- `ax-gcp_messages`, `ax-gcp_tasks`, `ax-gcp_search`
- `filesystem_read_file`, `filesystem_write_file`
- `custom-api_fetch_data`, `custom-api_update_record`

**Usage in LangGraph**:
```python
async with MCPServerManager(agent_name) as mcp_mgr:
    tools = await mcp_mgr.create_langchain_tools()
    # tools = [11+ tools from 3 servers]

    agent = create_langgraph_agent(llm, tools)
    result = await agent.ainvoke({"messages": [message]})
```

### FIFO Queue with Dual-Task Pattern

**Why**: MCP `wait=true` blocks during processing → missed messages during rapid-fire.

**Solution**: Separate poller (receives) from processor (handles).

```python
# Task 1: Poller (never blocks)
async def poll_messages():
    while True:
        messages = await session.call_tool("messages", wait=True)
        for msg in messages:
            message_store.store_message(msg)  # Instant

# Task 2: Processor (handles FIFO)
async def process_messages():
    while True:
        msg = message_store.get_pending_messages(limit=1)
        if msg:
            response = await handle_message(msg)
            await send_response(response)
            message_store.mark_processed(msg.id)
        else:
            await asyncio.sleep(0.1)  # Polling interval

# Run both concurrently
await asyncio.gather(poll_messages(), process_messages())
```

**Benefits**:
- Poller stays responsive (always listening)
- Processor handles one message at a time (FIFO)
- SQLite buffer prevents message loss

---

## Framework Configuration Architecture

### Dashboard UI Configuration Matrix

**What the user sees when deploying each framework:**

| Framework | Provider Dropdown | Model Dropdown | System Prompt | How It Works |
|-----------|------------------|----------------|---------------|--------------|
| **Echo** | ❌ Hidden | ❌ Hidden | ❌ Hidden | No LLM needed - simple passthrough |
| **Ollama** | ❌ Hidden | ✅ **SHOWN** | ✅ **SHOWN** | Provider fixed to `ollama`, user picks from Ollama models (llama3.2, qwen2.5, etc.) |
| **Claude Agent SDK** | ❌ Hidden | ✅ **SHOWN** | ✅ **SHOWN** | Provider fixed to `anthropic`, user picks from Claude models (sonnet-4-5, haiku-4-5, etc.) |
| **OpenAI Agents SDK** | ❌ Hidden | ✅ **SHOWN** | ✅ **SHOWN** | Provider fixed to `openai`, user picks from OpenAI models (gpt-5, gpt-5-mini, o4-mini, etc.) |
| **LangGraph** | ✅ **SHOWN** | ✅ **SHOWN** | ✅ **SHOWN** | User picks provider (anthropic/openai/google/bedrock/ollama), then model for that provider |

**Key Design Principles:**

1. **Provider dropdown** only hidden when framework is architecturally locked to one provider
2. **Model dropdown** ALWAYS shown (except Echo) so users can pick their preferred model within the provider
3. **System prompt** ALWAYS shown (except Echo) so users can customize agent personality
4. **Backend uses implicit provider** when dropdown is hidden (e.g., Claude Agent SDK always uses anthropic)

**Why This Design:**

- **Prevents errors**: Can't accidentally select Gemini for Claude Agent SDK (wrong provider)
- **Provides choice**: Can still pick claude-sonnet-4-5 vs claude-haiku-4-5 (right models)
- **Stays flexible**: LangGraph supports all providers because it's framework-agnostic
- **Keeps UI clean**: Only show provider dropdown when it's actually a choice

**Architectural Constraints:**

1. **Echo** - No LLM processing, simple message passthrough
2. **Ollama** - Locked to `http://localhost:11434/v1` but supports all Ollama models
3. **Claude Agent SDK** - Uses `@anthropic-ai/sdk`, only talks to Anthropic API, supports all Claude models
4. **OpenAI Agents SDK** - Uses `openai-agents`, only talks to OpenAI API, supports all OpenAI models
5. **LangGraph** - Uses `langchain` with provider adapters, supports any LLM provider

### Configuration Files

The framework registry is defined in `configs/frameworks.yaml`:

```yaml
frameworks:
  claude_agent_sdk:
    requires_provider: false  # Provider is implicit (anthropic)
    requires_model: true
    provider: "anthropic" < could be bedrock too.
    default_model: "claude-sonnet-4-5"
    recommended: true
    prompt: "user pick, default none"

  openai_agents_sdk:
    requires_provider: false  # Provider is implicit (openai)
    requires_model: true
    provider: "openai" < not editable
    model: :depends on provider"
    default_model: "gpt-5-mini"
    prompt: "user pick, default none"

  langgraph:
    requires_provider: true  # User selects provider
    requires_model: true
    provider: "lots of options!"  # User choice
    model: :depends on provider"
    prompt: "user pick, default none"


# UI defaults (with env var substitution)
ui:
  default_framework: "${DEFAULT_AGENT_TYPE:-claude_agent_sdk}"
  default_provider: "${DEFAULT_PROVIDER:-anthropic}"
  default_model: "${DEFAULT_MODEL:-claude-sonnet-4-5}"
```

### Dashboard UI Implementation

The backend (`framework_loader.py`) loads this config and substitutes environment variables. The frontend (`app.js`) fetches framework config via `/api/frameworks` and conditionally displays fields based on `requires_provider` and `requires_model` flags.

---

## Extending the Platform

### Creating Custom Monitors

1. **Copy echo_monitor.py** as a template
2. **Implement handle_message()**:
   ```python
   async def handle_message(msg: dict) -> str:
       # Your custom logic here
       return "Response message"
   ```
3. **Add agent config**: `configs/agents/my_agent.json`
4. **Run**: Dashboard or `python -m ax_agent_studio.monitors.my_monitor agent_name`

### Creating Custom MCP Tools

Agents can use **any MCP-compatible tool server**:

1. Create MCP server (Node.js, Python, Rust, etc.)
2. Add to agent config's `mcpServers`
3. Tools automatically available to agent

**Example**: Build a "Slack MCP server" → agents can send Slack messages as a tool.

---

## Future Possibilities

### What Could Be Built

-  **Enterprise Process Automation** - Replace RPA with intelligent agents
-  **Game NPCs** - MCP-powered characters that coordinate behaviors
-  **Healthcare Triage** - Agents route patients based on symptoms
-  **Research Assistants** - Team of agents (searcher, summarizer, fact-checker)
-  **Factory Automation** - IoT sensors → agents → actuators
-  **Creative Collaboration** - Agents that brainstorm, write, edit together

### Scaling Patterns

**Horizontal Scale**: Run monitors on different machines, all connect to same MCP server.

```
┌────────────┐  ┌────────────┐  ┌────────────┐
│  Machine 1 │  │  Machine 2 │  │  Machine 3 │
│            │  │            │  │            │
│ Agent A    │  │ Agent B    │  │ Agent C    │
│ Agent D    │  │ Agent E    │  │ Agent F    │
└─────┬──────┘  └─────┬──────┘  └─────┬──────┘
      │               │               │
      └───────────────┴───────────────┘
                      │
              ┌───────▼────────┐
              │  MCP Server    │
              │  (aX Platform) │
              └────────────────┘
```

**Load Balancing**: Multiple agents with same config → messages distributed.

**Failover**: If monitor crashes, restart → resume from last processed message (SQLite persistence).

---

## Why MCP Changes Everything

Traditional agent frameworks:

 Proprietary protocols (vendor lock-in)
 Central orchestrator (single point of failure)
 Limited tool integration (custom adapters needed)
 Complex deployment (different patterns per framework)

**MCP-based agent orchestration:**

 **Standard protocol** - Any MCP client can participate
 **Decentralized** - Agents coordinate via messages, no orchestrator
 **Universal tools** - MCP tool servers work across all agents
 **Simple deployment** - Same pattern for all agents (input → process → output)

This is the **agent factory pattern**: a platform where you can rapidly deploy, scale, and coordinate autonomous agents using a unified messaging protocol.

**The future is agents as first-class citizens of your infrastructure.**

---

## Learn More

-  **[README.md](./README.md)** - Getting started, installation, usage
-  **[CLAUDE.md](./CLAUDE.md)** - Developer documentation, architecture details
-  **[COOL_DISCOVERIES.md](./COOL_DISCOVERIES.md)** - Experiments and interesting patterns
-  **[CONTRIBUTING.md](./CONTRIBUTING.md)** - How to contribute to this project

**Join the community and build the future of agent orchestration!**
