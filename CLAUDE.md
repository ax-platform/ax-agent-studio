# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**aX Agent Studio** is a monitor and management platform for aX platform MCP agents. It provides:
- Real-time monitoring dashboard
- Multiple monitor types (echo, ollama, langgraph)
- Central configuration management
- Demo scripts for testing agent workflows

**Package Structure**: Python package managed with `uv` (fast Python package manager).

## Quick Start

### Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) installed
- aX platform MCP server running (default: http://localhost:8002)

### Installation

```bash
cd ax-agent-studio

# Easy way: Auto-setup and start (recommended)
python scripts/start_dashboard.py

# Or use platform-specific scripts:
./scripts/start_dashboard.sh      # Mac/Linux
scripts/start_dashboard.bat       # Windows (double-click!)

# Manual way: Install dependencies then start
uv sync
PYTHONPATH=src uv run uvicorn ax_agent_studio.dashboard.backend.main:app --host 127.0.0.1 --port 8000
```

The startup scripts will:
- ✅ Check dependencies and run `uv sync` (fast if already installed)
- ✅ Set up environment properly
- ✅ Start the dashboard automatically
- ✅ Work on Windows, Mac, and Linux

### Using the Dashboard

1. Open http://127.0.0.1:8000
2. Select monitor type
3. Choose agent configuration
4. Click "Start Monitor"
5. Use smart test button to send messages

### Deployment Groups (Optional)

**Batch deploy multiple agents** with pre-configured model settings:

```bash
# First time setup - copy example file
cp configs/deployment_groups.example.yaml configs/deployment_groups.yaml

# Edit deployment_groups.yaml to customize your groups
```

**Available groups** (from example):
- **Tiny Trio** ⚡ - Ultra-fast, lowest cost (gemini-2.5-flash-lite, gpt-5-nano, claude-haiku-4-5)
- **Small Trio** - Balanced, production-ready (gemini-2.5-flash, gpt-5-mini, claude-haiku-4-5)
- **Large Trio** 🚀 - Flagship models (gemini-2.5-pro, gpt-5, claude-sonnet-4-5)

**Features**:
- Robust validation - skips missing agents with warnings instead of failing
- Per-agent model/provider overrides
- Flexible agent assignments (not hardcoded to specific IDs)
- Environment tagging (local/production/any)

**Note**: Your `deployment_groups.yaml` is gitignored - customize freely without committing!

## Project Structure

```
ax-agent-studio/
├── src/ax_agent_studio/          # Main package
│   ├── __init__.py
│   ├── config.py                 # Config loader (reads config.yaml)
│   ├── mcp_manager.py            # Multi-server MCP manager (agent factory)
│   ├── message_store.py          # ✨ NEW: SQLite-backed FIFO message queue
│   ├── queue_manager.py          # ✨ NEW: Modular queue manager (dual-task pattern)
│   ├── monitors/                 # Monitor implementations
│   │   ├── echo_monitor.py       # Simple echo monitor with FIFO
│   │   ├── ollama_monitor.py     # Local LLM monitor with FIFO
│   │   └── langgraph_monitor.py  # LangGraph with multi-server + FIFO
│   ├── dashboard/                # Web dashboard
│   │   ├── backend/              # FastAPI server
│   │   │   ├── main.py          # API routes + log clearing
│   │   │   ├── process_manager.py # Process lifecycle management
│   │   │   ├── config_loader.py # Agent config loader
│   │   │   └── log_streamer.py  # Real-time log streaming
│   │   └── frontend/             # HTML/JS UI
│   │       ├── index.html       # Dashboard UI
│   │       ├── app.js           # Frontend logic (no confirm dialogs)
│   │       └── style.css        # Styling
│   └── demos/                    # Example scripts
│       ├── scrum_team.py        # ⚠️  Needs fixing
│       └── round_robin.py       # ⚠️  Needs fixing
├── configs/agents/               # Flat agent config structure
│   ├── _example_agent.json      # Template for new agents
│   ├── orion_344.json           # Example with filesystem server
│   └── lunar_craft_128.json     # Example with everything server
├── agent_files/                  # Safe workspace for filesystem MCP server
│   └── README.md                # Only file committed to git
├── data/                         # ✨ NEW: SQLite database storage
│   └── message_backlog.db       # FIFO queue (auto-created)
├── scripts/                      # 🚀 Utility scripts
│   ├── start_dashboard.py       # Smart startup script (cross-platform)
│   ├── start_dashboard.sh       # Shell script for Mac/Linux
│   ├── start_dashboard.bat      # Batch script for Windows
│   └── kill_switch.py           # Emergency kill switch CLI
├── config.yaml                   # Central configuration
├── pyproject.toml               # uv project config
├── .python-version              # Python 3.13
└── logs/                        # Monitor logs (auto-created, can be cleared)
```

## Configuration

All settings are centralized in `config.yaml`:

```yaml
mcp:
  server_url: "http://localhost:8002"
  oauth_url: "http://localhost:8001"

monitors:
  timeout: null  # No timeout - waits forever
  reconnect_delay: 5
  max_retries: 3
  mark_read: true

ollama:
  base_url: "http://localhost:11434/v1"
  default_model: "gpt-oss:latest"

dashboard:
  host: "127.0.0.1"
  port: 8000
```

### Config Loader

`src/ax_agent_studio/config.py` provides:
- `load_config()` - Load entire config
- `get_mcp_config()` - Get MCP settings
- `get_monitor_config()` - Get monitor settings
- `get_ollama_config()` - Get Ollama settings
- `get_dashboard_config()` - Get dashboard settings

All monitors import and use these functions for consistent configuration.

## Monitor Architecture

### FIFO Queue System (✨ NEW!)

**Problem Solved**: Monitors were missing rapid-fire messages because `wait=true` blocks during processing.

**Solution**: Modular FIFO queue with dual-task pattern using SQLite persistence.

### Architecture Overview

All monitors now use **QueueManager** (`queue_manager.py`) with two concurrent tasks:

**Task 1: Poller (Message Receiver)**
- Continuously calls `messages` tool with `wait=true`
- Immediately stores incoming messages in SQLite queue
- Never blocks - always listening

**Task 2: Processor (Handler)**
- Pulls messages from queue in FIFO order
- Processes with monitor's custom handler
- Sends response
- Marks message as complete

**Benefits:**
- ✅ Zero message loss (SQLite buffer)
- ✅ FIFO guaranteed (`ORDER BY timestamp ASC`)
- ✅ Crash resilient (persistent storage)
- ✅ Modular (zero code duplication)
- ✅ Pluggable handlers

### MessageStore (`message_store.py`)

SQLite-backed message queue with:
- Database: `data/message_backlog.db`
- Deduplication: `INSERT OR IGNORE` on message ID
- Processing states: `processing_started_at`, `processing_completed_at`
- Stats tracking: backlog count, avg processing time
- Auto-cleanup: deletes processed messages after 7 days

**API:**
```python
store = MessageStore()
store.store_message(msg_id, agent, sender, content)  # Add to queue
store.get_pending_messages(agent, limit=1)           # Get next FIFO
store.mark_processing_started(msg_id)                # Lock message
store.mark_processed(msg_id)                         # Complete & remove
```

### QueueManager (`queue_manager.py`)

Reusable queue abstraction with pluggable handlers:

```python
from ax_agent_studio.queue_manager import QueueManager

# Define your handler (what to do with each message)
async def handle_message(content: str) -> str:
    # Your processing logic here
    return "Response"

# Use QueueManager
queue_mgr = QueueManager(
    agent_name=agent_name,
    session=session,
    message_handler=handle_message,
    mark_read=False  # Recommended for FIFO
)

await queue_mgr.run()  # Runs both tasks forever
    })
```

### Monitor Types

1. **Echo Monitor** (`echo_monitor.py`)
   - Simplest monitor for testing
   - Echoes back any @mention
   - Pattern matching for sender/message extraction
   - Uses FIFO queue for message processing

2. **Ollama Monitor** (`ollama_monitor.py`)
   - Local LLM integration via OpenAI SDK
   - Maintains conversation history
   - Configurable model selection
   - Uses FIFO queue for message processing

3. **LangGraph Monitor** (`langgraph_monitor.py`)
   - Full agentic workflow with LangGraph
   - **Multi-server MCP support via MCPServerManager**
   - Dynamically loads all MCP servers from agent config
   - Access to tools from multiple servers simultaneously
   - Multi-step reasoning with full tool palette
   - Uses FIFO queue for message processing

### Agent Conversation Patterns

**How agents communicate:**
- **@mention** = Direct conversation (agent will respond)
- **#hashtag** = Topic/broadcast (no specific response expected)

**Example conversation control:**
```
User: @agent_a Please work with @agent_b on this task
  └─> agent_a: @agent_b Let's collaborate!
      └─> agent_b: @agent_a Great! What do you need?
          └─> agent_a: Thanks! #task-complete (no @mention = ends conversation)
```

**Best practices:**
- Use @mentions to keep conversations going
- Omit @mentions or use hashtags (#end, #done) to stop conversations
- Each agent only sees messages that @mention them (FIFO queue per agent)

## Multi-Server MCP Support (NEW!)

###  MCPServerManager - Agent Factory

**Location**: `src/ax_agent_studio/mcp_manager.py`

The MCPServerManager is a reusable agent factory that enables monitors to connect to multiple MCP servers simultaneously.

**Key Features**:
- Loads agent config from `configs/agents/{agent_name}.json`
- Connects to ALL mcpServers defined in config
- Dynamically discovers and creates LangChain tools from each server
- Manages lifecycle of all MCP connections
- Tool names prefixed with server name (e.g., `ax-gcp_messages`, `filesystem_read_file`)

**Usage Example**:
```python
from ax_agent_studio.mcp_manager import MCPServerManager

async with MCPServerManager(agent_name) as mcp_manager:
    # Get primary session for messaging
    primary_session = mcp_manager.get_primary_session()

    # Create tools from all servers
    tools = await mcp_manager.create_langchain_tools()
    # Returns: [ax-gcp_messages, ax-gcp_tasks, filesystem_read_file, ...]

    # Use tools with your agent
    agent = OllamaLangGraphAgent(tools=tools, model=model)
```

**Architecture**:
1. **Config Loading**: Reads `configs/agents/{agent_name}.json`
2. **Server Connection**: Creates stdio_client for each mcpServer
3. **Tool Discovery**: Queries each server's `list_tools()`
4. **Tool Creation**: Builds StructuredTool objects with proper Pydantic schemas
5. **Lifecycle**: Automatic cleanup via async context manager

**Tool Schema Conversion**:
- Converts MCP JSON schema to Pydantic Field definitions
- Handles required vs optional parameters
- Properly formats for OpenAI/Ollama API compatibility
- Uses `StructuredTool.model_json_schema()` for correct type serialization

**Example Agent Config** (`configs/agents/orion_344.json`):
```json
{
  "mcpServers": {
    "ax-gcp": {
      "command": "npx",
      "args": ["-y", "mcp-remote@0.1.29",
               "http://localhost:8002/mcp/agents/orion_344",
               "--transport", "http-only",
               "--oauth-server", "http://localhost:8001"]
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem",
               "/Users/jacob/ax-agent-studio/agent_files"]
    }
  },
  "environment": "local"
}
```

**Result**: Agent has access to 11+ tools from multiple servers!
- 5 ax-gcp tools (messages, tasks, search, agents, spaces)
- 6+ filesystem/everything tools (read_file, write_file, echo, add, etc.)

### Extending to Other Monitors

Any monitor can use MCPServerManager:

```python
# In your monitor
async with MCPServerManager(agent_name) as mgr:
    tools = await mgr.create_langchain_tools()
    # Use tools with your agent implementation
```

**Currently Supported**:
- ✅ LangGraph Monitor (full multi-server support)
- ⏳ Ollama Monitor (single-server, can be upgraded)
- ⏳ Echo Monitor (single-server, simple design)

## Running Monitors

### Via Dashboard (Recommended)

```bash
PYTHONPATH=src uv run uvicorn ax_agent_studio.dashboard.backend.main:app --host 127.0.0.1 --port 8000
```

### Directly (for debugging)

```bash
# Echo monitor
PYTHONPATH=src uv run python -m ax_agent_studio.monitors.echo_monitor rigelz_334

# Ollama monitor
PYTHONPATH=src uv run python -m ax_agent_studio.monitors.ollama_monitor lunar_craft_128

# LangGraph monitor
PYTHONPATH=src uv run python -m ax_agent_studio.monitors.langgraph_monitor rigelz_334
```

## Running Demos

```bash
# Scrum team workflow
PYTHONPATH=src uv run python -m ax_agent_studio.demos.scrum_team

# Round-robin multi-agent
PYTHONPATH=src uv run python -m ax_agent_studio.demos.round_robin
```

## Development Commands

### uv Commands (NOT pip/venv!)

```bash
# Install dependencies
uv sync

# Add new dependency
uv add <package>

# Run Python script
uv run python script.py

# Run module
uv run python -m ax_agent_studio.monitors.echo_monitor

# Update dependencies
uv lock --upgrade
```

### Dashboard Development

```bash
# Start dashboard backend (easy way)
python scripts/start_dashboard.py

# Or manually
PYTHONPATH=src uv run uvicorn ax_agent_studio.dashboard.backend.main:app --host 127.0.0.1 --port 8000

# View logs
tail -f logs/<monitor-id>.log

# Kill all monitors
pkill -9 -f "ax_agent_studio.monitors"
```

## Dashboard Backend

**Key Files**:
- `main.py` - FastAPI app, routes, WebSocket support
- `process_manager.py` - Monitor process lifecycle (start/stop/status)
- `config_loader.py` - Load agent configs from /configs
- `log_streamer.py` - Real-time log streaming

**Process Management**:
- Uses `uv run python -m` to start monitors
- Tracks PIDs with `psutil`
- Auto-cleanup of orphaned processes
- Real-time log streaming via WebSocket

## Known Issues & Solutions

### Competing Monitors Problem

**Symptom**: Multiple monitors for same agent cause messages to be consumed by only one.

**Solution**: Dashboard automatically kills existing monitors for an agent before starting new one.

### Infinite Loop Bug (FIXED!)

**Symptom**: LangGraph monitor would spam messages every 5 minutes.

**Root Cause**:
- `timeout: 300` caused MCP to return "no mentions found"
- LangGraph agent would investigate and report back
- This created infinite loop

**Fix Applied**:
- Removed `timeout` parameter from all monitors
- Added regex verification in langgraph_monitor.py (line 502)

### Missing MCPJam Server

**Symptom**: Monitors connect but receive no messages.

**Solution**: Ensure MCPJam Inspector is running on port 8002:
```bash
npx @mcpjam/inspector@latest
```

### Recent Bug Fixes (2025-01)

**1. Tool Creation Bug (FIXED)**
- **Issue**: `AttributeError: property 'args' of 'StructuredTool' object has no setter`
- **Cause**: Using `@tool` decorator which creates read-only properties
- **Fix**: Changed to `StructuredTool` constructor with `coroutine` and `args_schema` parameters
- **Commit**: `c37fd3e`

**2. Ollama Schema Format (FIXED)**
- **Issue**: `400 Bad Request - cannot unmarshal object into Go struct field`
- **Cause**: Improper conversion of Pydantic schema to OpenAI format
- **Fix**: Use `model_json_schema()` and ensure `type: "object"` is a string
- **Commit**: `83fa26c`

**3. Clear Logs Not Working (FIXED)**
- **Issue**: Logs reappear on page refresh after clearing
- **Cause**: Clear only affected DOM, not log files on disk
- **Fix**: Added `/api/logs/clear-all` endpoint that truncates all log files
- **Commit**: `a0787e1`

**4. Delete Confirmation Dialog (FIXED)**
- **Issue**: Annoying confirmation when deleting stopped monitors
- **Fix**: Removed confirmation, delete works instantly like skull button
- **Commit**: `c37fd3e`

**4. Startup Sweep Feature (IMPLEMENTED BUT DISABLED) ⚠️**
- **Status**: Code complete, disabled due to MCP server bug
- **Implementation**: `queue_manager.py` has startup sweep that fetches unread messages
- **Config**: `config.yaml` has `startup_sweep` and `startup_sweep_limit` settings
- **Issue**: MCP `mode='unread'` returns duplicate messages even with `mark_read=True`
- **Symptom**: Sweep fetches same message 10 times instead of 10 different messages
- **Root Cause**: MCP server doesn't respect read status within same session, or marking isn't working
- **Workaround**: Disabled via `startup_sweep: false` in config
- **Future Work**:
  - Investigate MCP server's unread message handling
  - Try alternative approaches (pagination with before_id/since_id)
  - Contact MCP maintainers about unread+mark_read behavior
- **Recommendation from ax_sentinel**: Use unread sweep + up_to_id for durable consumer pattern
- **Impact**: Monitors don't pick up messages sent while offline (original behavior maintained)

### Known Issues (To Fix)

**1. MCP Connection Shutdown Errors ⚠️**
- **Status**: Non-critical, cosmetic issue
- **Symptom**: Monitor shutdown shows MCP remote errors:
  ```
  Error from remote server: DOMException [AbortError]: This operation was aborted
  ```
- **Root Cause**: MCP connections not gracefully closed before monitor shutdown
- **Impact**: Cosmetic only - happens during shutdown, doesn't affect functionality
- **TODO**: Add graceful MCP connection cleanup in monitor shutdown sequence
- **Location**: `src/ax_agent_studio/monitors/*_monitor.py` shutdown handlers

**2. Demos Broken ⚠️**
- **Status**: Not tested, likely broken
- **Files**: `demos/scrum_team.py`, `demos/round_robin.py`
- **TODO**: Test and fix demo scripts

**3. Kill Switch Log Spam**
- **Status**: Working but verbose
- **Symptom**: Kill switch logs warning every 2 seconds while active
- **TODO**: Reduce frequency or make silent (log once, then quiet)

## Testing

### Automated Test Suite

**Unit Tests** - Test core message parsing and queue logic:
```bash
# Message parsing tests (regex, sender extraction, self-mention detection)
python tests/test_message_parsing.py

# Handler integration tests (verify sender info passed to LLM)
python tests/test_agent_handler.py
```

**End-to-End Tests** - Test full monitor workflows:
```bash
# Gemini monitor E2E test (requires monitor running)
python tests/test_gemini_monitor_e2e.py

# Gemini standalone E2E test
python tests/test_gemini_e2e.py

# Multi-provider tests (Ollama, Gemini, Bedrock)
python tests/test_providers_e2e.py

# Agent-to-agent conversation test
python tests/test_agent_conversation.py
```

**What the tests verify:**
- ✅ Message parsing from MCP server format
- ✅ Sender extraction (captures username correctly)
- ✅ Self-mention detection (prevents infinite loops)
- ✅ Agent-to-agent conversations (proper @mention handling)
- ✅ FIFO queue ordering (messages processed in sequence)
- ✅ Rapid-fire scenarios (no message loss)

### Smart Test Button (Dashboard)

Dashboard includes context-aware test button:
- Echo: Sends simple test message
- Ollama: Asks for fun fact
- LangGraph: Sends task-related question

### Manual Testing

```bash
# Start monitor via dashboard
python start_dashboard.py
# Or: http://127.0.0.1:8000

# Then use aX platform to send @mention
# Or use test scripts above
```

**Testing with MCP messages tool (RECOMMENDED)**:
```python
# Always use wait=true to verify agent responses immediately
# This blocks until agent responds, perfect for testing
mcp__ax-docker__messages(
    action="send",
    content="@agent_name Test message",
    wait=true,  # ← CRITICAL: Wait for agent response
    timeout=60  # Optional: seconds to wait
)

# wait=true returns the agent's response directly
# Avoids race conditions and verifies threading works correctly
```

**Why wait=true?**
- ✅ Immediate verification - see agent response instantly
- ✅ No race conditions - guarantees response is captured
- ✅ Validates threading - confirms auto-reply works
- ✅ Detects duplicates - multiple responses show up immediately

## File Naming Conventions

- Monitors: `{type}_monitor.py` (e.g., `echo_monitor.py`)
- Configs: `{agent_name}.json` in `/configs/agents/`
- Logs: `{agent}_{type}_{uuid}.log` in `/logs/`

## Best Practices

1. **Always use uv commands** - No pip/venv!
2. **Check config.yaml first** - All settings centralized
3. **One monitor per agent** - Avoid competing monitors
4. **Use dashboard for management** - Easier than CLI
5. **Check logs for debugging** - Real-time in UI or tail files

## Related Projects

This is an independent project that integrates with:
- **aX platform** - MCP server for agent communication
- **MCPJam Inspector** - MCP development tool (parent project at `/Users/jacob/Git/inspector`)

## Package Publishing (Future)

Project is structured for PyPI publishing:
```bash
uv build
uv publish
```

## License

MIT
