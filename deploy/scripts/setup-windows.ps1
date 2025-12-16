#Requires -Version 5.1
<#
.SYNOPSIS
    Scout setup script for Windows with NVIDIA GPU

.DESCRIPTION
    Installs Ollama, pulls recommended model, and starts Scout via Docker.

.PARAMETER Model
    Ollama model to use (default: qwen2.5:7b for GPU systems)

.PARAMETER CpuOnly
    Skip GPU configuration and use CPU-only mode

.EXAMPLE
    .\setup-windows.ps1
    .\setup-windows.ps1 -Model "qwen2.5:14b"
    .\setup-windows.ps1 -CpuOnly
#>

param(
    [string]$Model = "qwen2.5:7b",
    [switch]$CpuOnly
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Scout Setup for Windows" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Docker
Write-Host "[1/5] Checking Docker..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version
    Write-Host "  ✓ Docker found: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Docker not found. Please install Docker Desktop." -ForegroundColor Red
    Write-Host "    https://www.docker.com/products/docker-desktop/" -ForegroundColor Gray
    exit 1
}

# Check/Install Ollama
Write-Host "[2/5] Checking Ollama..." -ForegroundColor Yellow
$ollamaInstalled = Get-Command ollama -ErrorAction SilentlyContinue

if (-not $ollamaInstalled) {
    Write-Host "  Installing Ollama via winget..." -ForegroundColor Gray
    try {
        winget install Ollama.Ollama --accept-package-agreements --accept-source-agreements
        # Refresh PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    } catch {
        Write-Host "  ✗ Failed to install Ollama. Please install manually:" -ForegroundColor Red
        Write-Host "    https://ollama.com/download/windows" -ForegroundColor Gray
        exit 1
    }
}
Write-Host "  ✓ Ollama installed" -ForegroundColor Green

# Check GPU
Write-Host "[3/5] Checking GPU..." -ForegroundColor Yellow
if (-not $CpuOnly) {
    try {
        $gpuInfo = nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>$null
        if ($gpuInfo) {
            Write-Host "  ✓ NVIDIA GPU detected: $gpuInfo" -ForegroundColor Green
        } else {
            Write-Host "  ! No NVIDIA GPU detected, falling back to CPU mode" -ForegroundColor Yellow
            $CpuOnly = $true
            $Model = "qwen2.5:3b"
        }
    } catch {
        Write-Host "  ! nvidia-smi not found, falling back to CPU mode" -ForegroundColor Yellow
        $CpuOnly = $true
        $Model = "qwen2.5:3b"
    }
} else {
    Write-Host "  - CPU-only mode selected" -ForegroundColor Gray
    $Model = "qwen2.5:3b"
}

# Start Ollama and pull model
Write-Host "[4/5] Setting up Ollama model: $Model..." -ForegroundColor Yellow
Write-Host "  Starting Ollama service..." -ForegroundColor Gray
Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden -PassThru | Out-Null
Start-Sleep -Seconds 3

Write-Host "  Pulling model (this may take a while)..." -ForegroundColor Gray
& ollama pull $Model
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ Failed to pull model" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ Model ready: $Model" -ForegroundColor Green

# Create .env file
Write-Host "[5/5] Configuring Scout..." -ForegroundColor Yellow
$envContent = @"
# Scout Configuration - Windows
PLATFORM=windows-gpu
OLLAMA_HOST=http://host.docker.internal:11434
OLLAMA_MODEL=$Model
SCOUT_PORT=8000
SCOUT_LOG_LEVEL=INFO
BENCHMARK_RUNS=3
"@

$envContent | Out-File -FilePath ".env" -Encoding UTF8
Write-Host "  ✓ Configuration saved to .env" -ForegroundColor Green

# Start Scout
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setup complete! Starting Scout..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

docker-compose up -d scout

Write-Host ""
Write-Host "Scout is starting. Access the web interface at:" -ForegroundColor Green
Write-Host "  http://localhost:8000" -ForegroundColor White
Write-Host ""
Write-Host "To run benchmarks:" -ForegroundColor Gray
Write-Host "  python benchmark/run_benchmark.py" -ForegroundColor White
Write-Host ""
Write-Host "To view logs:" -ForegroundColor Gray
Write-Host "  docker-compose logs -f scout" -ForegroundColor White
