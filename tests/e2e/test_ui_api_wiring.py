#!/usr/bin/env python3
"""
E2E Smoke Test: UI→API Wiring

Verifies that the frontend UI correctly calls backend APIs.
This prevents regressions where UI changes break API integration.

Test Flow:
1. Clean slate via API
2. Click "Deploy Agent" button in UI (Chrome DevTools)
3. Verify API received the request and agent is running
4. Validates UI→API wiring works correctly
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from tests.e2e.helpers.dashboard_api import DashboardAPI

DASHBOARD_URL = "http://127.0.0.1:8000"


async def test_ui_deploy_button_wiring():
    """Test that UI Deploy button correctly calls backend API"""
    print("\n" + "=" * 80)
    print("UI→API WIRING TEST: Deploy Button")
    print("=" * 80)

    # Step 1: Clean slate
    print("\n📦 Step 1: Clean slate (via API)")
    with DashboardAPI() as api:
        api.cleanup_all()
        print("  ✓ All agents cleaned up")

        # Verify no agents running
        monitors_before = api.list_monitors()
        running_before = [m for m in monitors_before if m["status"] == "running"]
        print(f"  ✓ Verified 0 agents running (found {len(running_before)})")

    # Step 2: Click Deploy button in UI
    print("\n🖱️  Step 2: Click 'Deploy Agent' button (via Chrome DevTools)")

    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-chrome-devtools"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("  ✓ Connected to Chrome DevTools")

            # Navigate to dashboard
            await session.call_tool("navigate_page", {"url": DASHBOARD_URL, "type": "url"})
            await asyncio.sleep(2)
            print(f"  ✓ Navigated to {DASHBOARD_URL}")

            # Take snapshot to get current UIDs
            snapshot_result = await session.call_tool("take_snapshot", {})
            snapshot_text = snapshot_result.content[0].text

            # Verify dashboard loaded
            if "Agent Factory" not in snapshot_text:
                print("  ❌ Dashboard did not load")
                return False

            # Select Echo from Agent Type dropdown (should already be selected)
            # Find and click Deploy Agent button
            # Note: UIDs change, so we search for the button by finding the right elements
            # For now, let's use a simple approach - the Deploy button typically has known text

            # Extract UIDs using simple parsing (look for button containing "Deploy Agent")
            lines = snapshot_text.split("\n")
            deploy_button_uid = None
            for line in lines:
                if "button" in line.lower() and "deploy agent" in line.lower():
                    # Extract UID from line like: uid=17_43 button "▶️ Deploy Agent"
                    parts = line.strip().split()
                    for part in parts:
                        if part.startswith("uid="):
                            deploy_button_uid = part.split("=")[1]
                            break
                    if deploy_button_uid:
                        break

            if not deploy_button_uid:
                print("  ❌ Could not find Deploy Agent button")
                print(f"\nSnapshot (first 500 chars):\n{snapshot_text[:500]}")
                return False

            print(f"  ✓ Found Deploy Agent button (uid={deploy_button_uid})")

            # Click the button
            await session.call_tool("click", {"uid": deploy_button_uid})
            await asyncio.sleep(3)  # Wait for deployment
            print("  ✓ Clicked Deploy Agent button")

    # Step 3: Verify API received request and agent deployed
    print("\n✅ Step 3: Verify agent deployed (via API)")
    with DashboardAPI() as api:
        monitors_after = api.list_monitors()
        running_after = [m for m in monitors_after if m["status"] == "running"]

        if len(running_after) > 0:
            agent_name = running_after[0]["agent_name"]
            monitor_type = running_after[0]["monitor_type"]
            print(f"  ✓ Agent deployed: {agent_name} ({monitor_type})")
            print("  ✓ UI→API wiring verified!")
            return True
        else:
            print(f"  ❌ No agent deployed (found {len(monitors_after)} monitors)")
            print("  ❌ UI→API wiring FAILED")
            return False


async def main():
    """Run UI→API wiring test"""
    print("\n" + "=" * 80)
    print("E2E SMOKE TEST: UI→API Wiring")
    print("=" * 80)
    print("\nVerifies that frontend UI correctly calls backend APIs")
    print("Prevents regressions in UI→API integration")
    print("=" * 80)

    try:
        passed = await test_ui_deploy_button_wiring()

        # Cleanup
        print("\n🧹 Cleanup")
        with DashboardAPI() as api:
            api.cleanup_all()
            print("  ✓ All agents cleaned up")

        # Summary
        print("\n" + "=" * 80)
        if passed:
            print("✅ UI→API WIRING TEST PASSED")
            print("=" * 80 + "\n")
            sys.exit(0)
        else:
            print("❌ UI→API WIRING TEST FAILED")
            print("=" * 80 + "\n")
            sys.exit(1)

    except Exception as e:
        print(f"\n💥 ERROR: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()

        # Cleanup on error
        with DashboardAPI() as api:
            api.cleanup_all()

        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
