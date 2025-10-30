#!/bin/bash
# Simple startup script for aX Agent Studio Dashboard
# Just runs uvicorn directly - Ctrl+C works naturally

cd "$(dirname "$0")/.."

echo "🚀 Starting aX Agent Studio Dashboard..."
echo "📁 Project root: $(pwd)"
echo ""

# Check and create config files if needed
if [ ! -f "config.yaml" ] && [ -f "config.yaml.example" ]; then
    echo "📝 Creating config.yaml from config.yaml.example..."
    cp config.yaml.example config.yaml
fi

if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Edit .env to add your LLM provider API keys"
    echo ""
fi

# Quick dependency check
if [ ! -d ".venv" ]; then
    echo "📦 Installing dependencies..."
fi

uv sync
echo "✅ Dependencies ready!"
echo ""

echo "🌐 Starting dashboard on http://127.0.0.1:8000"
echo "📊 Press Ctrl+C to stop"
echo "------------------------------------------------------------"

# Run Python directly from venv (no activation or uv needed)
export PYTHONPATH=src
.venv/bin/python -m uvicorn \
    ax_agent_studio.dashboard.backend.main:app \
    --host 127.0.0.1 \
    --port 8000 \
    --log-level warning

echo ""
echo "👋 Dashboard stopped"
