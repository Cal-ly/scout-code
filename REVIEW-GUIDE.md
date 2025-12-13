# Scout Project Review Guide

This guide provides instructions for conducting a comprehensive review of the Scout codebase, architecture, implementation, and documentation.

---

## Review Objectives

1. **Assess Code Quality** - Evaluate implementation patterns, consistency, and maintainability
2. **Verify Architecture** - Confirm alignment with design specifications and best practices
3. **Identify Gaps** - Find missing functionality, edge cases, or incomplete implementations
4. **Evaluate Documentation** - Check accuracy, completeness, and usefulness
5. **Security Assessment** - Identify potential vulnerabilities or insecure patterns
6. **Performance Review** - Spot potential bottlenecks or inefficiencies
7. **Testing Coverage** - Assess test quality, coverage, and edge case handling
8. **Provide Recommendations** - Actionable improvements prioritized by impact

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
- `llm_service/` - S1 LLM Service
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

### 10. Code Consistency Review

**Patterns to verify:**
- Import ordering (stdlib ’ third-party ’ local)
- Naming conventions (snake_case, PascalCase)
- Error handling patterns
- Logging patterns
- Type hint completeness
- Docstring format

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

*Use this guide to conduct a thorough, systematic review of the Scout project.*
