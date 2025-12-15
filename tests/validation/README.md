# Scout Validation Test Framework

End-to-end validation testing framework for the Scout pipeline with metrics collection and comparison.

## Overview

This framework provides:
- **Structured test cases** - Reusable synthetic job postings with expected outcomes
- **Metrics collection** - Pipeline performance, extraction quality, compatibility scores
- **Regression detection** - Compare results across runs to catch regressions
- **Consistent baselines** - Standard test profile for reproducible results

## Quick Start

```bash
# List available test cases
python -m tests.validation.runner --list

# Run all test cases
python -m tests.validation.runner --all

# Run specific test case
python -m tests.validation.runner --case TC001

# Run with verbose output
python -m tests.validation.runner --all -v

# Dry run (no actual execution)
python -m tests.validation.runner --all --dry-run
```

## Test Cases

| ID | Name | Category | Complexity | Purpose |
|----|------|----------|------------|---------|
| TC001 | Clean Structured Posting | baseline | low | Best-case performance benchmark |
| TC002 | Marketing Heavy Posting | noise_filtering | medium | Tests Rinser noise removal |
| TC003 | Minimal Posting | edge_case | high | Sparse input handling |
| TC004 | Mixed Language Posting | language | medium | Danish/English bilingual |
| TC005 | Enterprise Detailed Posting | stress_test | high | Token limit stress test |
| TC006 | Startup Unconventional | edge_case | medium | Non-standard requirements |

## Directory Structure

```
tests/validation/
├── __init__.py           # Package init
├── runner.py             # Main validation runner
├── compare.py            # Results comparison tool
├── test_cases.yaml       # Test case definitions
├── test_profile.yaml     # Standard test profile
├── results/              # Output directory for results
│   └── .gitkeep
└── README.md             # This file
```

## Test Profile

The standard test profile (`test_profile.yaml`) represents a typical senior Python developer with:
- 7 years experience
- Strong Python/FastAPI/PostgreSQL skills
- AWS and Docker proficiency
- Team leadership experience

This profile is automatically loaded before running validation tests.

## Metrics Collected

Each test run captures:

| Metric | Description |
|--------|-------------|
| `total_duration_ms` | End-to-end pipeline time |
| `step_durations` | Per-step timing (rinser, analyzer, creator, formatter) |
| `compatibility_score` | Analysis module output (0-100%) |
| `extracted_job_title` | Rinser extraction result |
| `extracted_company` | Rinser extraction result |
| `extracted_requirements` | List of identified requirements |
| `cv_path` | Generated CV file path |
| `cover_letter_path` | Generated cover letter path |

## Results Format

Results are saved as JSON with this structure:

```json
{
  "summary": {
    "timestamp": "2024-12-15T10:30:00",
    "total_tests": 6,
    "passed": 5,
    "failed": 1,
    "pass_rate": "83.3%",
    "avg_duration_ms": 45000,
    "avg_compatibility_score": 72.5
  },
  "by_category": {
    "baseline": {"total": 1, "passed": 1},
    "edge_case": {"total": 2, "passed": 1}
  },
  "results": [
    {
      "test_case_id": "TC001",
      "success": true,
      "duration_ms": 32000,
      "extraction": {...},
      "analysis": {...}
    }
  ]
}
```

## Comparing Results

Compare results across runs to detect regressions:

```bash
# Compare two specific files
python -m tests.validation.compare \
    --baseline results/baseline.json \
    --current results/latest.json

# Compare first and last of multiple files
python -m tests.validation.compare results/validation_*.json

# Save comparison to file
python -m tests.validation.compare \
    --baseline results/baseline.json \
    --current results/latest.json \
    --output comparison.json
```

## Regression Detection

The comparison tool flags regressions when:
- A previously passing test now fails
- Compatibility score drops by more than 5 points
- Duration increases by more than 50%

## Establishing Baselines

After achieving stable performance, save a baseline:

```bash
# Run full validation
python -m tests.validation.runner --all

# Copy result as baseline
cp results/validation_YYYYMMDD_HHMMSS.json results/baseline.json

# Commit baseline
git add results/baseline.json
git commit -m "Establish validation baseline"
```

## Adding New Test Cases

Edit `test_cases.yaml` to add new cases:

```yaml
test_cases:
  - id: "TC007"
    name: "New Test Case"
    category: "edge_case"
    complexity: "medium"
    language: "en"
    description: "Description of what this tests"
    
    input:
      job_text: |
        Job posting text here...
      source: "linkedin"
    
    expected:
      job_title: "Expected Title"
      company_name: "Expected Company"
      key_requirements:
        - "Skill 1"
        - "Skill 2"
```

## Performance Expectations

On development machine (Ryzen 9 9950X + Ollama):
- Per-test duration: 30-90 seconds
- Full suite (6 tests): 3-10 minutes

On Raspberry Pi 5 (Ollama):
- Per-test duration: 5-15 minutes
- Full suite (6 tests): 30-90 minutes

## Troubleshooting

### Ollama not running
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve
```

### Profile not loading
```bash
# Ensure test profile exists
cat tests/validation/test_profile.yaml

# Check data directory
ls -la data/
```

### Out of memory (Pi 5)
- Reduce `max_tokens` in LLM config
- Use smaller model (gemma2:2b instead of qwen2.5:3b)
- Run one test at a time: `--case TC001`
