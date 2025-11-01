# Session Handoff: PR #10 - Claude Agent SDK Fix

## Current State
**Branch:** `fix/dashboard-websocket-resilience`
**PR:** https://github.com/ax-platform/ax-agent-studio/pull/10
**Status:** ✅ READY TO MERGE (all fixes complete)

## What Was Fixed

### 1. WebSocket Resilience (`0012d11`)
- Dashboard crashes when browser closes → Fixed
- Added `WebSocketDisconnect` exception handling to log streamer
- Monitors continue running after client disconnects

### 2. Claude Agent SDK UI (`905adb2`)
- Provider dropdown shown for Claude Agent SDK → Hidden
- Each framework now shows correct UI:
  - Echo: No settings
  - Ollama: Model only
  - Claude Agent SDK: Model only (no provider)
  - LangGraph: Provider + Model

### 3. Architecture Document (`ad5a3e5`)
- Created `AGENT_FRAMEWORK_ARCHITECTURE.md`
- Documents auth isolation design
- Framework registry pattern for future

### 4. DEFAULT_AGENT_TYPE (`f1e069a`)
- Added env var: `DEFAULT_AGENT_TYPE=claude_agent_sdk`
- Dashboard remembers preference
- Set in `.env.example`

### 5. Anthropic Provider with Subscription (`a154b25`) **CRITICAL FIX**
- Problem: `USE_CLAUDE_SUBSCRIPTION=true` hid Anthropic provider
- Fix: Anthropic available if API key OR subscription enabled
- Claude models now show in dashboard with subscription mode

## How Claude Agent SDK Now Works

**Environment Setup:**
```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...  # Optional, only for LangGraph
DEFAULT_AGENT_TYPE=claude_agent_sdk
USE_CLAUDE_SUBSCRIPTION=true
```

**Authentication Flow:**
1. Claude Agent SDK: Uses subscription (via `claude login`) if `USE_CLAUDE_SUBSCRIPTION=true`
2. LangGraph: Uses `ANTHROPIC_API_KEY` (unaffected by subscription mode)
3. Both can coexist without conflicts

**Dashboard Behavior:**
1. Opens to Claude Agent SDK by default
2. Anthropic provider shows in list (subscription enabled)
3. Provider dropdown hidden for Claude Agent SDK
4. Claude models available: claude-sonnet-4-5, claude-haiku-4-5, etc.

## To Fix Aurora

**Problem:** Aurora running with Gemini model on Claude Agent SDK (incompatible)

**Solution:**
1. Stop Aurora: `pkill -f "claude_agent_sdk_monitor.*Aurora"`
2. Add to `.env`: `DEFAULT_AGENT_TYPE=claude_agent_sdk`
3. Restart dashboard
4. Deploy Aurora:
   - Type: Claude Agent SDK
   - Model: claude-sonnet-4-5
   - System Prompt: research_assistant (optional)

## Merge Checklist

- [x] WebSocket resilience tested
- [x] Claude Agent SDK UI correct
- [x] Default agent type working
- [x] Anthropic provider shows with subscription
- [x] All commits pushed
- [ ] Test Aurora with claude-sonnet-4-5
- [ ] Verify LangGraph still works with Anthropic
- [ ] Merge PR #10

## Next Steps (Future Work)

1. **Implement Framework Registry** (from architecture doc)
   - Move to data-driven framework configs
   - Backend API `/api/frameworks`
   - Remove hardcoded framework logic

2. **Model Defaults per Framework**
   - Claude Agent SDK → claude-sonnet-4-5
   - LangGraph → user choice
   - Ollama → first available model

3. **Better Error Messages**
   - Detect incompatible model/framework combos
   - Show helpful error (e.g., "Gemini not supported on Claude Agent SDK")

## Files Modified (PR #10)

1. `src/ax_agent_studio/dashboard/backend/log_streamer.py` - WebSocket handling
2. `src/ax_agent_studio/dashboard/frontend/app.js` - Framework UI logic
3. `AGENT_FRAMEWORK_ARCHITECTURE.md` - Design doc
4. `.env.example` - DEFAULT_AGENT_TYPE, USE_CLAUDE_SUBSCRIPTION
5. `src/ax_agent_studio/dashboard/backend/providers_loader.py` - Anthropic subscription support

## Testing Notes

**Tested:**
- ✅ WebSocket disconnects (no crash)
- ✅ Claude Agent SDK UI (provider hidden)
- ✅ Default agent type loads
- ✅ Anthropic provider available with subscription

**Needs Testing:**
- ⚠️ Aurora with claude-sonnet-4-5
- ⚠️ LangGraph with Anthropic (verify not broken)
- ⚠️ Subscription mode auth (needs `claude login`)

## Important Notes

- **Auth Isolation:** Claude Agent SDK monitor uses try/finally to restore API key (commit `e7770de` from PR #9, already merged)
- **Subscription Preference:** When both API key and subscription available, Claude Agent SDK prefers subscription
- **LangGraph Unaffected:** Still uses ANTHROPIC_API_KEY as before
- **Provider Loading:** Now checks `USE_CLAUDE_SUBSCRIPTION` flag, not just API key presence

## Quick Commands

```bash
# Test Aurora
pkill -f "Aurora"  # Stop current
# Use dashboard to start with: Claude Agent SDK + claude-sonnet-4-5

# Test LangGraph with Anthropic
# Use dashboard to start with: LangGraph + Anthropic + claude-sonnet-4-5

# Check logs
tail -f logs/Aurora_claude_agent_sdk_*.log
```
