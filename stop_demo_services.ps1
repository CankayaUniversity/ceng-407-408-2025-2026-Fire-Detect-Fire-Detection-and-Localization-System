$ErrorActionPreference = "Continue"

$patterns = @(
    "-m uvicorn app.main:app",
    "-m src.main",
    "mediamtx.exe",
    "ffmpeg.exe"
)

Write-Host "Stopping FlameScope demo services..."

$processes = Get-CimInstance Win32_Process | Where-Object {
    $cmd = $_.CommandLine
    if (-not $cmd) { return $false }
    foreach ($pattern in $patterns) {
        if ($cmd -like "*$pattern*") { return $true }
    }
    return $false
}

foreach ($proc in $processes) {
    Write-Host "Stopping PID=$($proc.ProcessId) $($proc.Name)"
    Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
}

Start-Sleep -Seconds 1

$remaining = Get-CimInstance Win32_Process | Where-Object {
    $cmd = $_.CommandLine
    if (-not $cmd) { return $false }
    foreach ($pattern in $patterns) {
        if ($cmd -like "*$pattern*") { return $true }
    }
    return $false
}

if ($remaining) {
    Write-Host "Some processes are still visible:"
    $remaining | Select-Object ProcessId,Name,CommandLine | Format-List
} else {
    Write-Host "All FlameScope demo services are stopped."
}
