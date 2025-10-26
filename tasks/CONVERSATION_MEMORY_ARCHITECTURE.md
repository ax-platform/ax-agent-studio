# Conversation Memory Architecture - Analysis & Questions

## Status: NEEDS TEAM REVIEW & RESEARCH

**Created**: 2025-10-26
**Priority**: HIGH - Cost and performance implications
**Stakeholders**: @madtank, MCP Platform team, aX Agent Studio developers

---

## Problem Statement

Agents need conversation history to maintain context, but current implementation approaches have potential issues:
1. **Exponential duplication risk** - Could cause massive cost overruns
2. **Inconsistent implementation** - Different monitors handle history differently
3. **Unclear best practices** - No consensus on stateful vs stateless approach

**Real-World Example**:
- Agent lunar_craft_128 had no conversation memory
- Kept saying "I only see your most recent message"
- Users expect agents to remember the conversation

---

## Current State Analysis

### Ollama Monitor (Stateless - SAFE)

**Implementation**:
```python
# Every message received:
context_messages = await fetch_conversation_context(
    session=session,
    agent_name=agent_name,
    limit=25  # Fetch last 25 messages from server
)

# Format for LLM:
conversation = [system_message] + context_messages + [new_message]

# Send to LLM - no persistent state
response = ollama.chat.completions.create(messages=conversation)
```

**Characteristics**:
- ✅ Fresh context every message
- ✅ No accumulation in memory
- ✅ Server is source of truth
- ⚠️ Separate API call to fetch context (not atomic with wait=true)
- ⚠️ Potential race condition (context fetch vs new message)

**Cost Analysis** (⚠️ MORE COMPLEX THAN INITIALLY THOUGHT):

API Fetching (retrieving from server):
- Fetch 25 messages per incoming message
- If 100 messages: 100 fetches × 25 = 2,500 messages retrieved
- Linear growth: O(n) in fetches

LLM Token Processing (sending to model):
- Message 1: [system + message1] = 2 messages → ~100 tokens
- Message 2: [system + message1 + ai1 + message2] = 4 messages → ~200 tokens
- Message 3: [system + message1 + ai1 + message2 + ai2 + message3] = 6 messages → ~300 tokens
- Message N: 2N messages → N×100 tokens
- **TOTAL for 100 messages: 2 + 4 + 6 + ... + 200 = 10,100 messages = ~500,000 tokens!**
- **Quadratic growth: O(N²) in LLM token processing!**

⚠️ **KEY INSIGHT**: Even though we don't store history in memory, we're sending the FULL conversation to the LLM each time. This is NORMAL for conversational AI (like ChatGPT), but the cost is quadratic!

### LangGraph Monitor (Stateful - RISKY?)

**Implementation**:
```python
class OllamaLangGraphAgent:
    def __init__(self, max_history=20):
        self.conversation_history = [SystemMessage(content=system_prompt)]

    async def process(self, message):
        # Append new message
        self.conversation_history.append(HumanMessage(content=message))

        # Run LangGraph workflow
        result = await workflow.run({
            "messages": self.conversation_history  # Pass accumulated history
        })

        # Store AI response in history
        self.conversation_history = result["messages"]

        # Trim if too long
        if len(self.conversation_history) > self.max_history + 1:
            self.conversation_history = [system] + recent_messages[-max_history:]
```

**Characteristics**:
- ⚠️ Accumulates messages in memory across agent lifetime
- ⚠️ Trimming logic (keeps last 20) but still grows
- ❓ Does this cause duplication when combined with server-side history?
- ❓ What happens if agent restarts? History lost?
- ✅ No separate API call needed (uses in-memory state)

**Cost Analysis (UNCLEAR)**:
- If history IS duplicated with server context: Exponential growth potential
- If history is NOT duplicated: Linear growth like Ollama
- **NEEDS VERIFICATION**: Does LangGraph history duplicate server messages?

### Echo Monitor (No Memory)

**Implementation**:
```python
# Just echoes back - no conversation memory at all
return f"@{sender} Echo: {content}"
```

**Characteristics**:
- ✅ Zero memory - zero duplication risk
- ❌ No conversation context

---

## Key Questions (NEED ANSWERS)

### 1. Server-Side Behavior

**Q**: When we call `messages(action="check", limit=25)`, what exactly do we get?
- A) Last 25 messages in the entire space/channel?
- B) Last 25 messages mentioning this agent?
- C) Last 25 messages in current thread?

**Q**: If we fetch limit=25 twice in a row (no new messages), do we get:
- A) The same 25 messages? (Duplicate retrieval)
- B) Empty result? (No new messages)
- C) Different behavior based on mark_read?

**Q**: Does the server charge/count us for:
- A) Messages retrieved (fetched from DB)?
- B) Messages sent to client (network transfer)?
- C) Unique messages only (deduplicated)?

### 2. LangGraph Behavior

**Q**: When LangGraph maintains `self.conversation_history`, are these:
- A) New messages created by the agent (AI responses only)?
- B) Messages fetched from server PLUS AI responses?
- C) Only messages since agent started?

**Q**: If agent restarts, does LangGraph:
- A) Lose all conversation history (starts fresh)?
- B) Fetch previous messages from server?
- C) Load from persistent storage?

**Q**: When we pass `messages: self.conversation_history` to workflow, does LangGraph:
- A) Use ONLY these messages (ignore server history)?
- B) Fetch additional context from MCP tools?
- C) Combine both sources?

### 3. Cost & Performance

**Q**: What's the actual cost model?
- Messages retrieved from database? (API calls)
- LLM tokens processed? (Model inference)
- Network bandwidth? (Data transfer)
- All of the above?

**Q**: For a 100-message conversation, what's the total cost?

Breaking down by cost component:

**API Fetches** (retrieving messages from server):
- Stateless (Ollama): 100 fetches × 25 messages = 2,500 message retrievals
- Stateful (LangGraph): 0 fetches (uses in-memory history)

**LLM Token Processing** (sending to model):
- Both approaches: Quadratic O(N²) growth!
- Message 1: ~100 tokens
- Message 2: ~200 tokens
- Message 3: ~300 tokens
- ...
- Message 100: ~10,000 tokens
- **TOTAL: ~500,000 tokens for 100-message conversation**

⚠️ **CRITICAL REALIZATION**:
Even "stateless" approach has quadratic LLM cost because we send full conversation history to model each time. This is NORMAL for conversational AI, but expensive at scale!

**Q**: Is this additive? **YES!**
- We fetch the same messages repeatedly (storage/API cost)
- We send the same messages to LLM repeatedly (token processing cost)
- Both costs compound quadratically over conversation length

**Q**: Can we avoid this?
- ❓ Use conversation summarization? (compress old messages)
- ❓ Sliding window? (only last N messages, drop oldest)
- ❓ Sparse context? (only relevant messages, not all)
- ❓ Is quadratic growth acceptable/expected?

**Q**: What are the latency implications?
- Separate context fetch (Ollama): +Xms per message
- In-memory history (LangGraph): 0ms (instant)
- Server-side automatic context: +Yms per wait=true

---

## Proposed Solutions (PENDING VALIDATION)

### Option A: Server-Side Automatic Context

**Approach**: Server automatically includes last N messages with every `wait=true` response

**Server Change**:
```python
messages(
    action="check",
    wait=true,
    include_context=true,   # NEW
    context_limit=25,       # NEW
    mark_read=true
)

# Response:
{
  "new_mentions": [{"id": "abc", "content": "@agent Hi"}],
  "context": [last_25_messages]  # Automatically included
}
```

**Client Implementation**:
```python
# Receive from server
result = await session.call_tool("messages", {"wait": true})
new_message = result.new_mentions[0]
context = result.context  # Last 25 included automatically

# Use but don't accumulate
llm_input = [system] + context + [new_message]
response = llm.generate(llm_input)
# Throw away - no persistent state
```

**Pros**:
- ✅ Atomic operation (context + new message together)
- ✅ No race conditions
- ✅ Consistent across all monitors
- ✅ Server controls deduplication

**Cons**:
- ⚠️ Requires server-side changes
- ⚠️ More bandwidth per response
- ❓ How to prevent clients from ALSO accumulating?
- ❓ What if client wants different context_limit?

### Option B: Stateless Everywhere (Chirpy-Style)

**Approach**: All monitors fetch context fresh every time (like Ollama)

**Implementation**:
```python
# Every message:
context = await fetch_conversation_context(session, agent, limit=25)
llm_input = [system] + context + [new_message]
response = llm.generate(llm_input)
# No persistent history - completely stateless
```

**Changes Required**:
- Remove `self.conversation_history` from LangGraph
- Make all monitors stateless
- Accept separate fetch overhead

**Pros**:
- ✅ Simple mental model
- ✅ No accumulation risk
- ✅ Works today (no server changes)
- ✅ Predictable cost (O(n) linear)

**Cons**:
- ⚠️ Separate API call (not atomic)
- ⚠️ Potential race condition
- ⚠️ Extra latency per message
- ❓ Is the separate fetch overhead acceptable?

### Option C: Smart Caching (Hybrid)

**Approach**: Maintain short-term cache, but validate against server

**Implementation**:
```python
class ConversationCache:
    def __init__(self, ttl_seconds=60):
        self.cache = []
        self.last_fetch = None

    async def get_context(self, session, agent):
        # Fetch if cache expired or empty
        if self.should_refresh():
            self.cache = await fetch_conversation_context(session, agent, limit=25)
            self.last_fetch = now()
        return self.cache
```

**Pros**:
- ✅ Reduces API calls
- ✅ Still validates regularly
- ✅ Works with current architecture

**Cons**:
- ⚠️ More complex
- ⚠️ Still has staleness window
- ⚠️ Cache invalidation is hard
- ❓ Does this actually help or just add complexity?

---

## Testing & Validation Needed

### 1. Duplication Test
```python
# Test: Does fetching cause duplication?
context1 = await messages(action="check", limit=25)
context2 = await messages(action="check", limit=25)  # Same call

# Questions:
# - Are context1 and context2 identical?
# - Does mark_read affect this?
# - Are we charged twice?
```

### 2. Cost Measurement
```python
# Test: Measure actual costs for 100-message conversation
# - Ollama approach (stateless, fetch every time)
# - LangGraph approach (stateful, accumulate in memory)
# - Compare total API calls, data transferred, LLM tokens
```

### 3. Race Condition Test
```python
# Test: Can context fetch miss new messages?
# Thread 1: Send message
# Thread 2: Fetch context (does it include message from Thread 1?)
```

### 4. Memory Growth Test
```python
# Test: Run agent for 1000 messages
# Monitor: memory usage, API calls, response times
# Identify: where does cost/memory grow?
```

---

## Recommendations for Team Discussion

### Immediate Actions

1. **Clarify Server Behavior**:
   - Document exact behavior of `messages(action="check", limit=N)`
   - Understand cost model (what do we pay for?)
   - Understand deduplication (are repeated fetches free?)

2. **Measure Current Costs**:
   - Run controlled test: 100 messages with both monitor types
   - Track API calls, data transfer, LLM tokens
   - Compare actual costs

3. **Review LangGraph State**:
   - Is `self.conversation_history` duplicating server messages?
   - Should we remove it and go stateless?
   - Or is there a valid reason for in-memory accumulation?

### Medium-Term Decisions

1. **Standardize Approach**:
   - Choose ONE memory model for all monitors
   - Document why (performance, cost, simplicity)
   - Implement consistently

2. **Server Enhancement** (If Needed):
   - Add `include_context` parameter to wait=true
   - Implement server-side deduplication
   - Document guarantees and limitations

3. **Client Safeguards**:
   - Add defensive checks for duplication
   - Monitor API call patterns
   - Alert on unusual growth

---

## Related Documents

- `tasks/MEMORY_BOOST_FEATURE.md` - Configurable history depth proposal
- `configs/prompts/_base.yaml` - Current agent instructions
- `src/ax_agent_studio/conversation_memory.py` - Context fetching utility

---

## Next Steps

**BLOCKED ON**:
- [ ] Team meeting to discuss architecture options
- [ ] Clarification from MCP Platform team on server behavior
- [ ] Cost measurement tests
- [ ] Decision on stateful vs stateless approach

**OWNER**: @madtank
**DEADLINE**: TBD
**IMPACT**: HIGH - Affects all agents, cost, and user experience

---

## Notes

**Key Insight from Discussion**:
> "We absolutely need to change this architecture, they need to be getting the last 25 messages every single time. My concern with that though is if we're adding that to the conversation history every single time too that could be really dangerous and expensive."

This captures the core tension:
- Agents NEED conversation context (last 25 messages)
- But we can't ACCUMULATE them exponentially
- Must fetch fresh OR server must provide without duplication

**Decision Required**: How do we safely provide context without exponential growth?
