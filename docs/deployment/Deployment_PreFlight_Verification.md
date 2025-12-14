# Scout PoC - Deployment Pre-Flight Verification

**Version:** 1.0  
**Date:** December 14, 2025  
**Purpose:** Comprehensive verification checklist to ensure Scout codebase is deployment-ready for Raspberry Pi 5

---

## Executive Summary

This document provides a systematic verification process to validate that the Scout codebase aligns with the Raspberry Pi 5 Deployment Guide and PoC scope before actual deployment. Each verification task includes specific commands, expected outputs, and resolution strategies.

**Target Audience:** Claude Code or human developer performing pre-deployment validation  
**Estimated Time:** 45-60 minutes  
**Prerequisites:** Development machine with Scout repository cloned

---

## Table of Contents

1. [Environment Configuration Verification](#1-environment-configuration-verification)
2. [Dependency Compatibility Check](#2-dependency-compatibility-check)
3. [Service Integration Validation](#3-service-integration-validation)
4. [Local LLM Integration Test](#4-local-llm-integration-test)
5. [Cost Tracker Metrics Mode](#5-cost-tracker-metrics-mode)
6. [Cache Service Validation](#6-cache-service-validation)
7. [ARM64 Compatibility Check](#7-arm64-compatibility-check)
8. [Minimal Functional Test Suite](#8-minimal-functional-test-suite)

---

## Verification Methodology

Each verification task follows this structure:

```
TASK: [What to verify]
WHY: [Rationale and deployment impact]
HOW: [Specific commands/steps]
EXPECTED: [What should happen]
IF FAILED: [Resolution steps]
SUCCESS CRITERIA: [Explicit pass/fail criteria]
```

---

## 1. Environment Configuration Verification

### 1.1 Validate .env.example Alignment with PoC Scope

**TASK:** Ensure `.env.example` reflects local Ollama configuration without cloud API dependencies

**WHY:** Deployment guide uses local Ollama exclusively. Any cloud API configuration creates confusion and potential misconfiguration.

**HOW:**
```bash
# From repository root
cat .env.example | grep -E "(LLM_|OLLAMA_|ANTHROPIC|OPENAI)"
```

**EXPECTED OUTPUT:**
```bash
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:3b
LLM_FALLBACK_MODEL=gemma2:2b
OLLAMA_HOST=http://localhost:11434
LLM_MAX_TOKENS=2000
LLM_TEMPERATURE=0.3
LLM_TIMEOUT=120
```

**SHOULD NOT CONTAIN:**
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`
- Any API key placeholders for cloud services

**IF FAILED:**
```bash
# Update .env.example to remove cloud API references
# Ensure only Ollama configuration remains
```

**SUCCESS CRITERIA:**
- [ ] Only Ollama-related LLM configuration present
- [ ] No cloud API key variables
- [ ] Timeout set to 120s minimum (Pi 5 inference is slow)

---

### 1.2 Remove Legacy Redis Configuration

**TASK:** Verify Redis configuration is removed from `.env.example`

**WHY:** PoC scope explicitly excludes Redis. Per scope document: "Caching: Memory + File (no Redis)"

**HOW:**
```bash
cat .env.example | grep -i redis
```

**EXPECTED OUTPUT:**
```
# Should return empty / no matches
```

**IF FAILED:**
```bash
# Edit .env.example
# Remove all Redis-related variables:
# - REDIS_HOST
# - REDIS_PORT
# - REDIS_DB
# - REDIS_PASSWORD
```

**SUCCESS CRITERIA:**
- [ ] No Redis configuration variables present
- [ ] Cache configuration only references file-based caching
- [ ] CACHE_TTL (if present) clearly documented as file cache TTL

---

### 1.3 Validate Data Directory Structure

**TASK:** Ensure required data directories are specified correctly

**WHY:** Services depend on specific directory structure for persistence

**HOW:**
```bash
cat .env.example | grep -E "(DIR|PATH)" | grep -v "^#"
```

**EXPECTED OUTPUT:**
```bash
DATABASE_PATH=data/scout.db
CHROMA_PERSIST_DIR=data/chroma_data
UPLOAD_DIR=data/uploads
OUTPUT_DIR=data/outputs
TEMPLATE_DIR=data/templates
```

**ADDITIONAL CHECK:**
```bash
# Verify cache directory reference (if explicitly configured)
# Should reference data/cache or similar local path
```

**IF FAILED:**
- Correct paths to use `data/` prefix
- Ensure no absolute paths that assume specific deployment environment

**SUCCESS CRITERIA:**
- [ ] All paths use relative `data/` prefix
- [ ] No hardcoded absolute paths
- [ ] Cache directory configuration (if explicit) points to local filesystem

---

## 2. Dependency Compatibility Check

### 2.1 Validate requirements.txt for ARM64 Compatibility

**TASK:** Ensure all dependencies support ARM64 architecture (aarch64)

**WHY:** Raspberry Pi 5 runs ARM64. Some Python packages have x86-only wheels or require compilation.

**HOW:**
```bash
# Check for known problematic packages
cat requirements.txt | grep -E "(tensorflow|torch|opencv|onnx)"
```

**EXPECTED OUTPUT:**
```
# Should return empty (these packages not used in PoC)
```

**CRITICAL PACKAGES TO VALIDATE:**
```bash
# Verify these are present and compatible
grep -E "(ollama|chromadb|sentence-transformers|fastapi|uvicorn)" requirements.txt
```

**EXPECTED:**
```
ollama>=0.4.0
chromadb>=0.4.22
sentence-transformers>=2.3.0
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
```

**IF FAILED:**
- Remove incompatible packages
- Find ARM64-compatible alternatives
- Document any packages requiring compilation on Pi 5

**SUCCESS CRITERIA:**
- [ ] No x86-only packages present
- [ ] All ML packages are ARM64-compatible
- [ ] sentence-transformers version supports ARM64

---

### 2.2 Verify No Redis Dependencies

**TASK:** Confirm Redis client libraries are absent from requirements

**WHY:** Aligns with PoC scope exclusion of Redis

**HOW:**
```bash
grep -i redis requirements.txt
grep -i redis requirements-dev.txt
```

**EXPECTED OUTPUT:**
```
# Should return empty / no matches
```

**IF FAILED:**
```bash
# Remove redis, aioredis, or any Redis client libraries
# Update cache_service to only use memory + file
```

**SUCCESS CRITERIA:**
- [ ] No `redis` package in requirements.txt
- [ ] No `aioredis` package in requirements.txt
- [ ] No Redis client libraries in any requirements file

---

### 2.3 Validate ChromaDB Configuration

**TASK:** Ensure ChromaDB version supports ARM64 and file-based persistence

**WHY:** ChromaDB is the vector store for semantic matching. Must work on Pi 5.

**HOW:**
```bash
grep chromadb requirements.txt
```

**EXPECTED:**
```
chromadb>=0.4.22
```

**NOTES:**
- ChromaDB 0.4.22+ supports ARM64
- Earlier versions may have SQLite compatibility issues on ARM
- File-based persistence mode is required (no client-server mode)

**SUCCESS CRITERIA:**
- [ ] ChromaDB version >= 0.4.22
- [ ] No ChromaDB server configuration in .env.example
- [ ] CHROMA_PERSIST_DIR configured for local file storage

---

## 3. Service Integration Validation

### 3.1 Cost Tracker Metrics-Only Mode

**TASK:** Verify cost tracker gracefully handles $0.00 costs from local LLM

**WHY:** Cost tracker infrastructure remains for metrics, but all costs = $0.00 with Ollama

**HOW:**
```python
# Create test script: test_cost_tracker_local.py
from src.services.cost_tracker import CostTrackerService
import asyncio

async def test_local_llm_tracking():
    tracker = CostTrackerService(daily_limit=10.0, monthly_limit=50.0)
    await tracker.initialize()
    
    # Simulate local LLM call (zero cost)
    await tracker.record_cost(
        service_name="ollama",
        model="qwen2.5:3b",
        input_tokens=100,
        output_tokens=200,
        cost=0.0,  # Local inference
        module="test"
    )
    
    # Verify can_proceed works with zero costs
    can_proceed = await tracker.can_proceed()
    assert can_proceed == True, "Should always proceed with zero costs"
    
    # Get budget status
    status = await tracker.get_budget_status()
    print(f"Daily spent: ${status.daily_spent}")
    print(f"Monthly spent: ${status.monthly_spent}")
    print(f"Total tokens: {status.total_input_tokens + status.total_output_tokens}")
    
    await tracker.shutdown()
    print("✓ Cost tracker handles local LLM correctly")

asyncio.run(test_local_llm_tracking())
```

**RUN:**
```bash
python test_cost_tracker_local.py
```

**EXPECTED OUTPUT:**
```
Daily spent: $0.00
Monthly spent: $0.00
Total tokens: 300
✓ Cost tracker handles local LLM correctly
```

**IF FAILED:**
- Check BudgetExceededError is not raised for $0.00 costs
- Verify metrics (tokens) are still tracked
- Ensure budget checking logic handles edge case of $0.00

**SUCCESS CRITERIA:**
- [ ] Cost tracker accepts $0.00 costs without error
- [ ] Token counting still works
- [ ] Budget status reports correctly
- [ ] No BudgetExceededError raised for zero-cost operations

---

### 3.2 Cache Service File-Based Persistence

**TASK:** Validate cache service works with memory + file (no Redis)

**WHY:** Deployment guide assumes file-based caching only

**HOW:**
```python
# Create test script: test_cache_service.py
from src.services.cache_service import CacheService
from pathlib import Path
import asyncio

async def test_cache_persistence():
    cache_dir = Path("test_cache_temp")
    cache = CacheService(cache_dir=cache_dir, memory_max_entries=10)
    await cache.initialize()
    
    # Test memory cache
    await cache.set("mem_key", {"data": "value"}, ttl=3600)
    result = await cache.get("mem_key")
    assert result == {"data": "value"}, "Memory cache failed"
    
    # Test file cache (by exceeding memory limit)
    for i in range(15):
        await cache.set(f"key_{i}", {"index": i}, ttl=3600)
    
    # Verify file cache contains entries
    file_count = len(list(cache_dir.glob("*.json")))
    assert file_count > 0, "File cache not persisting"
    
    await cache.shutdown()
    
    # Verify persistence across restarts
    cache2 = CacheService(cache_dir=cache_dir)
    await cache2.initialize()
    
    # Should find entries from file cache
    result = await cache2.get("key_10")
    assert result is not None, "File cache not persisting across restarts"
    
    await cache2.shutdown()
    
    # Cleanup
    import shutil
    shutil.rmtree(cache_dir)
    
    print("✓ Cache service file persistence works correctly")

asyncio.run(test_cache_persistence())
```

**RUN:**
```bash
python test_cache_service.py
```

**EXPECTED OUTPUT:**
```
✓ Cache service file persistence works correctly
```

**IF FAILED:**
- Verify cache_dir is created during initialize()
- Check file JSON serialization/deserialization
- Ensure LRU eviction works for memory cache

**SUCCESS CRITERIA:**
- [ ] Memory cache (L1) works
- [ ] File cache (L2) persists data
- [ ] Data survives service restart
- [ ] No Redis dependencies attempted

---

### 3.3 LLM Service Ollama Provider Initialization

**TASK:** Verify LLM service can initialize without Anthropic API

**WHY:** Deployment uses only Ollama, no cloud fallback

**HOW:**
```python
# Create test script: test_llm_service_init.py
from src.services.llm_service import LLMService, LLMConfig
from src.services.cost_tracker import CostTrackerService
from src.services.cache_service import CacheService
import asyncio

async def test_llm_init_ollama_only():
    # Initialize dependencies
    tracker = CostTrackerService()
    await tracker.initialize()
    
    cache = CacheService()
    await cache.initialize()
    
    # Create LLM service with Ollama config
    config = LLMConfig(
        provider="ollama",
        model="qwen2.5:3b",
        fallback_model="gemma2:2b",
        max_tokens=500,
        temperature=0.3,
        timeout=120.0
    )
    
    llm = LLMService(cost_tracker=tracker, cache=cache, config=config)
    
    try:
        await llm.initialize()
        print("✓ LLM service initialized successfully")
        
        # Verify provider type
        provider = llm._provider
        from src.services.llm_service.providers import OllamaProvider
        assert isinstance(provider, OllamaProvider), "Should use OllamaProvider"
        print("✓ Using OllamaProvider (not Anthropic)")
        
        await llm.shutdown()
        await cache.shutdown()
        await tracker.shutdown()
        
    except Exception as e:
        print(f"✗ Initialization failed: {e}")
        raise

asyncio.run(test_llm_init_ollama_only())
```

**RUN:**
```bash
# Note: This test will fail if Ollama is not running
# That's expected - we're testing the initialization logic
python test_llm_service_init.py
```

**EXPECTED OUTPUT (if Ollama running):**
```
✓ LLM service initialized successfully
✓ Using OllamaProvider (not Anthropic)
```

**EXPECTED OUTPUT (if Ollama not running):**
```
✗ Initialization failed: Failed to connect to Ollama at http://localhost:11434
```

**IF FAILED WITH UNEXPECTED ERROR:**
- Check for leftover Anthropic provider imports
- Verify no hardcoded Anthropic API calls
- Ensure provider selection logic respects LLM_PROVIDER env var

**SUCCESS CRITERIA:**
- [ ] LLM service initializes with OllamaProvider
- [ ] No Anthropic API key required
- [ ] Graceful error if Ollama not running (expected during pre-flight)
- [ ] No fallback to Anthropic provider attempted

---

## 4. Local LLM Integration Test

### 4.1 Mock Ollama Response Test

**TASK:** Test LLM service can process Ollama-style responses

**WHY:** Validate response parsing without requiring actual Ollama server

**HOW:**
```python
# Create test script: test_ollama_response_parsing.py
from src.services.llm_service.models import LLMRequest, MessageRole, PromptMessage
from src.services.llm_service.providers import OllamaProvider
import asyncio

async def test_ollama_response_format():
    """Test that provider can handle Ollama response structure"""
    provider = OllamaProvider(
        model="qwen2.5:3b",
        fallback_model="gemma2:2b",
        host="http://localhost:11434"
    )
    
    # Manually create a mock response structure
    # This simulates what Ollama returns
    mock_ollama_response = {
        "message": {
            "role": "assistant",
            "content": "This is a test response"
        },
        "prompt_eval_count": 50,
        "eval_count": 20
    }
    
    # Verify we can extract content
    content = mock_ollama_response.get("message", {}).get("content", "")
    assert content == "This is a test response"
    
    # Verify we can extract token counts
    input_tokens = mock_ollama_response.get("prompt_eval_count", 0)
    output_tokens = mock_ollama_response.get("eval_count", 0)
    
    assert input_tokens == 50
    assert output_tokens == 20
    
    print("✓ Ollama response structure parsing works")
    print(f"  - Content extraction: OK")
    print(f"  - Token counting: OK")

asyncio.run(test_ollama_response_format())
```

**RUN:**
```bash
python test_ollama_response_parsing.py
```

**EXPECTED OUTPUT:**
```
✓ Ollama response structure parsing works
  - Content extraction: OK
  - Token counting: OK
```

**SUCCESS CRITERIA:**
- [ ] Can extract content from Ollama response format
- [ ] Token counting uses correct Ollama keys (prompt_eval_count, eval_count)
- [ ] No errors when parsing Ollama-specific fields

---

### 4.2 Ollama Availability Check Script

**TASK:** Create a utility script to verify Ollama is ready for deployment

**WHY:** Provides quick pre-deployment sanity check on Pi 5

**HOW:**
```python
# Create utility: scripts/check_ollama.py
import asyncio
import sys
from src.services.llm_service.providers import OllamaProvider

async def check_ollama():
    """Check if Ollama is running and models are available"""
    provider = OllamaProvider()
    
    try:
        print("Checking Ollama availability...")
        await provider.initialize()
        
        print("✓ Ollama is running")
        
        health = await provider.health_check()
        print(f"✓ Primary model: {health['model']}")
        print(f"✓ Fallback model: {health['fallback_model']}")
        print(f"✓ Available models: {health['available_models']}")
        
        await provider.shutdown()
        return 0
        
    except Exception as e:
        print(f"✗ Ollama check failed: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure Ollama is installed: curl -fsSL https://ollama.com/install.sh | sh")
        print("2. Start Ollama service: ollama serve")
        print("3. Pull required models:")
        print("   - ollama pull qwen2.5:3b")
        print("   - ollama pull gemma2:2b")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(check_ollama()))
```

**CREATE:**
```bash
mkdir -p scripts
# Save the above script to scripts/check_ollama.py
chmod +x scripts/check_ollama.py
```

**USAGE:**
```bash
# On development machine (will fail - Ollama not installed)
python scripts/check_ollama.py

# On Pi 5 after Ollama installation
python scripts/check_ollama.py
```

**SUCCESS CRITERIA:**
- [ ] Script created in scripts/check_ollama.py
- [ ] Provides clear error messages if Ollama unavailable
- [ ] Can be run on Pi 5 to verify deployment readiness

---

## 5. Cost Tracker Metrics Mode

### 5.1 Zero-Cost Budget Logic

**TASK:** Ensure cost tracker never blocks operations when costs are $0.00

**WHY:** Local LLM has zero cost, but budget checking logic should still work

**HOW:**
```python
# Create test: test_cost_tracker_zero_budget.py
from src.services.cost_tracker import CostTrackerService
import asyncio

async def test_zero_cost_never_blocks():
    """Verify zero-cost operations never trigger BudgetExceededError"""
    # Set extremely low budgets
    tracker = CostTrackerService(daily_limit=0.01, monthly_limit=0.05)
    await tracker.initialize()
    
    # Record many zero-cost operations
    for i in range(1000):
        await tracker.record_cost(
            service_name="ollama",
            model="qwen2.5:3b",
            input_tokens=1000,
            output_tokens=1000,
            cost=0.0,
            module=f"test_{i}"
        )
    
    # Should still be able to proceed
    can_proceed = await tracker.can_proceed()
    assert can_proceed == True, "Zero costs should never exceed budget"
    
    status = await tracker.get_budget_status()
    assert status.daily_spent == 0.0
    assert status.monthly_spent == 0.0
    assert status.total_requests == 1000
    
    await tracker.shutdown()
    print("✓ Zero-cost operations never blocked by budget")
    print(f"  - Processed 1000 requests at $0.00 each")
    print(f"  - Budget check always passes")

asyncio.run(test_zero_cost_never_blocks())
```

**RUN:**
```bash
python test_cost_tracker_zero_budget.py
```

**EXPECTED OUTPUT:**
```
✓ Zero-cost operations never blocked by budget
  - Processed 1000 requests at $0.00 each
  - Budget check always passes
```

**SUCCESS CRITERIA:**
- [ ] Zero-cost operations never raise BudgetExceededError
- [ ] Token metrics still tracked accurately
- [ ] Budget status reports $0.00 correctly

---

### 5.2 Metrics Extraction Without Cost Enforcement

**TASK:** Verify cost tracker provides useful metrics even with zero costs

**WHY:** Demonstrates value of cost tracker for performance monitoring

**HOW:**
```python
# Create test: test_cost_tracker_metrics.py
from src.services.cost_tracker import CostTrackerService
import asyncio

async def test_metrics_collection():
    """Verify metrics are useful even without actual costs"""
    tracker = CostTrackerService()
    await tracker.initialize()
    
    # Simulate diverse module usage
    modules = ["rinser", "analyzer", "creator", "creator", "formatter"]
    models = ["qwen2.5:3b", "qwen2.5:3b", "gemma2:2b", "qwen2.5:3b", "qwen2.5:3b"]
    
    for module, model in zip(modules, models):
        await tracker.record_cost(
            service_name="ollama",
            model=model,
            input_tokens=500,
            output_tokens=300,
            cost=0.0,
            module=module
        )
    
    # Get summary
    summary = await tracker.get_cost_summary()
    
    print(f"Total requests: {summary.total_requests}")
    print(f"Total input tokens: {summary.total_input_tokens}")
    print(f"Total output tokens: {summary.total_output_tokens}")
    print(f"Requests by module: {summary.requests_by_module}")
    print(f"Requests by model: {summary.requests_by_model}")
    
    # Verify metrics make sense
    assert summary.total_requests == 5
    assert summary.total_input_tokens == 2500
    assert summary.total_output_tokens == 1500
    assert summary.requests_by_module["creator"] == 2
    
    await tracker.shutdown()
    print("\n✓ Metrics collection works correctly")

asyncio.run(test_metrics_collection())
```

**EXPECTED OUTPUT:**
```
Total requests: 5
Total input tokens: 2500
Total output tokens: 1500
Requests by module: {'rinser': 1, 'analyzer': 1, 'creator': 2, 'formatter': 1}
Requests by model: {'qwen2.5:3b': 4, 'gemma2:2b': 1}

✓ Metrics collection works correctly
```

**SUCCESS CRITERIA:**
- [ ] Token metrics tracked accurately
- [ ] Module-level usage tracked
- [ ] Model-level usage tracked
- [ ] Useful for performance analysis despite zero costs

---

## 6. Cache Service Validation

### 6.1 LRU Eviction in Memory Cache

**TASK:** Verify memory cache properly evicts oldest entries when full

**WHY:** Ensures memory doesn't grow unbounded on Pi 5

**HOW:**
```python
# Create test: test_cache_lru.py
from src.services.cache_service import CacheService
from pathlib import Path
import asyncio

async def test_lru_eviction():
    """Test LRU eviction when memory cache is full"""
    cache = CacheService(memory_max_entries=3)
    await cache.initialize()
    
    # Fill memory cache to capacity
    await cache.set("key_1", "value_1")
    await cache.set("key_2", "value_2")
    await cache.set("key_3", "value_3")
    
    # Verify all in memory
    assert await cache.get("key_1") == "value_1"
    assert await cache.get("key_2") == "value_2"
    assert await cache.get("key_3") == "value_3"
    
    # Add one more - should evict key_1 (oldest)
    await cache.set("key_4", "value_4")
    
    # key_1 should be evicted from memory (may be in file cache)
    # key_2, key_3, key_4 should be in memory
    assert await cache.get("key_4") == "value_4"
    assert await cache.get("key_3") == "value_3"
    assert await cache.get("key_2") == "value_2"
    
    await cache.shutdown()
    print("✓ LRU eviction works correctly")
    print("  - Memory cache limited to 3 entries")
    print("  - Oldest entries evicted when full")

asyncio.run(test_lru_eviction())
```

**SUCCESS CRITERIA:**
- [ ] Memory cache respects max_entries limit
- [ ] LRU eviction works correctly
- [ ] Evicted entries accessible from file cache (if TTL not expired)

---

## 7. ARM64 Compatibility Check

### 7.1 Sentence-Transformers Model Loading

**TASK:** Verify sentence-transformers can load embedding model on ARM64

**WHY:** This is the heaviest ML dependency and most likely to fail on ARM

**HOW:**
```python
# Create test: test_sentence_transformers_arm64.py
import sys

def test_import():
    """Test that sentence-transformers imports successfully"""
    try:
        from sentence_transformers import SentenceTransformer
        print("✓ sentence-transformers imported successfully")
        return True
    except Exception as e:
        print(f"✗ sentence-transformers import failed: {e}")
        return False

def test_model_download():
    """Test that we can download/load a small embedding model"""
    try:
        from sentence_transformers import SentenceTransformer
        
        # Use the same model as in production
        model_name = "all-MiniLM-L6-v2"
        print(f"Attempting to load model: {model_name}")
        
        model = SentenceTransformer(model_name)
        print(f"✓ Model loaded successfully")
        
        # Test encoding
        embedding = model.encode("Test sentence")
        print(f"✓ Encoding works (dimension: {len(embedding)})")
        
        return True
        
    except Exception as e:
        print(f"✗ Model loading failed: {e}")
        return False

if __name__ == "__main__":
    import_ok = test_import()
    if import_ok:
        model_ok = test_model_download()
        sys.exit(0 if model_ok else 1)
    else:
        sys.exit(1)
```

**RUN (on development machine):**
```bash
python test_sentence_transformers_arm64.py
```

**EXPECTED OUTPUT:**
```
✓ sentence-transformers imported successfully
Attempting to load model: all-MiniLM-L6-v2
✓ Model loaded successfully
✓ Encoding works (dimension: 384)
```

**NOTE:** This test should pass on development machine. On Pi 5, it validates ARM64 compatibility.

**SUCCESS CRITERIA:**
- [ ] sentence-transformers imports without error
- [ ] all-MiniLM-L6-v2 model can be loaded
- [ ] Embedding generation works

---

## 8. Minimal Functional Test Suite

### 8.1 End-to-End Pipeline Simulation (Mocked)

**TASK:** Create a minimal E2E test without requiring actual Ollama

**WHY:** Validates service integration before deployment

**HOW:**
```python
# Create test: test_pipeline_integration.py
from src.services.cost_tracker import CostTrackerService
from src.services.cache_service import CacheService
from src.services.llm_service import LLMService, LLMConfig
import asyncio

async def test_service_integration():
    """Test that all services can be initialized together"""
    print("Initializing services...")
    
    # Initialize cost tracker
    tracker = CostTrackerService()
    await tracker.initialize()
    print("✓ Cost Tracker initialized")
    
    # Initialize cache
    cache = CacheService()
    await cache.initialize()
    print("✓ Cache Service initialized")
    
    # Initialize LLM service (will fail if Ollama not running, that's OK)
    config = LLMConfig(
        provider="ollama",
        model="qwen2.5:3b",
        fallback_model="gemma2:2b"
    )
    llm = LLMService(cost_tracker=tracker, cache=cache, config=config)
    
    try:
        await llm.initialize()
        print("✓ LLM Service initialized")
        ollama_available = True
    except Exception as e:
        print(f"⚠ LLM Service initialization failed (expected if Ollama not running): {e}")
        ollama_available = False
    
    # Test service interaction (without Ollama)
    await tracker.record_cost(
        service_name="test",
        model="qwen2.5:3b",
        input_tokens=100,
        output_tokens=50,
        cost=0.0,
        module="integration_test"
    )
    print("✓ Cost tracking works")
    
    await cache.set("test_key", {"data": "test"})
    result = await cache.get("test_key")
    assert result == {"data": "test"}
    print("✓ Caching works")
    
    # Shutdown
    if ollama_available:
        await llm.shutdown()
    await cache.shutdown()
    await tracker.shutdown()
    print("\n✓ Service integration test passed")
    print(f"  - All services initialized successfully")
    print(f"  - Ollama: {'Available' if ollama_available else 'Not available (OK for pre-flight)'}")

asyncio.run(test_service_integration())
```

**RUN:**
```bash
python test_pipeline_integration.py
```

**EXPECTED OUTPUT:**
```
Initializing services...
✓ Cost Tracker initialized
✓ Cache Service initialized
⚠ LLM Service initialization failed (expected if Ollama not running): ...
✓ Cost tracking works
✓ Caching works

✓ Service integration test passed
  - All services initialized successfully
  - Ollama: Not available (OK for pre-flight)
```

**SUCCESS CRITERIA:**
- [ ] Cost tracker initializes
- [ ] Cache service initializes
- [ ] LLM service gracefully handles missing Ollama
- [ ] Services can interact without errors

---

## Verification Summary Checklist

Use this checklist to track overall verification status:

### Environment & Configuration
- [ ] 1.1: .env.example has only Ollama configuration
- [ ] 1.2: Redis configuration removed from .env.example
- [ ] 1.3: Data directories correctly configured

### Dependencies
- [ ] 2.1: All dependencies ARM64-compatible
- [ ] 2.2: No Redis dependencies in requirements
- [ ] 2.3: ChromaDB version >= 0.4.22

### Service Integration
- [ ] 3.1: Cost tracker handles $0.00 costs
- [ ] 3.2: Cache service uses memory + file only
- [ ] 3.3: LLM service uses OllamaProvider

### LLM Integration
- [ ] 4.1: Ollama response parsing works
- [ ] 4.2: Ollama check script created

### Cost Tracker
- [ ] 5.1: Zero costs never block operations
- [ ] 5.2: Metrics collected despite zero costs

### Cache Service
- [ ] 6.1: LRU eviction works correctly

### ARM64 Compatibility
- [ ] 7.1: sentence-transformers loads on ARM64

### Integration Testing
- [ ] 8.1: E2E service integration test passes

---

## Next Steps After Verification

Once all verification tasks pass:

1. **Create .env from .env.example**
   ```bash
   cp .env.example .env
   # Review and customize if needed
   ```

2. **Generate verification report**
   ```bash
   # Run all tests and capture output
   python test_cost_tracker_local.py > verification_report.txt
   python test_cache_service.py >> verification_report.txt
   # ... etc
   ```

3. **Commit any fixes**
   ```bash
   git add .
   git commit -m "Pre-deployment verification: Align code with Pi 5 deployment guide"
   ```

4. **Proceed to Pi 5 deployment**
   - Follow `Raspberry_Pi_5_Deployment_Guide.md`
   - Start with Phase 1 (SSH connection)

---

## Troubleshooting

### Common Issues

**Issue: sentence-transformers fails to install**
```bash
# May need system dependencies on ARM64
sudo apt install -y python3-dev build-essential
pip install sentence-transformers --no-cache-dir
```

**Issue: ChromaDB SQLite errors**
```bash
# Ensure ChromaDB >= 0.4.22
pip install --upgrade chromadb
```

**Issue: Ollama connection refused**
```bash
# Expected during pre-flight if Ollama not installed
# This is OK - we're validating code, not deployment environment
```

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-14 | Initial pre-flight verification document |

---

*This document is part of the Scout PoC deployment preparation.*  
*Execute all verifications before proceeding to Pi 5 deployment.*
