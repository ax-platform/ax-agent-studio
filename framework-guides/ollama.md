# Ollama Framework Guide

Run local, open-source LLMs with full privacy and MCP integration.

## Overview

Ollama enables running LLMs locally:
-  Complete privacy (no external API calls)
-  Offline operation
-  Custom/fine-tuned models
-  MCP tool integration
-  OpenAI-compatible API

**When to Use:**
- Privacy-sensitive applications
- Offline/air-gapped deployments
- Custom model testing
- Cost optimization (no API fees)

## Installation

### 1. Install Ollama

**macOS:**
```bash
brew install ollama
```

**Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Windows:**
Download from https://ollama.com/download

### 2. Start Ollama Service

```bash
ollama serve
```

### 3. Pull a Model

```bash
ollama pull llama3.2:latest
# or
ollama pull mistral:latest
# or
ollama pull codellama:latest
```

### 4. Verify

```bash
curl http://localhost:11434/v1/models
```

## Configuration

### Basic Configuration

```json
{
  "mcpServers": {
    "ax-docker": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote@0.1.29",
        "http://localhost:8002/mcp/agents/your_agent",
        "--transport",
        "http-only",
        "--oauth-server",
        "http://localhost:8001"
      ]
    }
  }
}
```

**Note:** Ollama does not support the `permissions` block. All security is via MCP servers.

## Running Your Agent

### Via Dashboard

1. Ensure Ollama is running: `ollama serve`
2. Open dashboard: `./scripts/start_dashboard.sh`
3. Select "Ollama" monitor
4. Select model from dropdown (auto-populated from `ollama list`)
5. Enter agent name
6. Click "Start Agent"

### Via CLI

```bash
python -m ax_agent_studio.monitors.ollama_monitor your_agent_name \
  --config configs/agents/your_agent.json \
  --model llama3.2:latest
```

## Recommended Models

**For coding:**
- `codellama:latest` (7B, 13B, 34B)
- `deepseek-coder:latest`

**For general tasks:**
- `llama3.2:latest` (3B, 8B)
- `mistral:latest` (7B)

**For chat:**
- `llama3.2:latest`
- `phi3:latest`

## Environment Configuration

In `.env`:
```bash
OLLAMA_BASE_URL=http://localhost:11434/v1
```

## Features

- **Local execution:** No data leaves your machine
- **Custom models:** Use any Ollama-compatible model
- **MCP integration:** Full tool access
- **OpenAI-compatible:** Easy migration path

## Limitations

- Model quality varies (not as capable as Claude/GPT-4)
- Requires local compute resources (GPU recommended)
- No built-in security sandboxing
- Slower than cloud APIs (depends on hardware)

## Performance Tips

1. **Use GPU acceleration** for better performance
2. **Choose smaller models** (3B-8B) for faster responses
3. **Quantized models** balance size and quality
4. **Limit context window** to reduce memory usage

## Next Steps

- Browse models: https://ollama.com/library
- See [Claude Agent SDK](./claude-agent-sdk.md) for production security
