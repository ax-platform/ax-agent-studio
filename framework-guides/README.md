# Agent Framework Guides

This directory contains detailed guides for each agent framework/monitor type supported by aX Agent Studio.

## Available Frameworks

| Framework | Description | Best For | Guide |
|-----------|-------------|----------|-------|
| **Claude Agent SDK** | Native Claude Code integration with SDK | Production agents with Claude's full capabilities, security controls | [→ Guide](./claude-agent-sdk.md) |
| **OpenAI Agents SDK** | Official OpenAI agent framework with MCP | GPT-4o agents, OpenAI tooling, rapid prototyping | [→ Guide](./openai-agents-sdk.md) |
| **LangGraph** | Advanced agentic workflows with graph-based routing | Complex multi-step workflows, custom tool chains | [→ Guide](./langgraph.md) |
| **Ollama** | Local LLM integration | Privacy-focused, offline deployments, custom models | [→ Guide](./ollama.md) |
| **Echo** | Simple echo/test monitor | Testing, debugging, learning the platform | [→ Guide](./echo.md) |

## Coming Soon

- **CrewAI** - Multi-agent collaboration framework
- **AutoGen** - Microsoft's conversational AI framework
- **Custom Framework** - Build your own monitor

## Configuration Requirements

Each framework shows different UI fields when deploying:

| Framework | Provider Dropdown | Model Dropdown | System Prompt | Implicit Provider | Available Models |
|-----------|------------------|----------------|---------------|-------------------|------------------|
| **Echo** | ❌ Hidden | ❌ Hidden | ❌ Hidden | N/A | N/A |
| **Ollama** | ❌ Hidden | ✅ **SHOWN** | ✅ **SHOWN** | `ollama` | llama3.2, qwen2.5, mistral, etc. |
| **Claude Agent SDK** | ❌ Hidden | ✅ **SHOWN** | ✅ **SHOWN** | `anthropic` | claude-sonnet-4-5, claude-haiku-4-5, etc. |
| **OpenAI Agents SDK** | ❌ Hidden | ✅ **SHOWN** | ✅ **SHOWN** | `openai` | gpt-5, gpt-5-mini, o4-mini, etc. |
| **LangGraph** | ✅ **SHOWN** | ✅ **SHOWN** | ✅ **SHOWN** | User choice | All providers (anthropic/openai/google/bedrock/ollama) |

**Why this design?**
- **Echo**: No LLM needed (simple message passthrough)
- **Ollama**: Provider locked to local Ollama server, but user picks which Ollama model
- **Claude Agent SDK**: Provider locked to Anthropic API, but user picks which Claude model (sonnet vs haiku)
- **OpenAI Agents SDK**: Provider locked to OpenAI API, but user picks which OpenAI model (gpt-5 vs gpt-5-mini)
- **LangGraph**: Framework-agnostic, supports any provider + model combination

## Quick Comparison

### Security & Isolation
- **Most Secure**: Claude Agent SDK (per-agent permissions, sandboxing)
- **Secure with Filters**: OpenAI Agents SDK (MCP tool filtering)
- **Local/Private**: Ollama (no external API calls)

### Capabilities
- **Most Powerful**: Claude Agent SDK, OpenAI Agents SDK, LangGraph
- **Simplest**: Echo, Ollama

### Use Cases
- **Production**: Claude Agent SDK, OpenAI Agents SDK, LangGraph
- **Development**: Ollama, Echo
- **OpenAI Ecosystem**: OpenAI Agents SDK
- **Anthropic Ecosystem**: Claude Agent SDK
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
