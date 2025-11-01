"""
Deployment Group Loader

Loads deployment group definitions from configs/deployment_groups.yaml.
Provides helper functions to retrieve group metadata for the dashboard
and process manager.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Dict, List, Optional, Any, Set

import yaml

from ax_agent_studio.dashboard.backend.config_loader import ConfigLoader


@dataclasses.dataclass
class DeploymentAgent:
    """Agent entry inside a deployment group."""

    id: str
    monitor: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    start_delay_ms: Optional[int] = None
    process_backlog: Optional[bool] = None  # DEPRECATED: Kept for backward compatibility, defaults to False


@dataclasses.dataclass
class DeploymentGroup:
    """Deployment group definition."""

    id: str
    name: str
    description: str
    defaults: Dict[str, Any]
    agents: List[DeploymentAgent]
    tags: List[str]
    environment: str = "any"


class DeploymentLoader:
    """Loads deployment group configuration."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.config_path = self.base_dir / "configs" / "deployment_groups.yaml"
        self._groups: Dict[str, DeploymentGroup] = {}
        self._config_loader = ConfigLoader(base_dir)
        self.reload()

    def reload(self) -> None:
        """Reload deployment groups from disk."""
        self._groups = {}

        if not self.config_path.exists():
            return

        try:
            with open(self.config_path, "r") as f:
                raw_config = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Error loading deployment groups: {e}")
            return

        groups_data = raw_config.get("deployment_groups", {})
        if not isinstance(groups_data, dict):
            print("deployment_groups.yaml: 'deployment_groups' must be a mapping")
            return

        existing_agents: Set[str] = {
            entry["agent_name"] for entry in self._config_loader.list_configs()
        }

        for group_id, group_info in groups_data.items():
            try:
                group = self._parse_group(group_id, group_info, existing_agents)
                if group:  # Only add if group was successfully parsed
                    self._groups[group_id] = group
            except Exception as e:
                print(f"  Skipping deployment group '{group_id}': {e}")

    def _parse_group(
        self,
        group_id: str,
        group_info: Dict[str, Any],
        existing_agents: Set[str],
    ) -> DeploymentGroup:
        """Parse a single group entry."""
        if not isinstance(group_info, dict):
            raise ValueError("Group definition must be a mapping")

        name = group_info.get("name", group_id.replace("_", " ").title())
        description = group_info.get("description", "")
        defaults = group_info.get("defaults", {}) or {}
        tags = group_info.get("tags", []) or []
        environment = group_info.get("environment", "any") or "any"

        if "agents" not in group_info or not isinstance(group_info["agents"], list):
            raise ValueError("Group must define an 'agents' list")

        agents: List[DeploymentAgent] = []
        skipped_agents: List[str] = []

        for raw_agent in group_info["agents"]:
            try:
                if isinstance(raw_agent, str):
                    agent_id = raw_agent
                    agent_data: Dict[str, Any] = {}
                elif isinstance(raw_agent, dict):
                    if "id" not in raw_agent:
                        print(f"    Skipping agent entry without 'id' in group '{group_id}'")
                        continue
                    agent_id = raw_agent["id"]
                    agent_data = {k: v for k, v in raw_agent.items() if k != "id"}
                else:
                    print(f"    Skipping invalid agent entry in group '{group_id}'")
                    continue

                # Validate agent exists, but don't fail - just skip
                if not self._agent_exists(agent_id, existing_agents):
                    if agent_id.startswith("YOUR_") or "EXAMPLE" in agent_id.upper():
                        print(f"   Placeholder agent '{agent_id}' - replace with your actual agent ID")
                    else:
                        print(f"    Agent '{agent_id}' not found in configs/agents/ - skipping")
                        print(f"     Available agents: {', '.join(sorted(existing_agents))}")
                    skipped_agents.append(agent_id)
                    continue

                agents.append(
                    DeploymentAgent(
                        id=agent_id,
                        monitor=agent_data.get("monitor"),
                        provider=agent_data.get("provider"),
                        model=agent_data.get("model"),
                        system_prompt=agent_data.get("system_prompt"),
                        start_delay_ms=agent_data.get("start_delay_ms"),
                        process_backlog=agent_data.get("process_backlog"),
                    )
                )
            except Exception as e:
                print(f"    Error processing agent in group '{group_id}': {e}")
                continue

        if skipped_agents:
            has_placeholders = any(a.startswith("YOUR_") or "EXAMPLE" in a.upper() for a in skipped_agents)
            if has_placeholders:
                print(f"   Group '{group_id}': Update placeholder agent names in deployment_groups.yaml")
            else:
                print(f"   Group '{group_id}': {len(agents)} agents loaded, {len(skipped_agents)} skipped")

        if not agents:
            print(f"  ℹ  Group '{group_id}' has no valid agents - check agent IDs in deployment_groups.yaml")
            print(f"     Available agents: {', '.join(sorted(existing_agents))}")
            return None  # Return None instead of raising error

        return DeploymentGroup(
            id=group_id,
            name=name,
            description=description,
            defaults=defaults,
            agents=agents,
            tags=tags,
            environment=environment,
        )

    def _agent_exists(self, agent_id: str, existing_agents: Optional[Set[str]] = None) -> bool:
        """Check if agent configuration file exists (non-throwing)."""
        if existing_agents is None:
            existing_agents = {
                entry["agent_name"] for entry in self._config_loader.list_configs()
            }
        return agent_id in existing_agents

    def list_groups(self, environment: Optional[str] = None) -> List[DeploymentGroup]:
        """List deployment groups, optionally filtered by environment."""
        groups = list(self._groups.values())
        if environment and environment != "any":
            return [
                g for g in groups if g.environment in ("any", environment)
            ]
        return groups

    def get_group(self, group_id: str) -> Optional[DeploymentGroup]:
        """Return a group by id."""
        return self._groups.get(group_id)


# Helper accessor used by other modules
_deployment_loader: Optional[DeploymentLoader] = None


def get_deployment_loader(base_dir: Optional[Path] = None) -> DeploymentLoader:
    """Get (and cache) the deployment loader instance."""
    global _deployment_loader
    if _deployment_loader is None:
        if base_dir is None:
            base_dir = Path(__file__).parent.parent.parent.parent
        _deployment_loader = DeploymentLoader(base_dir)
    return _deployment_loader
