# Work Package 5: Portable Deployment & Cross-Platform Benchmarking

## Overview

This work package creates a portable deployment system for Scout that enables easy installation and benchmarking across different platforms (Raspberry Pi, Windows with GPU, Linux with GPU).

**Goal:** Enable thesis comparison of Scout performance across edge (RPi) and GPU-accelerated platforms.

**Time Estimate:** 2-3 hours

---

## Directory Structure to Create

```
deploy/
├── README.md                      # Deployment guide
├── docker-compose.yml             # Main compose file (GPU-aware)
├── docker-compose.cpu.yml         # CPU-only override
├── .env.example                   # Environment template
├── scripts/
│   ├── setup-windows.ps1          # Windows setup script
│   ├── setup-linux-gpu.sh         # Linux with NVIDIA GPU
│   ├── setup-rpi.sh               # Raspberry Pi setup
│   └── pull-models.sh             # Model download helper
├── benchmark/
│   ├── run_benchmark.py           # Standardized benchmark script
│   ├── test_jobs/
│   │   ├── senior_python.txt      # Test job 1
│   │   ├── fullstack_react.txt    # Test job 2
│   │   └── devops_engineer.txt    # Test job 3
│   └── results/                   # Benchmark results directory
│       └── .gitkeep
└── configs/
    ├── ollama.env.example         # Ollama configuration
    └── scout.env.example          # Scout configuration
```

---

## Part 1: Main Docker Compose

**Create file:** `deploy/docker-compose.yml`

```yaml
# Scout Portable Deployment
# Supports CPU-only and GPU-accelerated configurations
#
# Usage:
#   CPU-only:  docker-compose up -d
#   With GPU:  docker-compose --profile gpu up -d
#
# Prerequisites:
#   - Docker and Docker Compose installed
#   - Ollama running (either as service or via this compose)
#   - For GPU: NVIDIA Container Toolkit installed

version: '3.8'

services:
  # ==========================================================================
  # SCOUT APPLICATION
  # ==========================================================================
  scout:
    build:
      context: ..
      dockerfile: Dockerfile
    container_name: scout-app
    ports:
      - "${SCOUT_PORT:-8000}:8000"
    volumes:
      # Persistent data
      - ../data:/app/data
      - ../outputs:/app/outputs
      # Optional: mount templates for customization
      - ../data/templates:/app/data/templates:ro
    environment:
      # Ollama connection
      - OLLAMA_HOST=${OLLAMA_HOST:-http://host.docker.internal:11434}
      - OLLAMA_MODEL=${OLLAMA_MODEL:-qwen2.5:3b}
      # Scout configuration
      - SCOUT_LOG_LEVEL=${SCOUT_LOG_LEVEL:-INFO}
      - SCOUT_ENVIRONMENT=${SCOUT_ENVIRONMENT:-production}
    extra_hosts:
      # Allows container to reach host's Ollama on Linux
      - "host.docker.internal:host-gateway"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    restart: unless-stopped
    depends_on:
      ollama:
        condition: service_healthy
        required: false

  # ==========================================================================
  # OLLAMA - CPU MODE (default)
  # ==========================================================================
  ollama:
    image: ollama/ollama:latest
    container_name: scout-ollama
    profiles:
      - ollama-cpu
      - full-cpu
    ports:
      - "${OLLAMA_PORT:-11434}:11434"
    volumes:
      - ollama_data:/root/.ollama
    environment:
      - OLLAMA_HOST=0.0.0.0
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 30s
    restart: unless-stopped

  # ==========================================================================
  # OLLAMA - GPU MODE (NVIDIA)
  # ==========================================================================
  ollama-gpu:
    image: ollama/ollama:latest
    container_name: scout-ollama-gpu
    profiles:
      - ollama-gpu
      - full-gpu
    ports:
      - "${OLLAMA_PORT:-11434}:11434"
    volumes:
      - ollama_data:/root/.ollama
    environment:
      - OLLAMA_HOST=0.0.0.0
      - NVIDIA_VISIBLE_DEVICES=all
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 30s
    restart: unless-stopped

  # ==========================================================================
  # BENCHMARK RUNNER (on-demand)
  # ==========================================================================
  benchmark:
    build:
      context: .
      dockerfile: benchmark/Dockerfile
    container_name: scout-benchmark
    profiles:
      - benchmark
    volumes:
      - ./benchmark/results:/app/results
      - ./benchmark/test_jobs:/app/test_jobs:ro
    environment:
      - SCOUT_URL=${SCOUT_URL:-http://scout:8000}
      - BENCHMARK_RUNS=${BENCHMARK_RUNS:-3}
    depends_on:
      - scout
    network_mode: "host"

volumes:
  ollama_data:
    name: scout-ollama-data
```

---

## Part 2: CPU-Only Override

**Create file:** `deploy/docker-compose.cpu.yml`

```yaml
# CPU-only override for Raspberry Pi and non-GPU systems
# Usage: docker-compose -f docker-compose.yml -f docker-compose.cpu.yml up -d

version: '3.8'

services:
  scout:
    environment:
      # Use smaller model for CPU
      - OLLAMA_MODEL=${OLLAMA_MODEL:-qwen2.5:3b}
      # Optimize for limited resources
      - SCOUT_LLM_TIMEOUT=600
```

---

## Part 3: Environment Template

**Create file:** `deploy/.env.example`

```bash
# Scout Portable Deployment Configuration
# Copy to .env and customize for your platform

# =============================================================================
# PLATFORM SELECTION
# =============================================================================
# Options: rpi, windows-gpu, linux-gpu, cpu-only
PLATFORM=cpu-only

# =============================================================================
# OLLAMA CONFIGURATION
# =============================================================================
# Where Ollama is running (use host.docker.internal for local Ollama on host)
OLLAMA_HOST=http://host.docker.internal:11434

# Model selection based on available resources:
#   RPi / CPU-only:  qwen2.5:3b (2GB VRAM/RAM)
#   8GB GPU:         qwen2.5:7b (5GB VRAM)
#   12GB+ GPU:       qwen2.5:14b (9GB VRAM)
#   24GB+ GPU:       qwen2.5:32b (20GB VRAM)
OLLAMA_MODEL=qwen2.5:3b

# Ollama port (if running via docker-compose)
OLLAMA_PORT=11434

# =============================================================================
# SCOUT CONFIGURATION
# =============================================================================
SCOUT_PORT=8000
SCOUT_LOG_LEVEL=INFO
SCOUT_ENVIRONMENT=production

# LLM timeout in seconds (increase for slow hardware)
SCOUT_LLM_TIMEOUT=300

# =============================================================================
# BENCHMARK CONFIGURATION
# =============================================================================
# Number of benchmark runs per test job
BENCHMARK_RUNS=3

# Scout URL for benchmark container
SCOUT_URL=http://localhost:8000
```

---

## Part 4: Setup Scripts

### 4.1 Windows Setup Script

**Create file:** `deploy/scripts/setup-windows.ps1`

```powershell
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
```

### 4.2 Linux GPU Setup Script

**Create file:** `deploy/scripts/setup-linux-gpu.sh`

```bash
#!/bin/bash
#
# Scout Setup for Linux with NVIDIA GPU
#
# Usage:
#   ./setup-linux-gpu.sh              # Auto-detect GPU, use recommended model
#   ./setup-linux-gpu.sh --model qwen2.5:14b    # Specify model
#   ./setup-linux-gpu.sh --cpu-only   # Force CPU mode
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Defaults
MODEL="qwen2.5:7b"
CPU_ONLY=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --model)
            MODEL="$2"
            shift 2
            ;;
        --cpu-only)
            CPU_ONLY=true
            MODEL="qwen2.5:3b"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo -e "${CYAN}========================================"
echo "Scout Setup for Linux"
echo -e "========================================${NC}"
echo ""

# Check Docker
echo -e "${YELLOW}[1/6] Checking Docker...${NC}"
if command -v docker &> /dev/null; then
    echo -e "  ${GREEN}✓ Docker found: $(docker --version)${NC}"
else
    echo -e "  ${RED}✗ Docker not found. Please install Docker.${NC}"
    echo "    https://docs.docker.com/engine/install/"
    exit 1
fi

# Check Docker Compose
echo -e "${YELLOW}[2/6] Checking Docker Compose...${NC}"
if docker compose version &> /dev/null; then
    echo -e "  ${GREEN}✓ Docker Compose found${NC}"
else
    echo -e "  ${RED}✗ Docker Compose not found.${NC}"
    exit 1
fi

# Check GPU
echo -e "${YELLOW}[3/6] Checking GPU...${NC}"
if [ "$CPU_ONLY" = false ]; then
    if command -v nvidia-smi &> /dev/null; then
        GPU_INFO=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || echo "")
        if [ -n "$GPU_INFO" ]; then
            echo -e "  ${GREEN}✓ NVIDIA GPU detected: $GPU_INFO${NC}"
            
            # Check NVIDIA Container Toolkit
            if docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi &> /dev/null; then
                echo -e "  ${GREEN}✓ NVIDIA Container Toolkit working${NC}"
            else
                echo -e "  ${YELLOW}! NVIDIA Container Toolkit not configured${NC}"
                echo "    Installing NVIDIA Container Toolkit..."
                
                # Install NVIDIA Container Toolkit
                distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
                curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
                curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
                    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
                    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
                sudo apt-get update
                sudo apt-get install -y nvidia-container-toolkit
                sudo nvidia-ctk runtime configure --runtime=docker
                sudo systemctl restart docker
                
                echo -e "  ${GREEN}✓ NVIDIA Container Toolkit installed${NC}"
            fi
            
            # Recommend model based on VRAM
            VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)
            if [ "$VRAM" -ge 20000 ]; then
                RECOMMENDED="qwen2.5:32b"
            elif [ "$VRAM" -ge 12000 ]; then
                RECOMMENDED="qwen2.5:14b"
            elif [ "$VRAM" -ge 8000 ]; then
                RECOMMENDED="qwen2.5:7b"
            else
                RECOMMENDED="qwen2.5:3b"
            fi
            echo -e "  ${CYAN}  Recommended model for ${VRAM}MB VRAM: $RECOMMENDED${NC}"
            
        else
            echo -e "  ${YELLOW}! No NVIDIA GPU detected, using CPU mode${NC}"
            CPU_ONLY=true
            MODEL="qwen2.5:3b"
        fi
    else
        echo -e "  ${YELLOW}! nvidia-smi not found, using CPU mode${NC}"
        CPU_ONLY=true
        MODEL="qwen2.5:3b"
    fi
else
    echo -e "  - CPU-only mode selected"
fi

# Install Ollama
echo -e "${YELLOW}[4/6] Setting up Ollama...${NC}"
if ! command -v ollama &> /dev/null; then
    echo "  Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
fi
echo -e "  ${GREEN}✓ Ollama installed${NC}"

# Start Ollama and pull model
echo -e "${YELLOW}[5/6] Pulling model: $MODEL...${NC}"
# Ensure Ollama is running
if ! pgrep -x "ollama" > /dev/null; then
    ollama serve &> /dev/null &
    sleep 3
fi

ollama pull "$MODEL"
echo -e "  ${GREEN}✓ Model ready: $MODEL${NC}"

# Create .env file
echo -e "${YELLOW}[6/6] Configuring Scout...${NC}"
cat > .env << EOF
# Scout Configuration - Linux
PLATFORM=linux-gpu
OLLAMA_HOST=http://host.docker.internal:11434
OLLAMA_MODEL=$MODEL
SCOUT_PORT=8000
SCOUT_LOG_LEVEL=INFO
BENCHMARK_RUNS=3
EOF
echo -e "  ${GREEN}✓ Configuration saved to .env${NC}"

# Start Scout
echo ""
echo -e "${CYAN}========================================"
echo "Setup complete! Starting Scout..."
echo -e "========================================${NC}"
echo ""

if [ "$CPU_ONLY" = true ]; then
    docker compose up -d scout
else
    docker compose --profile gpu up -d scout
fi

echo ""
echo -e "${GREEN}Scout is starting. Access the web interface at:${NC}"
echo "  http://localhost:8000"
echo ""
echo -e "To run benchmarks:"
echo "  python benchmark/run_benchmark.py"
echo ""
echo -e "To view logs:"
echo "  docker compose logs -f scout"
```

### 4.3 Raspberry Pi Setup Script

**Create file:** `deploy/scripts/setup-rpi.sh`

```bash
#!/bin/bash
#
# Scout Setup for Raspberry Pi 5
#
# Optimized for:
#   - Raspberry Pi 5 (8GB or 16GB)
#   - Ubuntu Server 24.04 or Raspberry Pi OS (64-bit)
#   - CPU-only inference with qwen2.5:3b
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

MODEL="qwen2.5:3b"

echo -e "${CYAN}========================================"
echo "Scout Setup for Raspberry Pi 5"
echo -e "========================================${NC}"
echo ""

# Check we're on ARM64
echo -e "${YELLOW}[1/5] Checking platform...${NC}"
ARCH=$(uname -m)
if [[ "$ARCH" != "aarch64" ]]; then
    echo -e "  ${RED}✗ This script is for ARM64 (aarch64). Detected: $ARCH${NC}"
    exit 1
fi

# Check memory
MEM_GB=$(free -g | awk '/^Mem:/{print $2}')
echo -e "  ${GREEN}✓ Platform: Raspberry Pi (ARM64)${NC}"
echo -e "  ${GREEN}✓ Memory: ${MEM_GB}GB${NC}"

if [ "$MEM_GB" -lt 8 ]; then
    echo -e "  ${YELLOW}! Less than 8GB RAM. Performance may be limited.${NC}"
fi

# Check Docker
echo -e "${YELLOW}[2/5] Checking Docker...${NC}"
if command -v docker &> /dev/null; then
    echo -e "  ${GREEN}✓ Docker found${NC}"
else
    echo "  Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    echo -e "  ${GREEN}✓ Docker installed${NC}"
    echo -e "  ${YELLOW}! You may need to log out and back in for docker permissions${NC}"
fi

# Install Ollama
echo -e "${YELLOW}[3/5] Setting up Ollama...${NC}"
if ! command -v ollama &> /dev/null; then
    echo "  Installing Ollama for ARM64..."
    curl -fsSL https://ollama.com/install.sh | sh
fi
echo -e "  ${GREEN}✓ Ollama installed${NC}"

# Pull model
echo -e "${YELLOW}[4/5] Pulling model: $MODEL...${NC}"
echo "  This will take several minutes on RPi..."
if ! pgrep -x "ollama" > /dev/null; then
    ollama serve &> /dev/null &
    sleep 5
fi
ollama pull "$MODEL"
echo -e "  ${GREEN}✓ Model ready${NC}"

# Configure Scout
echo -e "${YELLOW}[5/5] Configuring Scout...${NC}"
cat > .env << EOF
# Scout Configuration - Raspberry Pi 5
PLATFORM=rpi
OLLAMA_HOST=http://host.docker.internal:11434
OLLAMA_MODEL=$MODEL
SCOUT_PORT=8000
SCOUT_LOG_LEVEL=INFO
SCOUT_LLM_TIMEOUT=600
BENCHMARK_RUNS=3
EOF
echo -e "  ${GREEN}✓ Configuration saved${NC}"

# Build and start
echo ""
echo -e "${CYAN}========================================"
echo "Setup complete! Starting Scout..."
echo -e "========================================${NC}"
echo ""

docker compose -f docker-compose.yml -f docker-compose.cpu.yml up -d scout

echo ""
echo -e "${GREEN}Scout is starting. Access the web interface at:${NC}"
echo "  http://$(hostname -I | awk '{print $1}'):8000"
echo ""
echo -e "Performance notes for Raspberry Pi:"
echo "  - Expected inference speed: 1.5-2.5 tokens/second"
echo "  - Full pipeline time: 5-10 minutes"
echo "  - Monitor temperature: vcgencmd measure_temp"
echo ""
echo -e "To run benchmarks:"
echo "  python benchmark/run_benchmark.py"
```

### 4.4 Model Pull Helper

**Create file:** `deploy/scripts/pull-models.sh`

```bash
#!/bin/bash
#
# Pull Ollama models for different deployment scenarios
#

set -e

echo "Scout Model Download Helper"
echo "==========================="
echo ""

case "$1" in
    minimal)
        echo "Pulling minimal model (qwen2.5:3b) - ~2GB"
        ollama pull qwen2.5:3b
        ;;
    standard)
        echo "Pulling standard model (qwen2.5:7b) - ~5GB"
        ollama pull qwen2.5:7b
        ;;
    full)
        echo "Pulling full model (qwen2.5:14b) - ~9GB"
        ollama pull qwen2.5:14b
        ;;
    all)
        echo "Pulling all models..."
        ollama pull qwen2.5:3b
        ollama pull qwen2.5:7b
        ollama pull qwen2.5:14b
        ;;
    *)
        echo "Usage: $0 {minimal|standard|full|all}"
        echo ""
        echo "  minimal  - qwen2.5:3b  (~2GB) - RPi, low-end systems"
        echo "  standard - qwen2.5:7b  (~5GB) - 8GB+ GPU"
        echo "  full     - qwen2.5:14b (~9GB) - 12GB+ GPU"
        echo "  all      - Download all models"
        exit 1
        ;;
esac

echo ""
echo "Done! Models are ready for use."
```

---

## Part 5: Benchmark System

### 5.1 Benchmark Script

**Create file:** `deploy/benchmark/run_benchmark.py`

```python
#!/usr/bin/env python3
"""
Scout Cross-Platform Benchmark

Runs standardized job postings through Scout pipeline and collects metrics
for thesis comparison across different hardware platforms.

Usage:
    python run_benchmark.py                    # Run with defaults
    python run_benchmark.py --runs 5           # 5 runs per job
    python run_benchmark.py --url http://pi:8000  # Custom Scout URL
    python run_benchmark.py --output results/  # Custom output directory
"""

import argparse
import asyncio
import json
import platform
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import httpx
except ImportError:
    print("Installing required package: httpx")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx"])
    import httpx


# =============================================================================
# TEST JOB DEFINITIONS
# =============================================================================

TEST_JOBS = {
    "senior_python": {
        "name": "Senior Python Developer",
        "description": "Backend-focused Python role at a FinTech startup",
        "text": """
Senior Python Developer - FinTech Startup

Location: Remote (US/EU timezone overlap)
Salary: $150,000 - $180,000 + equity

About Us:
We're a fast-growing FinTech startup revolutionizing payment processing for 
small businesses. Our platform handles millions of transactions daily.

The Role:
We're seeking an experienced Python developer to join our backend team. You'll 
be working on our core payment processing engine and API infrastructure.

Requirements:
- 5+ years of professional Python development experience
- Strong experience with FastAPI or Django REST Framework
- PostgreSQL expertise including query optimization
- Redis for caching and message queuing
- Docker and Kubernetes in production environments
- AWS services (EC2, RDS, Lambda, SQS)
- Understanding of microservices architecture patterns
- Experience with async Python (asyncio, aiohttp)

Nice to Have:
- Financial services or payment processing background
- Real-time data processing with Kafka or similar
- Machine learning model deployment experience
- Contributions to open-source projects

What We Offer:
- Competitive salary and equity package
- Fully remote work environment
- Health, dental, and vision insurance
- Unlimited PTO policy
- Annual learning budget of $2,000
- Latest MacBook Pro and home office setup

Apply with your resume and a brief note about why you're interested.
"""
    },
    
    "fullstack_react": {
        "name": "Full Stack React Developer",
        "description": "Full stack role with React frontend focus",
        "text": """
Full Stack Developer - React & Node.js

Company: TechVentures Inc.
Location: San Francisco, CA (Hybrid - 2 days in office)
Compensation: $140,000 - $165,000

About TechVentures:
We build enterprise software solutions for Fortune 500 companies. Our 
flagship product is a workflow automation platform used by over 200 
organizations worldwide.

Role Overview:
Join our product team to build and enhance our web application. You'll work 
across the full stack, with a focus on creating exceptional user experiences 
with React while building robust Node.js backend services.

Technical Requirements:
- 4+ years of full stack development experience
- Expert-level React skills (hooks, context, Redux or Zustand)
- TypeScript proficiency (both frontend and backend)
- Node.js and Express.js backend development
- REST API design and GraphQL experience
- PostgreSQL and MongoDB database experience
- Git workflow and CI/CD pipelines
- Unit testing with Jest and React Testing Library

Bonus Points:
- Experience with Next.js or Remix
- Familiarity with AWS or GCP cloud services
- UI/UX design sensibility
- Experience with WebSocket real-time features
- Previous work on enterprise B2B products

Benefits:
- Competitive base salary plus annual bonus
- 401(k) with 4% company match
- Premium health insurance (medical, dental, vision)
- 3 weeks PTO plus holidays
- Commuter benefits for hybrid work
- Team events and professional development

To apply, send your resume and portfolio/GitHub profile.
"""
    },
    
    "devops_engineer": {
        "name": "DevOps Engineer",
        "description": "Infrastructure and automation focused role",
        "text": """
Senior DevOps Engineer

Organization: CloudScale Systems
Location: Austin, TX or Remote
Salary Range: $145,000 - $175,000

About CloudScale:
We provide cloud infrastructure management solutions to mid-size companies. 
Our platform automates cloud resource provisioning, monitoring, and cost 
optimization across AWS, Azure, and GCP.

Position Summary:
We're looking for a Senior DevOps Engineer to lead our infrastructure 
automation initiatives. You'll design and implement CI/CD pipelines, 
manage Kubernetes clusters, and ensure our platform maintains 99.99% uptime.

Required Skills:
- 5+ years in DevOps/SRE/Infrastructure roles
- Expert knowledge of Kubernetes (CKA certification preferred)
- Infrastructure as Code with Terraform or Pulumi
- CI/CD pipeline design (GitHub Actions, GitLab CI, or Jenkins)
- Strong Linux system administration skills
- AWS certification and hands-on experience
- Monitoring and observability (Prometheus, Grafana, DataDog)
- Python or Go scripting for automation

Desired Experience:
- Multi-cloud environment management
- Service mesh implementation (Istio or Linkerd)
- Database administration (PostgreSQL, Redis clusters)
- Security best practices and compliance (SOC2, HIPAA)
- On-call rotation and incident management experience

What We Provide:
- Competitive compensation with equity
- Full remote work option
- Health and wellness benefits
- $3,000 annual education budget
- Home office equipment allowance
- Flexible work schedule

Interview Process:
1. Initial phone screen (30 min)
2. Technical assessment (take-home, 2-3 hours)
3. System design interview (1 hour)
4. Team culture fit interview (45 min)
"""
    }
}


# =============================================================================
# SYSTEM INFORMATION
# =============================================================================

def get_system_info() -> dict:
    """Collect system information for benchmark context."""
    info = {
        "hostname": platform.node(),
        "platform": platform.system(),
        "platform_release": platform.release(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "timestamp": datetime.now().isoformat(),
    }
    
    # Try to get CPU info
    try:
        if platform.system() == "Linux":
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if "model name" in line:
                        info["cpu_model"] = line.split(":")[1].strip()
                        break
            # Get CPU count
            import os
            info["cpu_count"] = os.cpu_count()
    except:
        pass
    
    # Try to get memory info
    try:
        if platform.system() == "Linux":
            with open("/proc/meminfo") as f:
                for line in f:
                    if "MemTotal" in line:
                        mem_kb = int(line.split()[1])
                        info["memory_gb"] = round(mem_kb / 1024 / 1024, 1)
                        break
    except:
        pass
    
    # Try to get GPU info
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", 
             "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            info["gpu"] = result.stdout.strip()
        else:
            info["gpu"] = "None (CPU only)"
    except:
        info["gpu"] = "None (CPU only)"
    
    # Try to get Raspberry Pi info
    try:
        if platform.system() == "Linux" and platform.machine() == "aarch64":
            result = subprocess.run(
                ["cat", "/proc/device-tree/model"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                info["device_model"] = result.stdout.strip().replace('\x00', '')
    except:
        pass
    
    return info


def get_ollama_info(base_url: str) -> dict:
    """Get Ollama model information."""
    try:
        # Extract Ollama URL from environment or derive from Scout
        ollama_url = "http://localhost:11434"
        
        import httpx
        response = httpx.get(f"{ollama_url}/api/tags", timeout=10)
        if response.status_code == 200:
            data = response.json()
            models = [m["name"] for m in data.get("models", [])]
            return {"available_models": models}
    except:
        pass
    return {"available_models": "unknown"}


# =============================================================================
# BENCHMARK RUNNER
# =============================================================================

async def run_single_job(
    client: httpx.AsyncClient,
    base_url: str,
    job_key: str,
    job_data: dict,
    run_number: int
) -> dict:
    """Run a single job through the pipeline and collect metrics."""
    
    result = {
        "job_key": job_key,
        "job_name": job_data["name"],
        "run_number": run_number,
        "status": "unknown",
        "error": None,
        "timings": {},
    }
    
    try:
        # Start the job
        start_time = time.time()
        response = await client.post(
            f"{base_url}/api/v1/jobs/apply",
            json={"job_text": job_data["text"], "source": "benchmark"}
        )
        
        if response.status_code != 200:
            result["status"] = "failed"
            result["error"] = f"Failed to start job: {response.status_code}"
            return result
        
        job_id = response.json()["job_id"]
        result["job_id"] = job_id
        submit_time = time.time()
        result["timings"]["submit_ms"] = int((submit_time - start_time) * 1000)
        
        # Poll until complete
        while True:
            await asyncio.sleep(2)
            
            status_response = await client.get(f"{base_url}/api/v1/jobs/{job_id}")
            if status_response.status_code != 200:
                result["status"] = "failed"
                result["error"] = f"Failed to get status: {status_response.status_code}"
                return result
            
            status_data = status_response.json()
            
            if status_data["status"] in ("completed", "failed"):
                end_time = time.time()
                
                result["status"] = status_data["status"]
                result["timings"]["total_seconds"] = round(end_time - start_time, 2)
                result["compatibility_score"] = status_data.get("compatibility_score")
                
                # Extract step timings
                if "steps" in status_data:
                    for step in status_data["steps"]:
                        step_name = step.get("step", "unknown")
                        result["timings"][f"{step_name}_ms"] = step.get("duration_ms", 0)
                
                if status_data["status"] == "failed":
                    result["error"] = status_data.get("error", "Unknown error")
                
                return result
            
            # Timeout after 15 minutes
            if time.time() - start_time > 900:
                result["status"] = "timeout"
                result["error"] = "Pipeline timeout after 15 minutes"
                return result
                
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    
    return result


async def run_benchmark(
    base_url: str,
    runs_per_job: int = 3,
    jobs_to_run: list[str] | None = None
) -> dict:
    """Run full benchmark suite."""
    
    results = {
        "system_info": get_system_info(),
        "ollama_info": get_ollama_info(base_url),
        "scout_url": base_url,
        "runs_per_job": runs_per_job,
        "started_at": datetime.now().isoformat(),
        "job_results": [],
    }
    
    # Filter jobs if specified
    jobs = {k: v for k, v in TEST_JOBS.items() 
            if jobs_to_run is None or k in jobs_to_run}
    
    total_runs = len(jobs) * runs_per_job
    current_run = 0
    
    async with httpx.AsyncClient(timeout=httpx.Timeout(600.0)) as client:
        # Verify Scout is accessible
        try:
            health = await client.get(f"{base_url}/api/v1/health")
            if health.status_code != 200:
                print(f"Error: Scout not accessible at {base_url}")
                return results
            results["scout_health"] = health.json()
        except Exception as e:
            print(f"Error: Cannot connect to Scout at {base_url}: {e}")
            return results
        
        # Run benchmarks
        for job_key, job_data in jobs.items():
            print(f"\n{'='*60}")
            print(f"Job: {job_data['name']}")
            print(f"{'='*60}")
            
            for run in range(1, runs_per_job + 1):
                current_run += 1
                print(f"\n  Run {run}/{runs_per_job} ({current_run}/{total_runs} total)...")
                
                result = await run_single_job(
                    client, base_url, job_key, job_data, run
                )
                results["job_results"].append(result)
                
                if result["status"] == "completed":
                    total_sec = result["timings"].get("total_seconds", 0)
                    score = result.get("compatibility_score", "N/A")
                    print(f"    ✓ Completed in {total_sec:.1f}s (score: {score})")
                else:
                    print(f"    ✗ {result['status']}: {result.get('error', 'Unknown')}")
    
    results["completed_at"] = datetime.now().isoformat()
    
    # Calculate summary statistics
    completed_runs = [r for r in results["job_results"] if r["status"] == "completed"]
    if completed_runs:
        total_times = [r["timings"]["total_seconds"] for r in completed_runs]
        results["summary"] = {
            "total_runs": len(results["job_results"]),
            "successful_runs": len(completed_runs),
            "success_rate": len(completed_runs) / len(results["job_results"]),
            "avg_total_seconds": sum(total_times) / len(total_times),
            "min_total_seconds": min(total_times),
            "max_total_seconds": max(total_times),
        }
        
        # Per-module averages
        for module in ["rinser", "analyzer", "creator", "formatter"]:
            times = [r["timings"].get(f"{module}_ms", 0) for r in completed_runs 
                    if r["timings"].get(f"{module}_ms")]
            if times:
                results["summary"][f"avg_{module}_ms"] = sum(times) / len(times)
    
    return results


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Scout Cross-Platform Benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_benchmark.py
  python run_benchmark.py --runs 5 --url http://192.168.1.100:8000
  python run_benchmark.py --jobs senior_python devops_engineer
        """
    )
    
    parser.add_argument(
        "--url", 
        default="http://localhost:8000",
        help="Scout URL (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--runs", 
        type=int, 
        default=3,
        help="Number of runs per job (default: 3)"
    )
    parser.add_argument(
        "--output", 
        default="results",
        help="Output directory for results (default: results)"
    )
    parser.add_argument(
        "--jobs",
        nargs="+",
        choices=list(TEST_JOBS.keys()),
        help="Specific jobs to run (default: all)"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Scout Cross-Platform Benchmark")
    print("=" * 60)
    print(f"Scout URL: {args.url}")
    print(f"Runs per job: {args.runs}")
    print(f"Jobs: {args.jobs or 'all'}")
    print()
    
    # Run benchmark
    results = asyncio.run(run_benchmark(
        base_url=args.url,
        runs_per_job=args.runs,
        jobs_to_run=args.jobs
    ))
    
    # Save results
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    hostname = results["system_info"].get("hostname", "unknown")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"benchmark_{hostname}_{timestamp}.json"
    
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "=" * 60)
    print("Benchmark Complete")
    print("=" * 60)
    
    if "summary" in results:
        s = results["summary"]
        print(f"Success rate: {s['success_rate']*100:.0f}% ({s['successful_runs']}/{s['total_runs']})")
        print(f"Average time: {s['avg_total_seconds']:.1f}s")
        print(f"Time range: {s['min_total_seconds']:.1f}s - {s['max_total_seconds']:.1f}s")
    
    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    main()
```

### 5.2 Benchmark Dockerfile

**Create file:** `deploy/benchmark/Dockerfile`

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir httpx

# Copy benchmark files
COPY run_benchmark.py .
COPY test_jobs/ ./test_jobs/

# Create results directory
RUN mkdir -p /app/results

ENTRYPOINT ["python", "run_benchmark.py"]
CMD ["--runs", "3"]
```

### 5.3 Test Job Files

**Create file:** `deploy/benchmark/test_jobs/.gitkeep`

```
# Test job files are embedded in run_benchmark.py
# This directory can hold additional custom test jobs if needed
```

---

## Part 6: Documentation

**Create file:** `deploy/README.md`

```markdown
# Scout Portable Deployment

This directory contains everything needed to deploy Scout on different platforms for cross-platform benchmarking.

## Supported Platforms

| Platform | Script | Model | Expected Performance |
|----------|--------|-------|---------------------|
| Raspberry Pi 5 | `setup-rpi.sh` | qwen2.5:3b | ~2 tok/s, 5-8 min/job |
| Windows + NVIDIA GPU | `setup-windows.ps1` | qwen2.5:7b | ~40 tok/s, 30-60 sec/job |
| Linux + NVIDIA GPU | `setup-linux-gpu.sh` | qwen2.5:7b+ | ~50 tok/s, 20-40 sec/job |

## Quick Start

### 1. Clone and navigate to deploy directory

```bash
git clone <repository>
cd scout/deploy
```

### 2. Run platform-specific setup

**Raspberry Pi:**
```bash
chmod +x scripts/setup-rpi.sh
./scripts/setup-rpi.sh
```

**Windows (PowerShell as Administrator):**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\scripts\setup-windows.ps1
```

**Linux with NVIDIA GPU:**
```bash
chmod +x scripts/setup-linux-gpu.sh
./scripts/setup-linux-gpu.sh
```

### 3. Access Scout

Open http://localhost:8000 in your browser.

### 4. Run Benchmarks

```bash
python benchmark/run_benchmark.py
```

Results are saved to `benchmark/results/`.

## Configuration

Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
nano .env
```

Key settings:
- `OLLAMA_MODEL` - Model to use (adjust based on available VRAM)
- `SCOUT_PORT` - Web interface port
- `SCOUT_LLM_TIMEOUT` - Timeout for LLM calls (increase for slow hardware)

## Docker Compose Profiles

```bash
# Scout only (Ollama running separately on host)
docker compose up -d scout

# Scout + Ollama CPU
docker compose --profile ollama-cpu up -d

# Scout + Ollama GPU (requires NVIDIA Container Toolkit)
docker compose --profile ollama-gpu up -d

# Full stack CPU
docker compose --profile full-cpu up -d

# Full stack GPU
docker compose --profile full-gpu up -d
```

## Benchmark Results

Benchmark results are JSON files with:
- System information (CPU, RAM, GPU)
- Per-job timing breakdowns
- Module-level metrics (rinser, analyzer, creator, formatter)
- Success rates and averages

Compare across platforms:
```bash
# View results
cat benchmark/results/benchmark_*.json | jq '.summary'
```

## Troubleshooting

### Ollama connection issues

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Check from inside container
docker exec scout-app curl http://host.docker.internal:11434/api/tags
```

### GPU not detected

```bash
# Verify NVIDIA driver
nvidia-smi

# Verify container toolkit
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi
```

### Slow performance on RPi

- Ensure adequate cooling (active cooling recommended)
- Check thermal throttling: `vcgencmd measure_temp`
- Consider using swap if RAM limited: `sudo swapon --show`
```

---

## Validation Steps

### 1. File Structure Check

```bash
# Verify all files created
ls -la deploy/
ls -la deploy/scripts/
ls -la deploy/benchmark/
ls -la deploy/configs/
```

### 2. Script Syntax Check

```bash
# Check shell scripts
bash -n deploy/scripts/setup-linux-gpu.sh
bash -n deploy/scripts/setup-rpi.sh

# Check Python
python -m py_compile deploy/benchmark/run_benchmark.py
```

### 3. Docker Compose Validation

```bash
cd deploy
docker compose config
```

---

## Completion Checklist

- [ ] `deploy/docker-compose.yml` created
- [ ] `deploy/docker-compose.cpu.yml` created
- [ ] `deploy/.env.example` created
- [ ] `deploy/scripts/setup-windows.ps1` created
- [ ] `deploy/scripts/setup-linux-gpu.sh` created
- [ ] `deploy/scripts/setup-rpi.sh` created
- [ ] `deploy/scripts/pull-models.sh` created
- [ ] `deploy/benchmark/run_benchmark.py` created
- [ ] `deploy/benchmark/Dockerfile` created
- [ ] `deploy/benchmark/test_jobs/.gitkeep` created
- [ ] `deploy/benchmark/results/.gitkeep` created
- [ ] `deploy/configs/` directory created
- [ ] `deploy/README.md` created
- [ ] All scripts are executable
- [ ] Docker compose validates successfully
- [ ] Code committed

```bash
git add deploy/
git commit -m "WP5: Add portable deployment and cross-platform benchmarking

- Docker Compose with CPU and GPU profiles
- Platform setup scripts (Windows, Linux GPU, Raspberry Pi)
- Standardized benchmark suite with 3 test jobs
- Automated system info collection
- Results output in JSON for thesis analysis

Enables cross-platform performance comparison for thesis."
```
