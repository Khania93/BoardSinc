# build.ps1
# PowerShell script para compilar con PyInstaller
# Requisitos: Python, pip, PyInstaller instalados en el entorno activo.
# Asume que el Excel está en data/mi_datos.xlsx y assets/ contiene imágenes.
# Si tus rutas son distintas, modifica las variables $EXCEL y $ASSETS.

$ErrorActionPreference = "Stop"

# Opciones
$EXE_NAME = "MiApp"
$MAIN = "main.py"
$EXCEL = ".\data\mi_datos.xlsx"
$ASSETS = ".\assets"
$DIST_DIR = ".\dist"
$BUILD_DIR = ".\build"
$SPEC = "$EXE_NAME.spec"

Write-Host "Iniciando build.ps1..."

# Activar .venv si existe
if (Test-Path ".\.venv\Scripts\Activate.ps1") {
    Write-Host "Activando .venv..."
    . .\.venv\Scripts\Activate.ps1
} elseif (Test-Path ".\venv\Scripts\Activate.ps1") {
    Write-Host "Activando venv..."
    . .\venv\Scripts\Activate.ps1
} else {
    Write-Host "No se encontró entorno virtual (.venv o venv). Continuando con el entorno actual."
}

# Limpiar dist, build y spec
if (Test-Path $DIST_DIR) {
    Write-Host "Eliminando $DIST_DIR..."
    Remove-Item -Recurse -Force $DIST_DIR
}
if (Test-Path $BUILD_DIR) {
    Write-Host "Eliminando $BUILD_DIR..."
    Remove-Item -Recurse -Force $BUILD_DIR
}
if (Test-Path $SPEC) {
    Write-Host "Eliminando $SPEC..."
    Remove-Item -Force $SPEC
}

# Comprobar archivos
if (-not (Test-Path $EXCEL)) {
    Write-Warning "No se encontró $EXCEL. Asegúrate de que el Excel esté en data/mi_datos.xlsx o modifica la variable en build.ps1."
}

if (-not (Test-Path $ASSETS)) {
    Write-Warning "No se encontró $ASSETS. Asegúrate de que la carpeta assets/ exista o modifica la variable en build.ps1."
}

# Ejecutar PyInstaller (sin --noconsole para ver errores en la primera compilación)
$add_data_excel = "$EXCEL;data"
$add_data_assets = "$ASSETS;assets"

Write-Host "Ejecutando PyInstaller..."
python -m PyInstaller --onefile --name $EXE_NAME --add-data $add_data_excel --add-data $add_data_assets --hidden-import openpyxl $MAIN

Write-Host "Build finalizada. Revisa la carpeta dist para el ejecutable."
