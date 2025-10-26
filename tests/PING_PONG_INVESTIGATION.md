# Ping-Pong Investigation: Keeping MCP Connections Alive

## Problem Statement

When using `wait=true` for long periods, MCP connections to Cloud Run can disconnect, causing monitors to miss messages.

## Key Findings

### 1. **MCP Has Built-in Ping/Pong** ✅

The MCP `ClientSession` has a `send_ping()` method:

```python
result = await session.send_ping()
# Returns: EmptyResult(status='pong', timestamp='2025-10-26T05:00:23.718186')
```

### 2. **Pings Work Concurrently with Tool Calls** ✅

We confirmed that pings can be sent **while a tool call is blocking**:
- Wait call started and blocked for 192 seconds
- 4 pings were successfully sent during that time (every 30 seconds)
- Connection remained stable throughout

### 3. **Known Timeout Issues**

Research revealed:
- **TypeScript SDK**: Hard 60-second timeout (even with progress updates)
- **Python SDK**: More flexible with timeout options
- **HTTP Stream Transport**: Known to disconnect after ~60 seconds without keep-alive

### 4. **Python SDK Timeout Options**

The Python `call_tool` method supports:

```python
await session.call_tool(
    name="messages",
    arguments={...},
    read_timeout_seconds=timedelta(minutes=10),  # Extended timeout
    progress_callback=callback_fn                # Reset timeout on progress
)
```

## Test Scripts Created

### 1. `test_heartbeat.py`
Basic ping functionality test - confirms pings work.

### 2. `test_gcp_wait_heartbeat.py`
Full production test with concurrent pings and wait calls:
- ✅ **Result**: 4/4 pings successful over 3+ minutes
- ✅ **Conclusion**: Pings appear to keep connection alive

### 3. `test_wait_without_ping.py`
Comparison test: wait WITH pings vs WITHOUT pings
- **Purpose**: Prove pings are necessary for long connections

### 4. `test_timeout_options.py`
Test different timeout configurations:
- Default timeout
- Extended `read_timeout_seconds`
- Progress callbacks
- Concurrent pings

## Recommended Solutions

### Solution 1: Concurrent Ping Task (RECOMMENDED)

Add a heartbeat task to your monitors:

```python
async def heartbeat_task(session, interval=30):
    """Keep connection alive with periodic pings"""
    while True:
        await asyncio.sleep(interval)
        try:
            await session.send_ping()
            logger.info("💓 Heartbeat OK")
        except Exception as e:
            logger.error(f"❌ Ping failed: {e}")
            raise  # Trigger reconnect

# Run alongside poller
await asyncio.gather(
    heartbeat_task(session, interval=30),
    poll_and_store()
)
```

### Solution 2: Extended Client Timeout

For long-running operations, extend the client timeout:

```python
result = await session.call_tool(
    "messages",
    {"action": "check", "wait": True, "timeout": 300},
    read_timeout_seconds=timedelta(minutes=10)
)
```

### Solution 3: Progress Callbacks

If the server sends progress updates, use callback to reset timeout:

```python
def progress_handler(progress):
    logger.info(f"Progress: {progress}")

result = await session.call_tool(
    "messages",
    {...},
    progress_callback=progress_handler
)
```

## Next Steps

### 1. Run Comparison Test

```bash
PYTHONPATH=src uv run python tests/test_wait_without_ping.py agile_cipher_956
```

This will prove whether pings are required.

### 2. Run Timeout Options Test

```bash
PYTHONPATH=src uv run python tests/test_timeout_options.py agile_cipher_956
```

This will identify the optimal configuration.

### 3. Run Long-Duration Test

```bash
PYTHONPATH=src uv run python tests/test_gcp_wait_heartbeat.py agile_cipher_956 30
```

Test for 30 minutes to see if connection remains stable with pings.

## Integration Plan

Once testing confirms pings keep connection alive:

1. **Add heartbeat to QueueManager**
   - Modify `queue_manager.py` to add a 3rd concurrent task
   - Ping every 30 seconds
   - Handle ping failures by triggering reconnect

2. **Update monitors**
   - All monitors use QueueManager, so they'll get heartbeat automatically

3. **Add config option**
   - Add `heartbeat_interval` to `config.yaml`
   - Allow disabling if not needed

## Questions to Answer

- [ ] Does wait WITHOUT pings disconnect?
- [ ] What's the maximum wait time WITH pings?
- [ ] Do we need extended `read_timeout_seconds`?
- [ ] Can progress callbacks help?
- [ ] What interval is optimal for pings? (30s? 60s?)

## References

- [MCP TypeScript SDK Issue #245](https://github.com/modelcontextprotocol/typescript-sdk/issues/245) - 60-second timeout
- [FastMCP Issue #120](https://github.com/punkpeye/fastmcp/issues/120) - Keep-alive for HTTP Stream
- MCP Specification: Lifecycle and Timeouts
