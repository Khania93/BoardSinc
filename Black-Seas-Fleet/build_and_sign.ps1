<#
build_and_sign.ps1
Uso
  powershell -ExecutionPolicy Bypass -File .\build_and_sign.ps1 -PfxPath "C:\ruta\cert.pfx" -PfxPassword (Read-Host -AsSecureString "PFX password")
  o
  powershell -ExecutionPolicy Bypass -File .\build_and_sign.ps1 -CertSubject "CN=MiEmpresa" 

Notas
  - Requiere Python en PATH y PyInstaller instalado en el venv o global.
  - Requiere signtool.exe (Windows SDK). Si no está, el script avisará.
#>

param(
    [string]$MainFile = "main.py",
    [string]$ExeName = "MiApp",
    [string]$VenvDir = ".venv",
    [string]$PfxPath = "",
    [System.Security.SecureString]$PfxPassword = $null,
    [string]$CertSubject = "",   # usar si el certificado está instalado en el almacén
    [switch]$KeepConsole = $true
)

$LogDir = ".build_logs"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }

function Write-Log {
    param([string]$msg, [string]$level="INFO")
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') [$level] $msg"
    Write-Host $line
    Add-Content -Path (Join-Path $LogDir "build.log") -Value $line
}

if (-not (Test-Path $MainFile)) {
    Write-Log "No se encontró $MainFile. Ejecuta el script desde la raíz del proyecto." "ERROR"
    exit 1
}

# Activar virtualenv si existe
$activateScript = Join-Path $VenvDir "Scripts\Activate.ps1"
if (Test-Path $activateScript) {
    try {
        Write-Log "Activando virtualenv $VenvDir"
        & $activateScript
        Write-Log "Virtualenv activado"
    } catch {
        Write-Log "No se pudo activar virtualenv automáticamente: $_" "WARN"
    }
} else {
    Write-Log "No se detectó virtualenv en $VenvDir. Asegúrate de tener dependencias instaladas." "WARN"
}

# Instalar dependencias mínimas si no existe requirements
if (Test-Path "requirements.txt") {
    Write-Log "Instalando dependencias desde requirements.txt"
    python -m pip install --upgrade pip setuptools wheel | Out-Null
    python -m pip install -r requirements.txt | Tee-Object -FilePath (Join-Path $LogDir "pip_install.log")
} else {
    Write-Log "No se encontró requirements.txt. Instalando paquetes mínimos"
    python -m pip install --upgrade pip setuptools wheel | Out-Null
    python -m pip install pyinstaller pandas openpyxl Pillow | Tee-Object -FilePath (Join-Path $LogDir "pip_install_minimal.log")
}

# Limpiar builds previos
Write-Log "Limpiando dist build y .spec"
Remove-Item -Recurse -Force .\dist, .\build, "$ExeName.spec" -ErrorAction SilentlyContinue

# Generar --add-data para carpetas comunes
$exclude = @('dist','build','.venv','venv','.git','__pycache__','.vs','.idea')
$resourceFolders = @('data','assets','resources','config')
$addDataArgs = @()

foreach ($f in $resourceFolders) {
    if (Test-Path $f) {
        $src = (Resolve-Path $f).Path
        $dest = $f
        $addDataArgs += "--add-data `"$src;$dest`""
        Write-Log "Incluir recurso: $src -> $dest"
    }
}

# Incluir archivos sueltos de primer nivel útiles (ejemplo .xlsx, .json)
$topFiles = Get-ChildItem -File -Force | Where-Object { $exclude -notcontains $_.Name -and $_.Name -ne $MainFile }
foreach ($it in $topFiles) {
    # omitir archivos temporales
    if ($it.Extension -in @(".pyc",".pdb")) { continue }
    try {
        $stream = [System.IO.File]::Open($it.FullName, 'Open', 'Read', 'Read')
        $stream.Close()
        $addDataArgs += "--add-data `"$($it.FullName);$($it.Name)`""
        Write-Log "Incluir archivo: $($it.FullName)"
    } catch {
        Write-Log "Omitido por permisos: $($it.FullName)" "WARN"
    }
}

$addDataStr = $addDataArgs -join " "
$onefile = "--onefile"
$noconsole = if ($KeepConsole) { "" } else { "--noconsole" }
$hiddenImports = "--hidden-import openpyxl"

$pyiCmd = "python -m PyInstaller $onefile $noconsole --name `"$ExeName`" $addDataStr $hiddenImports `"$MainFile`""
Write-Log "Ejecutando PyInstaller"
Write-Log $pyiCmd
cmd /c $pyiCmd 2>&1 | Tee-Object -FilePath (Join-Path $LogDir "pyinstaller_output.log")

$exePath = Join-Path -Path "dist" -ChildPath ("$ExeName.exe")
if (-not (Test-Path $exePath)) {
    Write-Log "No se generó el ejecutable. Revisa pyinstaller_output.log" "ERROR"
    exit 1
}
Write-Log "Ejecutable generado: $exePath"

# Firmar el ejecutable
# Buscar signtool
$signtool = Get-Command signtool -ErrorAction SilentlyContinue
if (-not $signtool) {
    Write-Log "signtool.exe no encontrado. Instala Windows SDK o Visual Studio Build Tools." "ERROR"
    Write-Host "Instala Windows SDK y asegúrate de que signtool.exe esté en PATH."
    exit 1
}

# Preparar comando de firma
$timestampUrl = "http://timestamp.digicert.com"  # servidor RFC3161 recomendado
if ($PfxPath -ne "") {
    if (-not (Test-Path $PfxPath)) {
        Write-Log "PFX no encontrado en $PfxPath" "ERROR"
        exit 1
    }
    if ($PfxPassword -eq $null) {
        # pedir password si no se pasó
        $PfxPassword = Read-Host -AsSecureString "Introduce la contraseña del PFX"
    }
    # Convertir SecureString a texto seguro temporalmente para signtool
    $bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($PfxPassword)
    $plainPwd = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
    [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)

    $signCmd = "signtool sign /f `"$PfxPath`" /p `"$plainPwd`" /fd SHA256 /tr $timestampUrl /td SHA256 `"$exePath`""
    Write-Log "Firmando con PFX: $PfxPath"
    cmd /c $signCmd 2>&1 | Tee-Object -FilePath (Join-Path $LogDir "signtool_sign.log")
    # Borrar variable de contraseña en memoria
    $plainPwd = $null
} elseif ($CertSubject -ne "") {
    # Firmar usando certificado instalado en el almacén por subject
    $signCmd = "signtool sign /n `"$CertSubject`" /fd SHA256 /tr $timestampUrl /td SHA256 `"$exePath`""
    Write-Log "Firmando con certificado del almacén Subject: $CertSubject"
    cmd /c $signCmd 2>&1 | Tee-Object -FilePath (Join-Path $LogDir "signtool_sign.log")
} else {
    Write-Log "No se proporcionó PFX ni CertSubject. Saltando firma." "WARN"
}

# Verificar firma
Write-Log "Verificando firma"
$verifyCmd = "signtool verify /pa `"$exePath`""
cmd /c $verifyCmd 2>&1 | Tee-Object -FilePath (Join-Path $LogDir "signtool_verify.log")

Write-Log "Proceso completado. Revisa logs en $LogDir"
Write-Host "Ejecutable firmado y verificado en: $exePath"
