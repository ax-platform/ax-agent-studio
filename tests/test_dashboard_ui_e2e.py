#!/usr/bin/env python3
"""
E2E test for dashboard UI elements

Tests that critical UI components work correctly and prevents regressions.
This includes Test Sender dropdown, framework registry loading, etc.

Run: python tests/test_dashboard_ui_e2e.py
"""

import os
import sys
import time
import requests
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


class DashboardUITest:
    """Test dashboard UI elements work correctly"""

    def __init__(self):
        self.dashboard_url = "http://localhost:8000"
        self.api_base = f"{self.dashboard_url}/api"
        self.driver = None

    def setup_driver(self):
        """Setup headless Chrome driver"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(10)

    def teardown_driver(self):
        """Close driver"""
        if self.driver:
            self.driver.quit()

    def test_test_sender_dropdown(self) -> bool:
        """Test that Test Sender Agent dropdown loads correctly"""
        print(f"\n{'=' * 70}")
        print("Testing Test Sender Agent Dropdown")
        print(f"{'=' * 70}")

        try:
            # Load dashboard
            self.driver.get(self.dashboard_url)
            print("✅ Dashboard loaded")

            # Wait for configs to load (indicated by test-sender-select being populated)
            wait = WebDriverWait(self.driver, 10)
            test_sender_select = wait.until(
                EC.presence_of_element_located((By.ID, "test-sender-select"))
            )

            # Check dropdown exists
            if not test_sender_select:
                print("❌ Test Sender dropdown not found")
                return False

            print("✅ Test Sender dropdown element exists")

            # Get all options
            options = test_sender_select.find_elements(By.TAG_NAME, "option")
            option_texts = [opt.text for opt in options]

            print(f"   Found {len(options)} options: {option_texts}")

            # Verify "Auto (first available)" is first option
            if len(options) == 0:
                print("❌ Test Sender dropdown has no options")
                return False

            if "Auto (first available)" not in options[0].text:
                print(f"❌ First option is not 'Auto (first available)': {options[0].text}")
                return False

            print("✅ 'Auto (first available)' is first option")

            # Verify agent names are loaded
            if len(options) == 1:
                print("⚠️  Only 'Auto' option found - no agent names loaded")
                print("   This might be OK if no agents configured")
            else:
                # Get agent names from API
                response = requests.get(f"{self.api_base}/configs")
                if response.status_code == 200:
                    configs = response.json().get("configs", [])
                    agent_names = sorted(list(set([c["agent_name"] for c in configs])))

                    print(f"   API returned {len(agent_names)} unique agents: {agent_names}")

                    # Verify dropdown has all agent names (skip first "Auto" option)
                    dropdown_agents = option_texts[1:]

                    if sorted(dropdown_agents) == agent_names:
                        print("✅ All agent names present in dropdown")
                    else:
                        print(f"❌ Agent names mismatch")
                        print(f"   Expected: {agent_names}")
                        print(f"   Got: {dropdown_agents}")
                        return False
                else:
                    print(f"⚠️  Could not verify agent names (API returned {response.status_code})")

            # Test selection persistence (localStorage)
            if len(options) > 1:
                # Select second option (first real agent)
                test_agent = options[1].get_attribute("value")
                print(f"\n   Testing selection persistence with agent: {test_agent}")

                # Select the agent
                self.driver.execute_script(
                    "arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('change'));",
                    test_sender_select,
                    test_agent,
                )

                # Check localStorage was updated
                stored_value = self.driver.execute_script(
                    "return localStorage.getItem('testSenderAgent');"
                )

                if stored_value == test_agent:
                    print(f"✅ Selection persisted to localStorage: {stored_value}")
                else:
                    print(f"❌ localStorage not updated correctly: {stored_value} vs {test_agent}")
                    return False

                # Reload page and verify selection is restored
                self.driver.refresh()
                time.sleep(2)

                test_sender_select = self.driver.find_element(By.ID, "test-sender-select")
                current_value = test_sender_select.get_attribute("value")

                if current_value == test_agent:
                    print(f"✅ Selection restored after page reload: {current_value}")
                else:
                    print(f"❌ Selection not restored: {current_value} vs {test_agent}")
                    return False

            print(f"\n✅ Test Sender dropdown test PASSED")
            return True

        except Exception as e:
            print(f"❌ Test Sender dropdown test FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False

    def test_framework_registry_loads(self) -> bool:
        """Test that framework registry loads correctly"""
        print(f"\n{'=' * 70}")
        print("Testing Framework Registry Loading")
        print(f"{'=' * 70}")

        try:
            # Load dashboard
            self.driver.get(self.dashboard_url)
            print("✅ Dashboard loaded")

            # Wait for monitor type dropdown to be populated
            wait = WebDriverWait(self.driver, 10)
            monitor_select = wait.until(
                EC.presence_of_element_located((By.ID, "monitor-type-select"))
            )

            # Get all framework options
            options = monitor_select.find_elements(By.TAG_NAME, "option")
            framework_ids = [opt.get_attribute("value") for opt in options]

            print(f"   Found {len(options)} frameworks: {framework_ids}")

            # Verify at least some expected frameworks exist
            expected_frameworks = ["echo", "langgraph", "openai_agents_sdk"]
            for fw in expected_frameworks:
                if fw in framework_ids:
                    print(f"✅ Framework '{fw}' loaded")
                else:
                    print(f"⚠️  Framework '{fw}' not found")

            # Check that framework registry is available in JavaScript
            has_registry = self.driver.execute_script("return frameworkRegistry !== null;")
            if has_registry:
                print("✅ Framework registry loaded in JavaScript")
            else:
                print("❌ Framework registry not available in JavaScript")
                return False

            print(f"\n✅ Framework registry test PASSED")
            return True

        except Exception as e:
            print(f"❌ Framework registry test FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False

    def run_all_tests(self) -> bool:
        """Run all UI tests"""
        try:
            self.setup_driver()

            results = []

            # Test 1: Test Sender dropdown
            success = self.test_test_sender_dropdown()
            results.append(("Test Sender Dropdown", success))

            # Test 2: Framework registry
            success = self.test_framework_registry_loads()
            results.append(("Framework Registry", success))

            # Summary
            print(f"\n{'=' * 70}")
            print("DASHBOARD UI TEST SUMMARY")
            print(f"{'=' * 70}")

            all_passed = True
            for test_name, success in results:
                status = "✅ PASS" if success else "❌ FAIL"
                print(f"{status}: {test_name}")
                if not success:
                    all_passed = False

            return all_passed

        except Exception as e:
            print(f"\n❌ Test suite failed with exception: {e}")
            import traceback
            traceback.print_exc()
            return False

        finally:
            self.teardown_driver()


def main():
    """Main test runner"""
    print("=" * 70)
    print("Dashboard UI E2E Test")
    print("=" * 70)
    print()
    print("This test verifies critical UI components work correctly")
    print()
    print("Prerequisites:")
    print("  1. Dashboard running on http://localhost:8000")
    print("  2. Chrome/Chromium browser installed")
    print("  3. ChromeDriver installed (pip install selenium)")
    print("  4. At least one agent config exists")
    print()

    # Check dashboard
    try:
        response = requests.get("http://localhost:8000", timeout=5)
        if response.status_code != 200:
            print("❌ Dashboard not responding correctly")
            sys.exit(1)
    except requests.exceptions.RequestException:
        print("❌ Dashboard is not running on http://localhost:8000")
        print("   Start it with: python scripts/start_dashboard.py")
        sys.exit(1)

    print("✅ Dashboard is running\n")

    # Run tests
    test = DashboardUITest()
    success = test.run_all_tests()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
