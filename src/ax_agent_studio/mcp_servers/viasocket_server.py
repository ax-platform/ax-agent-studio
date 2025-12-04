import httpx
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("viasocket-integration")

@mcp.tool()
async def trigger_workflow(webhook_url: str, payload: str) -> str:
    """
    Trigger a viaSocket workflow via webhook.
    
    Args:
        webhook_url: The full URL of the viaSocket webhook.
        payload: JSON string containing the data to send.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, content=payload, headers={"Content-Type": "application/json"})
            response.raise_for_status()
            return f"Workflow triggered successfully. Status: {response.status_code}, Response: {response.text}"
    except Exception as e:
        return f"Error triggering workflow: {str(e)}"

if __name__ == "__main__":
    mcp.run()
