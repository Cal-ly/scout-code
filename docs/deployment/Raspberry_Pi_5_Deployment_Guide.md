# Scout PoC - Raspberry Pi 5 Deployment Guide

**Version:** 1.0
**Date:** December 14, 2025
**Target:** Raspberry Pi 5 (16GB RAM, overclocked 3GHz)
**OS:** Ubuntu Server 24.04 LTS (Noble Numbat)

---

## Executive Summary

This guide provides step-by-step instructions for deploying Scout on a Raspberry Pi 5 for thesis demonstration. Scout uses **local Ollama inference** with Qwen 2.5 3B and Gemma 2 2B models, eliminating cloud API dependencies while showcasing edge computing capabilities.

### Deployment Profile

| Aspect | Specification |
|--------|---------------|
| **Target Use** | Bachelor's thesis demonstration, PoC validation |
| **Expected Load** | Single user, sequential pipeline execution |
| **Pipeline Time** | 15-30 minutes (expected for local LLM inference) |
| **Network** | Local network access via SSH and web browser |
| **Total Setup Time** | 2-3 hours (excluding model downloads) |

### Hardware Configuration

| Component | Specification |
|-----------|---------------|
| **Device** | Raspberry Pi 5 |
| **RAM** | 16GB |
| **CPU Clock** | Overclocked to 3GHz (stable) |
| **Storage** | (Your storage configuration) |
| **Swap** | 16GB swap file configured |
| **OS** | Ubuntu Server 24.04 LTS (Noble) |
| **IP Address** | 192.168.1.21 |
| **Username** | cally |

---

## Prerequisites

### Development Machine Requirements

Before starting deployment, ensure your development machine has:

- Git installed
- SSH client
- Web browser for testing

### Raspberry Pi Requirements (Already Configured)

Your Pi 5 should have:

- [x] Ubuntu Server 24.04 LTS installed
- [x] SSH access enabled
- [x] Network connectivity
- [x] 16GB swap configured
- [x] Python 3.12+ installed (check: `python3 --version`)

---

## Phase 1: SSH Connection and System Verification

### 1.1 Connect to Raspberry Pi

```bash
# From your Windows development machine (PowerShell or terminal)
ssh cally@192.168.1.21
```

### 1.2 Verify System Configuration

```bash
# Check Ubuntu version
lsb_release -a
# Expected: Ubuntu 24.04 LTS (Noble Numbat)

# Check architecture
uname -m
# Expected: aarch64

# Check available memory
free -h
# Expected: ~16GB total RAM

# Check swap
swapon --show
# Should show 16GB swap file

# Check CPU info
cat /proc/cpuinfo | grep -E "(model name|BogoMIPS)" | head -4
# BogoMIPS should reflect 3GHz overclock

# Check Python version
python3 --version
# Should be Python 3.12+
```

### 1.3 Update System Packages

```bash
sudo apt update && sudo apt upgrade -y

# Install essential build dependencies
sudo apt install -y \
    build-essential \
    python3-dev \
    python3-pip \
    python3-venv \
    git \
    curl \
    htop \
    tmux
```

---

## Phase 2: Ollama Installation

### 2.1 Install Ollama for ARM64

```bash
# Download and run Ollama installer
curl -fsSL https://ollama.com/install.sh | sh

# Verify installation
ollama --version
# Expected: ollama version 0.4.x or newer
```

### 2.2 Configure Ollama Service

```bash
# Check if Ollama service is running
sudo systemctl status ollama

# If not running, start it
sudo systemctl start ollama
sudo systemctl enable ollama

# Verify Ollama is listening
curl http://localhost:11434/api/tags
# Should return JSON with models list (empty initially)
```

### 2.3 Optimize Ollama for Pi 5

Create a systemd override for Pi 5 optimizations:

```bash
sudo mkdir -p /etc/systemd/system/ollama.service.d/

sudo tee /etc/systemd/system/ollama.service.d/override.conf > /dev/null <<EOF
[Service]
# Limit parallel requests to prevent memory pressure
Environment="OLLAMA_NUM_PARALLEL=1"
# Keep only one model loaded at a time
Environment="OLLAMA_MAX_LOADED_MODELS=1"
# Ensure sufficient timeout for slow inference
Environment="OLLAMA_KEEP_ALIVE=10m"
EOF

# Apply configuration
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

### 2.4 Pull Required Models

```bash
# Pull primary model - Qwen 2.5 3B (~2GB download)
# This will take 5-15 minutes depending on network speed
ollama pull qwen2.5:3b

# Pull fallback model - Gemma 2 2B (~1.6GB download)
ollama pull gemma2:2b

# Verify models are installed
ollama list
# Expected output:
# NAME            ID              SIZE    MODIFIED
# qwen2.5:3b      abc123...       2.0 GB  Just now
# gemma2:2b       def456...       1.6 GB  Just now
```

### 2.5 Test Ollama Inference

```bash
# Test basic inference (may take 30-60 seconds first time)
ollama run qwen2.5:3b "Hello! Please respond with exactly 5 words."

# Test JSON mode
curl http://localhost:11434/api/chat -d '{
  "model": "qwen2.5:3b",
  "messages": [{"role": "user", "content": "Return a JSON object with keys: name, age"}],
  "format": "json",
  "stream": false
}'
# Should return valid JSON response
```

---

## Phase 3: Scout Application Deployment

### 3.1 Clone Repository

```bash
# Create project directory
mkdir -p ~/projects
cd ~/projects

# Clone Scout repository
git clone https://github.com/Cal-ly/scout-code.git
cd scout-code

# Verify you're on main branch at expected commit
git branch
git log --oneline -1
# Should show: 58dcd21 Add configurable module settings...
```

### 3.2 Create Python Virtual Environment

```bash
# Create virtual environment with Python 3.12+
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Verify Python in venv
which python
# Should show: /home/cally/projects/scout-code/venv/bin/python

# Upgrade pip
pip install --upgrade pip
```

### 3.3 Install Dependencies

```bash
# Install production dependencies
pip install -r requirements.txt

# Note: sentence-transformers installation may take 5-10 minutes
# It downloads the embedding model (~90MB) on first use

# Verify critical packages installed
pip list | grep -E "(ollama|chromadb|fastapi|uvicorn|sentence-transformers)"
```

**Expected packages:**
- `ollama>=0.4.0`
- `chromadb>=0.4.0`
- `fastapi>=0.100.0`
- `uvicorn>=0.22.0`
- `sentence-transformers>=2.2.0`

### 3.4 Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

**Update `.env` with these settings:**

```bash
# ============================================
# LLM Service Configuration (Local Ollama)
# ============================================
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:3b
LLM_FALLBACK_MODEL=gemma2:2b
OLLAMA_HOST=http://localhost:11434

# Generation Parameters (optimized for Pi 5)
LLM_MAX_TOKENS=2000
LLM_TEMPERATURE=0.3
LLM_TIMEOUT=300  # Increased for slow inference

# ============================================
# Database Configuration
# ============================================
DATABASE_PATH=data/scout.db
CHROMA_PERSIST_DIR=data/chroma_data

# ============================================
# Cache Configuration
# ============================================
# PoC uses two-tier caching: Memory (L1) + File (L2)
# No Redis - file-based persistence only
CACHE_DIR=data/cache
CACHE_MEMORY_MAX_ENTRIES=100
CACHE_TTL=3600

# ============================================
# Application Settings
# ============================================
APP_ENV=production
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=false
LOG_LEVEL=INFO

# ============================================
# File Storage
# ============================================
UPLOAD_DIR=data/uploads
OUTPUT_DIR=data/outputs
TEMPLATE_DIR=src/templates
```

### 3.5 Create Data Directories

```bash
# Create required directories
mkdir -p data/{uploads,outputs,chroma_data,cache}

# Set permissions
chmod 755 data data/*
```

### 3.6 Verify Installation

```bash
# Test Python imports
python -c "
from src.services.llm_service import LLMService
from src.services.vector_store import VectorStoreService
from src.services.cache_service import CacheService
from src.modules.collector import Collector
from src.web.main import app
print('All imports successful!')
"
```

---

## Phase 4: Running Scout Application

### 4.1 Start Scout (Development Mode)

For initial testing:

```bash
# Ensure venv is activated
source ~/projects/scout-code/venv/bin/activate
cd ~/projects/scout-code

# Start with uvicorn (development)
uvicorn src.web.main:app --host 0.0.0.0 --port 8000
```

### 4.2 Verify Application is Running

From another terminal or your development machine:

```bash
# Health check
curl http://192.168.1.21:8000/api/health
# Expected: {"status":"healthy","services":{...}}

# Or open in browser
# http://192.168.1.21:8000
```

### 4.3 Start Scout (Production Mode with tmux)

For persistent deployment that survives SSH disconnection:

```bash
# Start a tmux session
tmux new-session -s scout

# Inside tmux, start Scout
source ~/projects/scout-code/venv/bin/activate
cd ~/projects/scout-code
uvicorn src.web.main:app --host 0.0.0.0 --port 8000 --workers 1

# Detach from tmux: Press Ctrl+B, then D
# The server continues running in background

# To reattach later:
tmux attach -t scout

# To list sessions:
tmux list-sessions
```

### 4.4 Create Systemd Service (Optional - For Auto-Start)

For automatic startup on boot:

```bash
sudo tee /etc/systemd/system/scout.service > /dev/null <<EOF
[Unit]
Description=Scout Job Application System
After=network.target ollama.service
Requires=ollama.service

[Service]
Type=simple
User=cally
Group=cally
WorkingDirectory=/home/cally/projects/scout-code
Environment="PATH=/home/cally/projects/scout-code/venv/bin:/usr/bin"
ExecStart=/home/cally/projects/scout-code/venv/bin/uvicorn src.web.main:app --host 0.0.0.0 --port 8000 --workers 1
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable scout
sudo systemctl start scout

# Check status
sudo systemctl status scout
```

---

## Phase 5: Validation Testing

### 5.1 Health Check Endpoints

```bash
# Full health check
curl http://192.168.1.21:8000/api/health | python3 -m json.tool

# Expected response shows all services healthy:
# {
#   "status": "healthy",
#   "services": {
#     "llm": {"status": "healthy", "provider": "ollama", "model": "qwen2.5:3b"},
#     "vector_store": {"status": "healthy", "collections": 2},
#     "cache": {"status": "healthy"},
#     ...
#   }
# }
```

### 5.2 Monitor Resources During Testing

Open a second SSH session to monitor:

```bash
# Monitor system resources
htop

# Monitor temperature (if vcgencmd available)
# For Ubuntu, use:
cat /sys/class/thermal/thermal_zone0/temp
# Divide by 1000 for Celsius (e.g., 65000 = 65°C)

# Watch Ollama logs
sudo journalctl -u ollama -f
```

### 5.3 End-to-End Pipeline Test

1. Open web interface: `http://192.168.1.21:8000`
2. Navigate to Profile section
3. Create or import a user profile
4. Submit a sample job posting
5. Monitor pipeline progress
6. Download generated PDF

---

## Phase 6: Troubleshooting

### Common Issues and Solutions

#### Issue: Ollama "connection refused"

```bash
# Check if Ollama is running
sudo systemctl status ollama

# If not running, start it
sudo systemctl start ollama

# Check logs for errors
sudo journalctl -u ollama -n 50
```

#### Issue: Out of memory during inference

```bash
# Check memory usage
free -h

# Ensure swap is active
swapon --show

# If needed, increase swap (one-time):
sudo swapoff -a
sudo fallocate -l 24G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

#### Issue: Very slow inference (>60 seconds per response)

This is expected for local LLM on Pi 5. Typical speeds:
- Qwen 2.5 3B: 2-4 tokens/second
- Gemma 2 2B: 4-6 tokens/second

For a 500-token response, expect 2-4 minutes.

#### Issue: Python import errors

```bash
# Ensure venv is activated
source ~/projects/scout-code/venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

#### Issue: ChromaDB permission errors

```bash
# Fix data directory permissions
chmod -R 755 ~/projects/scout-code/data
```

#### Issue: Port 8000 already in use

```bash
# Find what's using the port
sudo lsof -i :8000

# Kill the process if needed
sudo kill -9 <PID>
```

---

## Phase 7: Monitoring and Maintenance

### 7.1 Log Monitoring

```bash
# Scout application logs (if using systemd)
sudo journalctl -u scout -f

# Ollama logs
sudo journalctl -u ollama -f

# Combined view
sudo journalctl -u scout -u ollama -f
```

### 7.2 Temperature Monitoring

```bash
# Create monitoring script
cat > ~/monitor-temp.sh <<'EOF'
#!/bin/bash
while true; do
    TEMP=$(cat /sys/class/thermal/thermal_zone0/temp)
    TEMP_C=$((TEMP / 1000))
    MEM=$(free -h | grep Mem | awk '{print $3"/"$2}')
    echo "$(date '+%H:%M:%S') - Temp: ${TEMP_C}°C - Memory: ${MEM}"
    sleep 5
done
EOF
chmod +x ~/monitor-temp.sh

# Run monitoring
~/monitor-temp.sh
```

### 7.3 Updating Scout

```bash
# Stop Scout
sudo systemctl stop scout  # or Ctrl+C if running in foreground

# Pull latest changes
cd ~/projects/scout-code
git pull origin main

# Update dependencies if needed
source venv/bin/activate
pip install -r requirements.txt

# Restart Scout
sudo systemctl start scout  # or restart manually
```

---

## Phase 8: Network Access

### 8.1 Local Network Access

Scout is accessible from any device on your local network:

- **Web Interface:** `http://192.168.1.21:8000`
- **API Health:** `http://192.168.1.21:8000/api/health`

### 8.2 Firewall Configuration (If Needed)

```bash
# Check if UFW is active
sudo ufw status

# If active, allow Scout port
sudo ufw allow 8000/tcp comment 'Scout API'

# Verify rule added
sudo ufw status numbered
```

### 8.3 Accessing from Development Machine

**From Windows (PowerShell):**
```powershell
# Test connectivity
curl http://192.168.1.21:8000/api/health

# Or use browser
Start-Process "http://192.168.1.21:8000"
```

---

## Performance Expectations

### Inference Speed

| Model | Tokens/Second | 500 Token Response |
|-------|---------------|-------------------|
| Qwen 2.5 3B | 2-4 tok/s | 2-4 minutes |
| Gemma 2 2B | 4-6 tok/s | 1.5-2 minutes |

### Pipeline Step Timing (Estimated)

| Step | Operation | Expected Time |
|------|-----------|---------------|
| 1 | Job text parsing (Rinser) | 2-4 minutes |
| 2 | Semantic matching (Analyzer) | 4-8 minutes |
| 3 | CV generation (Creator) | 5-10 minutes |
| 4 | Cover letter (Creator) | 3-6 minutes |
| 5 | PDF formatting (Formatter) | 10-30 seconds |
| **Total** | **Full Pipeline** | **15-30 minutes** |

### Resource Usage

| Resource | Idle | During Inference |
|----------|------|------------------|
| CPU | 5-10% | 80-100% (all cores) |
| RAM | 2-3 GB | 6-8 GB |
| Temperature | 45-50°C | 65-75°C |

### Thermal Management

- **Safe Operating Range:** <80°C
- **Throttling Threshold:** 85°C
- **Recommended:** Active cooling with fan

Monitor temperature during extended pipeline runs. If temperature exceeds 75°C consistently, consider:
1. Improving airflow around the Pi
2. Reducing ambient temperature
3. Adding delays between pipeline runs

---

## Quick Reference

### Essential Commands

```bash
# Start Scout (tmux)
tmux attach -t scout || tmux new-session -s scout
source ~/projects/scout-code/venv/bin/activate
cd ~/projects/scout-code
uvicorn src.web.main:app --host 0.0.0.0 --port 8000

# Check Scout status
curl http://localhost:8000/api/health

# Check Ollama status
curl http://localhost:11434/api/tags

# Monitor resources
htop

# Monitor temperature
cat /sys/class/thermal/thermal_zone0/temp | awk '{print $1/1000"°C"}'

# View logs
sudo journalctl -u scout -f
```

### File Locations

| What | Location |
|------|----------|
| Scout Code | `/home/cally/projects/scout-code` |
| Virtual Environment | `/home/cally/projects/scout-code/venv` |
| Data Directory | `/home/cally/projects/scout-code/data` |
| Vector Database | `/home/cally/projects/scout-code/data/chroma_data` |
| Generated PDFs | `/home/cally/projects/scout-code/data/outputs` |
| Environment Config | `/home/cally/projects/scout-code/.env` |
| Ollama Models | `/usr/share/ollama/.ollama/models` |

---

## Success Criteria

### Minimum Viable Demonstration

- [ ] Scout application starts without errors
- [ ] Health endpoint returns healthy status
- [ ] Web interface loads in browser
- [ ] Profile can be created/imported
- [ ] Job posting can be submitted
- [ ] Pipeline completes (any duration)
- [ ] PDF output is generated and downloadable

### Thesis-Ready Demonstration

- [ ] Full pipeline completes in <30 minutes
- [ ] Generated CV/cover letter are professionally formatted
- [ ] System remains stable during pipeline execution
- [ ] No thermal throttling during operation
- [ ] Performance metrics documented

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-14 | Initial deployment guide for Pi 5 with Ubuntu 24.04 |

---

*This guide is part of the Scout PoC thesis documentation.*
*For questions or issues, refer to the project's LL-LI.md for known patterns and solutions.*
