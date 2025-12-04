import sys
import os
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.ax_agent_studio.mcp_servers.crm_server import add_lead, get_leads_by_status, init_db

def test_crm():
    print("Testing CRM Server...")
    try:
        init_db()
        result = add_lead("Test User", "https://linkedin.com/in/test", "test_script")
        print(f"  add_lead: {result}")
        
        leads = get_leads_by_status("RAW")
        print(f"  get_leads: {leads}")
        
        if "Test User" in leads:
            print("  ✅ CRM Test Passed")
        else:
            print("  ❌ CRM Test Failed")
    except Exception as e:
        print(f"  ❌ CRM Test Error: {e}")

async def test_browser():
    print("\nTesting Browser Server (Import Check)...")
    try:
        # We just check if we can import it and if playwright is installed
        from src.ax_agent_studio.mcp_servers.browser_server import navigate
        print("  ✅ Browser Server Import Passed")
        # We won't actually launch the browser in this automated test to avoid popping up windows unexpectedly
        # unless the user asked for it, but we verified the code exists.
    except ImportError as e:
        print(f"  ❌ Browser Server Import Error: {e}")
    except Exception as e:
        print(f"  ❌ Browser Server Error: {e}")

if __name__ == "__main__":
    test_crm()
    asyncio.run(test_browser())
