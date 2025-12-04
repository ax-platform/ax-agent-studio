
import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root / "src"))

from ax_agent_studio.mcp_manager import MCPServerManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    agent_name = "pipeline_master"
    print(f"Debugging MCP connection for {agent_name}...")
    
    mgr = MCPServerManager(agent_name)
    
    try:
        await mgr.connect_all()
        
        print("\n--- Connected Servers ---")
        for name, session in mgr.sessions.items():
            print(f"Server: {name}")
            try:
                tools = await session.list_tools()
                print(f"  Tools: {[t.name for t in tools.tools]}")
            except Exception as e:
                print(f"  Error listing tools: {e}")
                
    except Exception as e:
        print(f"Connection failed: {e}")
    finally:
        await mgr.disconnect_all()

if __name__ == "__main__":
    asyncio.run(main())
