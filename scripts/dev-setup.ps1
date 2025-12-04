# One-command dev setup and startup
$ErrorActionPreference = "Stop"

Write-Host "Starting aX Agent Studio Dev Environment..." -ForegroundColor Cyan

# 1. Check for venv
if (-not (Test-Path ".\.venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
    .\.venv\Scripts\python.exe -m ensurepip --upgrade
    .\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
}

# 2. Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow

# Ensure pip is installed
if (-not (Test-Path ".\.venv\Scripts\pip.exe")) {
    Write-Host "Pip not found, installing..." -ForegroundColor Yellow
    .\.venv\Scripts\python.exe -m ensurepip --default-pip
    .\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
}
# Install project in editable mode if pyproject.toml exists, otherwise install requirements
if (Test-Path "pyproject.toml") {
    .\.venv\Scripts\python.exe -m pip install -e .
}
elseif (Test-Path "requirements.txt") {
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
}

# Explicitly install dashboard dependencies to ensure they exist
Write-Host "Ensuring dashboard dependencies..." -ForegroundColor Yellow
.\.venv\Scripts\python.exe -m pip install uvicorn fastapi

# 3. Set Environment Variables
$env:PYTHONUTF8 = "1"
Write-Host "Environment configured (PYTHONUTF8=1)" -ForegroundColor Green

# 4. Start Dashboard
Write-Host "Starting Dashboard..." -ForegroundColor Cyan
.\.venv\Scripts\python.exe scripts/start_dashboard.py
