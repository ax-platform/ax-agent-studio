"""
E2E Test Configuration - Master Registry

This file defines:
1. Which agents are in scope for testing (TEST_AGENTS)
2. Which monitor types to test (MONITOR_TYPES)

To add a new test agent: Add to TEST_AGENTS dict
To add a new monitor type: Add to MONITOR_TYPES list
"""

# Master list of test agents (in scope for E2E testing)
TEST_AGENTS = {
    "ghost_ray_363": {
        "config_path": "configs/agents/local_ghost.json",
        "description": "Local development agent #1",
    },
    "lunar_ray_510": {
        "config_path": "configs/agents/local_lunar_ray.json",
        "description": "Local development agent #2",
    },
    "orion_344": {
        "config_path": "configs/agents/orion_344.json",
        "description": "Local development agent #3",
    },
    "rigelz_334": {
        "config_path": "configs/agents/rigelz_334.json",
        "description": "Local development agent #4",
    },
}


# Monitor types to test (with their configurations)
MONITOR_TYPES = [
    {
        "name": "Echo",
        "monitor_type": "echo",
        "provider": None,
        "model": None,
        "target_agent": "ghost_ray_363",  # Agent that will have the monitor
        "sender_agent": "lunar_ray_510",  # Agent that will send the test message
        "timeout": 10,  # Echo responds instantly
        "description": "Simple echo monitor (deterministic, no AI)",
    },
    {
        "name": "Ollama",
        "monitor_type": "ollama",
        "provider": "ollama",
        "model": "gpt-oss:latest",  # Updated to correct model name
        "target_agent": "lunar_ray_510",
        "sender_agent": "ghost_ray_363",
        "timeout": 60,  # AI needs time
        "description": "Local AI using Ollama (gpt-oss)",
    },
    {
        "name": "Claude SDK",
        "monitor_type": "claude_agent_sdk",
        "provider": "anthropic",
        "model": "claude-sonnet-4-5",
        "target_agent": "ghost_ray_363",
        "sender_agent": "lunar_ray_510",
        "timeout": 60,  # AI needs time
        "description": "Claude Agent SDK (secure, production-grade)",
    },
    {
        "name": "OpenAI SDK",
        "monitor_type": "openai_agents_sdk",
        "provider": "openai",
        "model": "gpt-5-mini",
        "target_agent": "lunar_ray_510",
        "sender_agent": "ghost_ray_363",
        "timeout": 60,  # AI needs time
        "description": "OpenAI Agents SDK",
    },
    {
        "name": "LangGraph",
        "monitor_type": "langgraph",
        "provider": "google",
        "model": "gemini-2.5-pro",
        "target_agent": "lunar_ray_510",
        "sender_agent": "ghost_ray_363",
        "timeout": 90,  # AI + tools need more time
        "description": "LangGraph with tool support",
    },
]
