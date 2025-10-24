# Session Handoff: Feature Branch Debug

## Context

**Branch:** `feature/verbose-logging-and-rate-limit-fixes`
**Status:** Has valuable features but causes excessive API calls
**Main Branch:** ✅ Working perfectly (baseline)

## The Problem

When starting an agent on the feature branch, we see **46+ tool calls** instead of the expected **~2-3 calls**:

```
[Local→Remote] tools/call (repeated 46+ times!)
Error: HTTP 429 - DDoS pattern detected
```

This triggers the server's DDoS protection. Main branch only makes 2 calls - clean and fast.

## Features Added in Feature Branch (Worth Keeping!)

### 1. Verbose Logging Toggle ⭐
**Files:** `dashboard/frontend/app.js`, `index.html`, `style.css`

- Added "Verbose" checkbox in Live Logs UI
- Shows/hides full AI responses (the "💬 RESPONSE:" logs)
- Default: condensed view (just "🤔 Agent thinking...")
- Toggle on: see complete agent responses
- Works retroactively on existing logs

**Status:** ✅ UI works great, just needs the backend verbose logs

### 2. Agent Filter Dropdown ⭐
**Files:** `dashboard/frontend/app.js`, `index.html`, `style.css`

- Filter live logs by specific agent
- Dropdown auto-populates with running agent names
- Shows "All Agents" by default
- Real-time filtering of log display

**Status:** ✅ Works perfectly

### 3. Full Response Logging
**Files:** `monitors/langgraph_monitor.py`, `monitors/ollama_monitor.py`

Added logging line:
```python
logger.info(f"💬 RESPONSE:\n{response}")  # Full, untruncated
```

Removed truncations like `content[:50]` and `content[:200]`

**Status:** ✅ Works correctly

### 4. Custom MCP Tool Loader ❌ **THIS IS THE PROBLEM**
**File:** `mcp_manager.py`

**What it does:**
- Replaces `load_mcp_tools()` from langchain_mcp_adapters
- Builds tools manually from `list_tools()` schema
- Goal: Avoid excessive API calls

**The Issue:**
Something in this implementation causes 46+ tool calls instead of reducing them!

## What Works on Main

**Main branch tool loading flow:**
```python
# mcp_manager.py line 188
server_tools = await load_mcp_tools(session)
```

**API call pattern (CLEAN):**
```
[Local→Remote] initialize
[Remote→Local] 0
[Local→Remote] notifications/initialized
[Local→Remote] tools/call   ← Just 1!
[Remote→Local] 1
[Local→Remote] tools/list   ← Just 1!
[Remote→Local] 2
```

Total: 2 calls per agent startup. Fast and clean!

## What Breaks on Feature Branch

**Feature branch tool loading:**
```python
# Custom implementation in mcp_manager.py lines 175-271
# Builds tools manually from schemas
```

**API call pattern (BROKEN):**
```
[Local→Remote] initialize
[Remote→Local] 0
[Local→Remote] notifications/initialized
[Local→Remote] tools/call   ← Call 2
[Remote→Local] 2
[Local→Remote] tools/call   ← Call 3
[Remote→Local] 3
... (continues to 46+)
Error: DDoS pattern detected
```

## Root Cause Analysis Needed

**Questions to investigate:**

1. **Why 46 calls?** We have ~25 tools total (5+6+14). Why almost 2x that?

2. **Where do the calls come from?**
   - Is the custom tool loader calling tools during creation?
   - Is something else triggering tool validation?
   - Are there duplicate tool registrations?

3. **Main vs Feature comparison:**
   - Main: Uses `load_mcp_tools()` → 2 calls
   - Feature: Custom loader → 46+ calls
   - What does `load_mcp_tools()` do differently?

4. **Hypothesis:** The custom implementation might be:
   - Calling tools to test them (shouldn't be)
   - Creating tools multiple times (shouldn't be)
   - Triggering LangChain validation that calls tools (possible)

## Debug Strategy

### Step 1: Compare Implementations
```bash
git checkout main
# Look at: src/ax_agent_studio/mcp_manager.py lines 175-198

git checkout feature/verbose-logging-and-rate-limit-fixes
# Look at: src/ax_agent_studio/mcp_manager.py lines 175-271
```

### Step 2: Add Debug Logging
In the feature branch custom tool loader, add:
```python
logger.info(f"🔍 Creating tool: {tool_name} (no calls should happen here)")
# ... tool creation code ...
logger.info(f"✅ Tool created: {tool_name} (should be 0 API calls)")
```

### Step 3: Check LangChain Behavior
The `StructuredTool` constructor might be calling tools for validation. Check:
- Does `StructuredTool.__init__` call the tool?
- Does setting both `func` and `coroutine` cause double calls?
- Is there a `validate=False` parameter?

### Step 4: Isolate the Feature
Try merging features individually:
1. Merge just verbose logging (monitors + frontend) → test
2. Merge just agent filter (frontend only) → test
3. Merge custom tool loader last → identify exact breaking point

## Key Files to Review

### Working (Main Branch)
- `src/ax_agent_studio/mcp_manager.py` lines 175-198

### Broken (Feature Branch)
- `src/ax_agent_studio/mcp_manager.py` lines 175-271

### Worth Keeping
- `src/ax_agent_studio/dashboard/frontend/app.js` (verbose + filter)
- `src/ax_agent_studio/dashboard/frontend/index.html` (UI)
- `src/ax_agent_studio/dashboard/frontend/style.css` (styles)
- `src/ax_agent_studio/monitors/langgraph_monitor.py` (line 840: full response log)
- `src/ax_agent_studio/monitors/ollama_monitor.py` (line 133: full response log)

## Success Criteria

Feature branch should:
1. ✅ Make only 2-3 API calls per agent startup (like main)
2. ✅ Show verbose logging toggle in UI
3. ✅ Show agent filter dropdown
4. ✅ Log full responses without truncation
5. ✅ Not trigger rate limits or DDoS protection

## Testing

### Test on Main (Baseline)
```bash
git checkout main
./scripts/start_dashboard.sh
# Start agent → Count API calls in output
# Expected: 2 calls (1 tools/call, 1 tools/list)
```

### Test on Feature Branch
```bash
git checkout feature/verbose-logging-and-rate-limit-fixes
./scripts/start_dashboard.sh
# Start agent → Count API calls in output
# Current: 46+ calls ❌
# Goal: 2-3 calls ✅
```

## Additional Context

### Server-Side Changes
@code_weaver fixed rate limits on aX server:
- Increased to 300 req/min (was 120)
- Burst capacity: 1000 (was 20)
- Discovery methods (tools/list) exempt from limits

So rate limiting is less strict now, but 46 calls still triggers DDoS protection.

### Original Issue
- Started with 429 rate limit errors
- Tried to fix by reducing API calls
- Accidentally made it worse (46 calls instead of reducing)
- Main branch was always fine, we just panicked

## Recommended Approach

1. **Cherry-pick the good features:**
   ```bash
   git checkout main
   git checkout feature/verbose-logging-and-rate-limit-fixes -- \
     src/ax_agent_studio/dashboard/frontend/ \
     src/ax_agent_studio/monitors/langgraph_monitor.py \
     src/ax_agent_studio/monitors/ollama_monitor.py
   ```

2. **Test if these work without the tool loader changes**

3. **If tool loader is really needed:**
   - Study what `load_mcp_tools()` does
   - Understand why our version makes 46 calls
   - Fix the implementation or abandon it

## Notes

- Main branch is the source of truth - it works perfectly
- Don't overthink or panic - the original code was fine
- The verbose logging features are valuable and should be preserved
- The custom tool loader can be abandoned if it's too complex
- Sometimes the library knows better than we do!

---

**Session Goal:** Get feature branch working with same clean 2-call pattern as main, while keeping the UI enhancements.

**Remember:** Main works. Start from there. Add features incrementally. Test after each addition.
