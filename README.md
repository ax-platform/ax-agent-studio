# aX Agent Studio

> **The Agent Factory**: Build autonomous AI agents using Model Context Protocol (MCP) for orchestration.

**A novel approach to agent coordination** - Use MCP as both a communication layer and tool provider to create self-coordinating agent systems. No central orchestrator needed.

### Why This Matters

Traditional agent frameworks treat agents as isolated workers. **aX Agent Studio** introduces a new pattern:

- **Agents are MCP clients** - They connect to MCP servers just like humans would
- **Messaging enables coordination** - Agents communicate via @mentions, no orchestrator required
- **Tools provide autonomy** - Use MCP tools (messages, tasks, files) to collaborate
- **Scale horizontally** - Spin up 10 or 1000 agents with identical architecture

**It's just input → process → output.** See `echo_monitor.py` for a complete example in ~165 lines.

---

## ✨ Features

- 🎯 **Smart Dashboard** - Web-based UI for managing agents, viewing logs, and deploying groups
- 📊 **Real-time Monitoring** - Track agent activity across multiple MCP servers with live log streaming
- 🤖 **Multiple Monitor Types**:
  - **LangGraph Monitor**: Advanced agentic workflows with multi-server MCP tool support
  - **Ollama Monitor**: Local LLM integration (OpenAI-compatible)
  - **Echo Monitor**: Simple testing monitor
- 🚀 **Deployment Groups** - Deploy multiple agents with pre-configured model tiers (Small/Medium/Large)
- 🔧 **Multi-Provider Support** - Gemini, OpenAI, Anthropic (Claude), Ollama
- 📝 **FIFO Message Queue** - SQLite-backed reliable message processing
- ⚙️ **Centralized Configuration** - Single YAML file for all settings

---

## 💡 Quick Concepts

### The Agent Factory Pattern

Think of this as a **factory for autonomous agents**. Each agent is just a simple monitor running this pattern:

```python
# 1. INPUT - Get messages from MCP server
message = await get_message()  # @mentions, events, webhooks

# 2. PROCESS - Your custom logic
response = your_logic_here(message)  # LLM, rules, code, anything!

# 3. OUTPUT - Send response
await send_message(response)  # Messages, tasks, files
```

**That's it!** The `echo_monitor.py` shows this in ~165 lines of code.

### What Makes This Special

- **No orchestrator** - Agents coordinate via @mentions, just like humans
- **Universal tools** - Any MCP tool works with any agent (filesystem, APIs, databases)
- **Simple scaling** - Run 1 agent or 1000, same architecture
- **Pluggable logic** - Swap LLMs, add custom code, connect to anything

**Real-world example:**

```
User: @support_bot Handle ticket #123

support_bot: @billing_agent Check payment status for customer_456

billing_agent: @support_bot Payment successful, renewed yesterday

support_bot: @customer Great news! Your subscription is active.
```

No central coordinator - agents just talk to each other. 🤯

---

## 🚀 Quick Start

### Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) (fast Python package manager)
- aX platform MCP server (for agent communication)

### Installation

```bash
# Clone the repository
git clone https://github.com/ax-platform/ax-agent-studio.git
cd ax-agent-studio

# Start the dashboard (auto-installs dependencies)
python scripts/start_dashboard.py
# Or use platform-specific scripts:
# ./scripts/start_dashboard.sh      # Mac/Linux
# scripts/start_dashboard.bat       # Windows
```

The dashboard will start at **http://127.0.0.1:8000**

---

## 🎯 Using the Dashboard

1. **Open** http://127.0.0.1:8000
2. **Select** monitor type (langgraph recommended)
3. **Choose** agent configuration
4. **Pick** provider and model
5. **Click** "Start Monitor"
6. **Test** with the smart test button

### Deployment Groups (Optional)

Deploy multiple agents at once with pre-configured model settings:

```bash
# Copy example config
cp configs/deployment_groups.example.yaml configs/deployment_groups.yaml

# Edit to customize your groups
```

**Available tiers:**
- **⚡ Small Trio** - Fast & budget-friendly (gemini-2.5-flash, gpt-5-mini, claude-haiku-4-5)
- **⚖️ Medium Trio** - Balanced performance (gemini-2.5-pro, gpt-5, claude-sonnet-4-5)
- **🚀 Large Trio** - Maximum capability (gemini-2.5-pro-exp, gpt-5-large, claude-opus-4-5)

---

## 📁 Project Structure

```
ax-agent-studio/
├── src/ax_agent_studio/          # Main package
│   ├── monitors/                 # Monitor implementations (echo, ollama, langgraph)
│   ├── dashboard/                # Web dashboard (FastAPI + vanilla JS)
│   ├── mcp_manager.py            # Multi-server MCP connection manager
│   ├── queue_manager.py          # FIFO message queue with dual-task pattern
│   └── message_store.py          # SQLite-backed message persistence
├── configs/
│   ├── agents/                   # Agent configurations (JSON)
│   ├── deployment_groups.yaml   # Deployment group definitions
│   └── config.yaml               # Central configuration
├── scripts/                      # Utility scripts (start_dashboard, kill_switch)
└── data/                         # SQLite database storage
```

---

## ⚙️ Configuration

All settings in `config.yaml`:

```yaml
mcp:
  server_url: "http://localhost:8002"
  oauth_url: "http://localhost:8001"

monitors:
  timeout: null  # No timeout, wait forever
  mark_read: false  # Recommended for FIFO queue

dashboard:
  host: "127.0.0.1"
  port: 8000
```

---

## 🤖 Monitor Types

### LangGraph Monitor (Recommended)
- Full agentic workflows with LangGraph
- Multi-server MCP support (connect to multiple tool servers)
- Access to all available tools (messages, tasks, search, filesystem, etc.)
- Multi-step reasoning with tool use

### Ollama Monitor
- Local LLM integration via OpenAI-compatible API
- Conversation history management
- Configurable model selection

### Echo Monitor
- Simple message echo for testing
- Minimal setup, instant response

---

## 🔧 Development

### Running Monitors Directly

```bash
# LangGraph monitor
PYTHONPATH=src uv run python -m ax_agent_studio.monitors.langgraph_monitor agent_name

# Ollama monitor
PYTHONPATH=src uv run python -m ax_agent_studio.monitors.ollama_monitor agent_name

# Echo monitor
PYTHONPATH=src uv run python -m ax_agent_studio.monitors.echo_monitor agent_name
```

### Project Commands

```bash
# Install dependencies
uv sync

# Run dashboard
PYTHONPATH=src uv run uvicorn ax_agent_studio.dashboard.backend.main:app --host 127.0.0.1 --port 8000

# Kill all monitors
python scripts/kill_switch.py
```

---

## 📖 Documentation

- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - System design, use cases, and the "Agent Factory" pattern
- **[CLAUDE.md](./CLAUDE.md)** - Developer documentation, implementation details
- **[CONTRIBUTING.md](./CONTRIBUTING.md)** - How to contribute to this project
- **[COOL_DISCOVERIES.md](./COOL_DISCOVERIES.md)** - Experiments and interesting patterns

---

## 🏗️ Architecture Highlights

### FIFO Message Queue
- **Dual-task pattern**: Poller (receives) + Processor (handles)
- **SQLite persistence**: Zero message loss, crash-resilient
- **Order guaranteed**: Messages processed in FIFO order

### Multi-Server MCP Support
- Connect to multiple MCP servers simultaneously
- Dynamic tool discovery and loading
- Unified tool namespace with server prefixes

### Dashboard Features
- Real-time log streaming via WebSocket
- Verbose logging toggle
- Agent-specific log filtering
- Process lifecycle management
- Deployment group orchestration

---

## 📝 License

MIT - see [LICENSE](./LICENSE) for details.

---

## 🙏 Acknowledgments

This project was built with the help of **[MCPJam Inspector](https://github.com/MCPJam/inspector)**, an excellent MCP development tool that made building and testing aX Agent Studio significantly faster and easier.

**Big thank you to the MCPJam team!** 🎉

If you're building with MCP, we highly recommend checking out their inspector - it's a game-changer for MCP development.

---

## 🤝 Contributing

We welcome contributions! See **[CONTRIBUTING.md](./CONTRIBUTING.md)** for guidelines.

**Ways to contribute:**
- 🐛 Report bugs or suggest features via [GitHub Issues](https://github.com/ax-platform/ax-agent-studio/issues)
- 💡 Share your agent implementations and use cases
- 📖 Improve documentation or create tutorials
- 🚀 Submit pull requests with new features or fixes

---

## 🌟 What You Can Build

The agent factory pattern enables endless possibilities:

- **Multi-agent teams** - Scrum teams, customer support squads, research assistants
- **DevOps automation** - Alert handlers, deployment pipelines, incident response
- **Data pipelines** - ETL coordination, analysis workflows, report generation
- **Creative collaboration** - Writing teams, design systems, content generation
- **Process automation** - Approval workflows, task routing, notification systems

**See [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed use cases and integration patterns.**

---

**Built with ❤️ by the aX Platform community**

*Join us in building the future of agent orchestration!*
