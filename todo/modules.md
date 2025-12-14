# Modules TODOs

## Overview
Scout has 5 core modules that form the application pipeline. This document tracks module-level improvements.

**Status**: All modules complete and tested (268 tests passing)

---

## Module Status

| Module | Tests | Status | Spec |
|--------|-------|--------|------|
| M1 Collector | 49 | Complete | `docs/modules/Module 1 Collector*.md` |
| M2 Rinser | 71 | Complete | `docs/modules/Module_2_Rinser_*.md` |
| M3 Analyzer | 62 | Complete | `docs/modules/Module_3_Analyzer_*.md` |
| M4 Creator | 48 | Complete | `docs/modules/Module_4_Creator_*.md` |
| M5 Formatter | 38 | Complete | `docs/modules/Module_5_Formatter_*.md` |

---

## Pipeline Flow

```
Job Posting Text
       │
       ▼
┌─────────────┐
│ M2 Rinser   │  Extract job details, clean HTML, normalize text
└─────────────┘
       │
       ▼
┌─────────────┐
│ M3 Analyzer │  Semantic matching, compatibility scoring, gap analysis
└─────────────┘
       │
       ▼
┌─────────────┐
│ M4 Creator  │  Generate tailored CV & cover letter content
└─────────────┘
       │
       ▼
┌─────────────┐
│ M5 Formatter│  Create PDF documents
└─────────────┘
       │
       ▼
   Output PDFs
```

**Note**: M1 Collector handles profile management (loading, indexing), not part of main pipeline flow.

---

## Outstanding Items by Module

### M1 Collector (`src/modules/collector/`)

- [x] Profile YAML loading complete
- [x] Vector indexing integration complete
- [ ] **Profile Versioning**: Track changes to profile over time
  - **Priority**: Low - nice-to-have
  - **Current**: Profile is overwritten on update

### M2 Rinser (`src/modules/rinser/`)

- [x] HTML cleaning complete
- [x] Job detail extraction complete
- [ ] **Better Company Detection**: Some job postings have company name in unusual places
  - **Priority**: Low
  - **Current**: Uses heuristics + LLM fallback

- [ ] **Salary Extraction**: Parse salary ranges from job text
  - **Priority**: Low - informational only

### M3 Analyzer (`src/modules/analyzer/`)

- [x] Semantic matching complete
- [x] Gap analysis complete
- [x] Compatibility scoring complete
- [ ] **Score Calibration**: Scores may vary by job type
  - **Priority**: Low
  - **Observation**: Tech jobs score higher than non-tech

### M4 Creator (`src/modules/creator/`)

- [x] CV generation complete
- [x] Cover letter generation complete
- [ ] **Tone Customization**: User preference for formal/casual tone
  - **Priority**: Low
  - **Current**: Professional tone hard-coded in prompts

- [ ] **Length Control**: Allow user to specify CV length
  - **Priority**: Low
  - **Current**: 2-page target in prompts

### M5 Formatter (`src/modules/formatter/`)

- [x] PDF generation complete (WeasyPrint)
- [x] Template rendering complete
- [ ] **Template Customization**: User-selectable CV templates
  - **Priority**: Low
  - **Current**: Single professional template

- [-] **DOCX Output**: Deferred per scope document

---

## Module Architecture Notes

### Dependency Injection
Modules receive services via dependency injection:
```python
async def process(self, input_data: InputModel) -> OutputModel:
    llm = await get_llm_service()
    cache = await get_cache_service()
    # ... use services ...
```

### Error Handling
Each module has custom exceptions:
```python
class RinserError(Exception): ...
class ExtractionError(RinserError): ...
```

### Input/Output Models
Each module defines typed I/O:
```python
# M2 Rinser
JobPostingInput → RinsedJobPosting

# M3 Analyzer
AnalysisInput → AnalysisResult

# M4 Creator
CreatorInput → CreatedContent

# M5 Formatter
FormatterInput → FormattedOutput
```

---

## Test Coverage

```
tests/
├── test_collector.py      # 49 tests
├── test_rinser.py         # 71 tests
├── test_analyzer.py       # 62 tests
├── test_creator.py        # 48 tests
└── test_formatter.py      # 38 tests
```

Run all module tests:
```bash
pytest tests/test_collector.py tests/test_rinser.py tests/test_analyzer.py tests/test_creator.py tests/test_formatter.py -v
```

---

## Performance Notes (Pi 5)

From `docs/deployment/Performance_Benchmarks.md`:

| Module | Typical Duration | Notes |
|--------|-----------------|-------|
| M2 Rinser | 30-60s | LLM extraction |
| M3 Analyzer | 60-120s | Semantic search + LLM |
| M4 Creator | 120-300s | Multiple LLM calls |
| M5 Formatter | 5-15s | PDF generation |
| **Total Pipeline** | 4-8 minutes | Depends on job complexity |

---

## Deferred Features

- [-] **URL Job Fetching**: M2 would fetch from URL (text paste only)
- [-] **File Upload**: M2 would accept uploaded files (text paste only)
- [-] **Parallel Module Execution**: Pipeline is sequential
- [-] **DOCX Templates**: M5 PDF only

---

*Last updated: December 14, 2025*
