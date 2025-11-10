# aX Agent Studio Testing Guide

Comprehensive reference for all tests in the project, organized by type and purpose.

---

## Quick Reference

| Test Type | Count | Run Command | In Pre-Commit |
|-----------|-------|-------------|---------------|
| **Pre-Commit** | 3 | automatic on commit | ✅ |
| **Unit Tests** | 7 | `uv run python tests/test_*.py` | ❌ |
| **Integration Tests** | 8 | `uv run python tests/test_*_e2e.py` | ❌ |
| **E2E Tests (Dashboard)** | 12 | `uv run python tests/e2e/test_*.py` | ❌ |
| **E2E Tests (Multi-Agent)** | 3 | `node tests/test-*.js` | ❌ |
| **FILO/Context Tests** | 2 | `uv run python tests/test_filo_*.py` | ❌ |

**Total: 35 tests**

---

## 1. PRE-COMMIT TESTS (Automatic)

These run automatically on every commit to prevent regressions.

### 1.1 `test_done_message_clearing.py` 🔥
**Purpose:** Prevents infinite loops by validating #done command behavior

**What it tests:**
- `#done` command pauses agent for 60 seconds
- Accumulated messages during pause are cleared on resume
- Message store cleanup works correctly

**Why critical:** Prevents agents from reprocessing old messages after #done

**Files monitored:**
- `src/ax_agent_studio/message_store.py`
- `src/ax_agent_studio/queue_manager.py`
- `configs/prompts/_base.yaml`

**Run manually:**
```bash
uv run python tests/test_done_message_clearing.py
```

---

### 1.2 `test_queue_manager_smoke.py` 🔥
**Purpose:** Catches runtime errors in QueueManager (prevents UnboundLocalError)

**What it tests:**
- QueueManager initializes without errors
- `is_done_command` variable properly initialized
- Basic queue operations work

**Why critical:** Smoke test prevents runtime crashes in production

**Files monitored:**
- `src/ax_agent_studio/queue_manager.py`

**Run manually:**
```bash
uv run python tests/test_queue_manager_smoke.py
```

---

### 1.3 `e2e/pre_commit_wrapper.py` 🔥
**Purpose:** Quick E2E validation of Echo deployment (skips if dashboard not running)

**What it tests:**
- Dashboard API is accessible
- Echo monitor can be deployed
- Basic monitor lifecycle works

**Why critical:** Catches breaking changes in dashboard/monitor integration

**Files monitored:**
- `src/ax_agent_studio/dashboard/backend/*.py`
- `tests/e2e/helpers/*.py`

**Run manually:**
```bash
uv run python tests/e2e/pre_commit_wrapper.py
```

---

## 2. UNIT TESTS (Core Functionality)

Test individual components in isolation.

### 2.1 `test_message_store.py`
**Tests:** MessageStore operations (create, read, update, delete, FILO ordering)

**Run:**
```bash
uv run python tests/test_message_store.py
```

---

### 2.2 `test_message_parsing.py`
**Tests:** Message content parsing (@mentions, #commands)

**Run:**
```bash
uv run python tests/test_message_parsing.py
```

---

### 2.3 `test_agent_handler.py`
**Tests:** Agent handler base functionality

**Run:**
```bash
uv run python tests/test_agent_handler.py
```

---

### 2.4 `test_duplicate_agent_prevention.py`
**Tests:** Prevents duplicate agent deployment

**Run:**
```bash
uv run python tests/test_duplicate_agent_prevention.py
```

---

### 2.5 `test_no_emojis.py`
**Tests:** Validates emoji-free responses in production mode

**Run:**
```bash
uv run python tests/test_no_emojis.py
```

---

### 2.6 `test_utf8_log_handling.py`
**Tests:** UTF-8 encoding in log files

**Run:**
```bash
uv run python tests/test_utf8_log_handling.py
```

---

### 2.7 `test_ollama_models.py`
**Tests:** Ollama model detection and availability

**Run:**
```bash
uv run python tests/test_ollama_models.py
```

---

## 3. INTEGRATION TESTS (Component Interaction)

Test how multiple components work together.

### 3.1 `test_dashboard_api_e2e.py`
**Tests:** Dashboard backend API endpoints

**What it tests:**
- Health check
- Providers list
- Model lists (Anthropic, Gemini, Ollama)
- Environment endpoints
- Kill switch

**Run:**
```bash
# Dashboard must be running
uv run dashboard &
uv run python tests/test_dashboard_api_e2e.py
```

---

### 3.2 `test_dashboard_ui_e2e.py`
**Tests:** Dashboard UI with Playwright

**What it tests:**
- Echo agent UI (no provider/model)
- Ollama agent UI (model dropdown only)
- Claude SDK agent UI (Claude models only, Sonnet 4.5 default)
- LangGraph agent UI (provider + model dropdowns)

**Run:**
```bash
uv run dashboard &
uv run python tests/test_dashboard_ui_e2e.py
```

---

### 3.3 `test_all_monitors_e2e.py`
**Tests:** All monitor types deployment lifecycle

**What it tests:**
- Echo monitor
- Ollama monitor
- Claude Agent SDK monitor
- LangGraph monitor

**Run:**
```bash
uv run dashboard &
uv run python tests/test_all_monitors_e2e.py
```

---

### 3.4 `test_providers_e2e.py`
**Tests:** Provider configuration and detection

**Run:**
```bash
uv run python tests/test_providers_e2e.py
```

---

### 3.5 `test_all_frameworks_e2e.py`
**Tests:** All 5 agent frameworks

**Run:**
```bash
uv run dashboard &
uv run python tests/test_all_frameworks_e2e.py
```

---

### 3.6 `test_claude_agent_sdk_monitor.py`
**Tests:** Claude Agent SDK monitor specifically

**Run:**
```bash
uv run python tests/test_claude_agent_sdk_monitor.py
```

---

### 3.7 `test_gemini_monitor_e2e.py`
**Tests:** Gemini/LangGraph monitor

**Run:**
```bash
uv run python tests/test_gemini_monitor_e2e.py
```

---

### 3.8 `test_openai_agents_monitor_e2e.py`
**Tests:** OpenAI Agents SDK monitor

**Run:**
```bash
uv run python tests/test_openai_agents_monitor_e2e.py
```

---

## 4. E2E TESTS - DASHBOARD (Full System)

Test complete user workflows through the dashboard.

### 4.1 `e2e/test_01_agent_connectivity.py`
**Tests:** Basic agent MCP connectivity

**Run:**
```bash
uv run python tests/e2e/test_01_agent_connectivity.py
```

---

### 4.2 `e2e/test_02_echo_all_agents.py`
**Tests:** Echo monitor on all available agents

**Run:**
```bash
uv run dashboard &
uv run python tests/e2e/test_02_echo_all_agents.py
```

---

### 4.3 `e2e/test_02_monitor_validation.py`
**Tests:** Monitor validation with @mention responses

**What it tests:**
- Deploy monitor on target agent
- Send @mention from sender agent
- Use `wait=true, wait_mode='mentions'` to get response
- Verify response received

**Run:**
```bash
uv run dashboard &
# All monitors
uv run python tests/e2e/test_02_monitor_validation.py

# Specific monitor type
uv run python tests/e2e/test_02_monitor_validation.py Echo
uv run python tests/e2e/test_02_monitor_validation.py Ollama
```

---

### 4.4 `e2e/test_03_ollama.py`
**Tests:** Ollama monitor deployment and responses

**Run:**
```bash
uv run dashboard &
uv run python tests/e2e/test_03_ollama.py
```

---

### 4.5 `e2e/test_04_ollama_crisscross.py`
**Tests:** Two Ollama agents messaging each other

**Run:**
```bash
uv run dashboard &
uv run python tests/e2e/test_04_ollama_crisscross.py
```

---

### 4.6 `e2e/test_05_four_way_conversation.py`
**Tests:** 4 agents in conversation

**Run:**
```bash
uv run dashboard &
uv run python tests/e2e/test_05_four_way_conversation.py
```

---

### 4.7 `e2e/test_06_ollama_smoke.py`
**Tests:** Quick Ollama smoke test

**Run:**
```bash
uv run dashboard &
uv run python tests/e2e/test_06_ollama_smoke.py
```

---

### 4.8 `e2e/test_07_claude_sdk.py`
**Tests:** Claude Agent SDK deployment

**Run:**
```bash
uv run dashboard &
uv run python tests/e2e/test_07_claude_sdk.py
```

---

### 4.9 `e2e/test_08_openai_sdk.py`
**Tests:** OpenAI Agents SDK deployment

**Run:**
```bash
uv run dashboard &
uv run python tests/e2e/test_08_openai_sdk.py
```

---

### 4.10 `e2e/test_09_langgraph.py`
**Tests:** LangGraph deployment

**Run:**
```bash
uv run dashboard &
uv run python tests/e2e/test_09_langgraph.py
```

---

### 4.11 `e2e/test_all_agent_types.py` ⭐
**Tests:** All 5 monitor types with validation

**What it tests:**
- Echo, Ollama, Claude SDK, OpenAI SDK, LangGraph
- Full deployment lifecycle
- Message validation using MCP JAM SDK
- Agent response verification

**Run:**
```bash
uv run dashboard &
uv run python tests/e2e/test_all_agent_types.py
```

---

### 4.12 `e2e/test_ui_api_wiring.py`
**Tests:** UI and API integration

**Run:**
```bash
uv run dashboard &
uv run python tests/e2e/test_ui_api_wiring.py
```

---

## 5. E2E TESTS - MULTI-AGENT (JavaScript)

Test multi-agent coordination using MCP JAM SDK.

### 5.1 `test-basic-message-exchange.js` ✅
**Status:** PASSING

**Tests:** Basic 2-agent message exchange

**What it tests:**
- Agent A sends to Agent B
- Agent B receives message
- Agent B replies to Agent A
- Agent A receives reply

**Run:**
```bash
node tests/test-basic-message-exchange.js
```

---

### 5.2 `test-message-flow-validation.js`
**Tests:** Message flow patterns

**Run:**
```bash
node tests/test-message-flow-validation.js
```

---

### 5.3 `test-message-storm-coordination.js`
**Tests:** Message storm handling (10+ concurrent messages)

**What it tests:**
- 3 agents: coordinator + 2 workers
- Coordinator sends message to both
- Workers respond concurrently
- 5 rapid messages from each worker (10 total)
- Coordinator batch processes all 10

**Run:**
```bash
node tests/test-message-storm-coordination.js
```

---

## 6. FILO & CONTEXT AWARENESS TESTS ⭐

Validate FILO queue processing and multi-agent context awareness.

### 6.1 `test_filo_batching.py` ✅ NEW
**Tests:** FILO queue batching with 5-message burst

**What it tests:**
- Agent receives 5 rapid messages
- All 5 messages batched together
- FILO processing: newest message first (Message 5)
- Full context provided: all previous messages (1-4)
- Agent can respond with full conversation understanding

**Test scenario:**
```
lunar_ray_510 → ghost_ray_363 (5 messages):
  1. "What is the weather?"
  2. "Never mind the weather, what about sports?"
  3. "Actually, I want to talk about food."
  4. "On second thought, let's discuss technology."
  5. "Final question - can you summarize our conversation?"

Expected: ghost_ray_363 processes Message 5 with context of 1-4
```

**Run:**
```bash
uv run dashboard &
uv run python tests/test_filo_batching.py
```

---

### 6.2 `test_multi_agent_context.py` ✅ NEW
**Tests:** Multi-agent context awareness (4-agent collaboration)

**What it tests:**
- 4 agents in shared conversation space
- Agent A reports issues (2 messages)
- Agent B reports related issues (2 messages)
- Coordinator asks Observer to diagnose (1 message)
- Observer receives ALL 5 messages with full context
- Observer sees messages from agents they weren't directly conversing with

**Test scenario:**
```
Multi-agent conversation:
  lunar_ray_510:     "Message 1: Performance issues"
  lunar_ray_510:     "Message 2: CPU at 90%"
  lunar_craft_128:   "Message 3: Timeout errors"
  lunar_craft_128:   "Message 4: Slow database"
  orion_344:         "@ghost_ray_363 Can you diagnose?"

Expected: ghost_ray_363 sees all 5 messages, even though only mentioned once
```

**Demonstrates:**
- ✅ Message board awareness (see all messages, not just @mentions)
- ✅ FILO processing (newest first: Message 5)
- ✅ Full context (Messages 1-4 provide background)
- ✅ Multi-agent coordination (4 agents collaborating)

**Run:**
```bash
uv run dashboard &
uv run python tests/test_multi_agent_context.py
```

---

## 7. HELPER SCRIPTS

Reusable test utilities.

### 7.1 `e2e/helpers/dashboard_api.py`
**Purpose:** Dashboard API wrapper for E2E tests

**Features:**
- Start/stop monitors
- Wait for monitor ready state
- Cleanup all monitors
- Kill switch management

**Usage:**
```python
from tests.e2e.helpers.dashboard_api import DashboardAPI

with DashboardAPI() as api:
    api.start_monitor("ghost_ray_363", "echo")
    api.wait_for_monitor_ready("ghost_ray_363")
    # ... test code ...
    api.cleanup_all()
```

---

### 7.2 `e2e/validate-agent-response.js`
**Purpose:** Validate agent responses using MCP JAM SDK

**Usage:**
```bash
node tests/e2e/validate-agent-response.js <target_agent> <sender_agent> [message] [timeout]
```

**Example:**
```bash
node tests/e2e/validate-agent-response.js ghost_ray_363 lunar_ray_510 "Hello!" 30
```

---

### 7.3 `e2e/send_burst_messages.js`
**Purpose:** Send burst of messages for FILO testing

**Usage:**
```bash
node tests/e2e/send_burst_messages.js <target_agent> <sender_agent>
```

---

## 8. ARCHIVED TESTS

Tests archived due to infinite loop issues with echo monitors.

### 8.1 `archived/test-simple-echo.js` ❌
**Issue:** Echo processed own responses, creating infinite loops

---

### 8.2 `archived/test-batch-processing.js` ❌
**Issue:** Echo created message storms

---

### 8.3 `archived/test-hybrid-message-board.js` ❌
**Issue:** Too complex, chaotic output

**Note:** Use real agents with proper self-message filtering instead of echo monitors.

---

## 9. TEST PLANS & DOCUMENTATION

Reference documents for test strategy and planning.

### 9.1 `tests/E2E_TEST_PLAN.md`
**Content:** Comprehensive E2E test plan (~40 tests)
- Component tests (UI elements)
- Deployment tests (all 5 monitor types)
- Message validation tests
- Error handling tests
- Integration scenarios

---

### 9.2 `tests/TEST_PLAN.md`
**Content:** Multi-agent message system test plan
- "Crawl → Walk → Run" testing philosophy
- Message threading tests
- Queue awareness tests
- Batch context tests
- Multi-agent coordination tests

---

### 9.3 `docs/TESTING.md`
**Content:** Testing infrastructure overview
- Current test coverage
- Tools used (Playwright, pytest, httpx)
- Success metrics
- CI/CD integration

---

## 10. RUNNING TEST SUITES

### Run All Pre-Commit Tests
```bash
pre-commit run --all-files
```

---

### Run All Unit Tests
```bash
uv run python -m pytest tests/test_*.py -v
```

---

### Run All E2E Tests (Dashboard Required)
```bash
# Start dashboard first
uv run dashboard &

# Run all E2E tests
uv run python tests/e2e/test_*.py
```

---

### Run FILO & Context Tests
```bash
uv run dashboard &
uv run python tests/test_filo_batching.py
uv run python tests/test_multi_agent_context.py
```

---

### Run Multi-Agent JavaScript Tests
```bash
node tests/test-basic-message-exchange.js
node tests/test-message-storm-coordination.js
```

---

## 11. TEST DEVELOPMENT GUIDELINES

### When to Add Tests

**Add to pre-commit when:**
- Test prevents critical bugs (infinite loops, runtime crashes)
- Test runs fast (<5 seconds)
- Test validates core functionality that must never break

**Keep as manual tests when:**
- Test requires dashboard to be running
- Test takes >10 seconds
- Test is for occasional validation (not every commit)

---

### Test Organization

```
tests/
├── test_*.py              # Unit tests (fast, isolated)
├── test_*_e2e.py         # Integration tests (require services)
├── e2e/
│   ├── test_*.py         # Dashboard E2E tests
│   ├── helpers/          # Reusable test utilities
│   └── *.js              # Multi-agent coordination tests
└── archived/             # Deprecated tests (for reference)
```

---

### Test Naming Convention

- `test_<component>.py` - Unit test
- `test_<feature>_e2e.py` - Integration/E2E test
- `test-<scenario>.js` - Multi-agent coordination test

---

## 12. CI/CD INTEGRATION

### GitHub Actions (Future)

```yaml
name: Tests

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run unit tests
        run: uv run python -m pytest tests/test_*.py

  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Start dashboard
        run: uv run dashboard &
      - name: Run E2E tests
        run: uv run python tests/e2e/test_all_agent_types.py
```

---

## 13. QUICK START CHECKLIST

### For New Contributors

1. ✅ Run pre-commit tests: `pre-commit run --all-files`
2. ✅ Run unit tests: `uv run python -m pytest tests/test_*.py`
3. ✅ Start dashboard: `uv run dashboard`
4. ✅ Run FILO tests: `uv run python tests/test_filo_batching.py`
5. ✅ Run multi-agent test: `uv run python tests/test_multi_agent_context.py`

---

## 14. SUCCESS METRICS

- **Pre-commit tests:** Must pass on every commit
- **Unit tests:** Should pass 100% before PR
- **E2E tests:** Run before major releases
- **FILO/Context tests:** Validate new queue behavior

---

## 15. SUPPORT

Questions about tests? See:
- `tests/E2E_TEST_PLAN.md` - Comprehensive test plan
- `tests/TEST_PLAN.md` - Testing philosophy
- `docs/TESTING.md` - Infrastructure overview

---

**Last Updated:** 2025-11-10
**Test Count:** 35 tests (3 in pre-commit, 32 manual)
**Coverage:** Unit, Integration, E2E, Multi-Agent, FILO/Context
