
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root / "src"))

from ax_agent_studio.dashboard.backend.deployment_loader import DeploymentLoader

def main():
    print(f"Project Root: {project_root}")
    loader = DeploymentLoader(project_root)
    print(f"Groups found: {len(loader._groups)}")
    for gid, group in loader._groups.items():
        print(f"- {gid}: {len(group.agents)} agents")

if __name__ == "__main__":
    main()
