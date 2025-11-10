# Agent Factory E2E Test Plan

## Overview
Comprehensive end-to-end testing plan for Agent Factory dashboard at http://127.0.0.1:8000

## Test Strategy
- **Environment**: Local testing only (acknowledge that Production exists but don't test it)
- **Models**: Default models only (no need to test every model variant)
- **Test Approach**:
  1. **E2E (Chrome DevTools MCP)**: Deploy agent via dashboard UI
  2. **MCP JAM SDK**: Send messages and validate agent responses
- **Tools**:
  - Chrome DevTools MCP: UI automation (click buttons, select options, deploy agents)
  - MCP JAM SDK (@mcpjam/sdk): Backend testing (send/read messages, verify functionality)

---

## 1. COMPONENT TESTS

### 1.1 Environment Selector
- [ ] **Test 1.1.1**: Verify Local environment is selected
  - Verify dropdown shows "Local"
  - Verify "Production" option exists in dropdown
  - All tests will use Local environment only

### 1.2 Agent Selector
Test each agent in Local environment:

- [ ] **Test 1.2.1**: Select Ghost Ray 363
  - Verify agent appears in dropdown
  - Verify config loads correctly

- [ ] **Test 1.2.2**: Select Lunar Craft 128
  - Verify agent appears in dropdown
  - Verify config loads correctly

- [ ] **Test 1.2.3**: Select Orion 344
  - Verify agent appears in dropdown
  - Verify config loads correctly

- [ ] **Test 1.2.4**: Select Rigelz 334
  - Verify agent appears in dropdown
  - Verify config loads correctly

### 1.3 Agent Type Selector
Test all available agent types:

- [ ] **Test 1.3.1**: Echo (Simple)
  - Verify Echo option selects
  - Verify no model dropdown appears (Echo doesn't need model)

- [ ] **Test 1.3.2**: Ollama (AI)
  - Verify Ollama option selects
  - Verify model dropdown appears with Ollama models

- [ ] **Test 1.3.3**: Claude Agent SDK (Secure)
  - Verify Claude SDK option selects
  - Verify model dropdown shows Claude models

- [ ] **Test 1.3.4**: OpenAI Agents SDK
  - Verify OpenAI option selects
  - Verify model dropdown shows OpenAI models

- [ ] **Test 1.3.5**: LangGraph (Tools)
  - Verify LangGraph option selects
  - Verify appropriate configuration options appear

### 1.4 Model Selector
Test that model selector appears and default model works:

- [ ] **Test 1.4.1**: Verify Ollama shows model dropdown with default selected
- [ ] **Test 1.4.2**: Verify Claude SDK shows model dropdown with default selected
- [ ] **Test 1.4.3**: Verify OpenAI shows model dropdown with default selected

**Note**: We test with default models only - no need to test every model variant

### 1.5 System Prompt Selector
- [ ] **Test 1.5.1**: None (use model defaults)
  - Verify agent deploys with default behavior

- [ ] **Test 1.5.2**: Code Reviewer prompt
  - Verify agent adopts code review personality

- [ ] **Test 1.5.3**: Collaborative Agent prompt
  - Verify agent adopts collaborative personality

- [ ] **Test 1.5.4**: Other available prompts
  - Test each system prompt template

### 1.6 Test Sender Agent
- [ ] **Test 1.6.1**: Auto (first available)
  - Verify auto-selection works
  - Verify test messages send from correct agent

- [ ] **Test 1.6.2**: Specific agent selection
  - Select different test sender agents
  - Verify messages come from selected agent

---

## 2. DEPLOYMENT TESTS

### 2.1 Basic Deployments (Local Environment)

**Echo Monitor Tests:**
- [ ] **Test 2.1.1**: Deploy Ghost Ray 363 + Echo
  - Click Deploy Agent
  - Verify agent appears in Running Agents section
  - Click test button (✏️)
  - Verify echo response received using MCP JAM SDK

- [ ] **Test 2.1.2**: Deploy Lunar Craft 128 + Echo
  - Same validation as 2.1.1

- [ ] **Test 2.1.3**: Deploy Orion 344 + Echo
  - Same validation as 2.1.1

- [ ] **Test 2.1.4**: Deploy Rigelz 334 + Echo
  - Same validation as 2.1.1

**Ollama Monitor Tests:**
- [ ] **Test 2.1.5**: Deploy Ghost Ray 363 + Ollama (default model)
  - Deploy agent
  - Click test button
  - Send: "Write a hello world function in Python"
  - Validate response using MCP JAM SDK
  - Verify response contains code

- [ ] **Test 2.1.6**: Deploy Lunar Craft 128 + Ollama (default model)
  - Same validation pattern

**Claude Agent SDK Tests:**
- [ ] **Test 2.1.7**: Deploy Ghost Ray 363 + Claude SDK (default model)
  - Deploy agent
  - Click test button
  - Send: "Explain what you can do"
  - Validate response using MCP JAM SDK

- [ ] **Test 2.1.8**: Deploy Lunar Craft 128 + Claude SDK (default model)
  - Same validation

**OpenAI Agents SDK Tests:**
- [ ] **Test 2.1.9**: Deploy Ghost Ray 363 + OpenAI (default model)
  - Deploy agent
  - Click test button
  - Send: "What's your model?"
  - Validate response using MCP JAM SDK

- [ ] **Test 2.1.10**: Deploy Lunar Craft 128 + OpenAI (default model)
  - Same validation

**LangGraph Tests:**
- [ ] **Test 2.1.11**: Deploy Ghost Ray 363 + LangGraph
  - Deploy agent
  - Click test button
  - Send tool-use request
  - Validate tool execution

- [ ] **Test 2.1.12**: Deploy Lunar Craft 128 + LangGraph
  - Same validation

### 2.2 System Prompt Tests
Test that system prompts actually affect behavior (use default models):

- [ ] **Test 2.2.1**: Deploy Ollama (default) + Code Reviewer prompt
  - Send code snippet
  - Verify agent reviews code (not just echoes)

- [ ] **Test 2.2.2**: Deploy Claude SDK (default) + Collaborative Agent prompt
  - Send collaborative task
  - Verify agent asks clarifying questions

- [ ] **Test 2.2.3**: Deploy with "None" system prompt vs custom prompt
  - Compare behavior between default and custom prompt
  - Verify custom prompt changes behavior

### 2.3 Multi-Agent Tests
- [ ] **Test 2.3.1**: Deploy 2 different agents simultaneously
  - Deploy Ghost Ray 363 + Echo
  - Deploy Lunar Craft 128 + Ollama
  - Verify both appear in Running Agents
  - Test both agents respond independently

- [ ] **Test 2.3.2**: Deploy 3+ agents
  - Verify all agents run without conflicts
  - Test message routing to correct agents

---

## 3. MESSAGE VALIDATION TESTS

### 3.1 Basic Message Flow
Using MCP JAM SDK (`@mcpjam/sdk`):

- [ ] **Test 3.1.1**: Send message to agent
  ```javascript
  // Pseudo-code
  await messages.send({
    content: "Test message",
    reply_to: null
  });
  await messages.check({ wait: true, wait_mode: "mentions" });
  // Verify response received
  ```

- [ ] **Test 3.1.2**: Read agent response
  ```javascript
  const response = await messages.check({
    since: "1m",
    mark_read: false
  });
  // Verify response content
  ```

### 3.2 Agent Response Tests
For each agent type, verify:

- [ ] **Test 3.2.1**: Echo responds with exact echo
- [ ] **Test 3.2.2**: Ollama generates valid AI response
- [ ] **Test 3.2.3**: Claude SDK generates valid response
- [ ] **Test 3.2.4**: OpenAI generates valid response
- [ ] **Test 3.2.5**: LangGraph executes tools correctly

### 3.3 Special Command Tests
Test pause commands AND @mention behavior (critical regression prevention):

- [ ] **Test 3.3.1**: Send #pause command with @mention
  - Send: "@ghost_ray_363 #pause Need to review logs"
  - Verify agent pauses
  - Verify status shows "paused"
  - **CRITICAL**: Verify @mention is NOT stripped (queue_manager.py:454 - only #done strips mentions)
  - Verify other agents receive the mention notification

- [ ] **Test 3.3.2**: Send #stop command with @mention
  - Send: "@ghost_ray_363 #stop Stopping for maintenance"
  - Verify agent stops
  - **CRITICAL**: Verify @mention is NOT stripped
  - Verify other agents receive the mention notification

- [ ] **Test 3.3.3**: Send #done command with @mention
  - Send: "@ghost_ray_363 #done Task complete, check results @lunar_craft_128"
  - Verify agent pauses for 60 seconds
  - **CRITICAL**: Verify @mentions ARE stripped (queue_manager.py:454-457)
  - Verify response contains "check results lunar_craft_128" (no @ symbol)
  - Accumulate test messages during pause period
  - **Wait for auto-resume** (resume_at = time.time() + 60)
  - Force resume check or wait 60 seconds
  - Verify agent returns to RUNNING status
  - Verify accumulated messages were cleared (message_store.py:400-430)
  - Verify agent processes new messages normally after resume

---

## 4. ERROR HANDLING TESTS

### 4.1 Invalid Configurations
- [ ] **Test 4.1.1**: Deploy without selecting agent
  - Verify error message

- [ ] **Test 4.1.2**: Deploy without selecting agent type
  - Verify error message

- [ ] **Test 4.1.3**: Deploy Ollama without model
  - Verify error message

### 4.2 Runtime Errors
- [ ] **Test 4.2.1**: Deploy with non-existent model
  - Verify graceful error handling

- [ ] **Test 4.2.2**: Send malformed message
  - Verify agent doesn't crash

- [ ] **Test 4.2.3**: Network interruption during deployment
  - Verify recovery or clear error

### 4.3 Resource Limits
- [ ] **Test 4.3.1**: Deploy maximum number of agents
  - Verify limit enforcement or warning

- [ ] **Test 4.3.2**: Send very long message
  - Verify truncation or rejection

---

## 5. UI STATE TESTS

### 5.1 Visual Feedback
- [ ] **Test 5.1.1**: Verify loading states during deployment
- [ ] **Test 5.1.2**: Verify success notification after deployment
- [ ] **Test 5.1.3**: Verify error notifications
- [ ] **Test 5.1.4**: Verify Running Agents section updates

### 5.2 Agent Management UI
- [ ] **Test 5.2.1**: Verify Stop button appears for running agents
- [ ] **Test 5.2.2**: Click Stop button, verify agent stops
- [ ] **Test 5.2.3**: Verify agent status indicators (running/paused/stopped)
- [ ] **Test 5.2.4**: Verify test button (✏️) appears and works

---

## 6. INTEGRATION TEST SCENARIOS

### 6.1 Realistic Workflows
- [ ] **Test 6.1.1**: Full Developer Workflow
  1. Deploy Lunar Craft 128 + Claude SDK + Code Reviewer prompt
  2. Send code for review
  3. Receive review feedback
  4. Send updated code
  5. Verify iterative conversation works

- [ ] **Test 6.1.2**: Multi-Agent Collaboration
  1. Deploy Ghost Ray 363 + Ollama (Code Generator)
  2. Deploy Lunar Craft 128 + Claude SDK (Code Reviewer)
  3. Send task to code generator
  4. Generator mentions reviewer for review
  5. Reviewer provides feedback
  6. Verify collaboration flow

### 6.2 Stress Tests
- [ ] **Test 6.2.1**: Rapid deployments
  - Deploy 5 agents in quick succession
  - Verify all deploy successfully

- [ ] **Test 6.2.2**: Message storm
  - Send 20 messages to agent
  - Verify all processed correctly

- [ ] **Test 6.2.3**: Long-running agent
  - Deploy agent
  - Send messages over 10+ minutes
  - Verify consistent behavior

---

## 7. TEST IMPLEMENTATION PRIORITY

### Phase 1: Core Functionality (MUST HAVE)
1. Basic deployment for each agent type (Tests 2.1.1-2.1.12) - using default models
2. Message validation (Tests 3.1.1-3.1.2)
3. Agent response validation (Tests 3.2.1-3.2.5)

### Phase 2: Configuration Options (SHOULD HAVE)
1. Model dropdown verification (Tests 1.4.1-1.4.3) - just verify dropdowns work
2. System prompt tests (Tests 2.2.1-2.2.3)
3. Environment dropdown exists (Test 1.1.1) - verify UI component only

### Phase 3: Edge Cases (NICE TO HAVE)
1. Error handling (Section 4)
2. Multi-agent tests (Section 2.3)
3. Stress tests (Section 6.2)

---

## 8. TEST AUTOMATION STRUCTURE

### Proposed File Structure:
```
tests/
├── e2e/
│   ├── test-01-component-ui.py          # UI component tests (Section 1)
│   ├── test-02-basic-deployments.py     # Basic deployment tests (Section 2.1)
│   ├── test-03-system-prompts.py        # System prompt tests (Section 2.2)
│   ├── test-04-message-validation.py    # Message flow tests (Section 3)
│   ├── test-05-error-handling.py        # Error tests (Section 4)
│   ├── test-06-integration.py           # Integration scenarios (Section 6)
│   └── helpers/
│       ├── dashboard_helper.py          # Chrome DevTools UI helpers
│       ├── mcpjam_helper.py            # MCP JAM SDK message helpers
│       └── validation_helper.py         # Response validation helpers
```

### Reusable Test Helpers:

**dashboard_helper.py**:
```python
async def deploy_agent(session, agent_name, agent_type, model=None, system_prompt=None):
    """Deploy an agent via dashboard UI"""

async def click_test_button(session, agent_name):
    """Click test button for specific agent"""

async def verify_agent_running(session, agent_name):
    """Verify agent appears in Running Agents section"""

async def stop_agent(session, agent_name):
    """Stop a running agent"""
```

**mcpjam_helper.py**:
```javascript
async function sendTestMessage(agentName, content) {
    // Send message using MCP JAM SDK
}

async function waitForResponse(agentName, timeout = 30000) {
    // Wait for and return agent response
}

async function validateResponse(response, expectedPattern) {
    // Validate response matches expected pattern
}
```

---

## 9. SUCCESS CRITERIA

Each test passes when:
1. ✅ Agent deploys without errors
2. ✅ Agent appears in Running Agents section
3. ✅ Test button sends message successfully
4. ✅ Agent responds within timeout (30s default)
5. ✅ Response validated via MCP JAM SDK
6. ✅ Response content matches expected behavior
7. ✅ No errors in browser console
8. ✅ No errors in agent logs

---

## 10. TEST EXECUTION PLAN

### Manual Testing (Initial):
1. Go through each test in order
2. Check off completed tests
3. Document any failures
4. Take screenshots of failures

### Automated Testing (Goal):
1. Run dashboard E2E: `npm run test:e2e:dashboard`
2. Run validation test: `npm run test:e2e:echo`
3. (Future) Add more test scripts as we build them

---

## NOTES

- **Test Data**: Use consistent test messages across runs
- **Cleanup**: Stop all agents after each test to prevent interference
- **Timing**: Allow 2-3 seconds between UI interactions
- **Logging**: Save screenshots on failure for debugging
- **CI/CD**: Phase 1 tests should run in CI, others optional

---

## ESTIMATED EFFORT

- **Phase 1**: ~20 tests (core deployments + message validation), ~3-4 hours to implement
- **Phase 2**: ~8 tests (UI components + system prompts), ~1-2 hours to implement
- **Phase 3**: ~12 tests (error handling + edge cases), ~2-3 hours to implement
- **Total**: ~40 tests, ~6-9 hours for full automation

**Simplifications applied**:
- Default models only (no testing all model variants)
- Local environment only (acknowledge Production exists but don't test it)
- Reduces test count from original ~75 to ~40 tests

---

**Status**: 📝 Test plan created, ready for review and implementation
