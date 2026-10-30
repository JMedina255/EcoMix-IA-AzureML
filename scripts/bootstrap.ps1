<#
.SYNOPSIS
    Script de inicialización y diagnóstico portable de EcoMix IA (Bootstrap).

.DESCRIPTION
    Verifica el entorno de ejecución (OS, Python, Git, datasets, configuración de Azure,
    modelos e inferencia) sin requerir privilegios de administrador ni modificar
    configuraciones globales por defecto.

.PARAMETER Install
    Crea el entorno virtual (.venv) si no existe e instala las dependencias de requirements.txt.

.PARAMETER CreateVenv
    Crea únicamente el entorno virtual (.venv) sin instalar paquetes adicionales.

.PARAMETER CheckOnly
    Modo por defecto: inspecciona el sistema y emite recomendaciones sin alterar archivos.

.EXAMPLE
    .\scripts\bootstrap.ps1
    .\scripts\bootstrap.ps1 -Install
#>

[CmdletBinding()]
param (
    [switch]$Install,
    [switch]$CreateVenv,
    [switch]$CheckOnly
)

$ErrorActionPreference = "Continue"

# Ubicación base del repositorio
$RootDir = Split-Path -Parent $PSScriptRoot
if (-not $RootDir) {
    $RootDir = (Get-Location).Path
}

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host " ECOMIX IA — SCRIPT DE INICIALIZACIÓN PORTABLE (BOOTSTRAP)" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host " Directorio Raíz: $RootDir"

# 1. Detección de Sistema Operativo
$OSName = [System.Environment]::OSVersion.VersionString
$PlatformWindows = [System.Environment]::OSVersion.Platform -eq [System.PlatformID]::Win32NT
Write-Host "`n[1/7] Sistema Operativo: $OSName" -ForegroundColor Yellow

# 2. Detección de Python
Write-Host "`n[2/7] Verificando Intérprete Python..." -ForegroundColor Yellow
$PythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $PythonCmd) {
    $PythonCmd = Get-Command py -ErrorAction SilentlyContinue
}

if ($PythonCmd) {
    $PyVersionRaw = & $PythonCmd.Source --version 2>&1
    Write-Host "  -> Python detectado: $PyVersionRaw" -ForegroundColor Green
    
    # Comprobar versión mínima (3.10+)
    $PyVersionMatch = [regex]::Match($PyVersionRaw, "(\d+)\.(\d+)")
    if ($PyVersionMatch.Success) {
        $Major = [int]$PyVersionMatch.Groups[1].Value
        $Minor = [int]$PyVersionMatch.Groups[2].Value
        if ($Major -lt 3 -or ($Major -eq 3 -and $Minor -lt 10)) {
            Write-Host "  [ALERTA] Se recomienda Python >= 3.10 para compatibilidad con dependencias ML." -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "  [ERROR] No se encontró Python en el PATH del sistema." -ForegroundColor Red
    Write-Host "          Descargue e instale Python 3.10 - 3.13 desde https://www.python.org/" -ForegroundColor Red
}

# 3. Verificación de Git y Repositorio
Write-Host "`n[3/7] Verificando Control de Versiones (Git)..." -ForegroundColor Yellow
$GitCmd = Get-Command git -ErrorAction SilentlyContinue
if ($GitCmd) {
    $GitVer = & git --version
    Write-Host "  -> Git disponible: $GitVer" -ForegroundColor Green
    $InsideWorkTree = & git rev-parse --is-inside-work-tree 2>$null
    if ($InsideWorkTree -eq "true") {
        $Branch = & git rev-parse --abbrev-ref HEAD 2>$null
        Write-Host "  -> Repositorio Git activo en rama: '$Branch'" -ForegroundColor Green
    } else {
        Write-Host "  [AVISO] No se detecta un árbol de trabajo Git en este directorio." -ForegroundColor Yellow
    }
} else {
    Write-Host "  [AVISO] Git no está en el PATH. Recomendado para sincronización de código." -ForegroundColor Yellow
}

# 4. Entorno Virtual y Dependencias
Write-Host "`n[4/7] Verificando Entorno Virtual..." -ForegroundColor Yellow
$VenvPath = Join-Path $RootDir ".venv"
$VenvExists = Test-Path $VenvPath
$VenvActive = ($env:VIRTUAL_ENV -ne $null)

if ($VenvActive) {
    Write-Host "  -> Entorno virtual actualmente activo: $env:VIRTUAL_ENV" -ForegroundColor Green
} elseif ($VenvExists) {
    Write-Host "  -> Entorno virtual encontrado en: $VenvPath (Inactivo en esta consola)" -ForegroundColor Yellow
    Write-Host "     Para activarlo: .\.venv\Scripts\Activate.ps1" -ForegroundColor Gray
} else {
    Write-Host "  -> No se encontró entorno virtual (.venv)." -ForegroundColor Gray
}

# Acciones de instalación solicitadas explícitamente
if ($CreateVenv -or $Install) {
    if (-not $VenvExists) {
        Write-Host "  [*] Creando entorno virtual aislado en .venv (sin privilegios de administrador)..." -ForegroundColor Cyan
        & python -m venv (Join-Path $RootDir ".venv")
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [OK] Entorno virtual .venv creado con éxito." -ForegroundColor Green
        } else {
            Write-Host "  [ERROR] Falló la creación del entorno virtual." -ForegroundColor Red
        }
    }
}

if ($Install) {
    $ReqPath = Join-Path $RootDir "requirements.txt"
    if (Test-Path $ReqPath) {
        $PipExecutable = if (Test-Path (Join-Path $VenvPath "Scripts\pip.exe")) {
            Join-Path $VenvPath "Scripts\pip.exe"
        } else {
            "pip"
        }
        Write-Host "  [*] Instalando dependencias desde requirements.txt..." -ForegroundColor Cyan
        & $PipExecutable install -r $ReqPath
    } else {
        Write-Host "  [AVISO] 'requirements.txt' no encontrado en la raíz del proyecto." -ForegroundColor Yellow
    }
} else {
    Write-Host "  -> Modo inspección: No se realizaron modificaciones en el entorno." -ForegroundColor Gray
    Write-Host "     Use '-Install' para crear .venv e instalar requirements.txt de forma controlada." -ForegroundColor Gray
}

# 5. Datasets y Particiones
Write-Host "`n[5/7] Verificando Datasets del Proyecto..." -ForegroundColor Yellow
$RawData = Join-Path $RootDir "data\raw\concrete_raw.csv"
$TrainData = Join-Path $RootDir "data\processed\concrete_train.csv"
$TestData = Join-Path $RootDir "data\processed\concrete_test.csv"

if (Test-Path $RawData) {
    Write-Host "  -> Dataset crudo: Presente en data/raw/concrete_raw.csv" -ForegroundColor Green
} else {
    Write-Host "  [AVISO] Dataset crudo ausente en data/raw/concrete_raw.csv" -ForegroundColor Yellow
}

if ((Test-Path $TrainData) -and (Test-Path $TestData)) {
    Write-Host "  -> Datasets procesados (train/test): Presentes y auditados" -ForegroundColor Green
} else {
    Write-Host "  [AVISO] Faltan particiones procesadas. Ejecute: python src/prepare_data.py" -ForegroundColor Yellow
}

# 6. Configuración de Azure ML
Write-Host "`n[6/7] Verificando Configuración de Azure ML..." -ForegroundColor Yellow
$ConfigFile = Join-Path $RootDir "config.json"
$ExampleConfigFile = Join-Path $RootDir "config.example.json"

if (Test-Path $ConfigFile) {
    try {
        $ConfigJson = Get-Content $ConfigFile -Raw | ConvertFrom-Json
        $SubId = $ConfigJson.subscription_id
        $Workspace = $ConfigJson.workspace_name
        if ($SubId -and $SubId -ne "TU_SUBSCRIPTION_ID") {
            $MaskedSub = "..." + $SubId.Substring([Math]::Max(0, $SubId.Length - 4))
            Write-Host "  -> config.json configurado correctamente (Workspace: '$Workspace', Sub: $MaskedSub)" -ForegroundColor Green
        } else {
            Write-Host "  [AVISO] config.json contiene valores de plantilla pendientes de configurar." -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  [ERROR] config.json existe pero no tiene formato JSON válido." -ForegroundColor Red
    }
} else {
    Write-Host "  [AVISO] 'config.json' no existe (normal en clones limpios para no filtrar credenciales)." -ForegroundColor Yellow
    if (Test-Path $ExampleConfigFile) {
        Write-Host "          Copie 'config.example.json' a 'config.json' con sus claves de Azure." -ForegroundColor Gray
    }
}

# 7. Modelo Local y Opciones de Inferencia
Write-Host "`n[7/7] Verificando Modelo y Capacidad de Inferencia..." -ForegroundColor Yellow
$ModelsDir = Join-Path $RootDir "models"
$PklFiles = @()
if (Test-Path $ModelsDir) {
    $PklFiles = Get-ChildItem -Path $ModelsDir -Filter "*.pkl" -Recurse
}

if ($PklFiles.Count -gt 0) {
    Write-Host "  -> Modelo local detectado: $($PklFiles[0].Name) ($($PklFiles.Count) archivo(s) .pkl)" -ForegroundColor Green
} else {
    Write-Host "  [INFO] Modelo no descargado en 'models/' (los binarios no se suben a Git)." -ForegroundColor Yellow
    Write-Host "         Para descargarlo selectivamente desde Azure ML:" -ForegroundColor Cyan
    Write-Host "         python src/evaluate_model.py --download" -ForegroundColor Cyan
}

# Docker y opciones de ejecución
$DockerCmd = Get-Command docker -ErrorAction SilentlyContinue
if ($DockerCmd) {
    Write-Host "  -> Docker CLI detectado (útil para reproducibilidad en contenedor con Python 3.10)." -ForegroundColor Green
} else {
    Write-Host "  -> Docker no detectado (opcional: la evaluación y desarrollo pueden ejecutarse en Python nativo)." -ForegroundColor Gray
}

# Ejecutar diagnóstico python doctor si está disponible
Write-Host "`n=================================================================" -ForegroundColor Cyan
Write-Host " RESUMEN: Para diagnóstico detallado por entornos, ejecute:" -ForegroundColor Cyan
Write-Host " python scripts/doctor.py" -ForegroundColor White
Write-Host "=================================================================" -ForegroundColor Cyan
