#!/bin/bash
set -e

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "Starting Environment Diagnostics (POSIX/Docker)..."

# Detect Python interpreter
if command -v python3 &> /dev/null; then
    PY_CMD=python3
elif command -v python &> /dev/null; then
    PY_CMD=python
else
    echo "Error: Neither 'python3' nor 'python' found in PATH."
    exit 1
fi

echo "Using Python: $(command -v $PY_CMD)"

# Run diagnostics
"$PY_CMD" "$SCRIPT_DIR/diagnose_env.py"

echo "Done."
