#!/bin/bash
# Quick lint check script - run before committing
# Usage: ./scripts/lint_check.sh

set -e

echo "🔍 Running Ruff linter..."
uv run ruff check .

echo "✨ Running Ruff formatter check..."
uv run ruff format --check .

echo "🔒 Running Bandit security check..."
uv run bandit -r src/ -c pyproject.toml --severity-level medium

echo "✅ All checks passed! Ready to commit."
