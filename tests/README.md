# Testing Guide

This directory contains comprehensive E2E tests for the aX Agent Studio dashboard and monitors.

## Test Suites

### 1. Dashboard UI Tests (`test_dashboard_ui_e2e.py`)
Tests the dashboard frontend using Playwright to verify UI behavior for all agent types.

**What it tests:**
- ✅ Dashboard loads correctly
- ✅ **Echo Agent**: No provider, no model (simple passthrough)
- ✅ **Ollama Agent**: No provider (implicit), model dropdown visible
- ✅ **Claude Agent SDK**: No provider (uses Anthropic SDK), Claude models only, Sonnet 4.5 default
- ✅ **LangGraph Agent**: Provider and model dropdowns both visible
- ✅ Default agent type loads from `DEFAULT_AGENT_TYPE` env var

**Prerequisites:**
- Dashboard must be running: `uv run dashboard`
- Playwright installed: `uv pip install playwright && python -m playwright install chromium`

**Run:**
```bash
python tests/test_dashboard_ui_e2e.py
```

**Output:**
- Console: Test results summary
- Screenshots: `/tmp/*.png` for debugging

---

### 2. Dashboard API Tests (`test_dashboard_api_e2e.py`)
Tests the dashboard backend API endpoints.

**What it tests:**
- Health check endpoint
- Providers list and defaults
- Model lists for each provider
- Claude models (Sonnet 4.5 and Haiku 4.5)
- Gemini models
- Ollama models (dynamic)
- Environment and config endpoints
- Kill switch status

**Prerequisites:**
- Dashboard must be running: `uv run dashboard`
- pytest installed: `uv pip install pytest pytest-asyncio httpx`

**Run:**
```bash
python tests/test_dashboard_api_e2e.py
```

---

### 3. All Monitors Tests (`test_all_monitors_e2e.py`)
Tests actual monitor deployment and lifecycle for all 4 monitor types.

**What it tests:**
- Echo monitor deployment (no provider, no model)
- Ollama monitor deployment (no provider, requires model)
- Claude Agent SDK monitor deployment (no provider, Claude model)
- LangGraph monitor deployment (requires provider + model)
- Monitor start/stop/cleanup

**Prerequisites:**
- Dashboard must be running: `uv run dashboard`
- Agent configs must exist: `configs/agents/lunar_craft_128.json`
- httpx installed: `uv pip install httpx`

**Run:**
```bash
python tests/test_all_monitors_e2e.py
```

---

## Quick Start

### Install Test Dependencies
```bash
# Install testing tools
uv pip install pytest pytest-asyncio httpx playwright

# Install Playwright browsers
.venv/bin/python -m playwright install chromium
```

### Run All Tests
```bash
# Start dashboard in background
uv run dashboard &

# Wait for dashboard to start
sleep 3

# Run all test suites
python tests/test_dashboard_ui_e2e.py
python tests/test_dashboard_api_e2e.py
python tests/test_all_monitors_e2e.py

# Stop dashboard
pkill -f "dashboard.backend.main"
```

---

## Test Matrix

| Test Suite | Tool | What It Tests | Speed |
|------------|------|---------------|-------|
| `test_dashboard_ui_e2e.py` | Playwright | Frontend UI behavior | Fast ⚡ |
| `test_dashboard_api_e2e.py` | pytest + httpx | Backend API endpoints | Fast ⚡ |
| `test_all_monitors_e2e.py` | httpx | Monitor deployment | Slow 🐌 |

---

## CI/CD Integration

### GitHub Actions Example
```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.13'

      - name: Install dependencies
        run: |
          pip install uv
          uv pip install -r requirements.txt
          uv pip install pytest pytest-asyncio httpx playwright
          python -m playwright install chromium

      - name: Start dashboard
        run: uv run dashboard &

      - name: Wait for dashboard
        run: sleep 5

      - name: Run UI tests
        run: python tests/test_dashboard_ui_e2e.py

      - name: Run API tests
        run: python tests/test_dashboard_api_e2e.py

      - name: Upload screenshots
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: test-screenshots
          path: /tmp/*.png
```

---

## Debugging Failed Tests

### View Screenshots
All UI tests save screenshots to `/tmp/`:
```bash
open /tmp/dashboard_loaded.png
open /tmp/claude_sdk_agent.png
```

### Run Tests in Non-Headless Mode
Edit test file and change:
```python
browser = p.chromium.launch(headless=False)  # See browser in action
```

### Check Dashboard Logs
```bash
tail -f logs/dashboard.log
```

---

## Adding New Tests

### UI Test Template
```python
def test_new_feature_ui():
    """Test description"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            page.goto('http://localhost:8000')
            page.wait_for_load_state('networkidle')

            # Your test logic
            expect(page.locator('#element')).to_be_visible()

            print("✅ Test PASSED")
            return True
        except Exception as e:
            print(f"❌ Test FAILED: {e}")
            return False
        finally:
            browser.close()
```

### API Test Template
```python
async def test_new_api_endpoint(client):
    """Test API endpoint"""
    response = await client.get("/api/new-endpoint")
    assert response.status_code == 200
    data = response.json()
    assert "expected_field" in data
```

---

## Troubleshooting

### Playwright: `Error: Browser was not found`
```bash
.venv/bin/python -m playwright install chromium
```

### `ModuleNotFoundError: No module named 'playwright'`
```bash
uv pip install playwright
```

### Dashboard not responding
```bash
# Check if dashboard is running
curl http://localhost:8000/api/health

# Start dashboard
uv run dashboard
```

### Tests timeout
- Increase timeout in test: `page.wait_for_timeout(5000)`
- Check network: Dashboard might be slow to respond
- Check logs: `tail -f logs/dashboard.log`

---

## Coverage

Current test coverage:
- ✅ Dashboard UI: 6 tests
- ✅ Dashboard API: 10+ tests
- ✅ Monitor deployment: 4 agent types
- ⏭️ Message flow: TODO
- ⏭️ MCP server integration: TODO
- ⏭️ Error handling: TODO

---

## Best Practices

1. **Always start dashboard before running tests**
2. **Clean up monitors after tests** (tests do this automatically)
3. **Use headless mode in CI/CD** (faster, no display needed)
4. **Save screenshots on failure** (easier debugging)
5. **Run tests in isolation** (don't depend on previous test state)
6. **Test edge cases** (missing configs, invalid inputs)
7. **Keep tests fast** (mock slow operations if possible)
