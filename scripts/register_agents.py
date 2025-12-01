import requests
import json

MOCK_URL = "http://127.0.0.1:9000"
AGENTS = [
    {"name": "lead_scout", "type": "langgraph"},
    {"name": "dossier_builder", "type": "langgraph"},
    {"name": "message_architect", "type": "langgraph"},
    {"name": "pipeline_master", "type": "langgraph"}
]

def register_agents():
    print(f"Registering agents to {MOCK_URL}...")
    for agent in AGENTS:
        try:
            # In a real scenario, this would POST to an endpoint to register the agent.
            # For the mock, we just send a message to simulate activity/registration.
            payload = {
                "text": f"Registering agent {agent['name']}",
                "agent_id": agent['name'],
                "type": "registration"
            }
            response = requests.post(f"{MOCK_URL}/workspaces/demo/messages", json=payload)
            print(f"Registered {agent['name']}: {response.status_code} {response.text}")
        except Exception as e:
            print(f"Failed to register {agent['name']}: {e}")

if __name__ == "__main__":
    register_agents()
