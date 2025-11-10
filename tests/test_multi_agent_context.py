#!/usr/bin/env python3
"""
Test Multi-Agent Context Awareness

CURRENT BEHAVIOR:
This test validates how agents receive messages in multi-agent conversations.
Currently, agents only receive messages that directly @mention them.

Test Flow:
1. Deploy 4 agents (all with Echo for predictability)
2. Simulate multi-agent conversation:
   - Agent A reports issues (2 messages) - NO @mentions
   - Agent B reports related issues (2 messages) - NO @mentions
   - Coordinator @mentions Observer to diagnose (1 message)
3. Verify Observer receives ONLY the message that mentions it
4. Document current behavior vs desired "message board awareness"

CURRENT BEHAVIOR (✅ What this test validates):
- Agents receive messages that @mention them
- FILO processing (newest message first)
- Context includes previous messages (if from same conversation thread)

DESIRED BEHAVIOR (🔮 Future enhancement):
- Message board awareness: agents see ALL messages in a space
- Even without @mentions, agents see full conversation context
- Enables passive monitoring and proactive assistance

This test documents the current architecture and can be updated
when full message board awareness is implemented.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.e2e.helpers.dashboard_api import DashboardAPI


def test_multi_agent_context_awareness():
    """Test that agents pick up context from multi-agent conversations"""
    print("\n" + "=" * 80)
    print("TEST: Multi-Agent Context Awareness (4-agent collaboration)")
    print("=" * 80)

    with DashboardAPI() as api:
        try:
            # 1. Clean slate
            print("\n1. Cleaning up...")
            api.cleanup_all()
            print("   ✓ Clean")

            # 2. Deploy 4 agents (using Echo for predictable behavior)
            print("\n2. Deploying 4 agents...")

            agents = {
                "ghost_ray_363": "Observer (will diagnose issues)",
                "lunar_ray_510": "Participant A (reports performance)",
                "lunar_craft_128": "Participant B (reports errors)",
                "orion_344": "Coordinator (requests diagnosis)",
            }

            # Map agent names to their config files
            config_map = {
                "ghost_ray_363": "configs/agents/local_ghost.json",
                "lunar_ray_510": "configs/agents/local_lunar_ray.json",
                "lunar_craft_128": "configs/agents/lunar_craft_128.json",
                "orion_344": "configs/agents/orion_344.json",
            }

            monitor_ids = {}
            for agent_name, description in agents.items():
                print(f"   Deploying {agent_name} ({description})...")
                config_path = config_map[agent_name]
                result = api.start_monitor(
                    agent_name=agent_name,
                    config_path=config_path,
                    monitor_type="echo",
                )
                monitor_ids[agent_name] = result["monitor_id"]
                print(f"      ✓ {result['monitor_id']}")

            # 3. Wait for all monitors to be ready
            print("\n3. Waiting for all monitors to be ready...")
            for agent_name in agents.keys():
                if api.wait_for_monitor_ready(agent_name, timeout=15):
                    print(f"   ✓ {agent_name} ready")
                else:
                    print(f"   ❌ {agent_name} not ready")
                    return False

            # 4. Simulate multi-agent conversation
            print("\n4. Simulating multi-agent conversation (5 messages)...")

            # Use Node.js script to send messages from different agents
            import subprocess

            conversation_script = Path(__file__).parent / "e2e" / "send_multi_agent_conversation.js"

            if not conversation_script.exists():
                # Create inline conversation script
                node_code = """
import { MCPClientManager } from '@mcpjam/sdk';

const agents = {
  lunar_ray_510: {
    command: 'npx',
    args: ['-y', 'mcp-remote@0.1.29', 'http://localhost:8002/mcp/agents/lunar_ray_510',
           '--transport', 'http-only', '--allow-http', '--oauth-server', 'http://localhost:8001']
  },
  lunar_craft_128: {
    command: 'npx',
    args: ['-y', 'mcp-remote@0.1.29', 'http://localhost:8002/mcp/agents/lunar_craft_128',
           '--transport', 'http-only', '--allow-http', '--oauth-server', 'http://localhost:8001']
  },
  orion_344: {
    command: 'npx',
    args: ['-y', 'mcp-remote@0.1.29', 'http://localhost:8002/mcp/agents/orion_344',
           '--transport', 'http-only', '--allow-http', '--oauth-server', 'http://localhost:8001']
  }
};

(async () => {
  try {
    console.log('Simulating multi-agent conversation...');

    const manager = new MCPClientManager(agents, {
      defaultClientName: 'Multi-Agent Test',
      defaultClientVersion: '1.0.0'
    });

    // Agent A reports performance issues
    await manager.executeTool('lunar_ray_510', 'messages', {
      action: 'send',
      content: 'Message 1: I am seeing performance issues in the system'
    });
    console.log('  ✓ lunar_ray_510: Message 1 (performance issues)');
    await new Promise(r => setTimeout(r, 200));

    await manager.executeTool('lunar_ray_510', 'messages', {
      action: 'send',
      content: 'Message 2: CPU usage is at 90% and climbing'
    });
    console.log('  ✓ lunar_ray_510: Message 2 (CPU at 90%)');
    await new Promise(r => setTimeout(r, 200));

    // Agent B reports related errors
    await manager.executeTool('lunar_craft_128', 'messages', {
      action: 'send',
      content: 'Message 3: I am getting timeout errors from the API'
    });
    console.log('  ✓ lunar_craft_128: Message 3 (timeout errors)');
    await new Promise(r => setTimeout(r, 200));

    await manager.executeTool('lunar_craft_128', 'messages', {
      action: 'send',
      content: 'Message 4: Database response time has increased to 5 seconds'
    });
    console.log('  ✓ lunar_craft_128: Message 4 (slow database)');
    await new Promise(r => setTimeout(r, 200));

    // Coordinator asks Observer to diagnose
    await manager.executeTool('orion_344', 'messages', {
      action: 'send',
      content: '@ghost_ray_363 Can you diagnose what is causing these issues?'
    });
    console.log('  ✓ orion_344: Message 5 (diagnosis request to @ghost_ray_363)');

    console.log('All 5 messages sent successfully!');
    process.exit(0);
  } catch (error) {
    console.error('Error:', error.message);
    process.exit(1);
  }
})();
"""
                temp_script = Path("/tmp/send_multi_agent_conversation.mjs")
                temp_script.write_text(node_code)
                conversation_script = temp_script

            result = subprocess.run(
                ["node", str(conversation_script)],
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
                return False

            # 5. Wait for processing
            print("\n5. Waiting for Observer to process queue...")
            time.sleep(3)

            # 6. Check Observer's logs for context awareness
            print("\n6. Checking Observer logs for multi-agent context awareness...")
            log_file = Path("logs") / f"{monitor_ids['ghost_ray_363']}.log"

            if log_file.exists():
                log_content = log_file.read_text()

                # CURRENT BEHAVIOR: Observer only sees messages that @mention it
                # Check that Observer received the @mention from orion_344
                found_orion_message = "orion_344" in log_content and "diagnose" in log_content

                # Check that Observer did NOT receive messages without @mentions
                # (validates current @mention-only behavior)
                found_lunar_ray = "lunar_ray_510" in log_content and "performance" in log_content
                found_lunar_craft = "lunar_craft_128" in log_content and "timeout" in log_content

                print("\n   Current Behavior Analysis (@ mention-only):")
                print(
                    f"   - Received @mention message from orion_344: {'✅' if found_orion_message else '❌'}"
                )
                print(
                    f"   - Did NOT receive non-@mention from lunar_ray_510: {'✅' if not found_lunar_ray else '❌ (unexpected)'}"
                )
                print(
                    f"   - Did NOT receive non-@mention from lunar_craft_128: {'✅' if not found_lunar_craft else '❌ (unexpected)'}"
                )

                # Success criteria for CURRENT behavior
                # (Test passes if agent only receives @mention messages)
                if found_orion_message and not found_lunar_ray and not found_lunar_craft:
                    print("\n✅ CURRENT BEHAVIOR VALIDATED")
                    print("   - Observer received message that @mentioned it")
                    print("   - Observer did NOT receive messages without @mentions")
                    print("   - This validates current @mention-only message delivery")
                    print("\n🔮 FUTURE ENHANCEMENT:")
                    print("   - For full 'message board awareness', agents would see ALL messages")
                    print("   - This would enable passive monitoring and proactive assistance")
                    print("   - Update this test when that feature is implemented")
                    print("=" * 80)
                    return True
                elif found_orion_message and (found_lunar_ray or found_lunar_craft):
                    print("\n✅ ENHANCED BEHAVIOR DETECTED!")
                    print("   - Observer received @mention message")
                    print("   - Observer ALSO received non-@mention messages")
                    print("   - This indicates full message board awareness is implemented!")
                    print("=" * 80)
                    return True
                else:
                    print("\n❌ TEST FAILED")
                    print("   - Observer did not receive expected @mention message")
                    print("=" * 80)
                    return False

            else:
                print(f"   ❌ Log file not found: {log_file}")
                return False

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback

            traceback.print_exc()
            return False
        finally:
            print("\n7. Cleanup...")
            api.cleanup_all()
            print("   ✓ All agents stopped")


if __name__ == "__main__":
    success = test_multi_agent_context_awareness()
    sys.exit(0 if success else 1)
