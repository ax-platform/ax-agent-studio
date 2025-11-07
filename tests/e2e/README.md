# E2E Testing Architecture

## Overview
Clean, maintainable E2E testing approach that avoids technical debt by using the right tool for each layer.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     E2E Test Flow                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Deploy Agent (Python → Dashboard API)                  │
│     - Fast, reliable, no UI flakiness                       │
│     - Uses: tests/e2e/helpers/dashboard_api.py             │
│                                                             │
│  2. Validate Response (JavaScript → MCP JAM SDK)           │
│     - Tests actual agent behavior                           │
│     - Uses: tests/e2e/test-01-echo-deployment.js           │
│                                                             │
│  3. Regression Prevention (Pre-commit hooks)                │
│     - Runs on dashboard backend changes                     │
│     - Catches API regressions before commit                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Dashboard API Helper (`helpers/dashboard_api.py`)
**Purpose**: Programmatic access to Dashboard backend

**Key Methods**:
- `kill_all_monitors()` - Clean slate
- `start_monitor(agent_name, monitor_type, ...)` - Deploy agent
- `list_monitors()` - Check status
- `wait_for_monitor_running()` - Wait for deployment

**Why**: Direct API calls are 10x faster and more reliable than UI automation

### 2. Agent Type Tests (`test_all_agent_types.py`)
**Purpose**: Test deployment of all agent types

**Tests**:
- Echo Monitor (Simple)
- Ollama Monitor (AI)
- Claude Agent SDK (Secure)
- OpenAI Agents SDK
- LangGraph (Tools)

**Flow**: API deploy → Wait for RUNNING → Validate with MCP JAM SDK

### 3. JavaScript Validation (`test-01-echo-deployment.js`)
**Purpose**: Validate agent responses using MCP JAM SDK

**Why**: MCP JAM SDK is the official way to interact with agents
- Uses `wait=true, wait_mode='mentions'` for reliable responses
- Tests actual agent behavior, not just deployment
- Avoids self-mention loops (lunar_craft_128 → ghost_ray_363)

## Running Tests

```bash
# Test Echo deployment via API
npm run test:e2e:echo

# Test all agent types (future)
npm run test:e2e:all-types

# Run pre-commit hooks (includes E2E)
pre-commit run --all-files
```

## Pre-commit Integration

E2E tests run automatically when you modify:
- Dashboard backend code (`src/ax_agent_studio/dashboard/backend/*.py`)
- E2E helpers (`tests/e2e/helpers/*.py`)

This prevents regressions in:
- Agent deployment APIs
- Monitor lifecycle management
- Dashboard backend logic

## Avoiding Tech Debt

### ❌ What We DON'T Do
- UI automation with Chrome DevTools for deployment
  - **Why**: Slow, flaky, brittle (UIDs change)
  - **When**: Only for smoke testing UI→API wiring (rare)

- Testing every model variant
  - **Why**: Too slow, not worth it
  - **Instead**: Test with default models only

- Testing Production environment
  - **Why**: Local testing is sufficient
  - **Instead**: Acknowledge Production exists in dropdown, but don't test it

### ✅ What We DO
- **API-first testing**: Fast, reliable, maintainable
- **MCP JAM SDK validation**: Official way to test agent behavior
- **Pre-commit hooks**: Catch regressions before they land
- **Default models only**: Faster tests, same coverage

## Test Organization

```
tests/e2e/
├── README.md                      # This file
├── helpers/
│   ├── __init__.py
│   └── dashboard_api.py          # Python API helper
├── test_all_agent_types.py       # API-based deployment tests
├── test_ui_api_wiring.py         # UI smoke test (optional)
└── test-01-echo-deployment.js    # MCP JAM SDK validation
```

## Future Enhancements

1. **Complete JavaScript validation** in `test_all_agent_types.py`
   - Currently skipped, needs implementation
   - Should call JS validation script with agent names as args

2. **Parallel test execution**
   - Run all agent type tests concurrently
   - Reduce total test time

3. **CI/CD Integration**
   - Run E2E tests in GitHub Actions
   - Block PRs that break dashboard APIs

## Key Learnings

1. **Use the right tool for each layer**
   - API for deployment (Python + httpx)
   - MCP JAM SDK for validation (JavaScript)
   - Chrome DevTools only for UI smoke tests

2. **Avoid self-mention loops**
   - System blocks self-mentions to prevent infinite loops
   - Always send FROM different agent than TO

3. **Use `wait=true` for validation**
   - Much more reliable than sleep timers
   - Returns response immediately when ready

4. **Keep it simple**
   - Test default configurations
   - Don't over-test model variants
   - Focus on regression prevention

## Summary

This architecture provides:
- ✅ Fast, reliable tests (API-first)
- ✅ Real behavior validation (MCP JAM SDK)
- ✅ Regression prevention (pre-commit hooks)
- ✅ Clean, maintainable code (no conflicting approaches)
- ✅ No technical debt (one approach per layer)
