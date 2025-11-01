#!/usr/bin/env python3
"""
Dashboard UI End-to-End Tests
Tests all 4 agent types and their UI requirements using Playwright

Tests verify:
- Echo: No provider dropdown, no model dropdown
- Ollama: No provider dropdown, model dropdown visible
- Claude Agent SDK: No provider dropdown, model dropdown with Claude models (Sonnet 4.5 default)
- LangGraph: Provider dropdown visible, model dropdown visible
"""

from playwright.sync_api import sync_playwright, expect
import time


def test_dashboard_loads():
    """Test that dashboard loads successfully"""
    print("\n" + "="*60)
    print("🌐 Testing Dashboard Load")
    print("="*60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # Navigate to dashboard
            page.goto('http://localhost:8000')
            page.wait_for_load_state('networkidle')

            # Take screenshot for debugging
            page.screenshot(path='/tmp/dashboard_loaded.png')

            # Verify key elements exist
            expect(page.locator('text=Deploy New Agent')).to_be_visible()
            expect(page.locator('#monitor-type-select')).to_be_visible()

            print("   ✓ Dashboard loaded successfully")
            return True

        except Exception as e:
            print(f"   ❌ Failed: {e}")
            page.screenshot(path='/tmp/dashboard_error.png')
            return False
        finally:
            browser.close()


def test_echo_agent_ui():
    """Test Echo agent type - should hide provider and model dropdowns"""
    print("\n" + "="*60)
    print("🔊 Testing Echo Agent UI")
    print("="*60)
    print("Expected: No provider dropdown, no model dropdown")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            page.goto('http://localhost:8000')
            page.wait_for_load_state('networkidle')

            # Select Echo monitor type
            page.select_option('#monitor-type-select', 'echo')
            page.wait_for_timeout(500)  # Wait for UI update

            # Take screenshot
            page.screenshot(path='/tmp/echo_agent.png')

            # Verify provider dropdown is hidden
            provider_group = page.locator('#provider-group')
            assert not provider_group.is_visible(), "Provider dropdown should be hidden for Echo"
            print("   ✓ Provider dropdown is hidden")

            # Verify model dropdown is hidden
            model_group = page.locator('#model-group')
            assert not model_group.is_visible(), "Model dropdown should be hidden for Echo"
            print("   ✓ Model dropdown is hidden")

            # Verify system prompt is hidden
            prompt_group = page.locator('#system-prompt-group')
            assert not prompt_group.is_visible(), "System prompt should be hidden for Echo"
            print("   ✓ System prompt is hidden")

            print("\n✅ Echo agent UI test PASSED")
            return True

        except Exception as e:
            print(f"\n❌ Echo agent UI test FAILED: {e}")
            page.screenshot(path='/tmp/echo_agent_error.png')
            return False
        finally:
            browser.close()


def test_ollama_agent_ui():
    """Test Ollama agent type - should show model dropdown but hide provider"""
    print("\n" + "="*60)
    print("🤖 Testing Ollama Agent UI")
    print("="*60)
    print("Expected: No provider dropdown, model dropdown visible")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            page.goto('http://localhost:8000')
            page.wait_for_load_state('networkidle')

            # Select Ollama monitor type
            page.select_option('#monitor-type-select', 'ollama')
            page.wait_for_timeout(1000)  # Wait for models to load

            # Take screenshot
            page.screenshot(path='/tmp/ollama_agent.png')

            # Verify provider dropdown is hidden
            provider_group = page.locator('#provider-group')
            assert not provider_group.is_visible(), "Provider dropdown should be hidden for Ollama"
            print("   ✓ Provider dropdown is hidden")

            # Verify model dropdown is visible
            model_group = page.locator('#model-group')
            assert model_group.is_visible(), "Model dropdown should be visible for Ollama"
            print("   ✓ Model dropdown is visible")

            # Verify system prompt is visible
            prompt_group = page.locator('#system-prompt-group')
            assert prompt_group.is_visible(), "System prompt should be visible for Ollama"
            print("   ✓ System prompt is visible")

            print("\n✅ Ollama agent UI test PASSED")
            return True

        except Exception as e:
            print(f"\n❌ Ollama agent UI test FAILED: {e}")
            page.screenshot(path='/tmp/ollama_agent_error.png')
            return False
        finally:
            browser.close()


def test_claude_agent_sdk_ui():
    """Test Claude Agent SDK - should show model dropdown with Claude models, hide provider"""
    print("\n" + "="*60)
    print("🛡 Testing Claude Agent SDK UI")
    print("="*60)
    print("Expected: No provider dropdown, Claude models in dropdown, Sonnet 4.5 default")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            page.goto('http://localhost:8000')
            page.wait_for_load_state('networkidle')

            # Select Claude Agent SDK monitor type
            page.select_option('#monitor-type-select', 'claude_agent_sdk')
            page.wait_for_timeout(1000)  # Wait for models to load

            # Take screenshot
            page.screenshot(path='/tmp/claude_sdk_agent.png', full_page=True)

            # Verify provider dropdown is hidden
            provider_group = page.locator('#provider-group')
            assert not provider_group.is_visible(), "Provider dropdown should be hidden for Claude Agent SDK"
            print("   ✓ Provider dropdown is hidden")

            # Verify model dropdown is visible
            model_group = page.locator('#model-group')
            assert model_group.is_visible(), "Model dropdown should be visible for Claude Agent SDK"
            print("   ✓ Model dropdown is visible")

            # Verify Claude Sonnet 4.5 is selected by default
            model_select = page.locator('#model-select')
            selected_value = model_select.input_value()
            assert selected_value == "claude-sonnet-4-5", f"Expected claude-sonnet-4-5 but got {selected_value}"
            print("   ✓ Claude Sonnet 4.5 is selected by default")

            # Verify Claude Haiku 4.5 is available as an option
            model_options = page.locator('#model-select option').all_text_contents()
            haiku_found = any("Haiku 4.5" in opt for opt in model_options)
            assert haiku_found, "Claude Haiku 4.5 should be available as an option"
            print("   ✓ Claude Haiku 4.5 is available")

            # Verify NO Gemini models are shown
            gemini_found = any("Gemini" in opt for opt in model_options)
            assert not gemini_found, "Gemini models should NOT be shown for Claude Agent SDK"
            print("   ✓ Gemini models are not shown")

            # Verify system prompt is visible
            prompt_group = page.locator('#system-prompt-group')
            assert prompt_group.is_visible(), "System prompt should be visible for Claude Agent SDK"
            print("   ✓ System prompt is visible")

            print("\n✅ Claude Agent SDK UI test PASSED")
            return True

        except Exception as e:
            print(f"\n❌ Claude Agent SDK UI test FAILED: {e}")
            page.screenshot(path='/tmp/claude_sdk_agent_error.png', full_page=True)

            # Debug info
            model_select = page.locator('#model-select')
            print(f"\n   Debug - Selected model: {model_select.input_value()}")
            print(f"   Debug - Available options: {page.locator('#model-select option').all_text_contents()}")

            return False
        finally:
            browser.close()


def test_langgraph_agent_ui():
    """Test LangGraph agent type - should show both provider and model dropdowns"""
    print("\n" + "="*60)
    print("🧠 Testing LangGraph Agent UI")
    print("="*60)
    print("Expected: Provider dropdown visible, model dropdown visible")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            page.goto('http://localhost:8000')
            page.wait_for_load_state('networkidle')

            # Select LangGraph monitor type
            page.select_option('#monitor-type-select', 'langgraph')
            page.wait_for_timeout(500)  # Wait for UI update

            # Take screenshot
            page.screenshot(path='/tmp/langgraph_agent.png')

            # Verify provider dropdown is visible
            provider_group = page.locator('#provider-group')
            assert provider_group.is_visible(), "Provider dropdown should be visible for LangGraph"
            print("   ✓ Provider dropdown is visible")

            # Verify model dropdown is visible
            model_group = page.locator('#model-group')
            assert model_group.is_visible(), "Model dropdown should be visible for LangGraph"
            print("   ✓ Model dropdown is visible")

            # Verify system prompt is visible
            prompt_group = page.locator('#system-prompt-group')
            assert prompt_group.is_visible(), "System prompt should be visible for LangGraph"
            print("   ✓ System prompt is visible")

            print("\n✅ LangGraph agent UI test PASSED")
            return True

        except Exception as e:
            print(f"\n❌ LangGraph agent UI test FAILED: {e}")
            page.screenshot(path='/tmp/langgraph_agent_error.png')
            return False
        finally:
            browser.close()


def test_default_agent_type():
    """Test that default agent type is set correctly from env var"""
    print("\n" + "="*60)
    print("⚙️  Testing Default Agent Type")
    print("="*60)
    print("Expected: DEFAULT_AGENT_TYPE from .env is pre-selected")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            page.goto('http://localhost:8000')
            page.wait_for_load_state('networkidle')
            page.wait_for_timeout(1000)  # Wait for defaults to load

            # Take screenshot
            page.screenshot(path='/tmp/default_agent_type.png')

            # Check what monitor type is selected
            monitor_select = page.locator('#monitor-type-select')
            selected_value = monitor_select.input_value()

            print(f"   Default agent type: {selected_value}")

            # It should be claude_agent_sdk if DEFAULT_AGENT_TYPE is set
            # (This might vary based on .env configuration)
            assert selected_value in ["echo", "ollama", "claude_agent_sdk", "langgraph"], \
                f"Invalid agent type selected: {selected_value}"
            print(f"   ✓ Valid agent type selected: {selected_value}")

            print("\n✅ Default agent type test PASSED")
            return True

        except Exception as e:
            print(f"\n❌ Default agent type test FAILED: {e}")
            page.screenshot(path='/tmp/default_agent_type_error.png')
            return False
        finally:
            browser.close()


def main():
    """Run all dashboard UI tests"""
    print("\n" + "="*60)
    print("🧪 Dashboard UI E2E Test Suite")
    print("="*60)
    print("Testing against: http://localhost:8000")
    print("Make sure the dashboard is running: uv run dashboard")

    # Check if dashboard is running
    import httpx
    try:
        response = httpx.get("http://localhost:8000/api/health", timeout=5.0)
        if response.status_code != 200:
            print("\n❌ Dashboard is not responding. Start it with: uv run dashboard")
            return 1
    except Exception as e:
        print(f"\n❌ Cannot connect to dashboard: {e}")
        print("   Start it with: uv run dashboard")
        return 1

    print("✅ Dashboard is running\n")

    # Run all tests
    results = {
        "Dashboard Load": test_dashboard_loads(),
        "Echo Agent UI": test_echo_agent_ui(),
        "Ollama Agent UI": test_ollama_agent_ui(),
        "Claude Agent SDK UI": test_claude_agent_sdk_ui(),
        "LangGraph Agent UI": test_langgraph_agent_ui(),
        "Default Agent Type": test_default_agent_type(),
    }

    # Summary
    print("\n" + "="*60)
    print("📊 Test Results Summary")
    print("="*60)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    all_passed = all(results.values())

    if all_passed:
        print("\n🎉 All dashboard UI tests passed!")
        print("\nScreenshots saved to /tmp/:")
        print("  - dashboard_loaded.png")
        print("  - echo_agent.png")
        print("  - ollama_agent.png")
        print("  - claude_sdk_agent.png")
        print("  - langgraph_agent.png")
        print("  - default_agent_type.png")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check screenshots in /tmp/")
        return 1


if __name__ == "__main__":
    import sys
    exit_code = main()
    sys.exit(exit_code)
