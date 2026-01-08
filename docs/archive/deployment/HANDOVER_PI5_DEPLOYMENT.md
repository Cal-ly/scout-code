# Scout Project - Raspberry Pi 5 Deployment Handover

**Date:** December 13, 2025
**Previous Session:** sharp-babbage (merged to main)
**Project State:** 95/100 quality score, 610 tests passing, Ollama architecture complete

---

## Session Objective

Deploy the Scout PoC to Raspberry Pi 5 target hardware for end-to-end validation. Create comprehensive deployment documentation for thesis use.

---

## Context

### What Was Completed
- Local LLM Transition: Anthropic Claude API → Ollama (Qwen 2.5 3B + Gemma 2 2B)
- All 610 tests passing with 94% coverage
- Provider abstraction pattern for LLM service
- Review improvements: thread safety, pagination, configurable thresholds
- Code quality: Mypy clean (61 files), Ruff clean

### Key Files to Reference
- `CLAUDE.md` - Project context and patterns
- `REVIEW.md` - Comprehensive quality review (95/100)
- `LL-LI.md` - 58+ lessons learned
- `docs/guides/Local_LLM_Transition_Guide.md` - Ollama architecture details
- `docs/guides/Scout_PoC_Scope_Document.md` - PoC constraints

### Repository State
- **Main branch:** `58dcd21` (all review improvements merged)
- **Tests:** 610 passing
- **Linting:** Clean (Mypy, Ruff)

---

## Deployment Tasks

### Phase 1: Pre-Deployment Preparation

#### 1.1 Hardware Requirements Documentation
Document the Raspberry Pi 5 specifications and requirements:
- Raspberry Pi 5 (8GB RAM recommended)
- MicroSD card (64GB+ recommended) or NVMe SSD
- Active cooling (essential for sustained LLM inference)
- Power supply (27W USB-C PD)

#### 1.2 Software Prerequisites
- Raspberry Pi OS (64-bit, Bookworm)
- Python 3.11+ (system or pyenv)
- Ollama for ARM64
- Git

#### 1.3 Model Selection for Pi 5
Current models may be too large for comfortable Pi 5 operation. Evaluate:

| Model | Size | RAM Required | Expected Speed |
|-------|------|--------------|----------------|
| Qwen 2.5 3B | ~2GB | ~4GB | 2-4 tok/s |
| Gemma 2 2B | ~1.5GB | ~3GB | 4-6 tok/s |
| Phi-3 Mini 3.8B | ~2.3GB | ~4GB | 2-3 tok/s |
| TinyLlama 1.1B | ~0.6GB | ~2GB | 8-12 tok/s |

**Recommendation:** Test with current models first. If too slow, consider:
- Quantized versions (Q4_K_M)
- Smaller fallback model (TinyLlama for speed-critical paths)

### Phase 2: Deployment Steps

#### 2.1 Ollama Installation on Pi 5
```bash
# Install Ollama (ARM64)
curl -fsSL https://ollama.com/install.sh | sh

# Verify installation
ollama --version

# Pull models
ollama pull qwen2.5:3b
ollama pull gemma2:2b

# Test inference
ollama run qwen2.5:3b "Hello, are you working?"
```

#### 2.2 Scout Application Deployment
```bash
# Clone repository
git clone https://github.com/Cal-ly/scout-code.git
cd scout-code

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env as needed (defaults should work for local Ollama)

# Verify installation
python -c "from src.services.llm_service import LLMService; print('OK')"
```

#### 2.3 Database Initialization
```bash
# ChromaDB will auto-initialize on first run
# Profile data needs to be loaded via web interface or API
```

#### 2.4 Running the Application
```bash
# Start Ollama (if not running as service)
ollama serve &

# Start Scout
uvicorn src.web.main:app --host 0.0.0.0 --port 8000

# Or use make command
make run
```

### Phase 3: Validation Testing

#### 3.1 Health Check
```bash
curl http://localhost:8000/api/health
# Expected: {"status": "healthy", ...}
```

#### 3.2 End-to-End Pipeline Test
1. Access web UI at `http://<pi-ip>:8000`
2. Load a test user profile (create minimal test profile)
3. Submit a sample job posting
4. Measure pipeline completion time
5. Verify PDF output quality

#### 3.3 Performance Benchmarks
Record for thesis documentation:
- Cold start time (application startup)
- Ollama model load time
- Per-step pipeline timing:
  - Rinser (job parsing): expected 30-60s
  - Analyzer (matching): expected 60-120s
  - Creator (CV/cover letter): expected 120-300s
  - Formatter (PDF): expected 5-10s
- Total pipeline time
- Memory usage during inference
- CPU temperature under load

#### 3.4 Stress Testing
- Run 3 consecutive pipeline executions
- Monitor for memory leaks
- Check thermal throttling

### Phase 4: Documentation Deliverables

Create these documents in `docs/deployment/`:

#### 4.1 `Raspberry_Pi_5_Deployment_Guide.md`
- Hardware requirements
- OS installation and configuration
- Ollama setup for ARM64
- Scout installation steps
- Configuration options
- Troubleshooting guide

#### 4.2 `Performance_Benchmarks.md`
- Test methodology
- Hardware specifications
- Benchmark results (tables and charts)
- Comparison: Development machine vs Pi 5
- Optimization recommendations

#### 4.3 `User_Guide.md`
- Web interface walkthrough
- Profile creation
- Job submission workflow
- Understanding results
- Downloading documents

---

## Known Considerations

### Performance Expectations
- Full pipeline on Pi 5: 15-30 minutes (vs ~2 min on dev machine)
- This is expected and acceptable for PoC demonstration
- Thesis should discuss edge computing trade-offs

### Potential Issues

1. **Memory Pressure**
   - Monitor with `htop` during inference
   - May need swap file if using 4GB Pi 5
   - Consider killing other processes during pipeline

2. **Thermal Throttling**
   - Active cooling essential
   - Monitor with `vcgencmd measure_temp`
   - Consider reducing CPU governor if throttling

3. **Model Loading**
   - First inference after boot is slow (model loading)
   - Consider keeping Ollama warm with periodic pings

4. **ChromaDB on SD Card**
   - May be slow for large collections
   - NVMe SSD recommended for production

### Fallback Options
If primary models too slow:
1. Use quantized models (Q4_K_M versions)
2. Switch to smaller models (TinyLlama)
3. Reduce generation length in prompts
4. Add more aggressive caching

---

## Success Criteria

### Minimum Viable Demonstration
- [ ] Scout runs on Raspberry Pi 5
- [ ] Full pipeline completes (any duration)
- [ ] PDF output is valid and readable
- [ ] Web interface accessible on local network

### Thesis-Ready Demonstration
- [ ] Pipeline completes in <30 minutes
- [ ] Documented performance benchmarks
- [ ] Reproducible deployment guide
- [ ] Professional-quality output documents

---

## Longer-Term: Documentation (Option D)

After successful Pi 5 deployment, focus on thesis documentation:

1. **Architecture Documentation**
   - System diagrams (already partially in docs)
   - Data flow diagrams
   - Component interaction diagrams

2. **Technical Writing**
   - Edge computing rationale
   - LLM selection methodology
   - Performance analysis

3. **Demonstration Materials**
   - Screenshots of web interface
   - Sample output documents
   - Video walkthrough (optional)

---

## Commands Reference

```bash
# Development machine
cd C:\Users\Cal-l\Documents\GitHub\Scout\scout-code
.\venv\Scripts\activate

# Run tests
pytest tests/ -v

# Type checking
mypy src/ --ignore-missing-imports

# Linting
ruff check src/

# Start dev server
uvicorn src.web.main:app --reload
```

```bash
# Raspberry Pi 5
cd ~/scout-code
source venv/bin/activate

# Check Ollama
ollama list
curl http://localhost:11434/api/tags

# Monitor resources
htop
vcgencmd measure_temp

# Start production server
uvicorn src.web.main:app --host 0.0.0.0 --port 8000
```

---

## Session Start Checklist

When starting the new session:

1. [ ] Confirm working on main branch
2. [ ] Create new branch for deployment work (e.g., `pi5-deployment`)
3. [ ] Read `CLAUDE.md` for project context
4. [ ] Check `LL-LI.md` for relevant patterns
5. [ ] Confirm 610 tests still passing
6. [ ] Start with documentation structure, then deployment steps

---

*Handover created: December 13, 2025*
*Previous session: sharp-babbage*
*Next focus: Raspberry Pi 5 deployment and documentation*
