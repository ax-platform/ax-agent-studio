#!/usr/bin/env python3
"""
Kill Switch for Agent Factory

Usage:
    python kill_switch.py on      # Pause all agents (processing stopped)
    python kill_switch.py off     # Resume agents (processing resumes)
    python kill_switch.py kill    # KILL all monitor processes (stops burning money!)
    python kill_switch.py status  # Check kill switch status
"""

import subprocess
import sys
from pathlib import Path

KILL_SWITCH_FILE = Path("data/KILL_SWITCH")


def activate():
    """Activate kill switch - all agents will pause processing"""
    KILL_SWITCH_FILE.parent.mkdir(exist_ok=True)
    KILL_SWITCH_FILE.touch()
    print(" KILL SWITCH ACTIVATED")
    print("   All agents are now PAUSED")
    print("   Run 'python kill_switch.py off' to resume")
    print("   Run 'python kill_switch.py kill' to STOP all processes")


def deactivate():
    """Deactivate kill switch - agents will resume processing"""
    if KILL_SWITCH_FILE.exists():
        KILL_SWITCH_FILE.unlink()
        print(" KILL SWITCH DEACTIVATED")
        print("   Agents will resume processing")
    else:
        print("ℹ  Kill switch was already off")


def kill_all_monitors():
    """Kill all monitor processes immediately"""
    print(" KILLING ALL MONITORS...")

    try:
        # Kill all monitor processes
        result = subprocess.run(
            ["pkill", "-9", "-f", "ax_agent_studio.monitors"], capture_output=True, text=True
        )

        # Check what's left
        check = subprocess.run(
            ["pgrep", "-f", "ax_agent_studio.monitors"], capture_output=True, text=True
        )

        if check.stdout.strip():
            print("  Some monitors may still be running:")
            print(check.stdout)
        else:
            print(" All monitors killed - no processes burning money!")

        # Also activate the kill switch to prevent restarts
        KILL_SWITCH_FILE.parent.mkdir(exist_ok=True)
        KILL_SWITCH_FILE.touch()
        print(" Kill switch activated to prevent restarts")

    except Exception as e:
        print(f" Error killing monitors: {e}")
        print(" Try manually: pkill -9 -f ax_agent_studio.monitors")


def status():
    """Check kill switch status and show running monitors"""
    if KILL_SWITCH_FILE.exists():
        print(" KILL SWITCH: ACTIVE (agents paused)")
    else:
        print(" KILL SWITCH: INACTIVE (agents running)")

    # Show running monitors
    print("\n Running monitors:")
    try:
        result = subprocess.run(
            ["pgrep", "-fl", "ax_agent_studio.monitors"], capture_output=True, text=True
        )
        if result.stdout.strip():
            for line in result.stdout.strip().split("\n"):
                print(f"   • {line}")
        else:
            print("   (none)")
    except Exception:
        print("   (could not check)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "on":
        activate()
    elif command == "off":
        deactivate()
    elif command == "kill":
        kill_all_monitors()
    elif command == "status":
        status()
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)
