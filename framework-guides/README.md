# Agent Framework Guides

This directory contains detailed guides for each agent framework/monitor type supported by aX Agent Studio.

## Available Frameworks

| Framework | Description | Best For | Guide |
|-----------|-------------|----------|-------|
| **Claude Agent SDK** | Native Claude Code integration with SDK | Production agents with Claude's full capabilities, security controls | [→ Guide](./claude-agent-sdk.md) |
| **LangGraph** | Advanced agentic workflows with graph-based routing | Complex multi-step workflows, custom tool chains | [→ Guide](./langgraph.md) |
| **Ollama** | Local LLM integration | Privacy-focused, offline deployments, custom models | [→ Guide](./ollama.md) |
| **Echo** | Simple echo/test monitor | Testing, debugging, learning the platform | [→ Guide](./echo.md) |

## Coming Soon

- **OpenAI Agents SDK** - OpenAI's agent framework integration
- **CrewAI** - Multi-agent collaboration framework
- **AutoGen** - Microsoft's conversational AI framework
- **Custom Framework** - Build your own monitor

## Quick Comparison

### Security & Isolation
- **Most Secure**: Claude Agent SDK (per-agent permissions, sandboxing)
- **Local/Private**: Ollama (no external API calls)

### Capabilities
- **Most Powerful**: Claude Agent SDK, LangGraph
- **Simplest**: Echo, Ollama

### Use Cases
- **Production**: Claude Agent SDK, LangGraph
- **Development**: Ollama, Echo
- **Research**: All frameworks

## Adding a New Framework

See [CONTRIBUTING.md](../CONTRIBUTING.md) for instructions on adding your own agent framework.

Each framework guide should include:
1. **Overview** - What it is and when to use it
2. **Installation** - Dependencies and setup
3. **Configuration** - Agent config file format
4. **Permissions** - Security and access controls
5. **Examples** - Real-world configurations
6. **Troubleshooting** - Common issues and solutions
