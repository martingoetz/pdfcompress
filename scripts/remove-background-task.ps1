$ErrorActionPreference = "Stop"
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Dieses Skript muss als Administrator ausgefuehrt werden."
}

& schtasks.exe /Delete /TN "PDFCompress" /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Die Hintergrund-Aufgabe konnte nicht entfernt werden."
}

Write-Host "Die Aufgabe 'PDFCompress' wurde entfernt."