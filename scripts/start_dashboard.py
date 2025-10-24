#!/usr/bin/env python3
"""
Simple dashboard startup script for aX Agent Studio.

Automatically:
1. Checks if .venv exists
2. Runs uv sync if needed
3. Starts the dashboard
"""

import os
import sys
import subprocess
from pathlib import Path


def main():
    # Get project root (parent of scripts directory)
    project_root = Path(__file__).parent.parent.resolve()
    venv_path = project_root / ".venv"

    print("🚀 Starting aX Agent Studio Dashboard...")
    print(f"📁 Project root: {project_root}\n")

    # Check dependencies
    if not venv_path.exists():
        print("⚠️  Virtual environment not found!")
        print("📦 Running 'uv sync' to install dependencies...\n")
    else:
        print("🔄 Checking dependencies...\n")

    # Always run uv sync (it's fast if everything is already installed)
    try:
        subprocess.run(
            ["uv", "sync"],
            cwd=project_root,
            check=True
        )
        print("✅ Dependencies ready!\n")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Failed to install dependencies: {e}")
        print("💡 Make sure 'uv' is installed: https://github.com/astral-sh/uv")
        sys.exit(1)
    except FileNotFoundError:
        print("\n❌ 'uv' command not found!")
        print("💡 Install uv: https://github.com/astral-sh/uv")
        sys.exit(1)

    # Set up environment
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root / "src")

    # Start the dashboard
    print("🌐 Starting dashboard on http://127.0.0.1:8000")
    print("📊 Press Ctrl+C to stop\n")
    print("-" * 60)

    try:
        # Run Python directly from venv (no uv wrapper)
        # This should make Ctrl+C work cleanly
        python_exe = venv_path / "bin" / "python"

        subprocess.run(
            [
                str(python_exe),
                "-m", "uvicorn",
                "ax_agent_studio.dashboard.backend.main:app",
                "--host", "127.0.0.1",
                "--port", "8000",
                "--log-level", "warning"
            ],
            cwd=project_root,
            env=env,
            check=True
        )
    except KeyboardInterrupt:
        # Ctrl+C pressed - subprocess is already dead
        print("\n\n👋 Dashboard stopped")
    except subprocess.CalledProcessError:
        # Subprocess exited with error
        print("\n❌ Dashboard stopped with error")
        sys.exit(1)


if __name__ == "__main__":
    main()
