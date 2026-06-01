# Flame Scope - on-demand Lobby/Outdoor stream controller
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\start_stream_controller.ps1

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Resolve-Path (Join-Path $scriptDir "..\..")
$python = Join-Path $projectRoot "detector\.venv\Scripts\python.exe"
$controller = Join-Path $scriptDir "stream_controller.py"

if (-not (Test-Path $python)) {
    Write-Host "[ERROR] Detector virtual env not found: $python" -ForegroundColor Red
    exit 1
}

& $python $controller
