# Echo Framework Guide

Simple echo/test monitor for learning and debugging the aX Agent Studio platform.

## Overview

The Echo monitor is a minimal implementation that:
- ✅ Echoes back received messages
- ✅ Demonstrates basic monitor structure
- ✅ Tests MCP connectivity
- ✅ No AI model required

**When to Use:**
- Learning how monitors work
- Testing MCP server connections
- Debugging queue/message flow
- Template for custom monitors

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
        "http://localhost:8002/mcp/agents/echo_test",
        "--transport",
        "http-only",
        "--oauth-server",
        "http://localhost:8001"
      ]
    }
  }
}
```

## Running Your Agent

### Via Dashboard

1. Select "Echo" monitor
2. Enter agent name
3. Click "Start Agent"

### Via CLI

```bash
python -m ax_agent_studio.monitors.echo_monitor echo_test \
  --config configs/agents/echo_test.json
```

## Behavior

When you send:
```
@echo_test Hello world!
```

The agent responds:
```
@you Echo: Hello world!
```

## Use Cases

- **Learn the platform:** Understand message flow without AI complexity
- **Test MCP setup:** Verify MCP servers are configured correctly
- **Debug issues:** Isolate problems to monitor vs. MCP layer
- **Template code:** Copy echo_monitor.py to build custom monitors

## Source Code

See `src/ax_agent_studio/monitors/echo_monitor.py` for implementation details.

## Next Steps

- Build a custom monitor using Echo as a template
- See [Claude Agent SDK](./claude-agent-sdk.md) for production agents
