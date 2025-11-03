#!/usr/bin/env python3
"""
End-to-End tests for Agent Name Independence

Verifies that agent filenames do NOT need to match the agent name in the URL.
The agent_name should ALWAYS be extracted from the MCP server URL, not the filename.

Run with: PYTHONPATH=src python tests/test_agent_name_independence_e2e.py
"""

import json
import tempfile
import time
from pathlib import Path
from typing import Dict

import requests


class AgentNameIndependenceE2ETest:
    """E2E tests that filenames don't need to match agent names"""

    def __init__(self, dashboard_url: str = "http://127.0.0.1:8000"):
        self.dashboard_url = dashboard_url
        self.api_base = dashboard_url + "/api"

    def test_filename_mismatch_allowed(self) -> bool:
        """Test that filename can be different from agent name in URL"""
        print("\n" + "=" * 70)
        print("TEST: Filename Mismatch Allowed (Real-World Example)")
        print("=" * 70)

        # Use real-world example: local_ghost.json has agent_name ghost_ray_363
        # This proves filename != agent_name is already working!

        response = requests.get(f"{self.api_base}/configs")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        configs = response.json()["configs"]

        # Find the real mismatched config
        ghost_config = None
        for config in configs:
            if config['filename'] == 'local_ghost.json' and config['agent_name'] == 'ghost_ray_363':
                ghost_config = config
                break

        assert ghost_config is not None, \
            "Real-world example not found: local_ghost.json should have agent_name ghost_ray_363"

        # CRITICAL: agent_name must be extracted from URL, not filename
        assert ghost_config['agent_name'] == 'ghost_ray_363', \
            f"Expected agent_name 'ghost_ray_363' from URL, got '{ghost_config['agent_name']}'"

        assert ghost_config['filename'] == 'local_ghost.json', \
            f"Expected filename 'local_ghost.json', got '{ghost_config['filename']}'"

        # Verify agent name is in the URL
        assert '/mcp/agents/ghost_ray_363' in ghost_config['server_url'], \
            f"URL should contain '/mcp/agents/ghost_ray_363', got '{ghost_config['server_url']}'"

        print(f"✅ Real-world config with mismatched filename:")
        print(f"   Filename: {ghost_config['filename']}")
        print(f"   Agent name: {ghost_config['agent_name']}")
        print(f"   URL: {ghost_config['server_url']}")
        print(f"   ✅ Agent name correctly extracted from URL, NOT filename!")

        return True

    def test_agent_name_from_url_required(self) -> bool:
        """Test that agent_name is always extracted from URL"""
        print("\n" + "=" * 70)
        print("TEST: Agent Name From URL Required")
        print("=" * 70)

        # Get a known config and verify agent_name matches URL
        response = requests.get(f"{self.api_base}/configs")
        configs = response.json()["configs"]

        verified_count = 0
        for config in configs:
            if config.get('server_url') and '/mcp/agents/' in config['server_url']:
                # Extract expected agent_name from URL
                url_parts = config['server_url'].split('/mcp/agents/')
                if len(url_parts) > 1:
                    expected_agent_name = url_parts[1].strip()

                    # Verify it matches the config's agent_name
                    assert config['agent_name'] == expected_agent_name, \
                        f"agent_name '{config['agent_name']}' doesn't match URL '{expected_agent_name}' " \
                        f"in {config['filename']}"

                    verified_count += 1
                    print(f"✅ {config['filename']}: agent_name correctly extracted from URL")

        assert verified_count > 0, "No configs with MCP URLs found to verify"
        print(f"✅ Verified {verified_count} configs have agent_name matching their URLs")

        return True

    def test_legacy_format_requires_explicit_agent_name(self) -> bool:
        """Test that legacy format configs must have explicit agent_name (no filename fallback)"""
        print("\n" + "=" * 70)
        print("TEST: Legacy Format Requires Explicit Agent Name")
        print("=" * 70)

        # Create a legacy config WITHOUT agent_name field
        # This should be REJECTED (not fall back to filename)
        legacy_config_bad = {
            "server_url": "http://localhost:8002",
            "oauth_url": "http://localhost:8001"
            # NOTE: No "agent_name" field!
        }

        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.json',
            prefix='bad_legacy_',
            dir='configs/agents',
            delete=False
        ) as f:
            temp_path = Path(f.name)
            json.dump(legacy_config_bad, f)

        try:
            # Give dashboard time to reload configs
            time.sleep(1)

            # Fetch configs from API
            response = requests.get(f"{self.api_base}/configs")
            configs = response.json()["configs"]

            # This config should NOT appear (should be skipped)
            bad_config_found = any(
                'bad_legacy' in config['filename']
                for config in configs
            )

            assert not bad_config_found, \
                "Config without agent_name was loaded - should have been rejected!"

            print("✅ Legacy config without explicit agent_name was correctly rejected")
            print("   (not using filename as fallback)")

            return True

        finally:
            # Cleanup
            if temp_path.exists():
                temp_path.unlink()
            time.sleep(1)

    def run_all_tests(self) -> bool:
        """Run all E2E tests"""
        print("\n" + "=" * 70)
        print("AGENT NAME INDEPENDENCE E2E TESTS")
        print("=" * 70)
        print(f"Dashboard URL: {self.dashboard_url}")
        print(f"API Base: {self.api_base}")

        try:
            # Check if dashboard is running
            response = requests.get(f"{self.api_base}/health", timeout=5)
            if response.status_code != 200:
                print("❌ Dashboard not healthy, cannot run tests")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Dashboard not reachable: {e}")
            print(f"   Make sure dashboard is running on {self.dashboard_url}")
            return False

        tests = [
            self.test_filename_mismatch_allowed,
            self.test_agent_name_from_url_required,
            self.test_legacy_format_requires_explicit_agent_name,
        ]

        passed = 0
        failed = 0

        for test in tests:
            try:
                if test():
                    passed += 1
                else:
                    failed += 1
                    print(f"❌ Test failed: {test.__name__}")
            except AssertionError as e:
                failed += 1
                print(f"❌ Test failed: {test.__name__}")
                print(f"   Assertion: {e}")
            except Exception as e:
                failed += 1
                print(f"❌ Test error: {test.__name__}")
                print(f"   Error: {e}")

        print("=" * 70)
        print(f"RESULTS: {passed} passed, {failed} failed")
        print("=" * 70)

        return failed == 0


if __name__ == "__main__":
    import sys

    tester = AgentNameIndependenceE2ETest()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
