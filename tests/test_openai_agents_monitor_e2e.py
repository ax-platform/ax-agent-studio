#!/usr/bin/env python3
"""
End-to-End Monitor Test for OpenAI Agents SDK
Starts the monitor, sends a test message from a different agent, and verifies response
"""

import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Load environment variables from .env file
load_dotenv()


async def send_test_message(sender_handle: str, agent_name: str, message: str):
    """Send a message to an agent and wait for response using MCP wait functionality"""

    # Connect to ax-gcp MCP server
    server_params = StdioServerParameters(
        command="npx",
        args=[
            "-y",
            "mcp-remote@0.1.29",
            f"http://localhost:8002/mcp/agents/{sender_handle}",
            "--transport",
            "http-only",
            "--oauth-server",
            "http://localhost:8001",
        ],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            print(f" Sending message from @{sender_handle} to @{agent_name}: {message}")
            print(f"⏳ Waiting for @{agent_name} to respond (timeout: 60s)...\n")

            # Send message with wait=true and wait_mode='mentions'
            # This will wait for the agent to respond before returning
            try:
                result = await session.call_tool(
                    "messages",
                    {
                        "action": "send",
                        "content": f"@{agent_name} {message}",
                        "wait": True,
                        "wait_mode": "mentions",
                        "timeout": 60,
                        "context_limit": 5,
                    },
                )

                # Parse response
                if hasattr(result, "content"):
                    content = result.content
                    if isinstance(content, list) and len(content) > 0:
                        text = str(content[0].text) if hasattr(content[0], "text") else str(content[0])
                        print(f" Response received:\n{text}\n")

                        # Check if agent responded (should mention the sender)
                        if f"@{sender_handle}" in text and agent_name in text:
                            print(" Agent response detected!")
                            return True
                        else:
                            print("  Response format unexpected")
                            print(f"   Expected mention of @{sender_handle} from @{agent_name}")
                            return False
                else:
                    print("  No content in response")
                    return False

            except Exception as e:
                print(f" Error during send/wait: {e}")
                print("   Monitor may not have responded in time or encountered an error")
                return False


async def test_openai_agents_monitor():
    """Test the OpenAI Agents SDK monitor end-to-end"""
    print("=" * 60)
    print("OpenAI Agents SDK Monitor End-to-End Test")
    print("=" * 60 + "\n")

    # Configuration
    agent_name = "lunar_craft_128"  # Target agent running OpenAI Agents SDK
    sender_handle = "orion_344"  # Valid sender agent (different to avoid self-mention)
    test_message = "Quick test: What is 2+2? Just answer with the number."

    # Verify OPENAI_API_KEY is set
    if not os.getenv("OPENAI_API_KEY"):
        print(" OPENAI_API_KEY not found in environment")
        print("   Set it in your .env file or environment")
        return False

    # Start the monitor in a subprocess
    print(f" Starting OpenAI Agents SDK monitor for @{agent_name}...")

    base_dir = Path(__file__).resolve().parent.parent
    venv_python = base_dir / ".venv" / "bin" / "python"
    config_path = base_dir / "configs" / "agents" / f"{agent_name}.json"

    if not config_path.exists():
        print(f" Agent config not found: {config_path}")
        return False

    # Start monitor process
    monitor_cmd = [
        str(venv_python),
        "-m",
        "ax_agent_studio.monitors.openai_agents_monitor",
        agent_name,
        "--config",
        str(config_path),
        "--model",
        "gpt-4o-mini",
    ]

    print(f"   Command: {' '.join(monitor_cmd)}\n")

    # Set PYTHONPATH to include src
    env = os.environ.copy()
    env["PYTHONPATH"] = str(base_dir / "src")

    monitor_process = subprocess.Popen(
        monitor_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )

    try:
        # Wait for monitor to initialize (watch for "Starting FIFO queue manager")
        print("⏳ Waiting for monitor to initialize...")
        initialized = False
        timeout = 30
        start_time = time.time()

        while time.time() - start_time < timeout:
            if monitor_process.poll() is not None:
                # Process died
                print(" Monitor process died during initialization")
                stdout, _ = monitor_process.communicate()
                print(f"Monitor output:\n{stdout}")
                return False

            # Give it time to start
            await asyncio.sleep(2)

            # Check if likely initialized (after reasonable time)
            if time.time() - start_time > 10:
                initialized = True
                break

        if not initialized:
            print(" Monitor did not initialize in time")
            monitor_process.terminate()
            return False

        print(" Monitor appears to be running\n")

        # Send test message from different handle
        success = await send_test_message(sender_handle, agent_name, test_message)

        if success:
            print("\n End-to-end test PASSED!")
            print(f"    Monitor started successfully")
            print(f"    Message sent from @{sender_handle}")
            print(f"    @{agent_name} processed and responded")
            return True
        else:
            print("\n Test FAILED: No response detected")
            print("   Fetching monitor logs for debugging...")
            return False

    finally:
        # Clean up monitor process and show its output
        print("\n Cleaning up monitor process...")

        # Get monitor output before terminating
        monitor_process.terminate()
        try:
            stdout, _ = monitor_process.communicate(timeout=5)
            print("\n Monitor Output:")
            print("=" * 60)
            print(stdout)
            print("=" * 60)
            print(" Monitor process terminated")
        except subprocess.TimeoutExpired:
            monitor_process.kill()
            stdout, _ = monitor_process.communicate()
            print("\n Monitor Output:")
            print("=" * 60)
            print(stdout)
            print("=" * 60)
            print("  Monitor process killed (did not terminate gracefully)")


if __name__ == "__main__":
    try:
        result = asyncio.run(test_openai_agents_monitor())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\nTest cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"\n Test failed with exception: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
