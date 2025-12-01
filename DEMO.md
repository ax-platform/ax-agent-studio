# aX Agent Studio - Developer Demo

This branch (`challenge/ax-clean-install`) implements a reproducible, one-command developer environment with a local MCP mock server and smoke testing harness.

## 🚀 One-Command Start

To start the entire environment (virtual env creation, dependency installation, and dashboard startup):

```powershell
.\scripts\dev-setup.ps1
```

This script will:
1.  Check for/create `.venv` and install `pip`.
2.  Install dependencies from `pyproject.toml` or `requirements.txt`.
3.  Set `PYTHONUTF8=1` to avoid Windows encoding issues.
4.  Start the **Agent Studio Dashboard** on `http://127.0.0.1:8000`.

## 🧪 Running the Smoke Test

To verify agent stability, heartbeats, and message flow without external dependencies:

1.  **Start the MCP Mock Server** (in a separate terminal):
    ```powershell
    .\.venv\Scripts\python.exe scripts/mcp_mock.py
    ```

2.  **Register Agents** (populates the mock workspace):
    ```powershell
    .\.venv\Scripts\python.exe scripts/register_agents.py
    ```

3.  **Run the Load/Smoke Test**:
    ```powershell
    # Run 10 agents for 60 seconds with 5-second heartbeats
    .\.venv\Scripts\python.exe tests/stability/load_test.py --agents 10 --duration 60 --heartbeat 5
    ```

## 🛠️ Features Added

*   **`scripts/dev-setup.ps1`**: Automated setup and startup script.
*   **`scripts/mcp_mock.py`**: Minimal HTTP server mocking MCP endpoints for deterministic testing.
*   **`scripts/validate_configs.py`**: Validates agent JSON configurations against required schema.
*   **`scripts/register_agents.py`**: Helper script to populate the mock workspace.
*   **`src/ax_agent_studio/llm_factory.py`**: Added fallback stub to prevent crashes when API keys are missing.
*   **`tests/stability/load_test.py`**: Harness for verifying system stability under load.

## 📋 Verification Results

*   **Venv**: Python 3.14.0, pip 25.3
*   **Config Validation**: All agent configs valid.
*   **Smoke Test**: 100% success rate on 10-agent run (60s duration).
