#!/usr/bin/env python3
"""
E2E Test 1: Agent Connectivity

Simple test: forEach loop, have each test agent send a message.
No monitors, no deployment - just verify agents can communicate via MCP JAM SDK.

Usage:
    python test_01_agent_connectivity.py
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tests.e2e.test_config import TEST_AGENTS


def test_agent_can_send_message(agent_name: str) -> bool:
    """Test that an agent can send a message via MCP JAM SDK"""
    print(f"\n{'─' * 80}")
    print(f"Testing: {agent_name}")
    print("─" * 80)

    test_message = f"Test 1: {agent_name} connectivity check"

    try:
        result = subprocess.run(
            [
                "node",
                "-e",
                f"""
const {{ MCPClientManager }} = require('@mcpjam/sdk');

const mcpConfig = {{
  "{agent_name}": {{
    command: 'npx',
    args: [
      '-y', 'mcp-remote@0.1.29',
      'http://localhost:8002/mcp/agents/{agent_name}',
      '--transport', 'http-only',
      '--allow-http',
      '--oauth-server', 'http://localhost:8001'
    ]
  }}
}};

(async () => {{
  const manager = new MCPClientManager(mcpConfig, {{
    defaultClientName: 'E2E Test',
    defaultClientVersion: '1.0.0'
  }});

  const result = await manager.executeTool('{agent_name}', 'messages', {{
    action: 'send',
    content: '{test_message}'
  }});

  if (result.message_id) {{
    console.log('✅ Message sent successfully');
    console.log('   Message ID:', result.message_id.substring(0, 8));
    process.exit(0);
  }} else {{
    console.log('❌ No message ID returned');
    process.exit(1);
  }}
}})().catch(err => {{
  console.log('❌ Error:', err.message);
  process.exit(1);
}});
""",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Print output
        if result.stdout:
            print(result.stdout.strip())
        if result.stderr and "Shutting down" not in result.stderr:
            stderr_lines = [
                line
                for line in result.stderr.split("\n")
                if line
                and not any(
                    x in line for x in ["[", "Using", "Connected", "Proxy", "Press", "Shutting"]
                )
            ]
            if stderr_lines:
                print("\n".join(stderr_lines))

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print("❌ Timeout")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Test all agents can send messages"""
    print("\n" + "=" * 80)
    print("TEST 1: Agent Connectivity")
    print("=" * 80)
    print(f"\nTesting {len(TEST_AGENTS)} agents")
    print("Goal: Verify each agent can send messages via MCP JAM SDK")
    print("=" * 80)

    results = {}
    for agent_name in TEST_AGENTS.keys():
        results[agent_name] = test_agent_can_send_message(agent_name)

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    for name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {status}: {name}")

    passed_count = sum(1 for p in results.values() if p)
    total = len(results)
    print(f"\n{passed_count}/{total} agents can send messages")
    print("=" * 80 + "\n")

    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
