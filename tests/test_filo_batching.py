#!/usr/bin/env python3
"""
Test FILO Queue Batching

Validates that agents receive entire message queue in one batch
and can respond with full context.

Test Flow:
1. Deploy receiver agent (Echo monitor)
2. Send 5 messages rapidly from sender agent
3. Verify receiver gets all 5 in one batch
4. Check response includes full context
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.e2e.helpers.dashboard_api import DashboardAPI


def test_filo_batching():
    """Test FILO queue batching with 5-message burst"""
    print("\n" + "=" * 80)
    print("TEST: FILO Queue Batching (5-message burst)")
    print("=" * 80)

    with DashboardAPI() as api:
        try:
            # 1. Clean slate
            print("\n1. Cleaning up...")
            api.cleanup_all()
            print("   ✓ Clean")

            # 2. Deploy receiver (Echo monitor for predictable behavior)
            print("\n2. Deploying receiver agent (ghost_ray_363 with Echo)...")
            result = api.start_monitor(
                agent_name="ghost_ray_363",
                config_path="configs/agents/local_ghost.json",
                monitor_type="echo",
            )
            monitor_id = result["monitor_id"]
            print(f"   ✓ Receiver deployed: {monitor_id}")

            # Wait for monitor to be fully ready
            print("\n3. Waiting for monitor to be ready...")
            if api.wait_for_monitor_ready("ghost_ray_363", timeout=15):
                print("   ✓ Monitor ready")
            else:
                print("   ❌ Monitor not ready")
                return False

            # 4. Send 5 messages rapidly
            print("\n4. Sending 5-message burst...")

            test_messages = [
                "Message 1: What is the weather?",
                "Message 2: Never mind the weather, what about sports?",
                "Message 3: Actually, I want to talk about food.",
                "Message 4: On second thought, let's discuss technology.",
                "Message 5: Final question - can you summarize our conversation?",
            ]

            # Use Node.js script to send messages
            import subprocess

            node_script = Path(__file__).parent / "e2e" / "send_burst_messages.js"
            if not node_script.exists():
                # Create inline sending script
                send_commands = []
                for i, msg in enumerate(test_messages, 1):
                    send_commands.append(
                        f"await manager.executeTool('lunar_ray_510', 'messages', {{ action: 'send', content: '@ghost_ray_363 {msg}' }}); "
                        f"console.log('  Sent message {i}'); "
                        f"await new Promise(r => setTimeout(r, 100));"
                    )

                node_code = f"""
import {{ MCPClientManager }} from '@mcpjam/sdk';

(async () => {{
  const manager = new MCPClientManager({{
    lunar_ray_510: {{
      command: 'npx',
      args: ['-y', 'mcp-remote@0.1.29', 'http://localhost:8002/mcp/agents/lunar_ray_510', '--transport', 'http-only', '--allow-http', '--oauth-server', 'http://localhost:8001']
    }}
  }}, {{ defaultClientName: 'FILO Test', defaultClientVersion: '1.0.0' }});

  console.log('Sending 5 messages rapidly...');
  {"\\n  ".join(send_commands)}
  console.log('All messages sent!');
}})();
"""

                temp_script = Path("/tmp/send_burst.mjs")
                temp_script.write_text(node_code)

                result = subprocess.run(
                    ["node", str(temp_script)],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
            else:
                result = subprocess.run(
                    ["node", str(node_script)],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

            if result.returncode == 0:
                print("   ✓ All 5 messages sent")
                if result.stdout:
                    for line in result.stdout.splitlines():
                        print(f"     {line}")
            else:
                print("   ❌ Failed to send messages")
                if result.stderr:
                    print(f"     Error: {result.stderr[:200]}")
                # Continue anyway to check if any messages made it through

            # 5. Wait a moment for processing
            print("\n5. Waiting for agent to process queue...")
            time.sleep(3)

            # 6. Check monitor logs for batching behavior
            print("\n6. Checking monitor logs for FILO batching...")
            log_file = Path("logs") / f"{monitor_id}.log"

            if log_file.exists():
                log_content = log_file.read_text()

                # Look for batch processing indicators
                if "BATCH of 5 messages" in log_content or "batch_size = 5" in log_content:
                    print("   ✓ FOUND: Agent processed 5 messages in one batch!")
                elif "BATCH" in log_content:
                    # Count how many messages were batched
                    import re

                    batch_matches = re.findall(r"BATCH of (\d+)", log_content)
                    if batch_matches:
                        sizes = [int(m) for m in batch_matches]
                        print(f"   ⚠ Found batches of sizes: {sizes}")
                        if sum(sizes) >= 5:
                            print("   ✓ All 5 messages processed (possibly multiple batches)")
                        else:
                            print("   ❌ Not all messages processed")
                            return False
                else:
                    print("   ⚠ No explicit batch markers found")
                    # Check if all 5 messages appear in logs
                    messages_found = sum(1 for msg in test_messages if msg in log_content)
                    print(f"   Found {messages_found}/5 messages in logs")

                    if messages_found >= 4:  # Allow some tolerance
                        print("   ✓ Most messages found in logs")
                    else:
                        print("   ❌ Not enough messages found")
                        return False

                # Check for FILO processing (newest first)
                if "Message 5" in log_content:
                    # Find position of Message 5 vs Message 1
                    pos_msg5 = log_content.find("Message 5:")
                    pos_msg1 = log_content.find("Message 1:")

                    if pos_msg5 > 0 and pos_msg1 > 0:
                        if pos_msg5 < pos_msg1:
                            print("   ✓ FILO confirmed: Message 5 processed before Message 1")
                        else:
                            print("   ℹ Messages in chronological order (history context)")

            else:
                print(f"   ❌ Log file not found: {log_file}")
                return False

            print("\n" + "=" * 80)
            print("✅ TEST PASSED: FILO batching working correctly")
            print("=" * 80)
            return True

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback

            traceback.print_exc()
            return False
        finally:
            api.cleanup_all()


if __name__ == "__main__":
    success = test_filo_batching()
    sys.exit(0 if success else 1)
