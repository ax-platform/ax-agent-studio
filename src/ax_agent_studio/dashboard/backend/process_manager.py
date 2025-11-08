"""
Process Manager for MCP Monitors
Handles starting, stopping, and tracking monitor processes
"""

import asyncio
import json
import os
import re
import signal
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import psutil
import yaml

from ax_agent_studio.dashboard.backend.config_loader import ConfigLoader
from ax_agent_studio.dashboard.backend.deployment_loader import (
    DeploymentLoader,
    get_deployment_loader,
)
from ax_agent_studio.mcp_manager import MCPServerManager
from ax_agent_studio.message_store import MessageStore


def sanitize_agent_name(agent_name: str) -> str:
    """
    Sanitize agent name to prevent path traversal and shell injection.

    Only allows: alphanumeric, underscore, hyphen
    Blocks: ../, shell metacharacters, etc.
    """
    # Allow only safe characters: letters, numbers, underscore, hyphen
    sanitized = re.sub(r"[^a-zA-Z0-9_-]", "_", agent_name)

    # Ensure it's not empty after sanitization
    if not sanitized or sanitized.isspace():
        raise ValueError(f"Invalid agent_name '{agent_name}': must contain alphanumeric characters")

    # Prevent path traversal
    if ".." in agent_name or "/" in agent_name or "\\" in agent_name:
        raise ValueError(f"Invalid agent_name '{agent_name}': cannot contain path separators")

    return sanitized


class ProcessManager:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.monitors: dict[str, dict] = {}  # monitor_id -> monitor info
        self.group_deployments: dict[str, dict[str, Any]] = {}
        self.log_dir = base_dir / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.config_loader = ConfigLoader(base_dir)
        self.deployment_loader: DeploymentLoader = get_deployment_loader(base_dir)
        self.message_store = MessageStore()

    def _resolve_system_prompt(self, prompt_ref: str | None) -> tuple[str | None, str | None]:
        """
        Resolve system prompt reference to actual text.

        Supports:
        - Direct text (strings with newline)
        - Relative paths within configs/ or configs/prompts/
        - YAML prompt files with `prompt` key
        """
        if not prompt_ref:
            return None, None

        # If looks like raw prompt text (contains newline), return as-is
        if "\n" in prompt_ref.strip():
            return prompt_ref, "custom"

        candidate_paths = []
        ref_path = Path(prompt_ref)
        if ref_path.is_absolute():
            candidate_paths.append(ref_path)
        else:
            candidate_paths.append(self.base_dir / prompt_ref)
            candidate_paths.append(self.base_dir / "configs" / prompt_ref)
            candidate_paths.append(self.base_dir / "configs" / "prompts" / prompt_ref)

        for path in candidate_paths:
            if path.exists():
                try:
                    if path.suffix in {".yaml", ".yml"}:
                        with open(path) as f:
                            data = yaml.safe_load(f) or {}
                        prompt_text = data.get("prompt")
                        if not prompt_text:
                            raise ValueError(f"No 'prompt' key found in {path}")
                        return prompt_text, prompt_ref
                    else:
                        return path.read_text(), prompt_ref
                except Exception as e:
                    print(f"Error loading system prompt {path}: {e}")
                    break

        # Fallback: treat as literal text but keep name for tracking
        return prompt_ref, prompt_ref

    def _get_agent_config_path(self, agent_id: str) -> Path:
        """
        Return absolute path to agent config JSON by finding the config
        where the agent_name (from the MCP URL) matches agent_id.
        This allows the filename to be anything - we extract the agent name from the URL.
        """
        # Get all configs and find the one with matching agent_name
        all_configs = self.config_loader.list_configs()

        for config in all_configs:
            if config["agent_name"] == agent_id:
                return Path(config["path"])

        # If not found, raise error with helpful message
        available_agents = [c["agent_name"] for c in all_configs]
        raise FileNotFoundError(
            f"No config found for agent '{agent_id}'.\n"
            f"Available agents: {', '.join(available_agents) if available_agents else 'none'}\n"
            f"Agent name is extracted from the MCP URL in your config file (e.g., https://mcp.paxai.app/mcp/agents/your_agent_name)"
        )

    def scan_system_monitors(self) -> list[dict]:
        """Scan system for ALL running monitor processes (even orphans)"""
        system_monitors = []

        try:
            for proc in psutil.process_iter(["pid", "name", "cmdline", "create_time"]):
                try:
                    cmdline = proc.info.get("cmdline", [])
                    if not cmdline or not isinstance(cmdline, list):
                        continue

                    cmdline_str = " ".join(cmdline)

                    # Match monitor processes (only Python processes, not uv wrapper)
                    if "ax_agent_studio.monitors" not in cmdline_str:
                        continue

                    # Filter out uv wrapper - only match actual Python processes
                    proc_name = proc.info.get("name", "").lower()
                    if "python" not in proc_name:
                        continue

                    # Extract monitor type and agent name from command line
                    monitor_type = None
                    agent_name = None

                    for i, arg in enumerate(cmdline):
                        if "monitors." in arg:
                            # Extract monitor type from path like "ax_agent_studio.monitors.langgraph_monitor"
                            parts = arg.split(".")
                            if len(parts) >= 3:
                                monitor_type = parts[-1].replace("_monitor", "")
                        elif i > 0 and "monitors" in cmdline[i - 1]:
                            # Agent name is usually the first arg after the monitor module
                            agent_name = arg

                    # Calculate uptime
                    create_time = datetime.fromtimestamp(proc.info["create_time"])
                    uptime = int((datetime.now() - create_time).total_seconds())

                    system_monitors.append(
                        {
                            "pid": proc.info["pid"],
                            "agent_name": agent_name or "unknown",
                            "monitor_type": monitor_type or "unknown",
                            "started_at": create_time.isoformat(),
                            "uptime_seconds": uptime,
                            "source": "system",  # Mark as found by system scan
                            "cmdline": " ".join(cmdline[:5]),  # For debugging
                        }
                    )

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        except Exception as e:
            print(f"Error scanning system monitors: {e}")

        return system_monitors

    def get_all_monitors(self) -> list[dict]:
        """Get all monitors: tracked + system orphans"""
        result = []
        system_pids = set()

        # First, add all system monitors
        system_monitors = self.scan_system_monitors()
        for sys_mon in system_monitors:
            system_pids.add(sys_mon["pid"])

            # Check if this PID is tracked
            tracked = False
            monitor_id = None
            for mid, info in self.monitors.items():
                if info.get("pid") == sys_mon["pid"]:
                    tracked = True
                    monitor_id = mid
                    break

            result.append(
                {
                    "id": monitor_id or f"orphan_{sys_mon['pid']}",
                    "agent_name": sys_mon["agent_name"],
                    "monitor_type": sys_mon["monitor_type"],
                    "status": "running",
                    "pid": sys_mon["pid"],
                    "started_at": sys_mon["started_at"],
                    "uptime_seconds": sys_mon["uptime_seconds"],
                    "config_path": self.monitors.get(monitor_id, {}).get("config_path")
                    if monitor_id
                    else None,
                    "model": self.monitors.get(monitor_id, {}).get("model") if monitor_id else None,
                    "provider": self.monitors.get(monitor_id, {}).get("provider")
                    if monitor_id
                    else None,
                    "system_prompt_name": self.monitors.get(monitor_id, {}).get(
                        "system_prompt_name"
                    )
                    if monitor_id
                    else None,
                    "mcp_servers": self.monitors.get(monitor_id, {}).get("mcp_servers", [])
                    if monitor_id
                    else [],
                    "environment": self.monitors.get(monitor_id, {}).get("environment", "unknown")
                    if monitor_id
                    else "unknown",
                    "deployment_group": self.monitors.get(monitor_id, {}).get("deployment_group")
                    if monitor_id
                    else None,
                    "tracked": tracked,  # Is dashboard tracking this?
                    "orphan": not tracked,  # Is this an orphan?
                }
            )

        # Then add tracked monitors that aren't running (zombies in dashboard memory)
        for monitor_id, info in self.monitors.items():
            pid = info.get("pid")
            if pid not in system_pids:
                # This is tracked but not actually running (zombie in memory)
                result.append(
                    {
                        "id": monitor_id,
                        "agent_name": info.get("agent_name"),
                        "monitor_type": info.get("monitor_type"),
                        "status": "stopped",
                        "pid": None,
                        "started_at": info.get("started_at"),
                        "uptime_seconds": None,
                        "config_path": info.get("config_path"),
                        "model": info.get("model"),
                        "provider": info.get("provider"),
                        "system_prompt_name": info.get("system_prompt_name"),
                        "mcp_servers": info.get("mcp_servers", []),
                        "environment": info.get("environment", "local"),
                        "deployment_group": info.get("deployment_group"),
                        "tracked": True,
                        "orphan": False,
                    }
                )

        return result

    def get_running_monitors(self) -> list[dict]:
        """Get only running monitors"""
        return [m for m in self.get_all_monitors() if m["status"] == "running"]

    def _get_monitor_status(self, monitor_id: str, info: dict) -> dict:
        """Check if a monitor is still running"""
        pid = info.get("pid")
        if pid and psutil.pid_exists(pid):
            try:
                process = psutil.Process(pid)
                if process.is_running():
                    started_at = info.get("started_at")
                    uptime = None
                    if started_at:
                        start_time = datetime.fromisoformat(started_at)
                        uptime = int((datetime.now() - start_time).total_seconds())

                    return {
                        "id": monitor_id,
                        "agent_name": info.get("agent_name"),
                        "monitor_type": info.get("monitor_type"),
                        "status": "running",
                        "pid": pid,
                        "started_at": started_at,
                        "uptime_seconds": uptime,
                        "config_path": info.get("config_path"),
                        "model": info.get("model"),
                        "provider": info.get("provider"),
                        "system_prompt_name": info.get("system_prompt_name"),
                        "mcp_servers": info.get("mcp_servers", []),
                        "environment": info.get("environment", "local"),
                        "deployment_group": info.get("deployment_group"),
                    }
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        # Process not running
        return {
            "id": monitor_id,
            "agent_name": info.get("agent_name"),
            "monitor_type": info.get("monitor_type"),
            "status": "stopped",
            "pid": None,
            "started_at": info.get("started_at"),
            "uptime_seconds": None,
            "config_path": info.get("config_path"),
            "model": info.get("model"),
            "provider": info.get("provider"),
            "system_prompt_name": info.get("system_prompt_name"),
            "mcp_servers": info.get("mcp_servers", []),
            "environment": info.get("environment", "local"),
            "deployment_group": info.get("deployment_group"),
        }

    async def start_monitor(
        self,
        agent_name: str,
        config_path: str,
        monitor_type: Literal[
            "echo", "ollama", "langgraph", "claude_agent_sdk", "openai_agents_sdk"
        ],
        model: str | None = None,
        provider: str | None = None,
        system_prompt: str | None = None,
        system_prompt_name: str | None = None,
        history_limit: int | None = 25,
    ) -> str:
        """Start a monitor process"""
        # Resolve config_path to full path if it's just a filename
        # API sends just filename, but monitors need full path
        if not os.path.isabs(config_path) and not config_path.startswith("configs/"):
            # Convert filename to full path
            full_config_path = self.base_dir / "configs" / "agents" / config_path
            if not full_config_path.exists():
                raise FileNotFoundError(f"Config file not found: {config_path}")
            config_path = str(full_config_path)

        # Sanitize agent_name to prevent shell injection and path traversal
        safe_agent_name = sanitize_agent_name(agent_name)

        # Kill any existing monitors for this agent (in our tracking)
        for monitor_id, info in list(self.monitors.items()):
            if info.get("agent_name") == agent_name and info.get("monitor_type") == monitor_type:
                print(f"Stopping existing {monitor_type} monitor for {agent_name}")
                await self.stop_monitor(monitor_id)
                self.delete_monitor(monitor_id)

        # Always clear local SQLite queue on startup
        # Queue is just a trigger - agent fetches last 25 messages for context each time
        print(f"Starting {agent_name} - clearing local queue")
        try:
            local_cleared = self.message_store.clear_agent(agent_name)
            if local_cleared > 0:
                print(f"   Cleared {local_cleared} local messages from SQLite queue")
        except Exception as e:
            print(f"Warning: Failed to clear local queue: {e}")

        # CRITICAL: Also kill any orphaned system processes for this agent
        # This prevents the "competing monitors" problem
        # Using psutil instead of pkill to avoid shell injection
        print(f"Checking for orphaned {agent_name} processes...")
        try:
            killed_count = 0
            # Find all Python processes running our monitors
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    cmdline = proc.info.get("cmdline", [])
                    if cmdline and isinstance(cmdline, list):
                        lower_args = [arg.lower() for arg in cmdline if isinstance(arg, str)]
                        # Match monitor processes for this specific agent
                        if (
                            any("ax_agent_studio.monitors" in arg for arg in lower_args)
                            and agent_name.lower()
                            in (arg.lower() for arg in cmdline if isinstance(arg, str))
                            and proc.pid != os.getpid()
                        ):  # Don't kill ourselves
                            print(
                                f"  Killing orphaned process PID {proc.pid}: {' '.join(cmdline[:3])}..."
                            )
                            proc.kill()
                            killed_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass

            if killed_count > 0:
                # Small delay to ensure processes are killed
                await asyncio.sleep(0.5)
                print(f"Cleaned up {killed_count} orphaned {agent_name} process(es)")
            else:
                print(f"No orphaned processes found for {agent_name}")
        except Exception as e:
            print(f"Error cleaning up processes: {e}")

        # Clean up old log files for this agent to prevent log confusion
        # Delete all log files that match the pattern {safe_agent_name}_{monitor_type}_*.log
        # Use sanitized name to prevent path traversal
        print(f"Cleaning up old log files for {agent_name}...")
        try:
            pattern = f"{safe_agent_name}_{monitor_type}_*.log"
            old_log_files = list(self.log_dir.glob(pattern))
            for old_log_file in old_log_files:
                old_log_file.unlink()
                print(f"Deleted old log file: {old_log_file.name}")
            if old_log_files:
                print(f"Cleaned up {len(old_log_files)} old log file(s)")
        except Exception as e:
            print(f"Error cleaning up log files: {e}")

        # Use sanitized agent name in monitor_id to prevent path traversal in log files
        monitor_id = f"{safe_agent_name}_{monitor_type}_{uuid.uuid4().hex[:8]}"
        log_file = self.log_dir / f"{monitor_id}.log"

        # Get Python from venv (no uv wrapper - cleaner process tree)
        venv_dir = self.base_dir / ".venv"
        if os.name == "nt":
            venv_python = venv_dir / "Scripts" / "python.exe"
        else:
            venv_python = venv_dir / "bin" / "python"
        if not venv_python.exists():
            raise FileNotFoundError(
                f"Virtual environment not found at {venv_python}. Run 'uv sync' first."
            )

        # Build command based on monitor type
        # IMPORTANT: Pass original agent_name so monitors join correct MCP channels
        if monitor_type == "echo":
            cmd = [
                str(venv_python),
                "-u",
                "-m",
                "ax_agent_studio.monitors.echo_monitor",
                agent_name,
                "--config",
                config_path,
            ]
        elif monitor_type == "ollama":
            cmd = [
                str(venv_python),
                "-u",
                "-m",
                "ax_agent_studio.monitors.ollama_monitor",
                agent_name,
                "--config",
                config_path,
            ]
            if model:
                cmd.extend(["--model", model])
            if history_limit is not None:
                cmd.extend(["--history-limit", str(history_limit)])
        elif monitor_type == "langgraph":
            cmd = [
                str(venv_python),
                "-u",
                "-m",
                "ax_agent_studio.monitors.langgraph_monitor",
                agent_name,
                "--config",
                config_path,
            ]
            if model:
                cmd.extend(["--model", model])
            if provider:
                cmd.extend(["--provider", provider])
            if history_limit is not None:
                cmd.extend(["--history-limit", str(history_limit)])
        elif monitor_type == "claude_agent_sdk":
            cmd = [
                str(venv_python),
                "-u",
                "-m",
                "ax_agent_studio.monitors.claude_agent_sdk_monitor",
                agent_name,
                "--config",
                config_path,
            ]
            if model:
                cmd.extend(["--model", model])
        elif monitor_type == "openai_agents_sdk":
            cmd = [
                str(venv_python),
                "-u",
                "-m",
                "ax_agent_studio.monitors.openai_agents_monitor",
                agent_name,
                "--config",
                config_path,
            ]
            if model:
                cmd.extend(["--model", model])
        else:
            raise ValueError(f"Unknown monitor type: {monitor_type}")

        # Prepare environment variables (include system prompt if provided)
        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.base_dir / "src")  # Needed since we're not using uv run
        if system_prompt:
            env["AGENT_SYSTEM_PROMPT"] = system_prompt

        with open(log_file, "w", encoding="utf-8") as f:
            f.write(f"=== Monitor started at {datetime.now().isoformat()} ===\n")
            f.write(f"Command: {' '.join(cmd)}\n")
            f.write(f"Agent: {safe_agent_name}\n")
            f.write(f"Type: {monitor_type}\n")
            if model:
                f.write(f"Model: {model}\n")
            if provider:
                f.write(f"Provider: {provider}\n")
            if system_prompt_name:
                f.write(f"System Prompt: {system_prompt_name}\n")
            f.write("=" * 50 + "\n\n")

        # Start process (using exec directly instead of shell)
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=str(self.base_dir),
            env=env,
            start_new_session=True,  # Cross-platform process group creation (Windows compatible)
        )

        # Load config to get MCP servers and auto-detect environment
        mcp_servers = []
        environment = "local"
        try:
            with open(config_path) as f:
                config_data = json.load(f)
                if "mcpServers" in config_data:
                    mcp_servers = list(config_data["mcpServers"].keys())

                    # Auto-detect environment from MCP server URLs
                    # Look for ax-docker/ax-gcp server to determine environment
                    for server_name, server_config in config_data["mcpServers"].items():
                        if server_name.startswith("ax-"):
                            args = server_config.get("args", [])
                            # Find URL in args
                            for arg in args:
                                if isinstance(arg, str) and "/mcp/agents/" in arg:
                                    # localhost = local, otherwise = production
                                    environment = "local" if "localhost" in arg else "production"
                                    break
                            break
        except Exception as e:
            print(f"Error loading config for monitor info: {e}")

        # Store monitor info
        self.monitors[monitor_id] = {
            "agent_name": agent_name,
            "monitor_type": monitor_type,
            "pid": process.pid,
            "started_at": datetime.now().isoformat(),
            "config_path": config_path,
            "model": model,
            "provider": provider,
            "system_prompt_name": system_prompt_name,
            "system_prompt": system_prompt,
            "mcp_servers": mcp_servers,
            "environment": environment,
            "log_file": str(log_file),
            "process": process,
        }

        # Start log tailing task
        asyncio.create_task(self._tail_process_output(monitor_id, process, log_file))

        return monitor_id

    async def clear_agent_backlog(
        self, agent_name: str, config_path: str | None = None
    ) -> dict[str, Any]:
        """Clear MCP backlog and local queue for a single agent."""
        summary = {"agent": agent_name, "remote_cleared": 0, "local_cleared": 0, "errors": []}

        if not config_path:
            try:
                config_path = str(self._get_agent_config_path(agent_name))
            except FileNotFoundError as e:
                summary["errors"].append(str(e))
                config_path = None

        try:
            summary["local_cleared"] = self.message_store.clear_agent(agent_name)
        except Exception as e:
            summary["errors"].append(f"local: {e}")

        try:
            async with MCPServerManager(agent_name) as manager:
                primary_session = manager.get_primary_session()

                max_iterations = 200  # Safety limit to prevent infinite loops
                iteration = 0

                while iteration < max_iterations:
                    result = await primary_session.call_tool(
                        "messages",
                        {
                            "action": "check",
                            "wait": False,
                            "mark_read": True,
                            "limit": 10,  # Batch process up to 10 at a time
                        },
                    )
                    mention_count = self._count_mentions(result)
                    if mention_count == 0:
                        break
                    summary["remote_cleared"] += mention_count
                    iteration += 1

                    # CRITICAL: Rate limit protection - wait between requests
                    # MCP server rate limit: ~100 req/min, so 0.7s = ~85 req/min (safe)
                    await asyncio.sleep(0.7)

                if iteration >= max_iterations:
                    summary["errors"].append(
                        f"Hit max iterations ({max_iterations}) - backlog may not be fully cleared"
                    )
        except Exception as e:
            summary["errors"].append(f"remote: {e}")

        if summary["errors"]:
            print(f"Reset backlog warnings for {agent_name}: {', '.join(summary['errors'])}")

        return summary

    async def clear_agents_backlog(
        self, agent_names: list[str] | None = None, environment: str | None = None
    ) -> dict[str, Any]:
        """Clear backlog for multiple agents."""
        monitors_snapshot = self.get_all_monitors()
        agent_state: dict[str, dict[str, Any]] = {}

        for monitor in monitors_snapshot:
            name = monitor.get("agent_name")
            if not name:
                continue
            state = agent_state.setdefault(name, {"running": False, "environments": set()})
            if monitor.get("status") == "running":
                state["running"] = True
            env = monitor.get("environment") or "any"
            state["environments"].add(env)

        agents_to_reset: set[str] = set()
        skipped_running: set[str] = set()

        if not agent_names:
            for name, state in agent_state.items():
                if (
                    environment
                    and environment not in state["environments"]
                    and environment != "any"
                ):
                    continue
                if state["running"]:
                    skipped_running.add(name)
                    continue
                agents_to_reset.add(name)
        else:
            for name in agent_names:
                state = agent_state.get(name)
                if state and state["running"]:
                    skipped_running.add(name)
                    continue
                if (
                    state
                    and environment
                    and environment not in state["environments"]
                    and environment != "any"
                ):
                    continue
                agents_to_reset.add(name)

        unique_agents = sorted(agents_to_reset)
        results = []
        for agent in unique_agents:
            summary = await self.clear_agent_backlog(agent)
            results.append(summary)

        return {
            "count": len(unique_agents),
            "results": results,
            "skipped_running": sorted(skipped_running),
        }

    def _count_mentions(self, result) -> int:
        """Determine how many mentions were returned in an MCP messages response."""
        if hasattr(result, "events") and result.events:
            return len(result.events)

        content = getattr(result, "content", None)
        text = ""

        if hasattr(content, "text") and content.text:
            text = content.text
        elif isinstance(content, list) and content:
            texts = []
            for item in content:
                if hasattr(item, "text") and item.text:
                    texts.append(item.text)
            text = "\n".join(texts)

        text = (text or "").strip()
        if not text:
            return 0

        if "No mentions found" in text:
            return 0

        match = re.search(r"Found\s+(\d+)\s+mention", text)
        if match:
            return int(match.group(1))

        if "• " in text:
            return text.count("• ")

        return 1

    async def start_deployment_group(
        self, group_id: str, environment: str | None = None
    ) -> dict[str, Any]:
        """Start all monitors defined in a deployment group."""
        group = self.deployment_loader.get_group(group_id)
        if not group:
            raise ValueError(f"Deployment group '{group_id}' not found")

        if environment and group.environment not in ("any", environment):
            raise ValueError(f"Group '{group_id}' is not available for environment '{environment}'")

        # Stop existing deployment if already running
        if group_id in self.group_deployments and self.group_deployments[group_id].get("monitors"):
            await self.stop_deployment_group(group_id)

        started_monitor_ids: list[str] = []
        record = {
            "monitors": started_monitor_ids,
            "group_id": group_id,
            "started_at": datetime.now().isoformat(),
            "status": "starting",
        }
        self.group_deployments[group_id] = record

        defaults = group.defaults or {}

        for agent in group.agents:
            monitor_type = agent.monitor or defaults.get("monitor") or "langgraph"
            provider = agent.provider or defaults.get("provider")
            model = agent.model or defaults.get("model")
            prompt_ref = agent.system_prompt or defaults.get("system_prompt")
            system_prompt, system_prompt_name = self._resolve_system_prompt(prompt_ref)
            start_delay_ms = agent.start_delay_ms or defaults.get("start_delay_ms", 0)

            if monitor_type not in {
                "echo",
                "ollama",
                "langgraph",
                "claude_agent_sdk",
                "openai_agents_sdk",
            }:
                raise ValueError(f"Unsupported monitor type '{monitor_type}' in group '{group_id}'")

            config_path = self._get_agent_config_path(agent.id)
            monitor_id = await self.start_monitor(
                agent_name=agent.id,
                config_path=str(config_path),
                monitor_type=monitor_type,  # type: ignore[arg-type]
                model=model,
                provider=provider,
                system_prompt=system_prompt,
                system_prompt_name=system_prompt_name,
            )

            started_monitor_ids.append(monitor_id)
            self.monitors[monitor_id]["deployment_group"] = group_id

            if start_delay_ms:
                await asyncio.sleep(start_delay_ms / 1000.0)

        record["status"] = "running"
        return {
            "group_id": group_id,
            "monitors": started_monitor_ids,
            "started_at": record["started_at"],
            "started_count": len(started_monitor_ids),
        }

    async def stop_deployment_group(self, group_id: str) -> int:
        """Stop all monitors that were started as part of a deployment group."""
        record = self.group_deployments.get(group_id)
        if not record:
            return 0

        monitor_ids = list(record.get("monitors", []))
        stopped = 0

        for monitor_id in monitor_ids:
            if await self.stop_monitor(monitor_id):
                stopped += 1

        record["monitors"] = []
        record["status"] = "stopped"
        record["stopped_at"] = datetime.now().isoformat()

        return stopped

    def get_deployment_groups(self, environment: str | None = None) -> list[dict[str, Any]]:
        """Return deployment groups with runtime status."""
        groups = self.deployment_loader.list_groups(environment)
        response: list[dict[str, Any]] = []

        for group in groups:
            record = self.group_deployments.get(group.id, {})
            monitor_ids: list[str] = record.get("monitors", [])

            running_ids = []
            for monitor_id in monitor_ids:
                info = self.monitors.get(monitor_id, {})
                status = self._get_monitor_status(monitor_id, info)
                if status["status"] == "running":
                    running_ids.append(monitor_id)

            response.append(
                {
                    "id": group.id,
                    "name": group.name,
                    "description": group.description,
                    "defaults": group.defaults,
                    "tags": group.tags,
                    "environment": group.environment,
                    "total_agents": len(group.agents),
                    "running_count": len(running_ids),
                    "monitor_ids": monitor_ids,
                    "status": "running" if running_ids else "stopped",
                    "started_at": record.get("started_at"),
                    "stopped_at": record.get("stopped_at"),
                    "agents": [
                        {
                            "id": agent.id,
                            "monitor": agent.monitor,
                            "provider": agent.provider,
                            "model": agent.model,
                            "system_prompt": agent.system_prompt,
                            "start_delay_ms": agent.start_delay_ms,
                        }
                        for agent in group.agents
                    ],
                }
            )

        return response

    def reload_deployment_groups(self) -> None:
        """Reload deployment group configuration from disk."""
        self.deployment_loader.reload()

    def _deregister_monitor_from_group(self, monitor_id: str) -> None:
        """Remove monitor from any group tracking structures."""
        group_id = self.monitors.get(monitor_id, {}).get("deployment_group")
        if not group_id:
            # Fallback: search all groups
            for gid, record in self.group_deployments.items():
                if monitor_id in record.get("monitors", []):
                    group_id = gid
                    break

        if not group_id:
            return

        record = self.group_deployments.get(group_id)
        if not record:
            return

        monitors = record.get("monitors", [])
        if monitor_id in monitors:
            monitors.remove(monitor_id)

        if not monitors:
            record["status"] = "stopped"
            record["stopped_at"] = datetime.now().isoformat()

    def _mark_monitor_inactive(self, monitor_id: str) -> None:
        """Reset runtime metadata once a monitor stops or is killed."""
        info = self.monitors.get(monitor_id)
        if not info:
            return

        info["pid"] = None
        info["process"] = None
        info["stopped_at"] = datetime.now().isoformat()

    async def _tail_process_output(self, monitor_id: str, process, log_file: Path):
        """Tail process output to log file"""
        try:
            with open(log_file, "a", encoding="utf-8", errors="replace") as f:
                async for line in process.stdout:
                    f.write(line.decode("utf-8", errors="replace"))
                    f.flush()
        except Exception as e:
            print(f"Error tailing output for {monitor_id}: {e}")

    async def stop_monitor(self, monitor_id: str) -> bool:
        """Stop a monitor gracefully (stops entire process group)"""
        if monitor_id not in self.monitors:
            return False

        info = self.monitors[monitor_id]
        pid = info.get("pid")

        if not pid or not psutil.pid_exists(pid):
            # Already stopped (or never fully started). Treat as success so UI can proceed.
            self._mark_monitor_inactive(monitor_id)
            self._deregister_monitor_from_group(monitor_id)
            return True

        try:
            process = psutil.Process(pid)

            # Try graceful shutdown first (SIGTERM to process group)
            if hasattr(os, "getpgid"):
                try:
                    pgid = os.getpgid(pid)
                    os.killpg(pgid, signal.SIGTERM)
                    print(f"Sent SIGTERM to process group {pgid} for monitor {monitor_id}")
                except (ProcessLookupError, PermissionError, AttributeError):
                    # Fallback to single process
                    process.terminate()
            else:
                process.terminate()

            # Wait up to 5 seconds for graceful shutdown
            try:
                process.wait(timeout=5)
            except psutil.TimeoutExpired:
                # Force kill entire process group if still running
                if hasattr(os, "getpgid"):
                    try:
                        pgid = os.getpgid(pid)
                        os.killpg(pgid, signal.SIGKILL)
                        print(f"Force killed process group {pgid} for monitor {monitor_id}")
                    except (ProcessLookupError, PermissionError, AttributeError):
                        process.kill()
                else:
                    process.kill()
                process.wait()

            # Log shutdown
            log_file = Path(info.get("log_file"))
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"\n=== Monitor stopped at {datetime.now().isoformat()} ===\n")

            self._mark_monitor_inactive(monitor_id)
            self._deregister_monitor_from_group(monitor_id)

            return True

        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            print(f"Error stopping monitor {monitor_id}: {e}")
            return False

    async def restart_monitor(self, monitor_id: str) -> bool:
        """Restart a monitor with same configuration"""
        if monitor_id not in self.monitors:
            return False

        info = self.monitors[monitor_id]

        # Stop existing process
        await self.stop_monitor(monitor_id)

        # Start new process with same config (preserve ALL settings)
        new_id = await self.start_monitor(
            agent_name=info["agent_name"],
            config_path=info["config_path"],
            monitor_type=info["monitor_type"],
            model=info.get("model"),
            provider=info.get("provider"),
            system_prompt=info.get("system_prompt"),
            system_prompt_name=info.get("system_prompt_name"),
        )

        # Remove old monitor entry
        del self.monitors[monitor_id]

        return True

    async def stop_all_monitors(self) -> int:
        """Stop all running monitors"""
        count = 0
        monitor_ids = list(self.monitors.keys())

        for monitor_id in monitor_ids:
            if await self.stop_monitor(monitor_id):
                count += 1

        return count

    async def kill_monitor(self, monitor_id: str) -> bool:
        """Force kill a monitor immediately (kills entire process tree)"""
        info = None
        pid: int | None = None
        tracked_monitor = False

        # Handle orphaned monitors (monitor_id format: "orphan_12345")
        if monitor_id.startswith("orphan_"):
            try:
                pid = int(monitor_id.split("_")[1])
                if not psutil.pid_exists(pid):
                    return False
            except (ValueError, IndexError):
                return False
        else:
            info = self.monitors.get(monitor_id)
            if not info:
                return False

            tracked_monitor = True
            pid = info.get("pid")

            if not pid or not psutil.pid_exists(pid):
                # Already dead - treat as success so caller can clean up dashboard state
                self._mark_monitor_inactive(monitor_id)
                self._deregister_monitor_from_group(monitor_id)
                return True

        try:
            process = psutil.Process(pid)

            # Kill ALL descendants (children, grandchildren, etc.)
            # This is critical for `uv run` which creates deep process trees
            children = process.children(recursive=True)
            print(f"Killing {len(children)} child processes for monitor {monitor_id}")

            # Kill children first (bottom-up)
            for child in children:
                try:
                    child.kill()
                    print(f"  Killed child PID {child.pid}")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            # Then kill the parent
            process.kill()
            print(f"Killed parent process {pid} for monitor {monitor_id}")

            # Try process group as backup (in case we missed something)
            try:
                pgid = os.getpgid(pid)
                os.killpg(pgid, signal.SIGKILL)
                print(f"Killed process group {pgid} for monitor {monitor_id}")
            except (ProcessLookupError, PermissionError):
                pass

            process.wait()

            if tracked_monitor and info:
                log_file = info.get("log_file")
                if log_file:
                    with open(Path(log_file), "a", encoding="utf-8") as f:
                        f.write(
                            f"\n=== Monitor killed (forced) at {datetime.now().isoformat()} ===\n"
                        )

                self._mark_monitor_inactive(monitor_id)
                self._deregister_monitor_from_group(monitor_id)

            return True

        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            print(f"Error killing monitor {monitor_id}: {e}")
            return False

    async def cleanup_orphaned_monitors(self) -> int:
        """
        Detect and kill all orphaned monitors on startup.

        Orphaned monitors are processes left running from a previous
        dashboard session (ungraceful shutdown, crash, kill -9, etc).

        Returns count of orphaned monitors killed.
        """
        all_monitors = self.get_all_monitors()
        orphaned = [m for m in all_monitors if not m.get("tracked", True)]

        killed_count = 0
        for monitor in orphaned:
            monitor_id = monitor["id"]
            agent_name = monitor["agent_name"]
            print(f"🧹 Cleaning up orphaned monitor: {agent_name} (PID: {monitor['pid']})")

            try:
                success = await self.kill_monitor(monitor_id)
                if success:
                    killed_count += 1
                    print(f"   ✓ Killed orphaned monitor {monitor_id}")
                else:
                    print(f"   ⚠ Failed to kill orphaned monitor {monitor_id}")
            except Exception as e:
                print(f"   ❌ Error killing orphaned monitor {monitor_id}: {e}")

        if killed_count > 0:
            print(f"✓ Cleanup complete: killed {killed_count} orphaned monitor(s)")

        return killed_count

    def delete_monitor(self, monitor_id: str) -> bool:
        """Remove a monitor from the list (must be stopped first)"""
        if monitor_id not in self.monitors:
            return False

        info = self.monitors[monitor_id]
        pid = info.get("pid")

        # Check if still running
        if pid and psutil.pid_exists(pid):
            try:
                process = psutil.Process(pid)
                if process.is_running():
                    return False  # Can't delete a running monitor
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        # Remove from monitors dict
        self._deregister_monitor_from_group(monitor_id)
        del self.monitors[monitor_id]
        return True

    def delete_all_stopped_monitors(self) -> int:
        """Delete all stopped monitors from the list"""
        count = 0
        monitor_ids = list(self.monitors.keys())

        for monitor_id in monitor_ids:
            info = self.monitors[monitor_id]
            pid = info.get("pid")

            # Check if stopped
            is_stopped = True
            if pid and psutil.pid_exists(pid):
                try:
                    process = psutil.Process(pid)
                    if process.is_running():
                        is_stopped = False
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            if is_stopped:
                del self.monitors[monitor_id]
                count += 1

        return count

    async def start_demo(
        self,
        demo_type: Literal["round_robin", "scrum_team"],
        agents: list[str],
        loops: int = 5,
        delay: int = 8,
        enable_tools: bool = True,
    ) -> str:
        """Start a demo script"""
        # Sanitize all agent names to prevent shell injection
        safe_agents = [sanitize_agent_name(agent) for agent in agents]

        demo_id = f"demo_{demo_type}_{uuid.uuid4().hex[:8]}"
        log_file = self.log_dir / f"{demo_id}.log"

        # Get Python from venv (no uv wrapper)
        venv_python = self.base_dir / ".venv" / "bin" / "python"
        if not venv_python.exists():
            raise FileNotFoundError(
                f"Virtual environment not found at {venv_python}. Run 'uv sync' first."
            )

        # Build demo command using venv's python directly
        if demo_type == "round_robin":
            if len(safe_agents) < 2:
                raise ValueError("Round robin requires at least 2 agents")
            cmd = [
                str(venv_python),
                "multi_agent_loop.py",
                *safe_agents,
                "--loops",
                str(loops),
                "--delay",
                str(delay),
            ]
        elif demo_type == "scrum_team":
            if len(safe_agents) < 3:
                raise ValueError("Scrum team requires 3 agents")
            cmd = [
                str(venv_python),
                "demo_scrum_team.py",
                *safe_agents[:3],  # Only use first 3 agents
            ]
        else:
            raise ValueError(f"Unknown demo type: {demo_type}")

        with open(log_file, "w", encoding="utf-8") as f:
            f.write(f"=== Demo started at {datetime.now().isoformat()} ===\n")
            f.write(f"Type: {demo_type}\n")
            f.write(f"Agents: {', '.join(safe_agents)}\n")
            f.write(f"Command: {' '.join(cmd)}\n")
            f.write("=" * 50 + "\n\n")

        # Set up environment (needed since we're not using uv run)
        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.base_dir / "src")

        # Use create_subprocess_exec instead of shell (prevents injection, works on Windows)
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=str(self.base_dir),
            env=env,
            start_new_session=True,  # Cross-platform process group
        )

        # Store demo info (treat as special monitor)
        self.monitors[demo_id] = {
            "agent_name": f"demo_{demo_type}",
            "monitor_type": "demo",
            "pid": process.pid,
            "started_at": datetime.now().isoformat(),
            "config_path": "",
            "model": None,
            "log_file": str(log_file),
            "process": process,
            "demo_type": demo_type,
            "demo_agents": agents,
        }

        # Start log tailing
        asyncio.create_task(self._tail_process_output(demo_id, process, log_file))

        return demo_id

    async def send_test_message(
        self,
        from_agent: str,
        to_agent: str,
        message: str,
        from_agent_environment: str | None = None,
    ) -> bool:
        """Send a test message from one agent to another

        Args:
            from_agent: Name of the agent sending the message
            to_agent: Name of the agent receiving the message
            message: Message content
            from_agent_environment: Environment of the from_agent (to find correct server URL)
        """
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        # Find the from_agent's config to get the correct server URL
        from_agent_config = None
        if from_agent_environment:
            # Look up agent in specific environment
            configs = self.config_loader.list_configs(from_agent_environment)
            from_agent_config = next((c for c in configs if c["agent_name"] == from_agent), None)
        else:
            # Fallback: search all environments
            all_configs = self.config_loader.list_configs()
            from_agent_config = next(
                (c for c in all_configs if c["agent_name"] == from_agent), None
            )

        if not from_agent_config:
            raise ValueError(
                f"Test sender agent '{from_agent}' not found"
                + (f" in environment '{from_agent_environment}'" if from_agent_environment else "")
            )

        # Get server URL and OAuth URL from the agent's config
        server_url = from_agent_config.get("server_url")
        oauth_url = from_agent_config.get("oauth_url")

        if not server_url or not oauth_url:
            raise ValueError(f"Agent '{from_agent}' config is missing server_url or oauth_url")

        server_params = StdioServerParameters(
            command="npx",
            args=[
                "-y",
                "mcp-remote@0.1.29",
                server_url,
                "--transport",
                "http-only",
                "--allow-http",
                "--oauth-server",
                oauth_url,
            ],
        )

        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    # Send message with @mention
                    full_message = f"@{to_agent} {message}"

                    await session.call_tool("messages", {"action": "send", "content": full_message})

                    return True
        except Exception as e:
            print(f"Error sending message from {from_agent} ({from_agent_environment}): {e}")
            raise
