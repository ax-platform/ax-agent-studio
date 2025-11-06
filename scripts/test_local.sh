#!/bin/bash
# Run tests against local running dashboard
# Assumes dashboard is already running at http://localhost:3000
# Usage: ./scripts/test_local.sh [test_file]

set -e

# Check if dashboard is running
if ! curl -s http://localhost:3000/health > /dev/null 2>&1; then
    echo "❌ Dashboard not running at http://localhost:3000"
    echo "   Start it with: python scripts/start_dashboard.py"
    exit 1
fi

echo "✅ Dashboard is running"
echo "🧪 Running tests..."

if [ $# -eq 0 ]; then
    # Run all unit tests (fast, no E2E)
    uv run pytest tests/ -v --tb=short -m "not e2e"
else
    # Run specific test file
    uv run pytest "$@" -v --tb=short
fi

echo "✅ Tests complete!"
