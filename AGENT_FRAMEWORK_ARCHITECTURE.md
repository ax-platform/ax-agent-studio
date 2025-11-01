# Agent Framework Architecture

## Problem Statement

Different agent frameworks have different authentication and configuration requirements. Currently, the platform uses global environment variables which creates conflicts:

- `USE_CLAUDE_SUBSCRIPTION=true` removes `ANTHROPIC_API_KEY` globally
- This breaks Anthropic provider for ALL monitors, even LangGraph
- Each framework needs different auth: subscription vs API key vs no auth

## Design Principles

1. **Agent Type as Pivot**: Monitor type determines all configuration options
2. **Isolated Authentication**: Each monitor manages its own auth, not global env vars
3. **Modular Design**: Easy to add new agent frameworks
4. **Clear Contracts**: Each framework declares its requirements upfront

## Agent Framework Configurations

### Echo Monitor
```yaml
type: echo
authentication: none
provider: none
model: none
settings: []
```

### Ollama Monitor
```yaml
type: ollama
authentication: none  # Local server, no auth needed
provider: implicit  # Always "ollama", not user-selectable
model: required  # User selects from available Ollama models
settings:
  - model: dropdown (from ollama provider)
  - system_prompt: optional
```

### Claude Agent SDK Monitor
```yaml
type: claude_agent_sdk
authentication:
  mode: subscription_or_api_key
  preference: subscription  # Prefer subscription if available
  fallback: api_key  # Fall back to API key if subscription fails
provider: implicit  # Always "anthropic", not user-selectable
model: required  # User selects from Claude models only
settings:
  - model: dropdown (claude-sonnet-4-5, claude-haiku-4-5, etc.)
  - system_prompt: optional
auth_isolation: true  # Manage own auth, don't affect global env
```

### LangGraph Monitor
```yaml
type: langgraph
authentication: api_key_required  # Must have API key for selected provider
provider: required  # User selects provider (anthropic, openai, google, etc.)
model: required  # User selects model from chosen provider
settings:
  - provider: dropdown (anthropic, openai, google, ollama, aws_bedrock)
  - model: dropdown (depends on provider)
  - system_prompt: optional
```

## Authentication Flow

### Global Environment (Current - BROKEN)
```
.env:
  ANTHROPIC_API_KEY=sk-ant-...
  USE_CLAUDE_SUBSCRIPTION=true

Monitor Start:
  1. Check USE_CLAUDE_SUBSCRIPTION
  2. Remove ANTHROPIC_API_KEY from os.environ
  3. ALL monitors lose access to Anthropic API
  4. LangGraph can't use Anthropic provider ❌
```

### Per-Monitor Authentication (Proposed - FIXED)
```
.env:
  ANTHROPIC_API_KEY=sk-ant-...
  USE_CLAUDE_SUBSCRIPTION=true  # Only affects Claude Agent SDK

Monitor Start (Claude Agent SDK):
  1. Read USE_CLAUDE_SUBSCRIPTION
  2. If true:
     - Try subscription auth (claude login)
     - Temporarily unset ANTHROPIC_API_KEY for THIS monitor only
     - Restore after ClaudeAgentOptions created
  3. If subscription fails OR USE_CLAUDE_SUBSCRIPTION=false:
     - Use ANTHROPIC_API_KEY
  4. Other monitors unaffected ✓

Monitor Start (LangGraph with Anthropic):
  1. Ignore USE_CLAUDE_SUBSCRIPTION (not relevant)
  2. Use ANTHROPIC_API_KEY directly
  3. Works normally ✓
```

## Dashboard UI Flow

```
User Selects Agent Type
  ↓
┌─────────────────────────────┐
│  Agent Type Configuration   │
│  (Defined per framework)    │
└─────────────────────────────┘
  ↓
┌──────────────┬──────────────────┬───────────────────┬─────────────────┐
│    Echo      │     Ollama       │  Claude Agent SDK │   LangGraph     │
├──────────────┼──────────────────┼───────────────────┼─────────────────┤
│ No settings  │ Model dropdown   │ Model dropdown    │ Provider        │
│              │ System prompt    │ System prompt     │ Model dropdown  │
│              │                  │                   │ System prompt   │
└──────────────┴──────────────────┴───────────────────┴─────────────────┘
  ↓
Backend API: /api/monitors/start
  {
    "agent_name": "Aurora",
    "monitor_type": "claude_agent_sdk",
    "model": "claude-sonnet-4-5",
    "system_prompt": "...",
    // provider: null (implicit for claude_agent_sdk)
  }
  ↓
Monitor Manager:
  1. Load framework config for "claude_agent_sdk"
  2. Validate: model must be Claude model
  3. Setup auth per framework requirements
  4. Start monitor with correct auth
```

## Implementation Plan

### Phase 1: Framework Registry (Backend)
Create `src/ax_agent_studio/framework_registry.py`:
```python
@dataclass
class FrameworkConfig:
    type: str
    auth_mode: str  # "none", "api_key", "subscription_or_api_key", "subscription_only"
    provider_mode: str  # "none", "implicit", "required"
    model_mode: str  # "none", "required"
    implicit_provider: Optional[str] = None
    supported_models: Optional[List[str]] = None

FRAMEWORKS = {
    "echo": FrameworkConfig(
        type="echo",
        auth_mode="none",
        provider_mode="none",
        model_mode="none"
    ),
    "ollama": FrameworkConfig(
        type="ollama",
        auth_mode="none",
        provider_mode="implicit",
        model_mode="required",
        implicit_provider="ollama"
    ),
    "claude_agent_sdk": FrameworkConfig(
        type="claude_agent_sdk",
        auth_mode="subscription_or_api_key",
        provider_mode="implicit",
        model_mode="required",
        implicit_provider="anthropic",
        supported_models=["claude-sonnet-4-5", "claude-haiku-4-5", "claude-opus-4"]
    ),
    "langgraph": FrameworkConfig(
        type="langgraph",
        auth_mode="api_key",
        provider_mode="required",
        model_mode="required"
    )
}
```

### Phase 2: Update Dashboard API
- GET `/api/frameworks` - Return framework configs
- GET `/api/frameworks/{type}/models` - Get models for framework
- POST `/api/monitors/start` - Validate against framework config

### Phase 3: Update Dashboard Frontend
- Load framework configs on init
- Dynamically show/hide UI based on framework config
- Validate selections against framework requirements

### Phase 4: Isolated Authentication
- Update Claude Agent SDK monitor to use try/finally for API key
- Don't modify global environment
- Each monitor gets its own auth context

## Benefits

1. ✅ Claude Agent SDK can use subscription without breaking other monitors
2. ✅ LangGraph can use Anthropic API key even when subscription is enabled
3. ✅ Easy to add new frameworks (just add to registry)
4. ✅ Type-safe configuration per framework
5. ✅ Clear separation of concerns
6. ✅ No global state pollution

## Migration Path

1. Implement framework registry (backend only)
2. Update monitor start logic to use registry
3. Test with existing monitors
4. Update dashboard to use `/api/frameworks` endpoint
5. Remove hardcoded framework logic from frontend
6. Add new frameworks by just updating registry
