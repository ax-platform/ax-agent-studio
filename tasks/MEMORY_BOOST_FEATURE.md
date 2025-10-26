# Task: Memory Boost Feature - Proper Implementation

## Status: DEFERRED - Needs Server-Side Support

## Problem

The current attempt to implement "Memory Boost" (configurable conversation history depth) doesn't work because:

1. **Current Architecture**: Monitors use `wait=true` which blocks until NEW messages arrive
2. **Missing Context**: `wait=true` only returns new mentions, not historical context
3. **Separate Fetch Required**: Agents must make a separate API call to fetch conversation history
4. **Timing Issue**: Can't guarantee the history fetch happens at the right time relative to new messages

## ⚠️ CRITICAL: Duplication Risk

**DANGER**: Improper implementation could cause exponential message duplication and massive cost overruns!

### The Problem

If agents fetch conversation history on EVERY message:
```
Message 1: Fetch 0 historical messages
Message 2: Fetch 1 historical message (message 1)
Message 3: Fetch 2 historical messages (1, 2)
Message 4: Fetch 3 historical messages (1, 2, 3)
...
Message 100: Fetch 99 historical messages
```

**Result**: O(n²) growth! 100 messages = 4,950 fetched messages = 50x cost!

### Safeguards Required

1. **Server-Side Deduplication**: Server must track what context was already sent
2. **Client-Side Intelligence**: Agent should only fetch context ONCE per conversation start
3. **Rate Limiting**: Limit context fetches to prevent abuse
4. **Caching**: Don't re-fetch messages already in agent's context window
5. **Monitoring**: Alert on unusual fetch patterns

### Current Mitigation

- Base prompt updated to instruct: "Only check messages ONCE per conversation"
- Agents taught to use memory tool for long-term storage
- Clear guidance: "be efficient - tools cost money"

## Current Workaround

- Ollama monitor manually calls `fetch_conversation_context(limit=25)` separately
- LangGraph monitor maintains in-memory conversation history with trimming
- Both are hardcoded to 25 messages (the attempted UI feature was hidden)

## Proposed Solution: Server-Side Enhancement

### Server-Side Changes (MCP Platform)

Add new parameter to `messages` tool with `wait=true`:

```python
messages(
    action="check",
    wait=true,
    include_context=true,        # NEW: Include historical messages
    context_limit=50,             # NEW: How many historical messages to include
    mark_read=true
)
```

**Response Format**:
```json
{
  "new_mentions": [
    {"id": "abc123", "sender": "alice", "content": "@bob Hello!"}
  ],
  "context": [
    {"id": "xyz789", "sender": "bob", "content": "Hi @alice"},
    {"id": "def456", "sender": "alice", "content": "@bob How are you?"},
    // ... up to context_limit messages
  ],
  "context_metadata": {
    "total_messages": 3,
    "oldest_id": "xyz789",
    "newest_id": "def456",
    "truncated": false
  }
}
```

### Benefits

1. **Atomic Operation**: Get new messages + context in single call
2. **No Race Conditions**: Server guarantees consistency
3. **Efficient**: Single network round-trip
4. **Configurable**: UI can control context_limit (10, 25, 50, 100)
5. **Deduplication Built-In**: Context only sent once per wait cycle

### Duplication Prevention Strategy

**Server-Side Tracking**:
```python
# Server maintains state per agent session
session_state = {
    "last_context_sent_at": timestamp,
    "last_context_newest_id": "abc123",
    "context_limit": 50
}

# Only send context if:
# 1. This is first wait call in session, OR
# 2. include_context=true explicitly requested, OR
# 3. X minutes elapsed since last context send

if should_send_context(session_state, request):
    context = fetch_recent_messages(agent, limit=context_limit)
    session_state["last_context_sent_at"] = now()
    session_state["last_context_newest_id"] = context[0]["id"]
else:
    context = []  # Don't re-send same context
```

**Client-Side Intelligence**:
- Agents maintain their own context window in memory
- Only request fresh context when needed (conversation start, topic change)
- Use memory tool for long-term facts
- Base prompt instructs: "check messages ONCE per conversation"

### Implementation Steps

#### Phase 1: Server-Side (MCP Platform)

1. Update `messages` tool schema to accept `include_context` and `context_limit`
2. Modify message retrieval logic to fetch recent history when requested
3. Return both new mentions and context in structured format
4. Add tests for context fetching logic

#### Phase 2: Client-Side (aX Agent Studio)

1. Update monitors to use new `include_context` parameter
2. Pass `context_limit` from dashboard UI to monitors
3. Update message parsing to handle both new mentions and context
4. Re-enable Memory Depth dropdown in dashboard

#### Phase 3: Dashboard UI

1. Uncomment Memory Depth dropdown in `index.html`
2. Re-enable history-limit-group display logic in `app.js`
3. Pass history_limit from UI → API → process_manager → monitors
4. Update help text to explain the feature

## Code Locations

**Backend (ready but disabled)**:
- `src/ax_agent_studio/dashboard/backend/main.py:55` - MonitorConfig has history_limit
- `src/ax_agent_studio/dashboard/backend/process_manager.py:296` - Passes --history-limit to monitors
- `src/ax_agent_studio/monitors/langgraph_monitor.py:755` - Accepts history_limit parameter
- `src/ax_agent_studio/monitors/ollama_monitor.py:19` - Accepts history_limit parameter

**Frontend (commented out)**:
- `src/ax_agent_studio/dashboard/frontend/index.html:90-101` - Memory Depth dropdown (commented)
- `src/ax_agent_studio/dashboard/frontend/app.js:334` - historyLimit hardcoded to 25

## Alternative Approaches (Not Recommended)

### Option A: Fetch Context Separately (Current Workaround)
**Cons**:
- Race condition between context fetch and new message arrival
- Two network calls instead of one
- Complexity in client code

### Option B: Client-Side History Management
**Cons**:
- State management complexity
- Memory usage
- Doesn't help agents that restart

### Option C: Increase Default History for All
**Cons**:
- Wastes bandwidth for agents that don't need it
- No flexibility

## Testing Plan

Once server-side support is added:

1. **Unit Tests**:
   - Test context_limit parameter parsing
   - Test context retrieval with various limits
   - Test that new mentions + context are returned correctly

2. **Integration Tests**:
   - Deploy agent with Memory Boost (50 messages)
   - Verify agent receives correct historical context
   - Test with rapid-fire messages (FIFO queue still works)

3. **E2E Tests**:
   - UI → API → Monitor → MCP Server → Response
   - Verify agent responses use full context
   - Test memory boost dropdown changes

## Priority: Medium

This is a nice-to-have feature, not critical. The current 25-message default works fine for most use cases. The memory server integration provides long-term memory, which is more important.

## Related Work

- **Memory Server Integration**: COMPLETED - Provides long-term knowledge graph memory
- **FIFO Queue**: COMPLETED - Ensures no message loss during processing
- **Stateless Conversation History**: COMPLETED - Last 25 messages fetched fresh each time

## Dependencies

- MCP Platform team to implement server-side changes
- Coordinate with @madtank or relevant MCP maintainer

## Notes

- The backend code is already in place and tested (monitors accept --history-limit)
- Only the server-side context fetching is missing
- Once server supports `include_context`, we can simply uncomment the UI code

---

**Created**: 2025-10-26
**Status**: Waiting on server-side support
**Owner**: TBD (needs MCP platform coordination)
