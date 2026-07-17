param(
    [string]$BindHost = "127.0.0.1",
    [ValidateRange(1, 65535)]
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    throw "Die virtuelle Umgebung fehlt: $pythonExe"
}

Set-Location $repoRoot
& $pythonExe -m uvicorn app.main:app --host $BindHost --port $Port
exit $LASTEXITCODE