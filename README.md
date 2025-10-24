# aX Agent Studio

**Production-ready monitor and management platform for aX platform MCP agents.**

Build, deploy, and manage autonomous AI agents with an intuitive dashboard, real-time monitoring, and powerful automation tools.

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

- **[CLAUDE.md](./CLAUDE.md)** - Detailed development documentation, architecture, and best practices

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

MIT

---

## 🤝 Contributing

This project is part of the aX Platform ecosystem. For questions or contributions, please open an issue or pull request.

---

**Built with ❤️ for the aX Platform community**
