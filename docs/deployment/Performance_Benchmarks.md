# Scout PoC - Performance Benchmarks

**Version:** 1.0
**Date:** December 14, 2025
**Purpose:** Document test methodology and benchmark results for thesis evaluation

---

## Overview

This document provides a framework for benchmarking Scout's performance on Raspberry Pi 5 edge hardware compared to the development machine. The benchmarks demonstrate the trade-offs between edge deployment (privacy, cost, offline capability) and cloud computing (speed, scalability).

---

## Test Environment

### Development Machine

| Component | Specification |
|-----------|---------------|
| **CPU** | AMD Ryzen 9 9950X (16C/32T @ 5.7GHz boost) |
| **GPU** | NVIDIA RTX 5070 Ti |
| **RAM** | 32GB DDR5 6000 MT/s |
| **Storage** | NVMe SSD |
| **OS** | EndeavourOS (Arch Linux) |
| **Python** | 3.13.7 |
| **Ollama** | Running with GPU acceleration |

### Raspberry Pi 5 Target

| Component | Specification |
|-----------|---------------|
| **CPU** | ARM Cortex-A76 (4C/4T @ 3GHz overclocked) |
| **GPU** | None (CPU-only inference) |
| **RAM** | 16GB LPDDR4X |
| **Swap** | 16GB swap file |
| **Storage** | (Document your storage type) |
| **OS** | Ubuntu Server 24.04 LTS |
| **Python** | 3.12+ |
| **Ollama** | CPU-only inference |

---

## Benchmark Categories

### 1. LLM Inference Speed

Measures raw token generation speed for the Ollama models.

#### Test Methodology

```bash
# Test script for LLM inference benchmarking
# Run this on both development machine and Pi 5

#!/bin/bash
echo "=== LLM Inference Benchmark ==="
echo "Model: qwen2.5:3b"
echo "Test: Generate 100-token response"
echo ""

# Warm-up run (load model into memory)
echo "Warming up..."
ollama run qwen2.5:3b "Say hello" > /dev/null 2>&1

# Timed test
echo "Running benchmark..."
START=$(date +%s.%N)
ollama run qwen2.5:3b "Write exactly 100 words about software engineering best practices." 2>/dev/null
END=$(date +%s.%N)

DURATION=$(echo "$END - $START" | bc)
echo ""
echo "Duration: ${DURATION} seconds"
```

#### Results Template

| Model | Metric | Dev Machine | Pi 5 | Ratio |
|-------|--------|-------------|------|-------|
| Qwen 2.5 3B | Tokens/second | ___ | ___ | ___x |
| Qwen 2.5 3B | 100 tokens time | ___ s | ___ s | ___x |
| Gemma 2 2B | Tokens/second | ___ | ___ | ___x |
| Gemma 2 2B | 100 tokens time | ___ s | ___ s | ___x |

#### Expected Results

| Model | Dev Machine (GPU) | Pi 5 (CPU) | Expected Ratio |
|-------|-------------------|------------|----------------|
| Qwen 2.5 3B | 50-100 tok/s | 2-4 tok/s | 15-50x slower |
| Gemma 2 2B | 80-150 tok/s | 4-6 tok/s | 15-40x slower |

---

### 2. Embedding Generation Speed

Measures sentence-transformers embedding generation for vector search.

#### Test Methodology

```python
# embedding_benchmark.py
import time
from sentence_transformers import SentenceTransformer

def benchmark_embeddings():
    print("=== Embedding Benchmark ===")

    # Load model (first load downloads ~90MB)
    print("Loading model...")
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # Test sentences
    sentences = [
        "Python developer with 5 years of experience in FastAPI and Django",
        "Machine learning engineer specializing in NLP and computer vision",
        "Full-stack developer experienced with React, Node.js, and PostgreSQL",
        "DevOps engineer with expertise in Docker, Kubernetes, and CI/CD",
        "Data scientist with background in statistical modeling and Python",
    ] * 10  # 50 sentences total

    # Warm-up
    print("Warming up...")
    _ = model.encode(sentences[:5])

    # Benchmark single encoding
    print("\nSingle sentence encoding:")
    start = time.time()
    for s in sentences[:10]:
        _ = model.encode([s])
    single_time = time.time() - start
    print(f"  10 sentences: {single_time:.2f}s ({single_time/10*1000:.0f}ms per sentence)")

    # Benchmark batch encoding
    print("\nBatch encoding (50 sentences):")
    start = time.time()
    _ = model.encode(sentences)
    batch_time = time.time() - start
    print(f"  50 sentences: {batch_time:.2f}s ({batch_time/50*1000:.0f}ms per sentence)")

    return {
        "single_per_sentence_ms": single_time / 10 * 1000,
        "batch_per_sentence_ms": batch_time / 50 * 1000,
    }

if __name__ == "__main__":
    benchmark_embeddings()
```

#### Results Template

| Metric | Dev Machine | Pi 5 | Ratio |
|--------|-------------|------|-------|
| Single sentence encoding | ___ ms | ___ ms | ___x |
| Batch encoding (50 sentences) | ___ ms/sent | ___ ms/sent | ___x |
| Model load time | ___ s | ___ s | ___x |

#### Expected Results

| Metric | Dev Machine | Pi 5 | Notes |
|--------|-------------|------|-------|
| Single sentence | 10-20 ms | 80-150 ms | CPU vs GPU difference |
| Batch (50) | 5-10 ms/sent | 50-100 ms/sent | Batching helps on both |
| Model load | 2-5 s | 10-20 s | First load only |

---

### 3. Full Pipeline Timing

Measures end-to-end pipeline execution time.

#### Test Methodology

1. Prepare a standardized test job posting (see Appendix A)
2. Prepare a standardized test user profile
3. Run full pipeline and measure each step
4. Repeat 3 times and average

#### Pipeline Steps to Measure

```python
# Pipeline timing points
TIMING_POINTS = {
    "start": "Pipeline initiated",
    "rinser_start": "Job parsing begins",
    "rinser_end": "Job parsing complete",
    "analyzer_start": "Semantic matching begins",
    "analyzer_end": "Semantic matching complete",
    "creator_cv_start": "CV generation begins",
    "creator_cv_end": "CV generation complete",
    "creator_cl_start": "Cover letter generation begins",
    "creator_cl_end": "Cover letter generation complete",
    "formatter_start": "PDF formatting begins",
    "formatter_end": "PDF formatting complete",
    "end": "Pipeline complete",
}
```

#### Results Template

| Pipeline Step | Dev Machine | Pi 5 | Ratio |
|---------------|-------------|------|-------|
| Rinser (job parsing) | ___ s | ___ s | ___x |
| Analyzer (semantic matching) | ___ s | ___ s | ___x |
| Creator - CV | ___ s | ___ s | ___x |
| Creator - Cover Letter | ___ s | ___ s | ___x |
| Formatter (PDF) | ___ s | ___ s | ___x |
| **Total Pipeline** | ___ s | ___ s | ___x |

#### Expected Results

| Pipeline Step | Dev Machine | Pi 5 | Notes |
|---------------|-------------|------|-------|
| Rinser | 10-30 s | 2-4 min | LLM extraction |
| Analyzer | 15-45 s | 4-8 min | LLM analysis + vector search |
| Creator - CV | 20-60 s | 5-10 min | Multiple LLM calls |
| Creator - Cover Letter | 15-30 s | 3-6 min | LLM generation |
| Formatter | 2-5 s | 10-30 s | PDF rendering (CPU-bound) |
| **Total** | 1-3 min | 15-30 min | Full pipeline |

---

### 4. Resource Utilization

Measures system resource usage during pipeline execution.

#### Test Methodology

Monitor resources during full pipeline run:

```bash
# Monitor script - run in separate terminal
#!/bin/bash
echo "timestamp,cpu_percent,memory_used_gb,memory_percent,temp_celsius" > resources.csv

while true; do
    CPU=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}')
    MEM=$(free -g | grep Mem | awk '{print $3}')
    MEM_PCT=$(free | grep Mem | awk '{print int($3/$2*100)}')
    TEMP=$(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null | awk '{print $1/1000}')
    echo "$(date +%s),$CPU,$MEM,$MEM_PCT,$TEMP" >> resources.csv
    sleep 5
done
```

#### Results Template

| Metric | Dev Machine | Pi 5 |
|--------|-------------|------|
| **CPU Usage** | | |
| Idle | ___% | ___% |
| During LLM inference | ___% | ___% |
| Peak | ___% | ___% |
| **Memory Usage** | | |
| Baseline (app running) | ___ GB | ___ GB |
| During LLM inference | ___ GB | ___ GB |
| Peak | ___ GB | ___ GB |
| **Temperature** | | |
| Idle | ___°C | ___°C |
| During inference | ___°C | ___°C |
| Peak | ___°C | ___°C |

#### Expected Results (Pi 5)

| Metric | Idle | During Inference | Peak |
|--------|------|------------------|------|
| CPU | 5-10% | 80-100% | 100% |
| Memory | 2-3 GB | 6-8 GB | 10 GB |
| Temperature | 45-50°C | 65-75°C | 80°C |

---

### 5. Concurrent Request Handling

Tests behavior under multiple requests (relevant for future scaling).

#### Test Methodology

```bash
# Simple load test with curl
# Note: PoC is single-user, but test for thesis completeness

# Sequential requests (baseline)
for i in {1..5}; do
    time curl -s http://localhost:8000/api/health > /dev/null
done

# Parallel requests (stress test)
for i in {1..5}; do
    curl -s http://localhost:8000/api/health &
done
wait
```

#### Results Template

| Test | Dev Machine | Pi 5 |
|------|-------------|------|
| Health endpoint (single) | ___ ms | ___ ms |
| Health endpoint (5 concurrent) | ___ ms avg | ___ ms avg |
| Pipeline (sequential, 3 runs) | ___ min avg | ___ min avg |

---

## Benchmark Execution Checklist

### Pre-Benchmark Setup

- [ ] Fresh system reboot on both machines
- [ ] No other applications running
- [ ] Ollama models loaded (warm start)
- [ ] Scout application running
- [ ] Monitoring scripts ready
- [ ] Test data prepared (job posting, user profile)

### During Benchmarks

- [ ] Record all timing data
- [ ] Monitor resource usage
- [ ] Note any errors or anomalies
- [ ] Take screenshots of monitoring tools
- [ ] Run each test 3 times minimum

### Post-Benchmark

- [ ] Calculate averages and standard deviations
- [ ] Fill in results templates
- [ ] Document any unexpected results
- [ ] Save raw data files
- [ ] Generate comparison charts (optional)

---

## Analysis Framework

### Performance Trade-off Analysis

| Factor | Cloud API | Pi 5 Edge | Winner |
|--------|-----------|-----------|--------|
| Speed | ~1-2 min pipeline | 15-30 min pipeline | Cloud |
| Cost per use | ~$0.01-0.05 | ~$0.001 (electricity) | Edge |
| Privacy | Data sent to cloud | Data stays local | Edge |
| Offline capability | Requires internet | Works offline | Edge |
| Scalability | Easy horizontal | Limited to device | Cloud |
| Initial cost | $0 | ~$150 hardware | Cloud |

### Thesis Discussion Points

1. **Edge Computing Trade-offs**
   - Speed vs. privacy
   - Cost (capital vs. operational)
   - Offline capability value

2. **Model Size Considerations**
   - Qwen 2.5 3B vs. Claude 3.5 Haiku quality comparison
   - Quality acceptable for PoC demonstration
   - Potential for larger models on better hardware

3. **Practical Applications**
   - Scenarios where 15-30 min pipeline is acceptable
   - Background processing use cases
   - Personal use vs. commercial deployment

4. **Future Optimization Paths**
   - Quantized models (Q4_K_M for speed)
   - Model distillation
   - Hardware upgrades (more RAM, SSD)
   - Hybrid cloud-edge architecture

---

## Appendix A: Standard Test Job Posting

Use this standardized job posting for consistent benchmarking:

```text
Senior Software Engineer - Python/AI

Company: TechCorp Solutions
Location: Copenhagen, Denmark (Hybrid)
Type: Full-time

About the Role:
We're seeking an experienced Software Engineer to join our AI team and help build
next-generation job matching solutions. You'll work on exciting projects involving
natural language processing, machine learning, and cloud architecture.

Requirements:
- 5+ years of professional Python development experience
- Strong experience with FastAPI or Django web frameworks
- Proficiency in Docker and containerization
- Experience with machine learning frameworks (PyTorch, TensorFlow, or similar)
- Familiarity with vector databases (ChromaDB, Pinecone, or similar)
- Experience with LLM integration and prompt engineering
- Excellent communication skills in English

Nice to Have:
- Experience with Raspberry Pi or edge computing
- Knowledge of Danish language
- Contributions to open source projects
- Experience with CI/CD pipelines

We Offer:
- Competitive salary and benefits
- Flexible working hours
- Professional development budget
- Modern office in central Copenhagen
- International team environment

To Apply:
Send your CV and cover letter explaining why you're a good fit for this role.
```

---

## Appendix B: Sample User Profile

Use a representative user profile with:
- 3-5 work experiences
- 10-15 skills
- 2-3 education entries
- Consistent formatting

(Refer to Collector module's sample profile format)

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-14 | Initial benchmark framework |

---

*This document provides the framework for performance benchmarking.*
*Fill in actual measurements after running benchmarks on both platforms.*
*Results will be included in the thesis performance analysis chapter.*
