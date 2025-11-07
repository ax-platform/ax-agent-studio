# Test Plan: Multi-Agent Message System

## Testing Philosophy: Crawl → Walk → Run

Start simple, validate each layer, then build complexity.

---

## CRAWL PHASE: Basic Infrastructure

### ✅ Test 1: Basic Message Exchange
**File:** `test-basic-message-exchange.js`
**Status:** ✅ PASSING

**What it tests:**
- Agent A can send message to Agent B
- Agent B receives the message
- Agent B can send message back to Agent A
- Agent A receives the reply

**Expected results:**
```
✓ TEST 1: orion_344 → rigelz_334 (message delivered)
  - Message ID exists
  - Sender is orion_344
  - Content matches sent message

✓ TEST 2: rigelz_334 → orion_344 (reply delivered)
  - Message ID exists
  - Sender is rigelz_334
  - Content matches reply message
```

**Why important:** Validates the core messaging infrastructure works before adding any complexity.

---

### 🔨 Test 2: Message Threading
**File:** `test-message-threading.js` (TO BUILD)
**Status:** ⏳ NOT YET IMPLEMENTED

**What it tests:**
- Agent A sends message to Agent B
- Agent B replies using `reply_to` field
- System correctly threads the conversation
- Both agents can see the thread relationship

**Expected results:**
```
✓ Original message sent with no reply_to
✓ Reply message sent with reply_to = original_message_id
✓ Backend correctly links reply to original
✓ Thread relationship visible when checking messages
```

**Validation criteria:**
- `reply.parent_message_id === original.id`
- Thread metadata shows correct parent-child relationship
- Conversation context includes thread history

**Why important:** Threading is critical for agents to understand conversation flow and maintain context.

---

### 🔨 Test 3: Multiple Recipients
**File:** `test-multiple-recipients.js` (TO BUILD)
**Status:** ⏳ NOT YET IMPLEMENTED

**What it tests:**
- Agent A sends message mentioning multiple agents (@B @C)
- All mentioned agents receive the message
- Reply-all functionality works correctly

**Expected results:**
```
✓ Message sent with content: "@agent_b @agent_c Hello everyone"
✓ agent_b receives message with sender = agent_a
✓ agent_c receives message with sender = agent_a
✓ Both agents see same message ID
```

**Validation criteria:**
- All mentioned agents receive identical message
- Message ID is consistent across all recipients
- Sender correctly identified for all

**Why important:** Multi-agent coordination requires broadcasting to multiple recipients.

---

## WALK PHASE: Queue & Context Management

### 🔨 Test 4: Queue Awareness
**File:** `test-queue-awareness.js` (TO BUILD)
**Status:** ⏳ NOT YET IMPLEMENTED

**What it tests:**
- Send 3 rapid messages to an agent
- Agent checks messages and sees all 3
- Messages are in correct chronological order
- Queue depth is accurately reported

**Expected results:**
```
✓ Send 3 messages rapidly (200ms apart)
✓ Agent receives all 3 messages (no loss)
✓ Messages ordered: message1, message2, message3
✓ Queue depth reported as 3
```

**Validation criteria:**
- `messages.length === 3`
- Messages sorted by timestamp (oldest to newest)
- No duplicate messages
- No missing messages

**Why important:** Agents need to see all pending messages to understand full context.

---

### 🔨 Test 5: Batch Context (wait=true + context_limit)
**File:** `test-batch-context.js` (TO BUILD)
**Status:** ⏳ NOT YET IMPLEMENTED

**What it tests:**
- Send 5 messages to message board
- Use `wait=true` with `context_limit=5`
- Verify API returns context array with trigger + history
- Validate context ordering

**Expected results:**
```
✓ Send 5 messages to space
✓ Call messages API with wait=true, context_limit=5
✓ Response includes context array with 5 messages
✓ context[-1] = newest/trigger message
✓ context[0:-1] = history (oldest to newer)
✓ context_metadata.includes_trigger = true
```

**Validation criteria:**
- `response.context.length === 5`
- `response.context[4].id === trigger_message.id` (newest)
- Messages in chronological order in context array
- All 5 messages present, no duplicates

**Why important:** This tests the API feature we're using for batch processing.

---

### 🔨 Test 6: Message Board View
**File:** `test-message-board-view.js` (TO BUILD)
**Status:** ⏳ NOT YET IMPLEMENTED

**What it tests:**
- Multiple agents send messages to a shared space
- Each agent sees full message board (inbox view)
- Messages from different senders are distinguished
- Unread/read status is tracked correctly

**Expected results:**
```
✓ Agent A, B, C each send 2 messages to shared space
✓ Total 6 messages in space
✓ Agent D joins and checks messages
✓ Agent D sees all 6 messages
✓ Messages show correct senders (A, B, C)
✓ All messages marked as unread for Agent D
```

**Validation criteria:**
- Message board shows messages from multiple senders
- Sender identification is accurate
- Timestamps are correct
- Unread count matches expected

**Why important:** Message board awareness is the foundation of multi-agent coordination.

---

## RUN PHASE: Real Monitors & Batch Processing

### 🔨 Test 7: Single Monitor with Batch Processing
**File:** `test-monitor-batch-processing.js` (TO BUILD)
**Status:** ⏳ NOT YET IMPLEMENTED

**What it tests:**
- Start ONE agent monitor (NOT echo - use Claude SDK)
- Send 4 rapid messages
- Monitor processes them as a batch
- Single response addresses all messages

**Expected results:**
```
✓ Start claude_agent_sdk_monitor for agent_a
✓ Send 4 messages rapidly from agent_b
✓ Monitor detects batch mode (batch_size=4)
✓ Handler receives current_message + history (3 messages)
✓ Monitor sends ONE comprehensive response
✓ Response addresses all 4 messages
```

**Validation criteria:**
- Monitor log shows "BATCH MODE: Processing 4 messages together"
- Handler receives `batch_mode=true` flag
- Handler receives `history_messages` array with 3 items
- Only ONE response message sent
- Response content references multiple messages

**Why important:** Validates the new batch processing architecture works with real monitors.

---

### 🔨 Test 8: Multi-Agent Coordination
**File:** `test-multi-agent-coordination.js` (TO BUILD)
**Status:** ⏳ NOT YET IMPLEMENTED

**What it tests:**
- 3 agents with monitors running
- Agent A sends message to Agent B and C
- Both B and C respond
- Agents see each other's responses (message board awareness)
- No infinite loops or message storms

**Expected results:**
```
✓ Start monitors for agent_a, agent_b, agent_c
✓ Agent A: "@agent_b @agent_c Let's coordinate on this task"
✓ Agent B receives and responds
✓ Agent C receives and responds
✓ All agents see full message board (A's message + B's reply + C's reply)
✓ No duplicate processing
✓ No infinite loops
✓ Total messages = 3 (original + 2 replies)
```

**Validation criteria:**
- Each monitor processes exactly the messages meant for them
- No self-message processing (no infinite loops)
- All agents see full conversation context
- Responses are coherent and reference the conversation
- Clean termination (no runaway processes)

**Why important:** This is the ultimate goal - multiple agents coordinating through shared message board.

---

### 🔨 Test 9: Task Delegation Pattern
**File:** `test-task-delegation.js` (TO BUILD)
**Status:** ⏳ NOT YET IMPLEMENTED

**What it tests:**
- Agent A (coordinator) assigns tasks to B and C
- B and C work on their tasks
- B and C report back to A
- A sees all responses and synthesizes result

**Expected results:**
```
✓ Agent A: "@agent_b Please analyze the data"
✓ Agent A: "@agent_c Please write the summary"
✓ Agent B processes request and responds with analysis
✓ Agent C processes request and responds with summary
✓ Agent A sees both responses in message board
✓ Agent A synthesizes final result
✓ All communication threaded correctly
```

**Validation criteria:**
- Task messages correctly routed to assignees
- Assignees respond to correct thread
- Coordinator sees all responses
- Threading maintains conversation structure
- No cross-talk or confusion

**Why important:** Task delegation is a key multi-agent pattern we want to enable.

---

## PRIORITY: Message Storm Test (Jump to Real-World Scenario)

### 🔥 Test 10: Concurrent Message Storm Handling
**File:** `test-message-storm-coordination.js` (BUILDING NOW)
**Status:** 🔨 IN PROGRESS

**What it tests:**
- 3 agents: coordinator (agent_a), workers (agent_b, agent_c)
- Coordinator sends message to both workers
- Both workers respond simultaneously
- Then send 5 rapid messages from both workers
- Coordinator's monitor must batch process all messages
- No message loss, no infinite loops

**Expected results:**
```
✓ Coordinator sends: "@agent_b @agent_c Please analyze this task"
✓ Agent B responds within 1 second
✓ Agent C responds within 1 second
✓ Both responses arrive concurrently at coordinator
✓ Send 5 rapid messages from B (200ms apart)
✓ Send 5 rapid messages from C (200ms apart)
✓ Total 10 messages in coordinator's queue
✓ Coordinator monitor processes as batch (batch_size=10)
✓ Single comprehensive response addresses all 10 messages
✓ No message loss
✓ No infinite loops
✓ Clean termination
```

**Validation criteria:**
- Coordinator receives exactly 12 messages total (1 original + 2 first responses + 5 from B + 5 from C - 1 self = 12)
- Monitor log shows batch processing: "BATCH MODE: Processing 10+ messages"
- Handler receives batch_mode=true with full history
- Only ONE response sent by coordinator
- No runaway processes
- Test completes in <30 seconds

**Why priority:** This tests the REAL challenge - handling concurrent message storms from multiple agents, which is what we built the batch processing for.

---

## Test Execution Order

1. **Phase 1 (CRAWL):** Test 1 ✅
   - Basic messaging works
   - Build confidence in infrastructure

2. **Phase 2 (PRIORITY - JUMP AHEAD):** Test 10 🔥
   - **Real-world message storm scenario**
   - Tests batch processing under load
   - Multiple concurrent senders
   - This is what we ACTUALLY need to work

3. **Phase 3 (WALK):** Tests 4-6
   - Fill in queue and context testing
   - Once we know storms work, validate details

4. **Phase 4 (RUN):** Tests 7-9
   - Polish multi-agent patterns
   - Task delegation
   - Complex coordination

---

## Archived Tests (Message Storms)

These tests are archived due to infinite loop issues with echo monitors:

- ❌ `archived/test-simple-echo.js` - Echo processed own responses
- ❌ `archived/test-batch-processing.js` - Echo created message storms
- ❌ `archived/test-hybrid-message-board.js` - Too complex, chaotic output

**Why archived:** Echo monitors process their own responses, creating infinite loops. Real agents with proper self-message filtering work better.

---

## Test Development Guidelines

1. **One thing at a time** - Each test validates ONE specific behavior
2. **Clear expected results** - Define exact pass/fail criteria before writing test
3. **No echo monitors** - Use real agents or no monitors for cleaner tests
4. **Clean output** - Test output should be readable and show progress clearly
5. **Fast feedback** - Tests should complete in <30 seconds when possible
6. **No message storms** - If test creates runaway messages, stop and fix immediately

---

## Success Criteria

A test is considered successful when:
- ✓ All validation criteria pass
- ✓ Output clearly shows what happened
- ✓ No unintended side effects (message storms, infinite loops)
- ✓ Test completes in reasonable time
- ✓ Test is deterministic (same result every run)

---

## Next Actions

1. Build Test 2: Message Threading
2. Build Test 3: Multiple Recipients
3. Build Test 4: Queue Awareness
4. Once Tests 1-6 pass, tackle batch processing with real monitors
