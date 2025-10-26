# Architecture Decisions: Conversation Memory

## Current Event-Driven System

**How it works:**
1. **Poller Task**: Calls `messages` with `wait=true`, stores in SQLite queue when message arrives
2. **Processor Task**: Pulls from queue FIFO, calls handler, sends response
3. **SQLite Queue**: Just a trigger/buffer - tells agent "you have work to do"

## Question: How Should Conversation Memory Work?

### Option 1: Stateless Memory (Chirpy-style) - RECOMMENDED
**On each message received:**
1. Agent gets triggered by queue
2. Fetches last 25 messages from server (single API call)
3. Sends those 25 + current message to LLM
4. LLM responds with full context
5. Agent replies to current message

**Pros:**
- Always fresh context
- Works across restarts
- No stale history
- Simple to understand

**Cons:**
- Extra API call per message (fetch last 25)
- Might fetch messages not relevant to this conversation
- How do we scope "last 25"? By agent? By conversation?

### Option 2: In-Memory History (Current broken approach)
**Maintain `conversation_history` list in memory:**
- Append messages as they come
- Send to LLM
- Keep trimming to last N

**Pros:**
- No extra API calls

**Cons:**
- Lost on restart
- Gets stale
- Grows unbounded without management
- Hard to debug

## Key Questions to Answer

1. **Message Scope**: When fetching "last 25 messages", what do we fetch?
   - Just @mentions to this agent?
   - All messages in the current "conversation"?
   - How do we define a "conversation"?

2. **Threading**: Do messages have parent_message_id to define conversation threads?
   - If yes, we could fetch "last 25 in this thread"
   - If no, we fetch "last 25 @mentions to this agent globally"

3. **Performance**: Is fetching 25 messages per response acceptable?
   - Single API call, should be fast
   - Gives best context

## Recommendation

**Use stateless memory with scoped fetching:**

```python
# When agent receives message
current_message = queue.pop()

# Fetch last 25 messages that mention this agent
context = fetch_messages(agent=agent_name, limit=25, mode='latest')

# Send to LLM
conversation = format_for_llm(context + [current_message])
response = llm.generate(conversation)

# Reply with threading
send_reply(response, parent_message_id=current_message.id)
```

**Benefits:**
- Simple, predictable behavior
- Always has recent context
- No state to manage
- Works great with event-driven queue

## What Needs Clarification

From user: "We need to figure out how that is supposed to work"

Need to decide:
- How to scope the "last 25 messages"?
- Should we use threading/parent_message_id?
- Is fetching 25 messages per response the right trade-off?
