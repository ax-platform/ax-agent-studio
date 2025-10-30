# LangGraph Framework Guide

Build advanced agentic workflows using LangChain's graph-based architecture with MCP tool integration.

## Overview

LangGraph allows you to create complex, multi-step agent workflows with:
- ✅ Graph-based flow control
- ✅ Custom tool chains
- ✅ MCP integration via adapters
- ✅ Multiple LLM provider support (Google Gemini, AWS Bedrock, Anthropic, OpenAI)
- ✅ Streaming responses

**When to Use:**
- Complex workflows requiring branching logic
- Multi-step reasoning tasks
- Custom tool orchestration
- When you need graph-based control flow

## Installation

Dependencies auto-installed with aX Agent Studio:
```bash
uv pip install langgraph langchain-mcp-adapters
```

### Provider-Specific Requirements

**Google Gemini:**
```bash
export GOOGLE_API_KEY=your_key_here
```

**AWS Bedrock:**
```bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_REGION=us-east-1
```

**Anthropic:**
```bash
export ANTHROPIC_API_KEY=sk-ant-api03-...
```

**OpenAI:**
```bash
export OPENAI_API_KEY=sk-...
```

## Configuration

### Basic Configuration

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

**Note:** LangGraph does not currently support the `permissions` block. Security is managed through MCP server configuration.

## Running Your Agent

### Via Dashboard

1. Open dashboard: `./scripts/start_dashboard.sh`
2. Select "LangGraph" monitor
3. Choose your provider (Gemini, Bedrock, Anthropic, OpenAI)
4. Enter agent name
5. Click "Start Agent"

### Via CLI

```bash
python -m ax_agent_studio.monitors.langgraph_monitor your_agent_name \
  --config configs/agents/your_agent.json \
  --provider gemini
```

**Provider options:** `gemini`, `bedrock`, `anthropic`, `openai`

## Features

- **Graph-based workflows:** Define complex agent behaviors
- **Multi-LLM support:** Choose the best model for your task
- **MCP integration:** Automatic tool discovery and binding
- **Streaming:** Real-time response streaming

## Limitations

- No built-in filesystem sandboxing (use MCP server permissions)
- No per-agent permission controls (coming soon)
- Provider-specific rate limits apply

## Next Steps

- See [Claude Agent SDK](./claude-agent-sdk.md) for more security controls
- Check [LangGraph documentation](https://langchain-ai.github.io/langgraph/) for workflow patterns
