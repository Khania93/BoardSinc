# test_run.ps1
# Ejecuta el exe generado y captura la salida en un log.
# Uso: ./test_run.ps1 .\dist\MiApp.exe

param(
    [string]$ExePath = ".\dist\MiApp.exe",
    [string]$LogFile = ".\dist\run_log.txt"
)

if (-not (Test-Path $ExePath)) {
    Write-Error "No se encontró el ejecutable: $ExePath"
    exit 1
}

Write-Host "Ejecutando $ExePath, salida en $LogFile"
Start-Process -FilePath $ExePath -NoNewWindow -RedirectStandardOutput $LogFile -RedirectStandardError $LogFile -Wait
Write-Host "Ejecución finalizada. Revisa $LogFile"
