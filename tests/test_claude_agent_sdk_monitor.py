"""Tests for the Claude Agent SDK monitor helpers."""

from pathlib import Path
import sys
import types

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT / "src"))

if "ax_agent_studio.config" not in sys.modules:  # pragma: no cover - dependency shim for tests
    config_stub = types.ModuleType("ax_agent_studio.config")
    config_stub.get_monitor_config = lambda: {}
    config_stub.get_mcp_config = lambda: {}
    config_stub.get_ollama_config = lambda: {}
    config_stub.get_dashboard_config = lambda: {}
    sys.modules["ax_agent_studio.config"] = config_stub

if "claude_agent_sdk" not in sys.modules:  # pragma: no cover - dependency shim for tests
    stub = types.ModuleType("claude_agent_sdk")
    stub.ClaudeAgentOptions = object

    async def _query(**_kwargs):  # minimal async generator placeholder
        if False:
            yield None

    stub.query = _query
    sys.modules["claude_agent_sdk"] = stub

from ax_agent_studio.monitors.claude_agent_sdk_monitor import _fix_code_blocks


def test_fix_code_blocks_handles_windows_line_endings():
    """Triple backtick code fences should normalize Windows style newlines."""

    original = "Before\r\n```python\r\nprint('hi')\r\n```\r\nAfter"

    expected = "Before\r\nCode (python):\n    print('hi')\r\nAfter"

    assert _fix_code_blocks(original) == expected


def test_fix_code_blocks_handles_unix_line_endings():
    """Triple backtick code fences should normalize Unix style newlines."""

    original = "Before\n```text\nline one\nline two\n```\nAfter"

    expected = "Before\nCode (text):\n    line one\n    line two\nAfter"

    assert _fix_code_blocks(original) == expected
