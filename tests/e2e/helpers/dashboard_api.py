"""
Dashboard API helpers for E2E testing

Uses FastAPI backend endpoints instead of Chrome DevTools UI automation.
Much faster, more reliable, and easier to maintain.
"""

import httpx


class DashboardAPI:
    """Helper class for interacting with Dashboard backend API"""

    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.client = httpx.Client(base_url=base_url, timeout=30.0)

    def kill_all_monitors(self) -> dict:
        """Nuclear option: Kill all monitors + activate kill switch"""
        response = self.client.post("/api/monitors/kill-all")
        response.raise_for_status()
        return response.json()

    def deactivate_kill_switch(self) -> dict:
        """Deactivate kill switch to resume agents"""
        response = self.client.post("/api/kill-switch/deactivate")
        response.raise_for_status()
        return response.json()

    def start_monitor(
        self,
        agent_name: str,
        monitor_type: str,
        config_path: str | None = None,
        model: str | None = None,
        provider: str | None = None,
        system_prompt: str | None = None,
        system_prompt_name: str | None = None,
        history_limit: int = 25,
    ) -> dict:
        """Start a new monitor

        Args:
            agent_name: Agent name (e.g., "ghost_ray_363")
            monitor_type: One of: echo, ollama, claude_agent_sdk, openai_agents_sdk, langgraph
            config_path: Path to agent config (auto-generated if None)
            model: Model name (required for AI monitors)
            provider: Provider name (required for AI monitors)
            system_prompt: Custom system prompt
            system_prompt_name: Name of system prompt file
            history_limit: Message history limit
        """
        if config_path is None:
            config_path = f"configs/agents/{agent_name}.json"

        payload = {
            "config": {
                "agent_name": agent_name,
                "config_path": config_path,
                "monitor_type": monitor_type,
                "model": model,
                "provider": provider,
                "system_prompt": system_prompt,
                "system_prompt_name": system_prompt_name,
                "history_limit": history_limit,
            }
        }

        response = self.client.post("/api/monitors/start", json=payload)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            # Include detail message from response body in error
            try:
                error_data = e.response.json()
                detail = error_data.get("detail", str(e))
            except Exception:
                detail = str(e)
            raise Exception(f"HTTP {e.response.status_code}: {detail}") from None
        return response.json()

    def stop_monitor(self, monitor_id: str) -> dict:
        """Stop a specific monitor"""
        response = self.client.post("/api/monitors/stop", json={"monitor_id": monitor_id})
        response.raise_for_status()
        return response.json()

    def list_monitors(self) -> list[dict]:
        """List all monitors"""
        response = self.client.get("/api/monitors")
        response.raise_for_status()
        return response.json()["monitors"]

    def get_monitor_by_agent(self, agent_name: str) -> dict | None:
        """Get monitor info for a specific agent"""
        monitors = self.list_monitors()
        for monitor in monitors:
            if monitor["agent_name"] == agent_name:
                return monitor
        return None

    def wait_for_monitor_running(self, agent_name: str, timeout: int = 10) -> bool:
        """Wait for a monitor to reach RUNNING status

        Returns True if monitor is running, False if timeout
        """
        import time

        start = time.time()
        while time.time() - start < timeout:
            monitor = self.get_monitor_by_agent(agent_name)
            if monitor and monitor["status"] == "running":
                return True
            time.sleep(0.5)
        return False

    def wait_for_monitor_ready(self, agent_name: str, timeout: int = 15) -> bool:
        """Wait for a monitor to be fully initialized and ready to process messages

        Checks the log file for initialization markers:
        - "✓ Starting FIFO queue manager..." (monitors ready to process)
        - "✓ Connected to MCP server" (MCP connection established)

        Returns True if monitor is ready, False if timeout
        """
        import time
        from pathlib import Path

        # First wait for RUNNING status
        if not self.wait_for_monitor_running(agent_name, timeout=timeout):
            return False

        # Get monitor ID to find log file
        monitor = self.get_monitor_by_agent(agent_name)
        if not monitor:
            return False

        monitor_id = monitor["id"]
        log_file = Path("logs") / f"{monitor_id}.log"

        # Wait for initialization marker in log file
        start = time.time()
        while time.time() - start < timeout:
            if log_file.exists():
                try:
                    content = log_file.read_text()
                    # Check for queue manager start (final init step)
                    # Different monitors have different formats:
                    # Echo: "✓ Starting FIFO queue manager..."
                    # Ollama/others: " Starting FIFO queue manager..."
                    if "Starting FIFO queue manager" in content:
                        return True
                except Exception:
                    pass
            time.sleep(0.2)
        return False

    def cleanup_all(self):
        """Clean slate: kill all monitors and deactivate kill switch"""
        result = self.kill_all_monitors()
        self.deactivate_kill_switch()
        return result

    def close(self):
        """Close HTTP client"""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
