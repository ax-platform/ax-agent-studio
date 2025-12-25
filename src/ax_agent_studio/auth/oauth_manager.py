"""OAuth flow manager for triggering authentication via mcp-remote."""

import asyncio
import subprocess
import sys
from pathlib import Path
from typing import Dict

from .token_validator import TokenValidator


class OAuthManager:
    """
    Manages OAuth authentication flow for MCP agents.
    Triggers mcp-remote OAuth when tokens are missing/expired.
    """

    def __init__(self, mcp_remote_version: str = "0.1.36"):
        """
        Initialize OAuthManager.

        Args:
            mcp_remote_version: Version of mcp-remote to use
        """
        self.version = mcp_remote_version
        self.validator = TokenValidator(mcp_remote_version)

    async def trigger_oauth_flow(
        self,
        agent_url: str,
        oauth_server: str,
        timeout: int = 300,  # 5 minutes
    ) -> Dict[str, any]:
        """
        Trigger OAuth flow by running mcp-remote as a subprocess.

        This method runs:
          npx -y mcp-remote@{version} {agent_url} --oauth-server {oauth_server}

        Then waits for the token file to be created.

        Args:
            agent_url: The MCP agent URL
            oauth_server: The OAuth server URL
            timeout: Maximum wait time in seconds (default: 300)

        Returns:
            Dictionary with authentication result:
            {
                "success": bool,
                "status": "completed" | "failed" | "timeout",
                "message": str,
                "error": str | None
            }
        """
        try:
            # Build command
            cmd = [
                "npx",
                "-y",
                f"mcp-remote@{self.version}",
                agent_url,
                "--transport",
                "http-only",
                "--oauth-server",
                oauth_server,
            ]

            print(f"[OAuth] Starting OAuth flow for: {agent_url}", file=sys.stderr)
            print(f"[OAuth] Command: {' '.join(cmd)}", file=sys.stderr)

            # Start subprocess with stdin redirected to DEVNULL
            # This prevents mcp-remote from trying to read JSON-RPC from stdin
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Wait for token file creation with timeout
            token_path = self.validator.get_token_path(agent_url)
            start_time = asyncio.get_event_loop().time()

            while True:
                # Check if token file exists
                if token_path.exists():
                    # Verify token validity
                    auth_status = self.validator.check_auth_status(agent_url)
                    if auth_status["authenticated"]:
                        print(f"[OAuth] Authentication successful!", file=sys.stderr)
                        # Terminate the process
                        try:
                            process.terminate()
                            await asyncio.wait_for(process.wait(), timeout=5)
                        except Exception:
                            process.kill()
                            await process.wait()

                        return {
                            "success": True,
                            "status": "completed",
                            "message": "OAuth authentication completed successfully",
                            "token_path": str(token_path),
                        }

                # Check timeout
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout:
                    print(f"[OAuth] Timeout after {timeout}s", file=sys.stderr)
                    process.terminate()
                    try:
                        await asyncio.wait_for(process.wait(), timeout=5)
                    except Exception:
                        process.kill()
                        await process.wait()

                    return {
                        "success": False,
                        "status": "timeout",
                        "message": f"OAuth flow timed out after {timeout} seconds. Please try again.",
                        "error": "timeout",
                    }

                # Check if process has exited (failed or cancelled)
                if process.returncode is not None:
                    stdout, stderr = await process.communicate()
                    print(f"[OAuth] Process exited with code {process.returncode}", file=sys.stderr)
                    if stderr:
                        print(f"[OAuth] stderr: {stderr.decode()}", file=sys.stderr)

                    return {
                        "success": False,
                        "status": "failed",
                        "message": "OAuth process exited unexpectedly",
                        "error": stderr.decode() if stderr else None,
                    }

                # Poll every second
                await asyncio.sleep(1)

        except Exception as e:
            print(f"[OAuth] Error: {str(e)}", file=sys.stderr)
            return {
                "success": False,
                "status": "failed",
                "message": f"Failed to start OAuth flow: {str(e)}",
                "error": str(e),
            }
