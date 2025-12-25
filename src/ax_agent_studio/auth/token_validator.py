"""Token validator for checking OAuth token existence and validity."""

import hashlib
import json
from pathlib import Path
from typing import Dict


class TokenValidator:
    """
    Validates OAuth tokens stored by mcp-remote in ~/.mcp-auth/

    Token hash calculation: MD5(agent_url)
    Token location: ~/.mcp-auth/mcp-remote-{version}/{hash}_tokens.json
    """

    def __init__(self, mcp_remote_version: str = "0.1.36"):
        """
        Initialize TokenValidator.

        Args:
            mcp_remote_version: Version of mcp-remote to check tokens for
        """
        self.version = mcp_remote_version
        self.auth_dir = Path.home() / ".mcp-auth" / f"mcp-remote-{mcp_remote_version}"
        self.mcp_auth_base = Path.home() / ".mcp-auth"

    def get_token_hash(self, agent_url: str) -> str:
        """
        Calculate MD5 hash of agent URL for token filename.

        Args:
            agent_url: The MCP agent URL (e.g., https://mcp.paxai.app/mcp/agents/twitter_agent)

        Returns:
            MD5 hash hex string
        """
        return hashlib.md5(agent_url.encode()).hexdigest()

    def get_token_path(self, agent_url: str) -> Path:
        """
        Get the file path for OAuth tokens for a given agent URL.
        Searches across all mcp-remote versions for existing tokens.

        Args:
            agent_url: The MCP agent URL

        Returns:
            Path to the token file (existing or primary location for creation)
        """
        hash_str = self.get_token_hash(agent_url)
        token_file = self.auth_dir / f"{hash_str}_tokens.json"

        # Check primary location first
        if token_file.exists():
            return token_file

        # Search all mcp-remote-* directories for existing tokens
        if self.mcp_auth_base.exists():
            # Get all mcp-remote directories, sorted by version (newest first)
            mcp_dirs = sorted(
                [d for d in self.mcp_auth_base.iterdir() if d.is_dir() and d.name.startswith("mcp-remote-")],
                reverse=True
            )

            for mcp_dir in mcp_dirs:
                fallback_token_file = mcp_dir / f"{hash_str}_tokens.json"
                if fallback_token_file.exists():
                    return fallback_token_file

        # Return primary path even if doesn't exist (for creation)
        return token_file

    def check_auth_status(self, agent_url: str) -> Dict[str, any]:
        """
        Check if OAuth tokens exist and are valid for a given agent URL.

        Args:
            agent_url: The MCP agent URL

        Returns:
            Dictionary with authentication status:
            {
                "authenticated": bool,
                "status": "valid" | "missing",
                "token_path": str,
                "needs_auth": bool,
                "version": str  # mcp-remote version where tokens were found
            }
        """
        token_path = self.get_token_path(agent_url)

        if not token_path.exists():
            return {
                "authenticated": False,
                "status": "missing",
                "token_path": str(token_path),
                "needs_auth": True,
                "version": self.version,
            }

        # Token file exists - validate structure
        try:
            with open(token_path, "r") as f:
                token_data = json.load(f)

            # Check required fields
            if not self.validate_token_structure(token_data):
                return {
                    "authenticated": False,
                    "status": "invalid",
                    "token_path": str(token_path),
                    "needs_auth": True,
                    "version": self._detect_version(token_path),
                }

            # Token exists and has valid structure
            # Note: We don't check expiry here because mcp-remote handles auto-refresh
            return {
                "authenticated": True,
                "status": "valid",
                "token_path": str(token_path),
                "needs_auth": False,
                "version": self._detect_version(token_path),
            }

        except (json.JSONDecodeError, IOError) as e:
            # Token file corrupted
            return {
                "authenticated": False,
                "status": "corrupted",
                "token_path": str(token_path),
                "needs_auth": True,
                "error": str(e),
                "version": self._detect_version(token_path),
            }

    def validate_token_structure(self, token_data: dict) -> bool:
        """
        Validate that token data has the required structure.

        Args:
            token_data: Token data dictionary from JSON

        Returns:
            True if valid, False otherwise
        """
        required_fields = ["access_token", "token_type"]
        return all(field in token_data for field in required_fields)

    def _detect_version(self, token_path: Path) -> str:
        """
        Detect which mcp-remote version directory the token is in.

        Args:
            token_path: Path to the token file

        Returns:
            Version string (e.g., "0.1.36", "0.1.35", "0.1.29")
        """
        # Extract version from the parent directory name
        for parent in token_path.parents:
            if parent.name.startswith("mcp-remote-"):
                return parent.name.replace("mcp-remote-", "")
        return self.version
