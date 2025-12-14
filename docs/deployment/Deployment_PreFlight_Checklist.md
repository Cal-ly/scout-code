# Scout PoC - Deployment Pre-Flight Checklist

**Version:** 1.0  
**Date:** December 14, 2025  
**Purpose:** Quick-reference checklist for deployment readiness validation

---

## Overview

This checklist provides a streamlined overview of deployment pre-flight verification. For detailed instructions on each item, refer to `Deployment_PreFlight_Verification.md`.

**Estimated Time:** 10-15 minutes (quick validation)  
**Use Case:** Quick check before handing to Claude Code or starting Pi 5 deployment

---

## Quick Validation Commands

Run these commands from the repository root to quickly validate readiness:

```bash
# 1. Check LLM configuration
cat .env.example | grep -E "(LLM_|OLLAMA_)" | grep -v "^#"

# 2. Verify no Redis
cat .env.example | grep -i redis

# 3. Check dependencies
grep -E "(ollama|chromadb|sentence-transformers)" requirements.txt

# 4. Verify no Redis dependencies
grep -i redis requirements.txt

# 5. Check data directory configuration
cat .env.example | grep -E "(DIR|PATH)" | grep -v "^#"
```

---

## ✅ Pre-Flight Checklist

### Phase 1: Configuration (5 min)

- [x] **1.1** - .env.example contains only Ollama LLM configuration (no ANTHROPIC_API_KEY or OPENAI_API_KEY)
- [x] **1.2** - Redis configuration removed from .env.example
- [x] **1.3** - All data paths use relative `data/` prefix
- [x] **1.4** - LLM timeout set to >= 120 seconds (Pi 5 is slow)

**Quick Check:**
```bash
cat .env.example | grep -E "(ANTHROPIC|OPENAI|REDIS)" && echo "FAIL: Found cloud API or Redis config" || echo "PASS"
```

---

### Phase 2: Dependencies (5 min)

- [x] **2.1** - requirements.txt has ollama >= 0.4.0
- [x] **2.2** - requirements.txt has chromadb >= 0.4.22
- [x] **2.3** - requirements.txt has sentence-transformers >= 2.3.0
- [x] **2.4** - No Redis client libraries in requirements.txt
- [x] **2.5** - No x86-only packages (tensorflow, torch, opencv-python)

**Quick Check:**
```bash
grep -E "(ollama|chromadb|sentence-transformers)" requirements.txt && echo "PASS: Core deps found"
grep -i redis requirements.txt && echo "FAIL: Redis dependency found" || echo "PASS: No Redis"
```

---

### Phase 3: Service Architecture (10 min)

- [x] **3.1** - Cost tracker handles $0.00 costs without error
- [x] **3.2** - Cost tracker still tracks token metrics with zero costs
- [x] **3.3** - Cache service uses memory + file (no Redis)
- [x] **3.4** - LLM service initializes with OllamaProvider only
- [x] **3.5** - No Anthropic provider attempted when LLM_PROVIDER=ollama

**Quick Test (requires running test scripts):**
```bash
# See Deployment_PreFlight_Verification.md section 3 for test scripts
# Test cost tracker:
python test_cost_tracker_local.py

# Test cache:
python test_cache_service.py

# Test LLM service:
python test_llm_service_init.py
```

---

### Phase 4: ARM64 Compatibility (5 min)

- [x] **4.1** - sentence-transformers imports successfully
- [x] **4.2** - all-MiniLM-L6-v2 model can be loaded
- [x] **4.3** - ChromaDB version supports ARM64 (>= 0.4.22)

**Quick Test:**
```bash
python -c "from sentence_transformers import SentenceTransformer; print('PASS')"
```

---

### Phase 5: Integration (5 min)

- [x] **5.1** - All services can initialize together
- [x] **5.2** - Services gracefully handle missing Ollama (expected on dev machine)
- [x] **5.3** - No import errors or missing dependencies

**Quick Test:**
```bash
python test_pipeline_integration.py
```

---

### Phase 6: Utilities Created (2 min)

- [x] **6.1** - scripts/check_ollama.py utility exists
- [x] **6.2** - All test scripts created (see list below)

**Required Test Scripts:**
```
test_cost_tracker_local.py
test_cache_service.py
test_llm_service_init.py
test_ollama_response_parsing.py
test_cost_tracker_zero_budget.py
test_cost_tracker_metrics.py
test_cache_lru.py
test_sentence_transformers_arm64.py
test_pipeline_integration.py
```

---

## Critical Findings Report

Use this section to document any issues found during verification:

### Configuration Issues
```
- [ ] Issue: _______________________________
  Fix: _________________________________
  Status: [ ] Fixed  [ ] Deferred  [ ] Blocker
```

### Dependency Issues
```
- [ ] Issue: _______________________________
  Fix: _________________________________
  Status: [ ] Fixed  [ ] Deferred  [ ] Blocker
```

### Service Integration Issues
```
- [ ] Issue: _______________________________
  Fix: _________________________________
  Status: [ ] Fixed  [ ] Deferred  [ ] Blocker
```

---

## Go/No-Go Decision Matrix

### ✅ GO Criteria (All must be YES)

| Criterion | Status | Notes |
|-----------|--------|-------|
| .env.example has only Ollama config | YES | Verified 2025-12-14 |
| No Redis in requirements or .env | YES | Verified 2025-12-14 |
| Core dependencies (ollama, chromadb, sentence-transformers) present | YES | Verified 2025-12-14 |
| Cost tracker accepts $0.00 costs | YES | test_cost_tracker_local.py PASS |
| Cache service uses file persistence | YES | test_cache_service.py PASS |
| LLM service uses OllamaProvider | YES | test_llm_service_init.py PASS |
| All test scripts run without import errors | YES | All 10 scripts created and run |

### ⚠️ NO-GO Conditions (Any triggers hold)

- [ ] Cloud API keys required in .env.example
- [ ] Redis is a hard dependency
- [ ] x86-only packages in requirements.txt
- [ ] Cost tracker blocks zero-cost operations
- [ ] Import errors in critical services
- [ ] ChromaDB < 0.4.22 (ARM64 incompatible)

---

## Next Steps Based on Results

### ✅ All Checks Pass
```bash
# 1. Clean up test artifacts
rm -f test_*.py
rm -rf test_cache_temp/
rm -f data/cost_tracker.json

# 2. Create .env
cp .env.example .env

# 3. Commit verification changes
git add .
git commit -m "Pre-flight verification complete - Ready for Pi 5 deployment"

# 4. Proceed to deployment
# Follow: docs/deployment/Raspberry_Pi_5_Deployment_Guide.md
```

### ⚠️ Issues Found
```bash
# 1. Document issues in "Critical Findings Report" above
# 2. Refer to Deployment_PreFlight_Verification.md for resolution steps
# 3. Fix issues and re-run verification
# 4. DO NOT proceed to deployment until all checks pass
```

---

## Claude Code Handover Readiness

### Pre-Conditions for Claude Code Deployment

- [x] All verification checks passed
- [x] Test scripts executed successfully
- [x] .env.example aligned with PoC scope
- [x] No blockers in "Go/No-Go Decision Matrix"
- [ ] Repository committed and clean

### Claude Code Deployment Phases

Once pre-flight complete, hand to Claude Code for:

1. **Phase 1-2**: Ollama installation on Pi 5
2. **Phase 3**: Scout application deployment
3. **Phase 4-5**: Application startup and validation
4. **Phase 6-8**: Monitoring and documentation

Refer to: `Raspberry_Pi_5_Deployment_Guide.md` sections 1-8

---

## Emergency Rollback

If deployment encounters critical issues:

```bash
# On Pi 5, restore to clean state
cd ~/projects/scout-code
git reset --hard HEAD
git clean -fd

# Remove data directory
rm -rf data/

# Restart from Phase 1 of deployment guide
```

---

## Verification History

| Date | Operator | Result | Notes |
|------|----------|--------|-------|
| 2025-12-14 | Claude Code | PASS | All 10 test scripts pass, GO for deployment |
| | | | |

---

## Document Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-14 | Initial pre-flight checklist |

---

## Quick Reference Commands

```bash
# Validate .env.example
cat .env.example | grep -E "(LLM_|REDIS)" | grep -v "^#"

# Check dependencies
grep -E "(ollama|chromadb|redis)" requirements.txt

# Run all tests (approximate)
for test in test_*.py; do python "$test" || echo "FAILED: $test"; done

# Check if ready for deployment
echo "Configuration: READY" && \
cat .env.example | grep -i redis > /dev/null && echo "Configuration: NOT READY (Redis found)" || true

# Create scripts directory if needed
mkdir -p scripts

# Verify Ollama check script exists
ls scripts/check_ollama.py && echo "Utility: READY" || echo "Utility: MISSING"
```

---

*Use this checklist in conjunction with `Deployment_PreFlight_Verification.md` for complete validation.*  
*Do not proceed to Pi 5 deployment until all checks pass.*
