import sys
import os
import platform
import json
import subprocess
from datetime import datetime

def get_installed_packages():
    """Get list of installed pip packages."""
    try:
        result = subprocess.run([sys.executable, '-m', 'pip', 'list', '--format=json'], 
                              capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Warning: Failed to list packages: {e}", file=sys.stderr)
    except Exception as e:
        print(f"Warning: Unexpected error listing packages: {e}", file=sys.stderr)
    return []

def diagnose():
    """Run environment diagnostics."""
    print("Collecting system information...", file=sys.stderr)
    
    try:
        data = {
            "timestamp": datetime.now().isoformat(),
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
            },
            "python": {
                "version": sys.version,
                "executable": sys.executable,
                "implementation": platform.python_implementation(),
            },
            "environment": {
                "virtual_env": os.environ.get("VIRTUAL_ENV"),
                "conda_prefix": os.environ.get("CONDA_PREFIX"),
                "ci": os.environ.get("CI", "false").lower() == "true",
            },
            "packages": get_installed_packages()
        }

        # Ensure artifacts directory exists
        os.makedirs("artifacts", exist_ok=True)

        # Write JSON
        json_path = "artifacts/diagnostics.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            
        print(f"JSON report written to {json_path}", file=sys.stderr)

        # Write Text Summary
        txt_path = "artifacts/diagnostics.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"Environment Diagnostics - {data['timestamp']}\n")
            f.write("========================================\n\n")
            f.write(f"OS: {data['platform']['system']} {data['platform']['release']} ({data['platform']['machine']})\n")
            f.write(f"Python: {data['python']['version'].split()[0]}\n")
            f.write(f"Venv: {data['environment']['virtual_env'] or 'None'}\n\n")
            f.write("Packages:\n")
            for pkg in data['packages']:
                f.write(f"- {pkg.get('name')}=={pkg.get('version')}\n")

        print(f"Text summary written to {txt_path}", file=sys.stderr)
        print(f"Diagnostics complete.", file=sys.stderr)

    except Exception as e:
        print(f"Error during diagnostics: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    diagnose()
