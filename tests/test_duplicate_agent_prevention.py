#!/usr/bin/env python3
"""
Test: Duplicate Agent Prevention

Ensures backend rejects attempts to start a second monitor
for an agent that already has one running.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.e2e.helpers.dashboard_api import DashboardAPI


def test_duplicate_agent_prevention():
    """Verify backend rejects starting duplicate agent monitors"""
    print("\n" + "=" * 80)
    print("TEST: Duplicate Agent Prevention")
    print("=" * 80)

    with DashboardAPI() as api:
        try:
            # 1. Clean slate
            print("\n1. Cleaning up...")
            api.cleanup_all()
            print("   ✓ Clean")

            # 2. Start first monitor
            print("\n2. Starting first monitor for ghost_ray_363...")
            result1 = api.start_monitor(
                agent_name="ghost_ray_363",
                config_path="configs/agents/local_ghost.json",
                monitor_type="echo",
            )
            monitor_id_1 = result1["monitor_id"]
            print(f"   ✓ First monitor started: {monitor_id_1}")

            # 3. Attempt to start second monitor (should fail)
            print("\n3. Attempting to start duplicate monitor for ghost_ray_363...")
            try:
                api.start_monitor(
                    agent_name="ghost_ray_363",
                    config_path="configs/agents/local_ghost.json",
                    monitor_type="ollama",
                    model="gpt-oss:latest",
                )
                print("   ❌ FAILED: Second monitor was allowed (should be rejected)")
                return False
            except Exception as e:
                error_msg = str(e)
                if "409" in error_msg and "already has a running monitor" in error_msg:
                    print("   ✓ Correctly rejected with HTTP 409")
                    print(f"   ✓ Error message: {error_msg}")
                else:
                    print(f"   ❌ Wrong error type: {error_msg}")
                    return False

            # 4. Verify first monitor still running
            print("\n4. Verifying first monitor still running...")
            monitors = api.list_monitors()
            ghost_monitors = [m for m in monitors if m["agent_name"] == "ghost_ray_363"]
            if len(ghost_monitors) == 1 and ghost_monitors[0]["id"] == monitor_id_1:
                print("   ✓ First monitor still running correctly")
            else:
                print(f"   ❌ Unexpected monitor state: {len(ghost_monitors)} monitors found")
                return False

            # 5. Stop first monitor
            print("\n5. Stopping first monitor...")
            api.kill_all_monitors()
            print("   ✓ Stopped")

            # 6. Now starting second monitor should work
            print("\n6. Starting monitor after first one stopped...")
            result2 = api.start_monitor(
                agent_name="ghost_ray_363",
                config_path="configs/agents/local_ghost.json",
                monitor_type="ollama",
                model="gpt-oss:latest",
            )
            monitor_id_2 = result2["monitor_id"]
            print(f"   ✓ New monitor started successfully: {monitor_id_2}")

            # 7. Verify it's a NEW monitor (different ID from first one)
            print("\n7. Verifying it's a new monitor process...")
            if not monitor_id_2:
                print("   ❌ Monitor ID is empty")
                return False
            if monitor_id_2 == monitor_id_1:
                print(f"   ❌ Same monitor ID as before: {monitor_id_2}")
                print("   (Should be a new monitor, not reusing old one)")
                return False
            print(f"   ✓ New monitor ID confirmed: {monitor_id_2}")
            print(f"   ✓ Different from first monitor: {monitor_id_1}")

            print("\n" + "=" * 80)
            print("✅ TEST PASSED: Duplicate agent prevention working correctly")
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
    success = test_duplicate_agent_prevention()
    sys.exit(0 if success else 1)
