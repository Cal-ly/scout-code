# Scout Project Review Guide

This guide provides instructions for conducting a comprehensive review of the Scout codebase, architecture, implementation, and documentation.

---

## Architecture Overview

**LLM Architecture:** Local Ollama inference (edge deployment)
- **Primary Model:** Qwen 2.5 3B
- **Fallback Model:** Gemma 2 2B
- **Provider Pattern:** Abstract `LLMProvider` with `OllamaProvider` implementation
- **Target Hardware:** Raspberry Pi 5 (edge computing)

---

## Review Objectives

1. **Assess Code Quality** - Evaluate implementation patterns, consistency, and maintainability
2. **Verify Architecture** - Confirm alignment with design specifications and best practices
3. **Identify Gaps** - Find missing functionality, edge cases, or incomplete implementations
4. **Evaluate Documentation** - Check accuracy, completeness, and usefulness
5. **Security Assessment** - Identify potential vulnerabilities or insecure patterns
6. **Performance Review** - Spot potential bottlenecks or inefficiencies (especially local LLM)
7. **Testing Coverage** - Assess test quality, coverage, and edge case handling
8. **Provide Recommendations** - Actionable improvements prioritized by impact
9. **Ollama Integration** - Verify local LLM implementation correctness and robustness

---

## Review Sections

### 1. Architecture Review

**Files to examine:**
- `CLAUDE.md` - Project context and patterns
- `docs/architecture/*.md` - Architecture specifications
- `docs/guides/Scout_PoC_Scope_Document.md` - Scope constraints

**Questions to answer:**
- Does the implementation match the documented architecture?
- Are service dependencies properly managed?
- Is the separation of concerns maintained?
- Are there any circular dependencies?
- Is the module/service boundary clear and consistent?

### 2. Service Implementation Review

**For each service in `src/services/`:**
- `cost_tracker/` - S2 Cost Tracker
- `cache_service/` - S3 Cache Service
- `vector_store/` - S4 Vector Store
- `llm_service/` - S1 LLM Service (Ollama provider)
- `pipeline/` - S6 Pipeline Orchestrator
- `notification/` - S8 Notification Service

**Checklist per service:**
- [ ] Follows three-file structure (models.py, exceptions.py, <service>.py)
- [ ] Proper async initialization pattern
- [ ] Singleton pattern correctly implemented
- [ ] Error handling is comprehensive
- [ ] Logging is appropriate and consistent
- [ ] Type hints are complete and accurate
- [ ] Docstrings are present and useful

**S1 LLM Service - Ollama-Specific Checklist:**
- [ ] Provider abstraction pattern correctly implemented (`LLMProvider` base class)
- [ ] `OllamaProvider` properly inherits and implements abstract methods
- [ ] Ollama connectivity check in `initialize()`
- [ ] Model availability verification (primary and fallback)
- [ ] Automatic fallback to secondary model on failure
- [ ] Proper async client usage (`ollama.AsyncClient`)
- [ ] JSON format support for structured output (`format="json"`)
- [ ] Cost rates set to 0.0 for local inference
- [ ] Token tracking (not cost tracking) in health status
- [ ] Graceful degradation when Ollama server unavailable

### 3. Module Implementation Review

**For each module in `src/modules/`:**
- `collector/` - M1 Collector
- `rinser/` - M2 Rinser
- `analyzer/` - M3 Analyzer
- `creator/` - M4 Creator
- `formatter/` - M5 Formatter

**Checklist per module:**
- [ ] Clear input/output contracts
- [ ] Proper integration with services
- [ ] Error propagation is correct
- [ ] Business logic is testable
- [ ] Edge cases are handled

### 4. Web Layer Review

**Files to examine:**
- `src/web/main.py` - FastAPI application
- `src/web/routes/*.py` - API routes
- `src/web/schemas.py` - Request/Response models
- `src/web/dependencies.py` - Dependency injection
- `src/web/templates/*.html` - Web templates

**Questions to answer:**
- Are API endpoints RESTful and well-designed?
- Is input validation sufficient?
- Are responses consistent and well-structured?
- Is error handling user-friendly?
- Is the web interface functional and usable?

### 5. Test Quality Review

**Files to examine:**
- `tests/test_*.py` - All test files
- `pyproject.toml` - Test configuration

**Checklist:**
- [ ] Unit tests cover happy paths
- [ ] Unit tests cover error cases
- [ ] Edge cases are tested
- [ ] Mocking is used appropriately
- [ ] Tests are isolated and independent
- [ ] Test names are descriptive
- [ ] Fixtures are reusable and well-organized

### 6. Security Review

**Areas to examine:**
- Input validation and sanitization
- Error message information leakage
- API key/credential handling
- File path handling (path traversal)
- SQL/NoSQL injection vectors
- Cross-site scripting (XSS) in web interface

### 7. Performance Review

**Areas to examine:**
- Async/await usage efficiency
- Caching effectiveness
- Database query optimization
- Memory usage patterns
- Potential blocking operations
- N+1 query problems

**Local LLM Performance Considerations:**
- Model loading time (expect ~30-90s on first inference)
- Inference speed (Qwen 2.5 3B: ~2-4 tok/s on RPi5; faster on dev machine)
- Memory footprint (3B model requires ~2-4GB RAM)
- Pipeline timeout implications (full pipeline: 15-30 min on RPi5)
- Cache effectiveness for repeated prompts
- Fallback model performance vs primary

### 8. Documentation Review

**Files to examine:**
- `README.md` (if exists)
- `CLAUDE.md`
- `HANDOVER.md`
- `LL-LI.md`
- `docs/**/*.md`

**Checklist:**
- [ ] Installation instructions are clear
- [ ] Usage examples are provided
- [ ] API documentation is accurate
- [ ] Architecture is documented
- [ ] Lessons learned are useful

### 9. Configuration & Environment Review

**Files to examine:**
- `pyproject.toml`
- `requirements.txt`
- `requirements-dev.txt`
- `.env.example`
- `.gitignore`

**Checklist:**
- [ ] Dependencies are pinned appropriately
- [ ] Dev dependencies are separated
- [ ] Environment variables are documented
- [ ] Sensitive files are gitignored
- [ ] Ollama-related settings present (host, models)
- [ ] No Anthropic API keys or references remaining

### 10. Code Consistency Review

**Patterns to verify:**
- Import ordering (stdlib → third-party → local)
- Naming conventions (snake_case, PascalCase)
- Error handling patterns
- Logging patterns
- Type hint completeness
- Docstring format

### 11. Ollama Integration Review

**Files to examine:**
- `src/services/llm_service/providers/base.py` - Abstract provider interface
- `src/services/llm_service/providers/ollama_provider.py` - Ollama implementation
- `src/services/llm_service/service.py` - Service orchestration
- `src/services/llm_service/models.py` - LLMConfig and LLMHealth models
- `tests/test_llm_service.py` - Ollama-specific tests

**Checklist:**
- [ ] Provider abstraction allows future provider additions
- [ ] `OllamaProvider.generate()` properly handles all request types
- [ ] Model fallback logic works correctly
- [ ] Connection errors handled gracefully with clear messages
- [ ] `format="json"` used for structured output requests
- [ ] Token counting accurate from Ollama response
- [ ] No hardcoded Anthropic references remaining in code
- [ ] Health check reflects Ollama connectivity status
- [ ] Tests mock Ollama client appropriately
- [ ] Documentation updated for Ollama architecture

---

## Review Output Format

Write the review to `REVIEW.md` with the following structure:

```markdown
# Scout Project - Comprehensive Review

**Review Date:** [Date]
**Reviewer:** Claude Code
**Codebase Version:** [Test count or git hash]

## Executive Summary
[High-level overview of findings]

## Strengths
[What the project does well]

## Areas for Improvement
[Organized by priority: Critical, High, Medium, Low]

## Detailed Findings

### Architecture
[Findings and recommendations]

### Services
[Per-service findings]

### Modules
[Per-module findings]

### Web Layer
[Findings and recommendations]

### Testing
[Findings and recommendations]

### Security
[Findings and recommendations]

### Performance
[Findings and recommendations]

### Documentation
[Findings and recommendations]

## Recommendations Summary
[Prioritized action items]

## Conclusion
[Overall assessment and next steps]
```

---

## Review Commands

Use these commands during the review:

```bash
# Run all tests
.\venv\Scripts\python.exe -m pytest tests/ -v

# Check type hints
.\venv\Scripts\python.exe -m mypy src/ --ignore-missing-imports

# Run linter
.\venv\Scripts\python.exe -m ruff check src/

# Check test coverage
.\venv\Scripts\python.exe -m pytest tests/ --cov=src --cov-report=term-missing

# Ollama-specific checks
ollama list                           # Verify models installed
curl http://localhost:11434/api/tags  # Check Ollama server status
```

---

## Priority Definitions

| Priority | Definition |
|----------|------------|
| **Critical** | Security vulnerabilities, data loss risks, blocking bugs |
| **High** | Significant functionality issues, major code smells |
| **Medium** | Code quality improvements, minor bugs, missing tests |
| **Low** | Style improvements, nice-to-haves, future enhancements |

---

## Ollama Transition Verification

When reviewing code after the Anthropic → Ollama transition, verify:

1. **No Anthropic References**
   - No `anthropic` in imports
   - No `ANTHROPIC_API_KEY` in config
   - No `claude-3` model references
   - Documentation updated

2. **Provider Pattern Correct**
   - `LLMProvider` abstract base class defined
   - `OllamaProvider` implements all abstract methods
   - Service delegates to provider (not direct implementation)

3. **Configuration Updated**
   - `LLMConfig.provider` defaults to "ollama"
   - `LLMConfig.ollama_host` present
   - `LLMConfig.model` defaults to "qwen2.5:3b"
   - `LLMConfig.fallback_model` defaults to "gemma2:2b"
   - Cost rates set to 0.0

4. **Health Status Reflects Ollama**
   - `LLMHealth.ollama_connected` (not `api_connected`)
   - `LLMHealth.model_loaded` (not API model)
   - `LLMHealth.total_tokens` (not `total_cost`)

5. **Tests Updated**
   - Mock `ollama.AsyncClient` (not `anthropic.Anthropic`)
   - Test Ollama response format
   - Test model fallback scenarios
   - Test connectivity failures

---

*Use this guide to conduct a thorough, systematic review of the Scout project.*

*Last updated: December 13, 2025 (Ollama architecture)*
