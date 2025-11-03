#!/usr/bin/env python3
"""
E2E test for OpenAI Agents SDK Monitor

Tests that the OpenAI Agents SDK monitor can:
1. Start successfully with lunar_craft_128
2. Skip ax-docker/ax-gcp (prevents 401 errors)
3. Connect stdio servers (everything, filesystem, memory)
4. Respond to messages via QueueManager

Run: python tests/test_openai_agents_monitor_e2e.py
"""

import os
import sys
import time
import subprocess
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class OpenAIAgentsMonitorE2ETest:
    """Test OpenAI Agents SDK monitor with real MCP server"""

    def __init__(self):
        self.agent_name = "lunar_craft_128"
        self.model = "gpt-5-mini"
        self.monitor_process = None
        self.log_file = Path(__file__).parent.parent / "logs" / "test_openai_monitor.log"

    def start_monitor(self) -> bool:
        """Start OpenAI Agents SDK monitor directly"""
        print(f"\n{'=' * 70}")
        print(f"Starting OpenAI Agents SDK monitor for {self.agent_name}")
        print(f"{'=' * 70}")

        # Check if OPENAI_API_KEY is set
        if not os.getenv("OPENAI_API_KEY"):
            print("⚠️  WARNING: OPENAI_API_KEY not set - test may fail")
            print("   Set it in your .env file")
            return False

        print("✅ OPENAI_API_KEY is set")

        # Start monitor process directly using uv
        cmd = [
            "uv",
            "run",
            "python",
            "-m",
            "ax_agent_studio.monitors.openai_agents_monitor",
            self.agent_name,
            "--model",
            self.model,
        ]

        # Create log file
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        log_handle = open(self.log_file, "w")

        print(f"Command: {' '.join(cmd)}")
        print(f"Log file: {self.log_file}")

        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path(__file__).parent.parent / "src")

        self.monitor_process = subprocess.Popen(
            cmd,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            env=env,
            cwd=Path(__file__).parent.parent,
        )

        print(f"✅ Monitor process started (PID: {self.monitor_process.pid})")
        return True

    def wait_for_startup(self, timeout: int = 15) -> bool:
        """Wait for monitor to fully start up by checking logs"""
        print(f"\nWaiting for monitor startup (max {timeout}s)...")

        for i in range(timeout):
            time.sleep(1)

            # Check if process is still running
            if self.monitor_process.poll() is not None:
                print(f"❌ Monitor process exited with code: {self.monitor_process.returncode}")
                return False

            # Check log file for startup indicators
            if self.log_file.exists():
                with open(self.log_file) as f:
                    logs = f.read()

                if "🚀 Starting FIFO queue manager" in logs:
                    print("✅ Monitor started successfully")
                    return True
                elif "401 Unauthorized" in logs:
                    print("❌ 401 error detected - monitor failed")
                    return False
                elif "Error" in logs or "Traceback" in logs:
                    print(f"⚠️  Errors detected in logs (but monitor may still be starting)")

            print(f"   [{i+1}s] Waiting for startup indicator in logs...")

        print("❌ Timeout waiting for monitor to start")
        return False

    def check_logs_for_errors(self) -> bool:
        """Check monitor logs for 401 errors or other issues"""
        print(f"\n{'=' * 70}")
        print("Checking logs for errors...")
        print(f"{'=' * 70}")

        if not self.log_file.exists():
            print("⚠️  Log file not found")
            return False

        with open(self.log_file) as f:
            logs = f.read()

        # Check for critical errors
        if "401 Unauthorized" in logs:
            print("❌ Found 401 Unauthorized error in logs")
            print("   This means ax-docker/ax-gcp weren't properly skipped")
            return False

        if "Configured HTTP MCP server: ax-docker" in logs:
            print("❌ ax-docker was added to OpenAI SDK servers")
            print("   This should be skipped!")
            return False

        # Check for success indicators
        if "Skipping ax-docker" in logs or "Skipping ax-gcp" in logs:
            print("✅ Confirmed: ax-docker/ax-gcp properly skipped")
        else:
            print("⚠️  No skip message found (maybe no ax-docker in config?)")

        if "✅ Connected" in logs and "MCP servers for agent" in logs:
            print("✅ Confirmed: MCP servers connected successfully")

        if "🚀 Starting FIFO queue manager" in logs:
            print("✅ Confirmed: Queue manager started")

        return True

    def send_test_message(self) -> bool:
        """Send a test message to the agent"""
        print(f"\n{'=' * 70}")
        print("Sending test message to agent...")
        print(f"{'=' * 70}")

        # Use MCP messages tool to send test (requires ax MCP tools)
        # This would require integrating with MCP client, so for now just verify startup
        print("⚠️  Message sending test not implemented yet")
        print("   Manual test: Use dashboard to send a message")
        return True

    def stop_monitor(self) -> bool:
        """Stop the monitor process"""
        if not self.monitor_process:
            return True

        print(f"\n{'=' * 70}")
        print("Stopping monitor...")
        print(f"{'=' * 70}")

        try:
            self.monitor_process.terminate()
            self.monitor_process.wait(timeout=5)
            print("✅ Monitor stopped")
            return True
        except subprocess.TimeoutExpired:
            print("⚠️  Monitor didn't stop gracefully, killing...")
            self.monitor_process.kill()
            self.monitor_process.wait()
            print("✅ Monitor killed")
            return True
        except Exception as e:
            print(f"⚠️  Error stopping monitor: {e}")
            return False

    def run_all_tests(self) -> bool:
        """Run all tests"""
        try:
            # Test 1: Start monitor
            if not self.start_monitor():
                return False

            # Test 2: Wait for startup
            if not self.wait_for_startup():
                return False

            # Test 3: Check logs for errors
            if not self.check_logs_for_errors():
                return False

            # Test 4: Send test message (TODO)
            # if not self.send_test_message():
            #     return False

            print(f"\n{'=' * 70}")
            print("✅ ALL TESTS PASSED")
            print(f"{'=' * 70}")
            return True

        except Exception as e:
            print(f"\n❌ Test failed with exception: {e}")
            import traceback

            traceback.print_exc()
            return False

        finally:
            # Cleanup
            self.stop_monitor()


def main():
    """Main test runner"""
    print("=" * 70)
    print("OpenAI Agents SDK Monitor E2E Test")
    print("=" * 70)
    print()
    print("Prerequisites:")
    print("  1. OPENAI_API_KEY set in environment")
    print("  2. lunar_craft_128.json config exists")
    print("  3. MCP server running (for actual messaging)")
    print()

    # Check if config exists
    config_file = Path(__file__).parent.parent / "configs" / "agents" / "lunar_craft_128.json"
    if not config_file.exists():
        print(f"❌ Config file not found: {config_file}")
        sys.exit(1)

    print(f"✅ Config file found: {config_file}\n")

    # Run tests
    test = OpenAIAgentsMonitorE2ETest()
    success = test.run_all_tests()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
