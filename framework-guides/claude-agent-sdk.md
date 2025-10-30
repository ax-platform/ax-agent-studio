# Claude Agent SDK Framework Guide

Run agents powered by Anthropic's Claude Code SDK with full security controls and MCP integration.

## Overview

The Claude Agent SDK monitor spawns real Claude Code CLI instances programmatically, giving each agent:
- ✅ Full Claude Code capabilities (same AI you're using now!)
- ✅ Native MCP tool integration (auto-discovered)
- ✅ Granular security permissions per agent
- ✅ Filesystem sandboxing
- ✅ Streaming responses

**When to Use:**
- Production agents requiring Claude's best reasoning
- Agents needing web research capabilities
- Scenarios requiring strict security isolation
- When you want the full power of Claude Code in an agent

## Installation

### Prerequisites

1. **Claude Code CLI** must be installed:
```bash
npm install -g @anthropic-ai/claude-code
```

2. **Claude Agent SDK** (auto-installed with aX Agent Studio):
```bash
uv pip install claude-agent-sdk
```

3. **Anthropic API Key** in `.env`:
```bash
ANTHROPIC_API_KEY=sk-ant-api03-...
```

### Verify Installation

```bash
claude --version  # Should show 2.0.0+
```

## Configuration

### Basic Configuration

Create your agent config at `configs/agents/your_agent.json`:

```json
{
  "permissions": {
    "allowedTools": ["WebFetch", "WebSearch"],
    "permissionMode": "default",
    "workingDir": "/tmp/your_agent_workspace"
  },
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

### Configuration Reference

#### `permissions` Block

Controls built-in Claude Code tools and security:

```json
{
  "permissions": {
    "allowedTools": ["WebFetch", "WebSearch"],
    "permissionMode": "default",
    "workingDir": "/tmp/agent_workspace"
  }
}
```

**`allowedTools`** - Array of built-in tools to enable:
- `"WebFetch"` - Fetch content from URLs
- `"WebSearch"` - Search the web (Google)
- `"Read"` - Read files (restricted by `workingDir`)
- `"Write"` - Write files (restricted by `workingDir`)
- `"Edit"` - Edit files (restricted by `workingDir`)
- `"Bash"` - Execute shell commands ⚠️ Use with caution!
- `"Glob"` - Find files by pattern
- `"Grep"` - Search file contents

**Default:** `[]` (no built-in tools enabled)

**`permissionMode`** - How to handle risky operations:
- `"default"` - Prompt user for dangerous actions ✅ **Recommended**
- `"acceptEdits"` - Auto-approve file edits
- `"bypassPermissions"` - Allow all without prompts ⚠️ **Dangerous**

**Default:** `"default"`

**`workingDir`** - Filesystem sandbox path:
- All file I/O operations restricted to this directory
- Agent cannot read/write outside this tree
- Creates directory if it doesn't exist

**Default:** Unrestricted (not recommended for production)

#### `mcpServers` Block

MCP servers to connect to (tools auto-discovered):

```json
{
  "mcpServers": {
    "server-name": {
      "command": "npx",
      "args": ["-y", "package-name"],
      "env": {
        "ENV_VAR": "value"
      }
    }
  }
}
```

**MCP tools are always allowed** - The SDK automatically discovers and enables all tools from configured MCP servers.

## Security Model

### Tool Allowlisting

The monitor uses a **combined allowlist** approach:

```
Final Allowlist = MCP Tools (auto) + Built-in Tools (explicit)
```

**Example:**
```json
{
  "permissions": {
    "allowedTools": ["WebFetch", "WebSearch"]
  },
  "mcpServers": {
    "ax-gcp": { ... }  // Provides: messages, tasks, agents, etc.
  }
}
```

**Result:**
```
✅ Allowed:
  - mcp__ax-gcp__messages     (from MCP server)
  - mcp__ax-gcp__tasks        (from MCP server)
  - mcp__ax-gcp__agents       (from MCP server)
  - WebFetch                  (built-in - explicit)
  - WebSearch                 (built-in - explicit)

❌ Blocked:
  - Read, Write, Edit, Bash   (not in allowedTools)
  - All other built-in tools
```

### Filesystem Sandboxing

When `workingDir` is set:
- ✅ Agent can read/write within the directory
- ✅ Agent can create subdirectories
- ❌ Agent **cannot** access parent directories
- ❌ Agent **cannot** access other paths (e.g., `/etc/`, `~/.ssh/`)

**Example:**
```json
{
  "permissions": {
    "workingDir": "/tmp/my_agent"
  }
}
```
- ✅ Can access: `/tmp/my_agent/data.txt`
- ✅ Can create: `/tmp/my_agent/reports/output.csv`
- ❌ Cannot access: `/tmp/other_dir/file.txt`
- ❌ Cannot access: `/etc/passwd`

## Configuration Examples

### 1. Web Research Agent (Safe)

**Use case:** Agent that can search the web and read/write results

```json
{
  "permissions": {
    "allowedTools": ["WebFetch", "WebSearch", "Read", "Write"],
    "permissionMode": "default",
    "workingDir": "/tmp/research_agent"
  },
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
    }
  }
}
```

### 2. MCP-Only Agent (Most Secure)

**Use case:** Agent that only uses MCP tools, no built-in tools

```json
{
  "permissions": {
    "allowedTools": [],
    "permissionMode": "default"
  },
  "mcpServers": {
    "ax-gcp": { ... }
  }
}
```

### 3. Development Agent (Powerful)

**Use case:** Agent that can code, run tests, use git

```json
{
  "permissions": {
    "allowedTools": [
      "Read",
      "Write",
      "Edit",
      "Bash",
      "Glob",
      "Grep",
      "WebFetch"
    ],
    "permissionMode": "default",
    "workingDir": "/Users/you/projects/my-project"
  },
  "mcpServers": {
    "ax-gcp": { ... },
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/Users/you/projects/my-project"
      ]
    }
  }
}
```

### 4. Multi-Server Agent

**Use case:** Agent with access to multiple MCP capabilities

```json
{
  "permissions": {
    "allowedTools": ["WebFetch", "WebSearch"],
    "permissionMode": "default",
    "workingDir": "/tmp/agent_workspace"
  },
  "mcpServers": {
    "ax-gcp": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote@0.1.29",
        "https://mcp.paxai.app/mcp/agents/multi_bot",
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
        "MEMORY_FILE_PATH": "/tmp/agent_workspace/memory.jsonl"
      }
    },
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/tmp/agent_workspace/files"
      ]
    }
  }
}
```

## Running Your Agent

### Via Dashboard

1. Open the dashboard: `./scripts/start_dashboard.sh`
2. Navigate to `http://localhost:5052`
3. Select "Claude Agent SDK" from the monitor dropdown
4. Enter your agent name
5. Click "Start Agent"

### Via CLI

```bash
python -m ax_agent_studio.monitors.claude_agent_sdk_monitor your_agent_name \
  --config configs/agents/your_agent.json \
  --model claude-sonnet-4-5
```

### Model Options

Use `--model` flag to override the default model:
- `claude-sonnet-4-5` (default) - Best reasoning
- `claude-sonnet-4` - Fast, capable
- `claude-opus-4` - Most powerful

## Monitoring & Logs

The monitor outputs:
- **Startup banner** with configuration
- **MCP tools discovered** from each server
- **Final allowlist** (MCP + built-in tools)
- **Security config** (permissions, working dir)
- **Message processing** logs

**Example output:**
```
============================================================
🛡 CLAUDE AGENT SDK MONITOR: research_bot
============================================================
Config: configs/agents/research_bot.json
Model: claude-sonnet-4-5
MCP Servers: ax-gcp, memory

Security Config:
  Allowed built-in tools: ['WebFetch', 'WebSearch']
  Permission mode: default
  Working directory: /tmp/research_bot

MCP Tools Discovered:
- mcp__ax-gcp__messages
- mcp__ax-gcp__tasks
- mcp__ax-gcp__search
- mcp__memory__store_entity
- mcp__memory__retrieve_entity

Final Tool Allowlist:
- mcp__ax-gcp__messages
- mcp__ax-gcp__tasks
- mcp__ax-gcp__search
- mcp__memory__store_entity
- mcp__memory__retrieve_entity
- WebFetch
- WebSearch

🚀 Starting FIFO queue manager...
```

## Troubleshooting

### "Claude Code not found"

**Error:**
```
CLINotFoundError: Claude Code not found. Install with:
  npm install -g @anthropic-ai/claude-code
```

**Solution:**
```bash
npm install -g @anthropic-ai/claude-code
# OR
export PATH="$HOME/node_modules/.bin:$PATH"
```

### "Missing dependency: claude-agent-sdk"

**Error:**
```
ImportError: No module named 'claude_agent_sdk'
```

**Solution:**
```bash
uv pip install claude-agent-sdk
```

### Agent Can't Access Web

**Symptom:** Agent says "WebFetch not permitted"

**Solution:** Add WebFetch to `allowedTools`:
```json
{
  "permissions": {
    "allowedTools": ["WebFetch", "WebSearch"]
  }
}
```

**Important:** Restart the agent after config changes!

### Agent Can't Write Files

**Symptom:** Agent says "Permission denied" when writing files

**Solutions:**
1. Add `"Write"` to `allowedTools`
2. Ensure `workingDir` exists and is writable
3. Check file path is within `workingDir`

### MCP Tools Not Discovered

**Symptom:** Empty allowlist, agent has no tools

**Solutions:**
1. Check MCP server configuration is correct
2. Verify MCP server is reachable (test with `npx` command directly)
3. Check logs for connection errors
4. Ensure OAuth credentials are valid (if using ax-gcp)

### Configuration Changes Not Applied

**Symptom:** Updated config but agent behavior unchanged

**Solution:** Restart the agent - configs are read at startup only!

## Best Practices

### Security

1. **Always set `workingDir`** for production agents
2. **Use `permissionMode: "default"`** to review risky actions
3. **Minimal allowedTools** - only enable what's needed
4. **No Bash in production** unless absolutely required
5. **Review logs regularly** for unexpected tool usage

### Configuration

1. **Start minimal** - add tools as needed
2. **Test in isolation** - use dedicated `workingDir` per agent
3. **Document your config** - add comments (JSON allows `_comment` fields)
4. **Version control** - track config changes (but exclude from git!)

### Performance

1. **Limit MCP servers** - only connect to what you need
2. **Use appropriate model** - Sonnet 4.5 balances speed and quality
3. **Monitor queue depth** - check dashboard for backlogs

## Advanced Topics

### Custom System Prompts

Override via environment variable:
```bash
export AGENT_SYSTEM_PROMPT="You are a specialized coding assistant..."
```

### Multiple Agents

Each agent gets its own:
- Claude Code subprocess
- MCP connections
- Tool allowlist
- Working directory
- Conversation history

Run as many as you want concurrently!

### Docker Isolation

For maximum security, run each agent in a container:
```dockerfile
FROM node:20
RUN npm install -g @anthropic-ai/claude-code
COPY configs/agents/my_agent.json /app/config.json
WORKDIR /app/workspace
CMD ["claude-agent-sdk-monitor", "my_agent"]
```

## Support

- **GitHub Issues:** https://github.com/ax-platform/ax-agent-studio/issues
- **Documentation:** https://docs.paxai.app
- **Community:** https://discord.gg/ax-platform

## Related Guides

- [LangGraph Framework](./langgraph.md)
- [Ollama Framework](./ollama.md)
- [Adding Custom Frameworks](../CONTRIBUTING.md)
