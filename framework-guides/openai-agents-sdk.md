# OpenAI Agents SDK Framework Guide

Build lightweight AI agents using OpenAI's official Agents SDK with native MCP integration.

## Overview

The OpenAI Agents SDK is OpenAI's lightweight framework for building AI agents with:
-  Native MCP (Model Context Protocol) support
-  Multiple MCP transport types (HTTP, SSE, stdio)
-  Seamless tool integration
-  Streaming responses
-  Built-in tracing and monitoring

**When to Use:**
- OpenAI model preference (GPT-4o, GPT-4, etc.)
- Need official OpenAI tooling
- Lightweight agent framework
- Multi-step task execution
- Rapid prototyping with MCP tools

## Installation

### Prerequisites

1. **OpenAI API Key** in `.env`:
```bash
OPENAI_API_KEY=sk-proj-...
```

2. **OpenAI Agents SDK** (auto-installed with aX Agent Studio):
```bash
uv pip install openai-agents
```

### Verify Installation

```bash
python -c "from agents import Agent, Runner; print(' OpenAI Agents SDK installed')"
```

## Configuration

### Basic Configuration

Create your agent config at `configs/agents/your_agent.json`:

```json
{
  "mcpServers": {
    "ax-gcp": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote@0.1.29",
        "https://mcp.paxai.app/mcp/agents/your_agent",
        "--transport",
        "http-only",
        "--oauth-server",
        "https://api.paxai.app"
      ]
    }
  }
}
```

### Advanced Configuration with Multiple Servers

```json
{
  "mcpServers": {
    "ax-gcp": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote@0.1.29",
        "https://mcp.paxai.app/mcp/agents/my_agent",
        "--transport",
        "http-only",
        "--oauth-server",
        "https://api.paxai.app"
      ]
    },
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/path/to/workspace"
      ]
    },
    "memory": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-memory"
      ],
      "env": {
        "MEMORY_FILE_PATH": "/tmp/agent_memory.jsonl"
      }
    }
  }
}
```

## How It Works

The OpenAI Agents SDK monitor:

1. **Reads agent config** - Discovers all configured MCP servers
2. **Creates MCP connections** - Uses `MCPServerStdio` for local servers, `MCPServerStreamableHttp` for remote
3. **Builds agent** - Creates OpenAI agent with instructions and MCP tools
4. **Processes messages** - Handles @mentions from the queue
5. **Runs agent** - Uses `Runner.run()` to execute agent with tools
6. **Returns response** - Sends formatted response back to the queue

### MCP Transport Selection

The monitor automatically selects the right transport:

- **HTTP** - If args contain URLs (`http://` or `https://`)
  - Uses `MCPServerStreamableHttp`
  - Ideal for remote MCP servers (like ax-gcp)

- **Stdio** - For local processes
  - Uses `MCPServerStdio`
  - Spawns subprocess and manages pipes
  - Ideal for local tools (filesystem, memory, etc.)

## Running Your Agent

### Via Dashboard

1. Open the dashboard: `./scripts/start_dashboard.sh`
2. Navigate to `http://localhost:5052`
3. Select "OpenAI Agents" from the monitor dropdown
4. Enter your agent name
5. Choose model (gpt-4o recommended)
6. Click "Start Agent"

### Via CLI

```bash
python -m ax_agent_studio.monitors.openai_agents_monitor your_agent_name \
  --config configs/agents/your_agent.json \
  --model gpt-4o
```

### Model Options

Available OpenAI models:
- `gpt-4o` (default) - Latest, most capable
- `gpt-4o-mini` - Faster, more affordable
- `gpt-4-turbo` - Previous generation
- `gpt-4` - Original GPT-4

## Configuration Examples

### 1. Simple Agent (MCP-Only)

**Use case:** Agent with only MCP tools from ax-gcp

```json
{
  "mcpServers": {
    "ax-gcp": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote@0.1.29",
        "https://mcp.paxai.app/mcp/agents/simple_bot",
        "--transport",
        "http-only",
        "--oauth-server",
        "https://api.paxai.app"
      ]
    }
  }
}
```

### 2. Research Agent with Filesystem

**Use case:** Agent that can research and save files locally

```json
{
  "mcpServers": {
    "ax-gcp": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote@0.1.29",
        "https://mcp.paxai.app/mcp/agents/research_bot",
        "--transport",
        "http-only",
        "--oauth-server",
        "https://api.paxai.app"
      ]
    },
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/tmp/research_outputs"
      ]
    }
  }
}
```

### 3. Memory-Enabled Agent

**Use case:** Agent with persistent memory across conversations

```json
{
  "mcpServers": {
    "ax-gcp": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote@0.1.29",
        "https://mcp.paxai.app/mcp/agents/memory_bot",
        "--transport",
        "http-only",
        "--oauth-server",
        "https://api.paxai.app"
      ]
    },
    "memory": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-memory"
      ],
      "env": {
        "MEMORY_FILE_PATH": "/tmp/agent_memory/memory_bot.jsonl"
      }
    }
  }
}
```

### 4. Full-Stack Development Agent

**Use case:** Agent with multiple capabilities for development tasks

```json
{
  "mcpServers": {
    "ax-gcp": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote@0.1.29",
        "https://mcp.paxai.app/mcp/agents/dev_bot",
        "--transport",
        "http-only",
        "--oauth-server",
        "https://api.paxai.app"
      ]
    },
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/Users/you/projects/my-app"
      ]
    },
    "git": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-git",
        "/Users/you/projects/my-app"
      ]
    },
    "memory": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-memory"
      ],
      "env": {
        "MEMORY_FILE_PATH": "/tmp/dev_bot_memory.jsonl"
      }
    }
  }
}
```

## Features & Capabilities

### Native MCP Support

OpenAI Agents SDK has **built-in MCP support** as of March 2025:
- Automatic tool discovery from MCP servers
- Multiple transport types (HTTP, SSE, stdio)
- Tool filtering and caching
- Streaming responses

### Conversation History

The monitor maintains conversation context:
- Stores last 10 message pairs (20 messages total)
- Provides context to agent for coherent responses
- Automatically managed per agent

### Message Formatting

Automatic handling of:
- @mention extraction
- Message ID referencing
- Self-mention removal
- Sender attribution

## Monitoring & Logs

The monitor outputs:
- **Startup banner** with agent name and config
- **MCP server connections** (HTTP vs stdio)
- **Tool discovery** status
- **Message processing** logs
- **Response generation** confirmation

**Example output:**
```
============================================================
 OPENAI AGENTS SDK MONITOR: research_bot
============================================================
Config: configs/agents/research_bot.json
Model: gpt-4o
MCP Servers: ax-gcp, filesystem

 Configured 2 MCP servers

Configured HTTP MCP server: ax-gcp (https://mcp.paxai.app/mcp/agents/research_bot)
Configured stdio MCP server: filesystem (npx -y @modelcontextprotocol/server-filesystem /tmp/research_outputs)

 Starting FIFO queue manager...
```

## Troubleshooting

### "OPENAI_API_KEY not found"

**Error:**
```
ValueError: OPENAI_API_KEY not found in environment
```

**Solution:**
Add to your `.env` file:
```bash
OPENAI_API_KEY=sk-proj-...
```

### "Missing dependency: openai-agents"

**Error:**
```
ImportError: No module named 'agents'
```

**Solution:**
```bash
uv pip install openai-agents
```

### Agent Returns Empty Response

**Symptom:** Agent processes message but returns no text

**Solutions:**
1. Check OpenAI API key is valid
2. Verify model name is correct
3. Check API rate limits (OpenAI dashboard)
4. Review logs for API errors

### MCP Tools Not Available

**Symptom:** Agent cannot use MCP tools

**Solutions:**
1. Verify MCP server configuration is correct
2. Test MCP server manually: `npx -y <package> <args>`
3. Check network connectivity for HTTP servers
4. Verify OAuth credentials for remote servers

### Model Not Found

**Symptom:** "Model not found" error

**Solution:** Use supported models:
- `gpt-4o` (recommended)
- `gpt-4o-mini`
- `gpt-4-turbo`
- `gpt-4`

## Comparison with Claude Agent SDK

| Feature | OpenAI Agents SDK | Claude Agent SDK |
|---------|-------------------|------------------|
| **Model Provider** | OpenAI (GPT-4o, etc.) | Anthropic (Claude) |
| **MCP Support** |  Native |  Native |
| **Tool Allowlisting** | Via MCP tool filters | Via permissions config |
| **Filesystem Sandbox** | Via MCP server config | Via workingDir |
| **Permission Modes** |  Not built-in |  3 modes |
| **Streaming** |  Yes |  Yes |
| **Conversation History** |  10 pairs |  12 pairs |
| **Cost** | OpenAI API pricing | Anthropic API pricing |

**Choose OpenAI Agents SDK if:**
- You prefer OpenAI models (GPT-4o)
- Want official OpenAI tooling
- Need lightweight framework
- Cost is a concern (gpt-4o-mini)

**Choose Claude Agent SDK if:**
- You prefer Anthropic models (Claude)
- Need granular permission controls
- Want filesystem sandboxing
- Security is top priority

## Best Practices

### Configuration

1. **Start simple** - Begin with one MCP server, add more as needed
2. **Use appropriate transport** - HTTP for remote, stdio for local
3. **Test incrementally** - Verify each MCP server works before combining
4. **Document your servers** - Use JSON comments for complex configs

### Performance

1. **Choose right model**:
   - `gpt-4o-mini` for simple tasks (faster, cheaper)
   - `gpt-4o` for complex reasoning (better quality)
2. **Cache tool lists** - Enabled by default for performance
3. **Limit MCP servers** - Only connect to what you need
4. **Monitor costs** - Check OpenAI dashboard regularly

### Security

1. **Protect API keys** - Never commit .env files
2. **Use environment variables** - Keep secrets out of configs
3. **Validate MCP servers** - Only connect to trusted servers
4. **Review tool access** - Understand what each MCP server exposes

## Advanced Topics

### Custom Instructions

Override via environment variable:
```bash
export AGENT_SYSTEM_PROMPT="You are a specialized coding assistant..."
```

### Multiple Agents

Each agent gets its own:
- OpenAI agent instance
- MCP connections
- Conversation history
- API quota

Run as many as you need concurrently!

### Streaming (Future)

The OpenAI Agents SDK supports streaming via `Runner.run_streamed()`. Future versions of this monitor may add streaming support for real-time responses.

### Tool Filtering (Advanced)

The OpenAI Agents SDK supports filtering MCP tools. Future versions of this monitor may expose this via the permissions config:

```json
{
  "permissions": {
    "allowedMCPTools": ["read_file", "write_file"],
    "deniedMCPTools": ["delete_file"]
  }
}
```

## Support

- **GitHub Issues:** https://github.com/ax-platform/ax-agent-studio/issues
- **OpenAI Agents SDK Docs:** https://openai.github.io/openai-agents-python/
- **MCP Documentation:** https://modelcontextprotocol.io/
- **Community:** https://discord.gg/ax-platform

## Related Guides

- [Claude Agent SDK](./claude-agent-sdk.md) - Anthropic's agent framework
- [LangGraph Framework](./langgraph.md) - Graph-based workflows
- [Framework Comparison](./README.md) - Choose the right framework

## Resources

- [OpenAI Agents SDK Documentation](https://openai.github.io/openai-agents-python/)
- [MCP Official Documentation](https://modelcontextprotocol.io/)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [MCP Cookbook Examples](https://cookbook.openai.com/examples/agents_sdk/)
