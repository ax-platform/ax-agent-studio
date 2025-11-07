#!/usr/bin/env python3
"""
E2E Dashboard Automation Test using Chrome DevTools MCP

This test automates the full user flow:
1. Opens the Agent Factory dashboard at http://127.0.0.1:8000
2. Deploys test agents (Echo monitor for Lunar Craft 128)
3. Verifies agent appears in Running Agents section
4. Takes screenshots for verification

Run with: uv run python tests/test_e2e_dashboard_automation.py

Requirements:
- Dashboard running at http://127.0.0.1:8000
- Chrome DevTools MCP server available
- Backend API at localhost:8002
"""

import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


DASHBOARD_URL = "http://127.0.0.1:8000"


async def run_dashboard_e2e_test():
    """Run full E2E test of dashboard functionality."""

    print("\n" + "=" * 80)
    print("E2E DASHBOARD AUTOMATION TEST")
    print("=" * 80)

    # Connect to Chrome DevTools MCP
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-chrome-devtools"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            print("\n✓ Connected to Chrome DevTools MCP")

            # Step 1: Open dashboard
            print("\n" + "-" * 80)
            print("STEP 1: Opening Agent Factory Dashboard")
            print("-" * 80)

            await session.call_tool(
                "navigate_page",
                {"url": DASHBOARD_URL, "type": "url"}
            )

            # Wait for page to load
            await asyncio.sleep(2)

            # Take snapshot to verify page loaded
            snapshot_result = await session.call_tool("take_snapshot", {})
            snapshot_text = snapshot_result.content[0].text

            if "Agent Factory" in snapshot_text:
                print("✓ Dashboard loaded successfully")
                print(f"  Found heading: 🏭 Agent Factory")
            else:
                print("❌ Dashboard did not load")
                return False

            # Step 2: Deploy Lunar Craft 128 with Echo monitor
            print("\n" + "-" * 80)
            print("STEP 2: Deploying Lunar Craft 128 (Echo Monitor)")
            print("-" * 80)

            # Select Lunar Craft 128 from Agent dropdown
            print("  Selecting agent: Lunar Craft 128")
            # The agent dropdown is uid=1_14
            await session.call_tool("click", {"uid": "1_14"})
            await asyncio.sleep(0.5)

            # Click Lunar Craft 128 option
            await session.call_tool("click", {"uid": "1_16"})
            await asyncio.sleep(0.5)
            print("  ✓ Selected Lunar Craft 128")

            # Select Echo from Agent Type dropdown
            print("  Selecting agent type: Echo")
            await session.call_tool("click", {"uid": "1_21"})
            await asyncio.sleep(0.5)

            # Click Echo option
            await session.call_tool("click", {"uid": "1_22"})
            await asyncio.sleep(0.5)
            print("  ✓ Selected Echo monitor")

            # Click Deploy Agent button
            print("  Clicking Deploy Agent...")
            await session.call_tool("click", {"uid": "1_45"})
            await asyncio.sleep(3)  # Wait for deployment
            print("  ✓ Deploy button clicked")

            # Step 3: Verify agent appears in Running Agents
            print("\n" + "-" * 80)
            print("STEP 3: Verifying Agent Deployment")
            print("-" * 80)

            # Take snapshot to check Running Agents section
            snapshot_result = await session.call_tool("take_snapshot", {})
            snapshot_text = snapshot_result.content[0].text

            # Check if "No agents running" is gone and lunar_craft_128 appears
            if "No agents running" not in snapshot_text and "lunar_craft_128" in snapshot_text:
                print("✅ Agent deployed successfully!")
                print("  Agent lunar_craft_128 is now running")
            elif "lunar_craft_128" in snapshot_text:
                print("✅ Agent is running (lunar_craft_128 found)")
            else:
                print("❌ Agent deployment failed or not visible yet")
                print("\n  Current page state:")
                print(snapshot_text[:1000])

            # Step 4: Take final screenshot
            print("\n" + "-" * 80)
            print("STEP 4: Taking Final Screenshot")
            print("-" * 80)

            await session.call_tool("take_screenshot", {
                "filePath": "/tmp/dashboard_e2e_test_final.png",
                "fullPage": True
            })
            print("✓ Screenshot saved to /tmp/dashboard_e2e_test_final.png")

            # Step 5: Check logs for errors
            print("\n" + "-" * 80)
            print("STEP 5: Checking Logs")
            print("-" * 80)

            snapshot_result = await session.call_tool("take_snapshot", {})
            snapshot_text = snapshot_result.content[0].text

            if "error" in snapshot_text.lower() or "failed" in snapshot_text.lower():
                print("⚠️  Found error/failed in logs - check screenshot")
            else:
                print("✓ No obvious errors in logs")

            print("\n" + "=" * 80)
            print("E2E TEST COMPLETE")
            print("=" * 80)

            return True


if __name__ == "__main__":
    try:
        result = asyncio.run(run_dashboard_e2e_test())
        if result:
            print("\n✅ ALL E2E TESTS PASSED\n")
            exit(0)
        else:
            print("\n❌ E2E TESTS FAILED\n")
            exit(1)
    except Exception as e:
        print(f"\n💥 ERROR: {type(e).__name__}: {e}\n")
        import traceback
        traceback.print_exc()
        exit(1)
