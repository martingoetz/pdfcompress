param(
    [string]$BindHost = "127.0.0.1",
    [ValidateRange(1, 65535)]
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Dieses Skript muss als Administrator ausgefuehrt werden."
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$launcher = Join-Path $repoRoot "scripts\start-app.ps1"
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
$taskName = "PDFCompress"

if (-not (Test-Path $pythonExe)) {
    throw "Die virtuelle Umgebung fehlt. Bitte zuerst .venv erstellen."
}

$taskCommand = "powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$launcher`" -BindHost $BindHost -Port $Port"
& schtasks.exe /Create /TN $taskName /TR $taskCommand /SC ONSTART /RU SYSTEM /RL HIGHEST /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Die Hintergrund-Aufgabe konnte nicht erstellt werden."
}

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Seconds 0) `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries
Set-ScheduledTask -TaskName $taskName -Settings $settings | Out-Null

Write-Host "Die Aufgabe '$taskName' wurde erstellt und startet die App beim Systemstart im Hintergrund."