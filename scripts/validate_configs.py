import json
import sys
from pathlib import Path

def validate_configs():
    configs_dir = Path("configs/agents")
    required_fields = ["agent_name", "server_url", "framework", "model", "mcpServers"]
    
    errors = []
    
    for config_file in configs_dir.glob("*.json"):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
            
            missing = [field for field in required_fields if field not in config]
            if missing:
                errors.append(f"{config_file.name}: Missing fields {missing}")
                
        except json.JSONDecodeError:
            errors.append(f"{config_file.name}: Invalid JSON")
        except Exception as e:
            errors.append(f"{config_file.name}: Error {str(e)}")
    
    if errors:
        print(json.dumps({"status": "invalid", "errors": errors}, indent=2))
        sys.exit(1)
    else:
        print(json.dumps({"status": "valid"}, indent=2))
        sys.exit(0)

if __name__ == "__main__":
    validate_configs()
