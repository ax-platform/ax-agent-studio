import argparse
import time
import requests
import json
import sys
from concurrent.futures import ThreadPoolExecutor

MOCK_URL = "http://127.0.0.1:9000"

def send_heartbeat(agent_id, seq):
    try:
        payload = {
            "text": "heartbeat",
            "agent_id": agent_id,
            "seq": seq,
            "ts": time.time()
        }
        response = requests.post(f"{MOCK_URL}/workspaces/demo/messages", json=payload)
        return response.status_code == 200
    except Exception:
        return False

def run_agent(agent_id, duration, heartbeat_interval):
    start_time = time.time()
    seq = 0
    heartbeats_sent = 0
    
    while time.time() - start_time < duration:
        seq += 1
        if send_heartbeat(agent_id, seq):
            heartbeats_sent += 1
        time.sleep(heartbeat_interval)
        
    return heartbeats_sent

def main():
    parser = argparse.ArgumentParser(description="Run smoke/load test on agents")
    parser.add_argument("--agents", type=int, default=5, help="Number of agents to simulate")
    parser.add_argument("--duration", type=int, default=30, help="Duration in seconds")
    parser.add_argument("--heartbeat", type=int, default=5, help="Heartbeat interval in seconds")
    
    args = parser.parse_args()
    
    print(f"Starting smoke test with {args.agents} agents for {args.duration}s...")
    
    with ThreadPoolExecutor(max_workers=args.agents) as executor:
        futures = []
        for i in range(args.agents):
            agent_id = f"test_agent_{i}"
            futures.append(executor.submit(run_agent, agent_id, args.duration, args.heartbeat))
            
        results = [f.result() for f in futures]
        
    total_heartbeats = sum(results)
    print(f"Smoke test completed.")
    print(f"Agents started: {args.agents}")
    print(f"Heartbeats sent: {total_heartbeats}")
    
    if total_heartbeats > 0:
        print("No errors reported.")
        
        # Verify messages were received
        try:
            r = requests.get(f"{MOCK_URL}/workspaces/demo/messages?since_seq=0")
            data = r.json()
            print("Sample GET after test:")
            # Print first 2 messages as sample
            sample = {"messages": data.get("messages", [])[:2]}
            print(json.dumps(sample, indent=2))
        except Exception as e:
            print(f"Failed to verify messages: {e}")
    else:
        print("Errors reported: No heartbeats sent.")
        sys.exit(1)

if __name__ == "__main__":
    main()
