<#
.SYNOPSIS
    Runs environment diagnostics on Windows.
.DESCRIPTION
    Wrapper for diagnose_env.py that handles execution policy and output encoding.
    Generates artifacts in ./artifacts/
#>

$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Definition
$PyScript = Join-Path $ScriptPath "diagnose_env.py"

Write-Host "Starting Environment Diagnostics..." -ForegroundColor Cyan

# Check for Python (fallback to PATH, avoiding WindowsApps shim)
$PythonExe = $null

# Check environment variable first if set
if ($env:PYTHON_PATH -and (Test-Path $env:PYTHON_PATH)) {
    $PythonExe = $env:PYTHON_PATH
}
else {
    # Find in PATH, ignoring WindowsApps shim
    $Commands = Get-Command python -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
    foreach ($Cmd in $Commands) {
        if ($Cmd -and $Cmd -notlike "*WindowsApps*") {
            $PythonExe = $Cmd
            break
        }
    }
}

if (-not $PythonExe) {
    Write-Error "Python not found in PATH (and skipped WindowsApps). Please install Python or set PYTHON_PATH."
    exit 1
}

Write-Host "Using Python: $PythonExe" -ForegroundColor Gray

# Run Python script
& $PythonExe $PyScript

if ($LASTEXITCODE -eq 0) {
    Write-Host "Success! Artifacts generated." -ForegroundColor Green
}
else {
    Write-Error "Diagnostics failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}
