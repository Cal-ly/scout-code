# Scout PoC - Deployment Execution Checklist

**Target:** Raspberry Pi 5 (cally@192.168.1.21)  
**Date:** December 14, 2025  
**Operator:** Claude Code

---

## Pre-Deployment Validation

**Run these checks before starting:**

```bash
# SSH connectivity
ssh cally@192.168.1.21 "echo 'SSH OK'"
# Expected: "SSH OK"

# Disk space (need ~10GB)
ssh cally@192.168.1.21 "df -h ~ | grep -E 'Filesystem|/$'"
# Expected: >10GB available

# Python version
ssh cally@192.168.1.21 "python3 --version"
# Expected: Python 3.12.x

# Memory
ssh cally@192.168.1.21 "free -h | grep Mem"
# Expected: ~16GB total
```

**Status:** [ ] PASS [ ] FAIL

---

## Phase 1: System Verification (5 min)

### 1.1 Update System

```bash
ssh cally@192.168.1.21 "sudo apt update && sudo apt upgrade -y"
```

**Success:** No errors, packages updated  
**Status:** [ ] PASS [ ] FAIL

### 1.2 Install Build Dependencies

```bash
ssh cally@192.168.1.21 "sudo apt install -y build-essential python3-dev python3-pip python3-venv git curl htop tmux"
```

**Success:** All packages installed  
**Status:** [ ] PASS [ ] FAIL

---

## Phase 2: Ollama Installation (15-20 min)

### 2.1 Install Ollama

```bash
ssh cally@192.168.1.21 "curl -fsSL https://ollama.com/install.sh | sh"
```

**Success:** "Ollama installed successfully" message  
**Status:** [ ] PASS [ ] FAIL

### 2.2 Verify Ollama Service

```bash
ssh cally@192.168.1.21 "sudo systemctl status ollama"
```

**Success:** "active (running)" status  
**Status:** [ ] PASS [ ] FAIL

### 2.3 Configure Ollama for Pi 5

```bash
ssh cally@192.168.1.21 'sudo mkdir -p /etc/systemd/system/ollama.service.d/ && sudo tee /etc/systemd/system/ollama.service.d/override.conf > /dev/null <<EOF
[Service]
Environment="OLLAMA_NUM_PARALLEL=1"
Environment="OLLAMA_MAX_LOADED_MODELS=1"
Environment="OLLAMA_KEEP_ALIVE=10m"
EOF'

ssh cally@192.168.1.21 "sudo systemctl daemon-reload && sudo systemctl restart ollama"
```

**Success:** No errors, service restarts  
**Status:** [ ] PASS [ ] FAIL

### 2.4 Pull Models (10-20 min)

```bash
# Primary model (2GB download)
ssh cally@192.168.1.21 "ollama pull qwen2.5:3b"
# Expected: Download progress, then "success"

# Fallback model (1.6GB download)
ssh cally@192.168.1.21 "ollama pull gemma2:2b"
# Expected: Download progress, then "success"
```

**Success:** Both models downloaded  
**Status:** [ ] PASS [ ] FAIL

### 2.5 Verify Models

```bash
ssh cally@192.168.1.21 "ollama list"
```

**Success:** Both qwen2.5:3b and gemma2:2b listed  
**Status:** [ ] PASS [ ] FAIL

### 2.6 Test Inference

```bash
ssh cally@192.168.1.21 "ollama run qwen2.5:3b 'Say hello in exactly 3 words'"
```

**Success:** Model responds (may take 30-60 seconds)  
**Status:** [ ] PASS [ ] FAIL

---

## Phase 3: Scout Application Deployment (10-15 min)

### 3.1 Clone Repository

```bash
ssh cally@192.168.1.21 "mkdir -p ~/projects && cd ~/projects && git clone https://github.com/Cal-ly/scout-code.git"
```

**Success:** Repository cloned, no errors  
**Status:** [ ] PASS [ ] FAIL

### 3.2 Verify Clone

```bash
ssh cally@192.168.1.21 "ls ~/projects/scout-code/src"
```

**Success:** src/ directory exists with modules/  
**Status:** [ ] PASS [ ] FAIL

### 3.3 Create Virtual Environment

```bash
ssh cally@192.168.1.21 "cd ~/projects/scout-code && python3 -m venv venv"
```

**Success:** venv/ directory created  
**Status:** [ ] PASS [ ] FAIL

### 3.4 Activate venv and Upgrade pip

```bash
ssh cally@192.168.1.21 "cd ~/projects/scout-code && source venv/bin/activate && pip install --upgrade pip"
```

**Success:** pip upgraded to latest version  
**Status:** [ ] PASS [ ] FAIL

### 3.5 Install Dependencies (5-10 min)

```bash
ssh cally@192.168.1.21 "cd ~/projects/scout-code && source venv/bin/activate && pip install -r requirements.txt"
```

**Success:** All packages installed, no errors  
**Note:** sentence-transformers may take 5-10 minutes  
**Status:** [ ] PASS [ ] FAIL

### 3.6 Verify Critical Packages

```bash
ssh cally@192.168.1.21 "cd ~/projects/scout-code && source venv/bin/activate && pip list | grep -E '(ollama|chromadb|fastapi|uvicorn|sentence-transformers)'"
```

**Success:** All 5 packages listed  
**Status:** [ ] PASS [ ] FAIL

### 3.7 Create Data Directories

```bash
ssh cally@192.168.1.21 "cd ~/projects/scout-code && mkdir -p data/{uploads,outputs,chroma_data,cache} && chmod 755 data data/*"
```

**Success:** All directories created  
**Status:** [ ] PASS [ ] FAIL

### 3.8 Copy Production .env

```bash
scp .env.production cally@192.168.1.21:~/projects/scout-code/.env
```

**Success:** File transferred  
**Status:** [ ] PASS [ ] FAIL

### 3.9 Verify .env

```bash
ssh cally@192.168.1.21 "cat ~/projects/scout-code/.env | grep -E '(APP_ENV|DEBUG|LLM_PROVIDER)'"
```

**Success:** APP_ENV=production, DEBUG=false, LLM_PROVIDER=ollama  
**Status:** [ ] PASS [ ] FAIL

### 3.10 Test Python Imports

```bash
ssh cally@192.168.1.21 "cd ~/projects/scout-code && source venv/bin/activate && python -c 'from src.services.llm_service import LLMService; from src.services.vector_store import VectorStoreService; from src.services.cache_service import CacheService; print(\"All imports successful!\")'"
```

**Success:** "All imports successful!" message  
**Status:** [ ] PASS [ ] FAIL

---

## Phase 4: Application Startup (2-3 min)

### 4.1 Start Scout (tmux session)

```bash
ssh cally@192.168.1.21 "cd ~/projects/scout-code && tmux new-session -d -s scout 'source venv/bin/activate && uvicorn src.web.main:app --host 0.0.0.0 --port 8000'"
```

**Success:** tmux session created  
**Status:** [ ] PASS [ ] FAIL

### 4.2 Verify tmux Session

```bash
ssh cally@192.168.1.21 "tmux list-sessions"
```

**Success:** "scout" session listed  
**Status:** [ ] PASS [ ] FAIL

### 4.3 Check Application Logs (wait 5 seconds first)

```bash
ssh cally@192.168.1.21 "tmux capture-pane -t scout -p"
```

**Success:** "Application startup complete" or similar  
**Status:** [ ] PASS [ ] FAIL

---

## Phase 5: Validation Testing (5 min)

### 5.1 Health Check Endpoint

```bash
curl http://192.168.1.21:8000/api/health
```

**Success:** JSON response with "status": "healthy"  
**Status:** [ ] PASS [ ] FAIL

### 5.2 Verify LLM Service

```bash
curl http://192.168.1.21:8000/api/health | python -m json.tool | grep -A 3 '"llm"'
```

**Success:** LLM service shows "healthy", "ollama", "qwen2.5:3b"  
**Status:** [ ] PASS [ ] FAIL

### 5.3 Verify Vector Store

```bash
curl http://192.168.1.21:8000/api/health | python -m json.tool | grep -A 2 '"vector_store"'
```

**Success:** Vector store shows "healthy"  
**Status:** [ ] PASS [ ] FAIL

### 5.4 Verify Cache Service

```bash
curl http://192.168.1.21:8000/api/health | python -m json.tool | grep -A 2 '"cache"'
```

**Success:** Cache shows "healthy"  
**Status:** [ ] PASS [ ] FAIL

### 5.5 Web Interface Access

Open in browser: `http://192.168.1.21:8000`

**Success:** Scout web interface loads  
**Status:** [ ] PASS [ ] FAIL

### 5.6 Run Ollama Check Script

```bash
ssh cally@192.168.1.21 "cd ~/projects/scout-code && source venv/bin/activate && python scripts/check_ollama.py"
```

**Success:** All checks pass, both models available  
**Status:** [ ] PASS [ ] FAIL

---

## Phase 6: Resource Monitoring (2 min)

### 6.1 Check Memory Usage

```bash
ssh cally@192.168.1.21 "free -h"
```

**Success:** <50% memory used while idle  
**Status:** [ ] PASS [ ] FAIL

### 6.2 Check Temperature

```bash
ssh cally@192.168.1.21 "cat /sys/class/thermal/thermal_zone0/temp | awk '{print \$1/1000\"°C\"}'"
```

**Success:** <60°C while idle  
**Status:** [ ] PASS [ ] FAIL

### 6.3 Check Disk Usage

```bash
ssh cally@192.168.1.21 "df -h ~"
```

**Success:** >5GB free after installation  
**Status:** [ ] PASS [ ] FAIL

---

## Phase 7: Optional Systemd Service (5 min)

**Only if auto-start on boot is desired**

### 7.1 Create Systemd Service

```bash
ssh cally@192.168.1.21 'sudo tee /etc/systemd/system/scout.service > /dev/null <<EOF
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
EOF'
```

**Success:** Service file created  
**Status:** [ ] PASS [ ] FAIL [ ] SKIPPED

### 7.2 Enable and Start Service

```bash
ssh cally@192.168.1.21 "sudo systemctl daemon-reload && sudo systemctl enable scout && sudo systemctl start scout"
```

**Success:** Service enabled and started  
**Status:** [ ] PASS [ ] FAIL [ ] SKIPPED

### 7.3 Verify Service Status

```bash
ssh cally@192.168.1.21 "sudo systemctl status scout"
```

**Success:** "active (running)" status  
**Status:** [ ] PASS [ ] FAIL [ ] SKIPPED

---

## Phase 8: Final Validation (3 min)

### 8.1 End-to-End Test

**Manual test via web interface:**
1. Open `http://192.168.1.21:8000`
2. Navigate to Profile section
3. Verify profile can be loaded/created
4. Submit a sample job posting (paste text)
5. Verify pipeline starts

**Success:** All UI elements responsive, no errors  
**Status:** [ ] PASS [ ] FAIL

### 8.2 Performance Baseline

```bash
# Run a simple LLM request and time it
ssh cally@192.168.1.21 "time ollama run qwen2.5:3b 'Say hello'"
```

**Success:** Completes in <60 seconds  
**Note:** Record time for performance baseline  
**Status:** [ ] PASS [ ] FAIL

---

## Deployment Summary

### Final Checks

- [ ] All phases PASS or SKIPPED (no FAIL)
- [ ] Health endpoint returns healthy
- [ ] Web interface accessible
- [ ] Ollama models available
- [ ] Temperature <70°C
- [ ] Memory usage reasonable

### Success Criteria Met

**Minimum Viable Deployment:**
- [ ] Scout application starts without errors
- [ ] Health endpoint returns healthy status
- [ ] Web interface loads in browser
- [ ] Ollama inference works (tested)

**Thesis-Ready Deployment:**
- [ ] All services initialized
- [ ] Resource usage documented
- [ ] Performance baseline established
- [ ] System stable

---

## Rollback Plan (If Needed)

```bash
# Stop Scout
ssh cally@192.168.1.21 "tmux kill-session -t scout"

# Stop systemd service (if created)
ssh cally@192.168.1.21 "sudo systemctl stop scout && sudo systemctl disable scout"

# Remove Scout directory
ssh cally@192.168.1.21 "rm -rf ~/projects/scout-code"

# Stop Ollama (if needed)
ssh cally@192.168.1.21 "sudo systemctl stop ollama"
```

---

## Notes for Operator

**Expected Timeline:**
- Phase 1: 5 minutes
- Phase 2: 15-20 minutes (model downloads)
- Phase 3: 10-15 minutes (Python packages)
- Phase 4-5: 5-7 minutes
- Phase 6-8: 5-10 minutes
- **Total: 40-60 minutes**

**Common Issues:**
- Ollama model download slow: Network dependent
- sentence-transformers install slow: ARM64 compilation
- First inference slow: Model loading (30-60s)

**Performance Notes:**
- Idle: 2-3GB RAM, <55°C
- During inference: 6-8GB RAM, 65-75°C
- Pipeline: 15-30 minutes expected

---

*Execute each phase sequentially. Mark PASS/FAIL after each step. Do not proceed if FAIL occurs - consult deployment guide troubleshooting.*
