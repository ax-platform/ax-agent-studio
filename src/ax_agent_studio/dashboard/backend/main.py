"""
Monitor Dashboard Backend
FastAPI server for managing MCP monitor processes
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Optional, Literal
import asyncio
import json
import os
import psutil
from pathlib import Path
from datetime import datetime

from ax_agent_studio.dashboard.backend.process_manager import ProcessManager
from ax_agent_studio.dashboard.backend.config_loader import ConfigLoader
from ax_agent_studio.dashboard.backend.log_streamer import LogStreamer
from ax_agent_studio.dashboard.backend.providers_loader import (
    get_providers_list,
    get_models_for_provider,
    get_defaults
)

app = FastAPI(title="MCP Monitor Dashboard", version="1.0.0")

# CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize managers
# Project root is 4 levels up: backend -> dashboard -> ax_agent_studio -> src -> root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
process_manager = ProcessManager(PROJECT_ROOT)
config_loader = ConfigLoader(PROJECT_ROOT)
log_streamer = LogStreamer(PROJECT_ROOT / "logs")

# Pydantic models
class MonitorConfig(BaseModel):
    agent_name: str
    config_path: str
    monitor_type: Literal["echo", "ollama", "langgraph"]
    model: Optional[str] = None
    provider: Optional[str] = None
    system_prompt: Optional[str] = None
    system_prompt_name: Optional[str] = None
    process_backlog: Optional[bool] = False  # Always start fresh, don't process old messages

class MonitorStatus(BaseModel):
    id: str
    agent_name: str
    monitor_type: str
    status: Literal["running", "stopped", "error"]
    pid: Optional[int] = None
    started_at: Optional[str] = None
    uptime_seconds: Optional[int] = None
    config_path: str
    model: Optional[str] = None
    provider: Optional[str] = None
    system_prompt_name: Optional[str] = None
    mcp_servers: Optional[List[str]] = None
    environment: Optional[str] = None

class DemoConfig(BaseModel):
    demo_type: Literal["round_robin", "scrum_team"]
    agents: List[str]
    loops: int = 5
    delay: int = 8
    enable_tools: bool = True

class SendMessageRequest(BaseModel):
    from_agent: str
    to_agent: str
    message: str

class StartMonitorRequest(BaseModel):
    config: MonitorConfig

class StopMonitorRequest(BaseModel):
    monitor_id: str

class DeploymentActionRequest(BaseModel):
    environment: Optional[str] = None

class ResetAgentsRequest(BaseModel):
    agents: Optional[List[str]] = None
    environment: Optional[str] = None

# API Routes

@app.get("/")
async def root():
    """Serve the dashboard HTML"""
    frontend_path = Path(__file__).parent.parent / "frontend" / "index.html"
    return FileResponse(frontend_path)

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "monitors_running": len(process_manager.get_running_monitors())
    }

@app.get("/api/processes/health")
async def processes_health():
    """Get detailed process health status (dashboards + monitors)"""
    processes = {
        "dashboards": [],
        "monitors": [],
        "total_memory_mb": 0,
        "warning": False,
        "warning_message": None
    }

    current_pid = os.getpid()

    # Find all dashboard processes
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time', 'memory_info']):
        try:
            cmdline = proc.info['cmdline']
            if not cmdline:
                continue

            cmdline_str = ' '.join(cmdline)

            # Dashboard processes
            if 'uvicorn' in cmdline_str and 'dashboard' in cmdline_str:
                memory_mb = proc.info['memory_info'].rss / 1024 / 1024
                uptime_seconds = int(datetime.now().timestamp() - proc.info['create_time'])

                processes['dashboards'].append({
                    'pid': proc.info['pid'],
                    'is_current': proc.info['pid'] == current_pid,
                    'started_at': datetime.fromtimestamp(proc.info['create_time']).isoformat(),
                    'uptime_seconds': uptime_seconds,
                    'memory_mb': round(memory_mb, 1)
                })
                processes['total_memory_mb'] += memory_mb

            # Monitor processes (only Python processes, not uv wrapper)
            elif 'ax_agent_studio.monitors' in cmdline_str:
                # Filter out uv wrapper - only match actual Python processes
                proc_name = proc.info.get('name', '').lower()
                if 'python' not in proc_name:
                    continue

                memory_mb = proc.info['memory_info'].rss / 1024 / 1024
                uptime_seconds = int(datetime.now().timestamp() - proc.info['create_time'])

                # Extract agent name from cmdline
                agent_name = None
                for i, arg in enumerate(cmdline):
                    if 'monitors.' in arg and i + 1 < len(cmdline):
                        agent_name = cmdline[i + 1]
                        break

                processes['monitors'].append({
                    'pid': proc.info['pid'],
                    'agent_name': agent_name,
                    'started_at': datetime.fromtimestamp(proc.info['create_time']).isoformat(),
                    'uptime_seconds': uptime_seconds,
                    'memory_mb': round(memory_mb, 1)
                })
                processes['total_memory_mb'] += memory_mb

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    # Check for zombie dashboards
    zombie_count = len([d for d in processes['dashboards'] if not d['is_current']])
    if zombie_count > 0:
        processes['warning'] = True
        processes['warning_message'] = f"{zombie_count} zombie dashboard process(es) detected - wasting {round(sum(d['memory_mb'] for d in processes['dashboards'] if not d['is_current']), 1)}MB RAM"

    processes['total_memory_mb'] = round(processes['total_memory_mb'], 1)

    return processes

@app.post("/api/processes/kill-zombies")
async def kill_zombie_dashboards():
    """Kill all dashboard processes except the current one"""
    current_pid = os.getpid()
    killed = []

    for proc in psutil.process_iter(['pid', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if not cmdline:
                continue

            cmdline_str = ' '.join(cmdline)

            # Dashboard processes (not current)
            if 'uvicorn' in cmdline_str and 'dashboard' in cmdline_str:
                if proc.info['pid'] != current_pid:
                    proc.kill()
                    killed.append(proc.info['pid'])

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    return {
        "success": True,
        "killed_count": len(killed),
        "killed_pids": killed,
        "message": f"Killed {len(killed)} zombie dashboard process(es)"
    }

@app.get("/api/environments")
async def list_environments():
    """List all available environments"""
    environments = config_loader.list_environments()
    return {"environments": environments}

@app.get("/api/configs")
async def list_configs(environment: Optional[str] = None):
    """List all available agent configurations, optionally filtered by environment"""
    configs = config_loader.list_configs(environment)
    return {"configs": configs}

@app.get("/api/configs/by-environment")
async def get_configs_by_environment():
    """Get configs grouped by environment"""
    configs_by_env = config_loader.get_configs_by_environment()
    return {"configs_by_environment": configs_by_env}

@app.get("/api/models/ollama")
async def list_ollama_models():
    """List available Ollama models"""
    models = await config_loader.get_ollama_models()
    return {"models": models}

@app.get("/api/providers")
async def list_providers():
    """List all available LLM providers"""
    providers = get_providers_list()
    return {"providers": providers}

@app.get("/api/providers/{provider_id}/models")
async def list_provider_models(provider_id: str):
    """Get available models for a specific provider"""
    models = get_models_for_provider(provider_id)
    if not models:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_id}' not found or has no models")
    return {"models": models}

@app.get("/api/providers/defaults")
async def get_provider_defaults():
    """Get default provider and model"""
    defaults = get_defaults()
    return defaults

@app.get("/api/prompts")
async def list_prompts():
    """List available system prompts from configs/prompts/"""
    import yaml
    prompts_dir = PROJECT_ROOT / "configs" / "prompts"
    prompts = []

    if prompts_dir.exists():
        for prompt_file in sorted(prompts_dir.glob("*.yaml")):
            # Skip example files
            if prompt_file.name.startswith("_"):
                continue

            try:
                with open(prompt_file, 'r') as f:
                    prompt_data = yaml.safe_load(f)
                    prompts.append({
                        "file": prompt_file.stem,
                        "name": prompt_data.get("name", prompt_file.stem),
                        "description": prompt_data.get("description", ""),
                        "prompt": prompt_data.get("prompt", "")
                    })
            except Exception as e:
                print(f"Error loading prompt {prompt_file}: {e}")

    return {"prompts": prompts}

@app.get("/api/deployments")
async def list_deployment_groups(environment: Optional[str] = None):
    """List deployment groups and their current status"""
    groups = process_manager.get_deployment_groups(environment)
    return {"deployment_groups": groups}

@app.post("/api/deployments/{group_id}/start")
async def start_deployment_group(group_id: str, request: DeploymentActionRequest):
    """Start all monitors defined in a deployment group"""
    try:
        result = await process_manager.start_deployment_group(group_id, request.environment)
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/deployments/{group_id}/stop")
async def stop_deployment_group(group_id: str):
    """Stop all monitors started by a deployment group"""
    try:
        stopped = await process_manager.stop_deployment_group(group_id)
        return {
            "success": True,
            "stopped": stopped,
            "message": f"Stopped {stopped} monitor(s) from group '{group_id}'"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/deployments/reload")
async def reload_deployment_groups():
    """Reload deployment group configuration from disk"""
    try:
        process_manager.reload_deployment_groups()
        return {"success": True, "message": "Deployment groups reloaded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/agents/reset")
async def reset_agents(request: ResetAgentsRequest):
    """Reset backlog for one or more agents."""
    try:
        result = await process_manager.clear_agents_backlog(
            agent_names=request.agents,
            environment=request.environment,
        )
        return {
            "success": True,
            **result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/agents/{agent_name}/reset")
async def reset_agent(agent_name: str):
    """Reset backlog for a single agent."""
    try:
        result = await process_manager.clear_agent_backlog(agent_name)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/monitors")
async def list_monitors():
    """List all monitors (running and stopped)"""
    monitors = process_manager.get_all_monitors()
    return {"monitors": monitors}

def load_base_prompt() -> str:
    """Load the base system prompt that's always included"""
    import yaml
    base_prompt_path = PROJECT_ROOT / "configs" / "prompts" / "_base.yaml"

    if not base_prompt_path.exists():
        return ""

    try:
        with open(base_prompt_path, 'r') as f:
            prompt_data = yaml.safe_load(f)
            return prompt_data.get("prompt", "")
    except Exception as e:
        print(f"Error loading base prompt: {e}")
        return ""

@app.post("/api/monitors/start")
async def start_monitor(request: StartMonitorRequest):
    """Start a new monitor"""
    try:
        # Load base prompt and combine with user-selected prompt
        base_prompt = load_base_prompt()

        if request.config.system_prompt:
            # Combine: base + user selection
            combined_prompt = f"{base_prompt}\n\n---\n\n{request.config.system_prompt}"
        else:
            # Just use base if no user selection
            combined_prompt = base_prompt if base_prompt else None

        monitor_id = await process_manager.start_monitor(
            agent_name=request.config.agent_name,
            config_path=request.config.config_path,
            monitor_type=request.config.monitor_type,
            model=request.config.model,
            provider=request.config.provider,
            system_prompt=combined_prompt,
            system_prompt_name=request.config.system_prompt_name,
            process_backlog=bool(request.config.process_backlog)
        )
        return {
            "success": True,
            "monitor_id": monitor_id,
            "message": f"Monitor started for {request.config.agent_name}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/monitors/stop")
async def stop_monitor(request: StopMonitorRequest):
    """Stop a running monitor"""
    try:
        success = await process_manager.stop_monitor(request.monitor_id)
        if success:
            return {
                "success": True,
                "message": f"Monitor {request.monitor_id} stopped"
            }
        else:
            raise HTTPException(status_code=404, detail="Monitor not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/monitors/restart/{monitor_id}")
async def restart_monitor(monitor_id: str, process_backlog: bool = False):
    """Restart a monitor (always starts fresh, no backlog processing)"""
    try:
        success = await process_manager.restart_monitor(monitor_id, process_backlog)
        if success:
            return {
                "success": True,
                "message": f"Monitor {monitor_id} restarted"
            }
        else:
            raise HTTPException(status_code=404, detail="Monitor not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/monitors/stop-all")
async def stop_all_monitors():
    """Stop all running monitors gracefully (no kill switch)"""
    try:
        count = await process_manager.stop_all_monitors()
        return {
            "success": True,
            "message": f"Stopped {count} monitor(s)",
            "count": count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/kill-switch/status")
async def get_kill_switch_status():
    """Check if kill switch is active"""
    from pathlib import Path
    kill_switch_file = Path("data/KILL_SWITCH")
    return {
        "active": kill_switch_file.exists(),
        "file_path": str(kill_switch_file)
    }

@app.post("/api/kill-switch/activate")
async def activate_kill_switch():
    """Activate kill switch (pause all agents)"""
    from pathlib import Path
    kill_switch_file = Path("data/KILL_SWITCH")
    kill_switch_file.parent.mkdir(exist_ok=True)
    kill_switch_file.touch()
    return {
        "success": True,
        "active": True,
        "message": "🛑 Kill switch activated - all agents paused"
    }

@app.post("/api/kill-switch/deactivate")
async def deactivate_kill_switch():
    """Deactivate kill switch (resume all agents)"""
    from pathlib import Path
    kill_switch_file = Path("data/KILL_SWITCH")
    if kill_switch_file.exists():
        kill_switch_file.unlink()
    return {
        "success": True,
        "active": False,
        "message": "✅ Kill switch deactivated - agents resumed"
    }

@app.post("/api/monitors/kill-all")
async def kill_all_monitors():
    """NUCLEAR OPTION: Force kill all monitors + activate kill switch + clear all"""
    try:
        # 1. Activate kill switch to prevent message processing
        from pathlib import Path
        kill_switch_file = Path("data/KILL_SWITCH")
        kill_switch_file.parent.mkdir(exist_ok=True)
        kill_switch_file.touch()

        # 2. Force kill ALL monitor processes (system-wide, not just tracked)
        import subprocess
        result = subprocess.run(["pkill", "-9", "-f", "ax_agent_studio.monitors"], capture_output=True)

        # 3. Stop all tracked monitors (in case pkill missed any)
        count = await process_manager.stop_all_monitors()

        # 4. Clear all monitors from the list (like pressing Clear button)
        deleted_count = process_manager.delete_all_stopped_monitors()

        return {
            "success": True,
            "message": f"☠️ Nuclear option: Killed {count} monitor(s), cleared {deleted_count} from list, activated kill switch",
            "kill_switch_active": True,
            "killed_count": count,
            "cleared_count": deleted_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/monitors/kill")
async def kill_monitor(request: StopMonitorRequest):
    """Force kill a running monitor immediately"""
    try:
        success = await process_manager.kill_monitor(request.monitor_id)
        if success:
            return {
                "success": True,
                "message": f"Monitor {request.monitor_id} killed"
            }
        else:
            raise HTTPException(status_code=404, detail="Monitor not found or already stopped")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/monitors/{monitor_id}")
async def delete_monitor(monitor_id: str):
    """Delete a stopped monitor from the list"""
    try:
        success = process_manager.delete_monitor(monitor_id)
        if success:
            return {
                "success": True,
                "message": f"Monitor {monitor_id} deleted"
            }
        else:
            raise HTTPException(status_code=404, detail="Monitor not found or still running")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/logs/clear-all")
async def clear_all_logs():
    """Clear/truncate ALL log files in the logs directory"""
    try:
        import glob
        log_pattern = str(process_manager.log_dir / "*.log")
        log_files = glob.glob(log_pattern)

        cleared = 0
        for log_file in log_files:
            try:
                # Truncate the log file
                open(log_file, 'w').close()
                cleared += 1
            except Exception as e:
                print(f"Error clearing {log_file}: {e}")

        return {
            "success": True,
            "message": f"Cleared {cleared} log file(s)",
            "count": cleared
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/monitors/clear-stopped")
async def clear_stopped_monitors():
    """Delete all stopped monitors from the list"""
    try:
        count = process_manager.delete_all_stopped_monitors()
        return {
            "success": True,
            "message": f"Cleared {count} stopped monitor(s)",
            "count": count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/demos/start")
async def start_demo(config: DemoConfig):
    """Start a demo (round-robin, scrum team, etc.)"""
    try:
        demo_id = await process_manager.start_demo(
            demo_type=config.demo_type,
            agents=config.agents,
            loops=config.loops,
            delay=config.delay,
            enable_tools=config.enable_tools
        )
        return {
            "success": True,
            "demo_id": demo_id,
            "message": f"Demo {config.demo_type} started"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/messages/send")
async def send_message(request: SendMessageRequest):
    """Send a message from one agent to another"""
    try:
        # Send message using test_sender logic
        result = await process_manager.send_test_message(
            from_agent=request.from_agent,
            to_agent=request.to_agent,
            message=request.message
        )
        return {
            "success": True,
            "message": f"Message sent from {request.from_agent} to {request.to_agent}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/logs/{monitor_id}")
async def websocket_logs(websocket: WebSocket, monitor_id: str):
    """Stream monitor logs via WebSocket"""
    await websocket.accept()
    try:
        await log_streamer.stream_logs(websocket, monitor_id)
    except WebSocketDisconnect:
        print(f"Client disconnected from logs for {monitor_id}")
    except Exception as e:
        print(f"Error streaming logs for {monitor_id}: {e}")
        await websocket.close()

@app.websocket("/ws/logs")
async def websocket_all_logs(websocket: WebSocket):
    """Stream all monitor logs via WebSocket"""
    await websocket.accept()
    try:
        await log_streamer.stream_all_logs(websocket)
    except WebSocketDisconnect:
        print("Client disconnected from all logs")
    except Exception as e:
        print(f"Error streaming all logs: {e}")
        await websocket.close()

# Mount static files (frontend)
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
