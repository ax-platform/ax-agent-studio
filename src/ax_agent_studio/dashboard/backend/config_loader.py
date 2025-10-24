"""
Configuration Loader
Loads agent configs and available models with environment support
"""

import json
import asyncio
import subprocess
from pathlib import Path
from typing import List, Dict, Optional
from collections import defaultdict


class ConfigLoader:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.agents_dir = base_dir / "configs" / "agents"

    def _parse_mcp_format(self, data: Dict) -> tuple[str, str, str]:
        """Parse MCP server format to extract agent name and URLs"""
        mcp_servers = data.get("mcpServers", {})

        # Look for ax-gcp or any server with agent URL
        for server_name, server_config in mcp_servers.items():
            args = server_config.get("args", [])

            # Find the URL argument (contains /mcp/agents/)
            for arg in args:
                if isinstance(arg, str) and "/mcp/agents/" in arg:
                    # Extract agent name from URL
                    # e.g., "https://mcp.paxai.app/mcp/agents/logic_keeper_930" → "logic_keeper_930"
                    parts = arg.split("/mcp/agents/")
                    if len(parts) > 1:
                        agent_name = parts[1].strip()
                        server_url = arg

                        # Find oauth server
                        oauth_url = ""
                        if "--oauth-server" in args:
                            oauth_idx = args.index("--oauth-server")
                            if oauth_idx + 1 < len(args):
                                oauth_url = args[oauth_idx + 1]

                        return agent_name, server_url, oauth_url

        # Fallback if no agent URL found
        return "", "", ""

    def list_environments(self) -> List[str]:
        """List all available environments from agent configs"""
        configs = self.list_configs()
        environments = sorted(set(config["environment"] for config in configs))
        return environments if environments else ["local"]

    def list_configs(self, environment: Optional[str] = None) -> List[Dict[str, str]]:
        """List all available agent configuration files from configs/agents/"""
        if not self.agents_dir.exists():
            return []

        configs = []

        for config_file in self.agents_dir.glob("*.json"):
            # Skip example/template files
            if config_file.name.startswith("_"):
                continue

            try:
                with open(config_file) as f:
                    data = json.load(f)

                    # Skip if it has _comment or _instructions (template file)
                    if "_comment" in data or "_instructions" in data:
                        continue

                    # Support both MCP server format and legacy format
                    if "mcpServers" in data:
                        # New MCP server format
                        agent_name, server_url, oauth_url = self._parse_mcp_format(data)
                        display_name = agent_name.replace("_", " ").title()
                        mcp_server_names = list(data['mcpServers'].keys())
                        description = f"Agent using {len(data['mcpServers'])} MCP server(s): {', '.join(mcp_server_names)}"
                    else:
                        # Legacy format (backward compatibility)
                        agent_name = data.get("agent_name", config_file.stem)
                        display_name = data.get("display_name", agent_name)
                        server_url = data.get("server_url", "")
                        oauth_url = data.get("oauth_url", "")
                        description = data.get("description", "")

                    if not agent_name or not server_url:
                        print(f"Skipping {config_file}: missing agent_name or server_url")
                        continue

                    # Auto-detect environment from URL (ignore any environment field in config)
                    config_env = "local" if "localhost" in server_url else "production"

                    # Filter by environment if specified
                    if environment and config_env != environment:
                        continue

                    # Extract server type from URL
                    server_type = "local" if "localhost" in server_url else "remote"

                    configs.append({
                        "path": str(config_file),
                        "filename": config_file.name,
                        "agent_name": agent_name,
                        "display_name": display_name,
                        "server_url": server_url,
                        "oauth_url": oauth_url,
                        "environment": config_env,
                        "server_type": server_type,
                        "description": description
                    })
            except Exception as e:
                print(f"Error loading config {config_file}: {e}")
                continue

        return sorted(configs, key=lambda x: (x["environment"], x["agent_name"]))

    def get_configs_by_environment(self) -> Dict[str, List[Dict]]:
        """Group configs by environment"""
        all_configs = self.list_configs()
        grouped = defaultdict(list)

        for config in all_configs:
            grouped[config["environment"]].append(config)

        return dict(grouped)

    async def get_ollama_models(self) -> List[str]:
        """Get list of available Ollama models"""
        try:
            # Run ollama list command
            process = await asyncio.create_subprocess_shell(
                "ollama list",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                print(f"Error getting Ollama models: {stderr.decode()}")
                return []

            # Parse output (skip header line)
            lines = stdout.decode().strip().split('\n')[1:]
            models = []

            for line in lines:
                if line.strip():
                    # Model name is first column
                    model_name = line.split()[0]
                    models.append(model_name)

            return models

        except Exception as e:
            print(f"Error getting Ollama models: {e}")
            return []

    def load_config(self, config_path: str) -> Optional[Dict]:
        """Load a specific configuration file"""
        try:
            with open(config_path) as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config {config_path}: {e}")
            return None

    def get_default_config(self, environment: str = "local") -> Optional[str]:
        """Get the first available config for an environment as default"""
        configs = self.list_configs(environment)
        return configs[0]["path"] if configs else None
