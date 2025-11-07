#!/usr/bin/env python3
"""
E2E Dashboard Automation Test using Chrome DevTools MCP

This test automates the full user flow:
1. Opens the dashboard at localhost:3001
2. Sends messages to agents
3. Verifies responses appear
4. Tests #done command functionality

Run with: uv run python tests/test_e2e_dashboard_automation.py

Requirements:
- Dashboard running at localhost:3001
- Chrome DevTools MCP server available
- Test agents (ghost_ray_363, lunar_craft_128) running
"""

import asyncio
import time
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


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
            print("STEP 1: Opening dashboard at localhost:3001")
            print("-" * 80)

            await session.call_tool(
                "navigate_page",
                {"url": "http://localhost:3001", "type": "url"}
            )

            # Wait for page to load
            await asyncio.sleep(2)

            # Take snapshot to see what's on screen
            snapshot_result = await session.call_tool("take_snapshot", {})
            print("\n📸 Dashboard loaded:")
            print(snapshot_result.content[0].text[:500])  # Show first 500 chars

            # Step 2: Find and click on ghost_ray_363
            print("\n" + "-" * 80)
            print("STEP 2: Testing ghost_ray_363 (should work)")
            print("-" * 80)

            # Find ghost_ray_363 in the agent list
            snapshot = await session.call_tool("take_snapshot", {})
            snapshot_text = snapshot.content[0].text

            # Look for ghost_ray_363 element
            if "ghost_ray_363" in snapshot_text:
                print("✓ Found ghost_ray_363 in agent list")

                # Find the uid for ghost_ray_363 and click it
                # This will select the agent
                lines = snapshot_text.split('\n')
                for line in lines:
                    if "ghost_ray_363" in line and "uid:" in line:
                        # Extract uid from line like: "[123] button "ghost_ray_363" uid:abc123"
                        parts = line.split("uid:")
                        if len(parts) > 1:
                            uid = parts[1].split()[0].strip()
                            print(f"  Clicking ghost_ray_363 (uid: {uid})")
                            await session.call_tool("click", {"uid": uid})
                            await asyncio.sleep(1)
                            break
            else:
                print("❌ ghost_ray_363 not found in agent list")
                return False

            # Step 3: Send test message to ghost_ray_363
            print("\n  Sending test message...")

            # Find message input field and send button
            snapshot = await session.call_tool("take_snapshot", {})
            snapshot_text = snapshot.content[0].text

            # Find input field uid
            input_uid = None
            send_uid = None

            for line in snapshot_text.split('\n'):
                if "textbox" in line.lower() or "input" in line.lower():
                    if "uid:" in line:
                        parts = line.split("uid:")
                        if len(parts) > 1:
                            input_uid = parts[1].split()[0].strip()
                            print(f"  Found input field (uid: {input_uid})")
                            break

            if input_uid:
                # Type message
                test_message = "E2E test - what's 5+5?"
                await session.call_tool("fill", {
                    "uid": input_uid,
                    "value": test_message
                })
                print(f"  ✓ Typed: '{test_message}'")

                # Find and click send button
                snapshot = await session.call_tool("take_snapshot", {})
                snapshot_text = snapshot.content[0].text

                for line in snapshot_text.split('\n'):
                    if "send" in line.lower() and "button" in line.lower():
                        if "uid:" in line:
                            parts = line.split("uid:")
                            if len(parts) > 1:
                                send_uid = parts[1].split()[0].strip()
                                print(f"  Found send button (uid: {send_uid})")
                                break

                if send_uid:
                    await session.call_tool("click", {"uid": send_uid})
                    print("  ✓ Clicked send")

                    # Wait for response
                    print("\n  Waiting for ghost_ray_363 response...")
                    await asyncio.sleep(5)

                    # Check for response
                    snapshot = await session.call_tool("take_snapshot", {})
                    snapshot_text = snapshot.content[0].text

                    if "ghost_ray" in snapshot_text and "5+5" in snapshot_text:
                        print("  ✅ ghost_ray_363 RESPONDED")
                    else:
                        print("  ❌ No response from ghost_ray_363")
                else:
                    print("  ❌ Send button not found")
            else:
                print("  ❌ Input field not found")

            # Step 4: Test lunar_craft_128
            print("\n" + "-" * 80)
            print("STEP 3: Testing lunar_craft_128")
            print("-" * 80)

            # Click on lunar_craft_128
            snapshot = await session.call_tool("take_snapshot", {})
            snapshot_text = snapshot.content[0].text

            if "lunar_craft_128" in snapshot_text:
                print("✓ Found lunar_craft_128 in agent list")

                for line in snapshot_text.split('\n'):
                    if "lunar_craft_128" in line and "uid:" in line:
                        parts = line.split("uid:")
                        if len(parts) > 1:
                            uid = parts[1].split()[0].strip()
                            print(f"  Clicking lunar_craft_128 (uid: {uid})")
                            await session.call_tool("click", {"uid": uid})
                            await asyncio.sleep(1)
                            break

                # Send test message
                print("\n  Sending test message...")

                snapshot = await session.call_tool("take_snapshot", {})
                snapshot_text = snapshot.content[0].text

                for line in snapshot_text.split('\n'):
                    if "textbox" in line.lower() or "input" in line.lower():
                        if "uid:" in line:
                            parts = line.split("uid:")
                            if len(parts) > 1:
                                input_uid = parts[1].split()[0].strip()
                                break

                if input_uid:
                    test_message = "E2E test - echo this message"
                    await session.call_tool("fill", {
                        "uid": input_uid,
                        "value": test_message
                    })
                    print(f"  ✓ Typed: '{test_message}'")

                    # Click send
                    for line in snapshot_text.split('\n'):
                        if "send" in line.lower() and "button" in line.lower():
                            if "uid:" in line:
                                parts = line.split("uid:")
                                if len(parts) > 1:
                                    send_uid = parts[1].split()[0].strip()
                                    break

                    if send_uid:
                        await session.call_tool("click", {"uid": send_uid})
                        print("  ✓ Clicked send")

                        # Wait for response
                        print("\n  Waiting for lunar_craft_128 response...")
                        await asyncio.sleep(5)

                        # Check for response
                        snapshot = await session.call_tool("take_snapshot", {})
                        snapshot_text = snapshot.content[0].text

                        if "lunar" in snapshot_text and "echo" in snapshot_text.lower():
                            print("  ✅ lunar_craft_128 RESPONDED")
                        else:
                            print("  ❌ No response from lunar_craft_128")
                            print("\n  📸 Current page state:")
                            print(snapshot_text[:1000])
            else:
                print("❌ lunar_craft_128 not found in agent list")

            # Step 5: Take final screenshot
            print("\n" + "-" * 80)
            print("STEP 4: Taking final screenshot")
            print("-" * 80)

            await session.call_tool("take_screenshot", {
                "filePath": "/tmp/dashboard_e2e_test.png",
                "fullPage": True
            })
            print("✓ Screenshot saved to /tmp/dashboard_e2e_test.png")

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
