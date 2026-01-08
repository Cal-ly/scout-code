# Scout Project - Claude Code Development Guide

**Version:** 1.0  
**Created:** November 26, 2025  
**Purpose:** Establish systematic, incremental development workflow for Claude Code

---

## Development Philosophy

This project follows an **Incremental Review-Driven Development (IRDD)** approach. Every implementation step follows a strict four-phase cycle:

```
┌─────────────────────────────────────────────────────────────────┐
│                    INCREMENTAL DEVELOPMENT CYCLE                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐ │
│   │  REVIEW  │───▶│ ANALYZE  │───▶│IMPLEMENT │───▶│  VERIFY  │ │
│   │  CONTEXT │    │   STEP   │    │   CODE   │    │  RESULT  │ │
│   └──────────┘    └──────────┘    └──────────┘    └──────────┘ │
│        │                                                │       │
│        └────────────────────────────────────────────────┘       │
│                         Next Step                               │
└─────────────────────────────────────────────────────────────────┘
```

### Core Principles

1. **Small Steps**: Each implementation increment should be completable in 10-30 minutes
2. **Context First**: Always understand existing code before writing new code
3. **Adjacent Awareness**: Consider how new code interacts with neighboring components
4. **Verify Before Proceeding**: Confirm each step works before moving to the next
5. **Document As You Go**: Update comments and docstrings during implementation

---

## Phase 1: REVIEW CONTEXT

Before implementing anything, review all relevant existing code and specifications.

### Review Checklist

```markdown
## Context Review Checklist

### Specifications
- [ ] Read the relevant module/service specification document
- [ ] Check Scout_PoC_Scope_Document.md for scope constraints
- [ ] Identify what features are IN scope vs DEFERRED

### Existing Code
- [ ] Review adjacent modules/services that will interact with this code
- [ ] Check existing data models that will be used
- [ ] Review utility functions and exceptions available
- [ ] Check configuration/settings patterns in use

### Dependencies
- [ ] Verify required packages are in pyproject.toml
- [ ] Check import patterns used elsewhere in codebase
- [ ] Review any shared constants or enums

### Interfaces
- [ ] Identify input data types expected
- [ ] Identify output data types required
- [ ] Note any async/await patterns to follow
- [ ] Check error handling patterns established
```

### Review Commands

```bash
# View project structure
find . -type f -name "*.py" | head -50

# Check existing implementations for patterns
cat app/services/existing_service.py

# Review data models
cat app/models/relevant_model.py

# Check configuration patterns
cat app/config/settings.py

# Review test patterns
cat tests/unit/services/test_existing.py
```

### What to Look For

| Aspect | Questions to Answer |
|--------|---------------------|
| **Naming Conventions** | How are classes, methods, variables named? |
| **Import Style** | Absolute or relative imports? Import order? |
| **Type Hints** | Full type hints? Optional patterns? |
| **Docstrings** | Google style? NumPy style? What's included? |
| **Error Handling** | Custom exceptions? How are errors propagated? |
| **Async Patterns** | Which methods are async? How is await used? |
| **Logging** | Logger naming? Log levels used? Message format? |
| **Testing** | Fixture patterns? Mock patterns? Assertion style? |

---

## Phase 2: ANALYZE STEP

Break down what needs to be implemented in this specific step.

### Step Analysis Template

```markdown
## Step Analysis: [Step Name]

### Objective
[One sentence describing what this step accomplishes]

### Inputs
- Input 1: [type] - [description]
- Input 2: [type] - [description]

### Outputs
- Output 1: [type] - [description]

### Dependencies (must exist before this step)
- [ ] Dependency 1: [file/class/function]
- [ ] Dependency 2: [file/class/function]

### Will Be Used By (future steps depend on this)
- Future step 1: [description]
- Future step 2: [description]

### Implementation Subtasks
1. [ ] Subtask 1 (e.g., "Create data model")
2. [ ] Subtask 2 (e.g., "Implement core method")
3. [ ] Subtask 3 (e.g., "Add error handling")
4. [ ] Subtask 4 (e.g., "Write unit test")

### Edge Cases to Handle
- Edge case 1: [description] → [handling approach]
- Edge case 2: [description] → [handling approach]

### NOT in This Step (explicitly deferred)
- Deferred item 1: [why]
- Deferred item 2: [why]
```

### Sizing Guidelines

A well-sized step should:

| Characteristic | Target |
|----------------|--------|
| Lines of production code | 50-150 lines |
| Number of methods | 1-3 methods |
| Number of files touched | 1-2 files |
| Test cases | 3-8 tests |
| Time to implement | 10-30 minutes |

### Step Decomposition Examples

**Too Large** (break it down):
```
"Implement the entire Analyzer module"
```

**Right Size**:
```
Step 1: "Create AnalysisResult and CompatibilityScore data models"
Step 2: "Implement skill matching with vector similarity"
Step 3: "Implement experience matching with relevance scoring"
Step 4: "Implement gap analysis generation"
Step 5: "Implement strategy recommendations via LLM"
Step 6: "Create main analyze() orchestration method"
Step 7: "Add error handling and logging"
Step 8: "Write integration tests for full analysis flow"
```

**Too Small** (combine with next):
```
"Add import statement for datetime"
```

---

## Phase 3: IMPLEMENT CODE

Write the code for this step following established patterns.

### Implementation Workflow

```
1. Create/open the target file
2. Add necessary imports (follow existing patterns)
3. Implement the code for this step only
4. Add appropriate docstrings and comments
5. Add type hints to all signatures
6. Handle edge cases identified in analysis
7. Run the file to check for syntax errors
8. Run related tests
```

### Code Quality Standards

#### Docstrings (Google Style)

```python
async def search_similar(
    self,
    text: str,
    collection: CollectionName,
    top_k: int = 10,
    threshold: Optional[float] = None
) -> SearchResults:
    """
    Perform similarity search in a vector collection.
    
    Generates an embedding for the query text and finds the most
    similar entries in the specified collection.
    
    Args:
        text: Query text to search for.
        collection: Collection to search in.
        top_k: Maximum number of results to return.
        threshold: Minimum similarity score (0.0-1.0). If None,
            returns all results up to top_k.
    
    Returns:
        SearchResults containing ranked matches with scores.
    
    Raises:
        EmbeddingError: If embedding generation fails.
        SearchError: If the search operation fails.
        CollectionNotFoundError: If collection doesn't exist.
    
    Example:
        >>> results = await vector_store.search_similar(
        ...     text="Python programming",
        ...     collection=CollectionName.USER_PROFILES,
        ...     top_k=5,
        ...     threshold=0.5
        ... )
        >>> print(results.total_found)
        3
    """
```

#### Type Hints

```python
from typing import List, Dict, Optional, Any, Tuple, Union
from datetime import datetime

# Always use type hints for:
# - Function parameters
# - Return types
# - Class attributes
# - Complex variables

def process_items(
    items: List[str],
    options: Optional[Dict[str, Any]] = None
) -> Tuple[List[str], int]:
    ...
```

#### Error Handling

```python
# Use custom exceptions from app/utils/exceptions.py
from app.utils.exceptions import VectorStoreError, EmbeddingError

# Provide context in error messages
try:
    result = await self._execute_search(query)
except ChromaDBError as e:
    error_msg = f"Search failed for collection '{query.collection}': {e}"
    logger.error(error_msg)
    raise SearchError(error_msg) from e

# Always use 'from e' to preserve exception chain
```

#### Logging

```python
import logging

logger = logging.getLogger(__name__)

# Log levels:
# DEBUG: Detailed diagnostic information
# INFO: General operational events
# WARNING: Unexpected but handled situations
# ERROR: Errors that prevent operation completion

logger.debug(f"Processing entry {entry.id}")
logger.info(f"Added {count} entries to {collection}")
logger.warning(f"Cache miss for key {key}, regenerating")
logger.error(f"Failed to connect to ChromaDB: {e}")
```

### Implementation Don'ts

| Don't | Do Instead |
|-------|------------|
| Implement features not in current step | Add TODO comment, defer to future step |
| Copy-paste large code blocks | Extract to shared utilities |
| Ignore existing patterns | Follow established conventions |
| Skip error handling | Handle errors as you go |
| Leave magic numbers | Use named constants |
| Write methods > 50 lines | Break into smaller methods |
| Use print() for debugging | Use logger.debug() |

---

## Phase 4: VERIFY RESULT

Confirm the implementation works correctly before proceeding.

### Verification Checklist

```markdown
## Verification Checklist

### Syntax & Imports
- [ ] File runs without syntax errors: `python -m py_compile app/path/file.py`
- [ ] All imports resolve correctly
- [ ] No circular import issues

### Type Checking
- [ ] mypy passes: `mypy app/path/file.py`
- [ ] All type hints are complete

### Code Style
- [ ] Black formatting applied: `black app/path/file.py`
- [ ] isort imports organized: `isort app/path/file.py`
- [ ] No flake8 warnings: `flake8 app/path/file.py`

### Unit Tests
- [ ] Tests for this step pass: `pytest tests/unit/path/test_file.py -v`
- [ ] No regressions in related tests
- [ ] Edge cases covered

### Integration Check
- [ ] Adjacent code still works with new code
- [ ] Interfaces match expected signatures
- [ ] Data flows correctly between components

### Documentation
- [ ] Docstrings complete and accurate
- [ ] Complex logic has inline comments
- [ ] Any API changes documented
```

### Verification Commands

```bash
# Syntax check
python -m py_compile app/services/vector_store.py

# Type checking
mypy app/services/vector_store.py --ignore-missing-imports

# Format check
black --check app/services/vector_store.py
isort --check-only app/services/vector_store.py

# Lint check
flake8 app/services/vector_store.py

# Run specific tests
pytest tests/unit/services/test_vector_store.py -v

# Run with coverage
pytest tests/unit/services/test_vector_store.py -v --cov=app/services/vector_store

# Quick integration check (if applicable)
python -c "from app.services.vector_store import VectorStoreService; print('Import OK')"
```

### When Verification Fails

```
If syntax error:
  → Fix immediately before proceeding

If type error:
  → Fix type hints or add appropriate casts

If test fails:
  → Debug and fix; don't proceed with failing tests

If integration breaks:
  → Review interface changes; may need to update adjacent code

If style check fails:
  → Run formatters; these are automatic fixes
```

---

## Incremental Step Definitions

### Service Implementation Steps

Each service follows this standard decomposition:

```
Step 1: Data Models
  - Create Pydantic models in app/models/{service}.py
  - Include all fields, validators, helper methods
  - Verify: Import models, create instances

Step 2: Configuration  
  - Add settings to app/config/settings.py
  - Create any service-specific config classes
  - Verify: Access settings, check defaults

Step 3: Exceptions
  - Add custom exceptions to app/utils/exceptions.py
  - Follow existing exception hierarchy
  - Verify: Raise and catch exceptions

Step 4: Core Service Class - Initialization
  - Create service class with __init__ and initialize()
  - Set up dependencies, connections, state
  - Verify: Instantiate and initialize service

Step 5: Core Service Class - Primary Operations
  - Implement main functionality methods
  - One method per sub-step if complex
  - Verify: Call methods with test data

Step 6: Core Service Class - Secondary Operations  
  - Implement helper methods, utilities
  - Add health check method
  - Verify: Full service functionality

Step 7: Dependency Injection
  - Add FastAPI dependency function
  - Add to application lifespan
  - Verify: Service available via Depends()

Step 8: Unit Tests
  - Create test file with fixtures
  - Test each public method
  - Cover edge cases
  - Verify: All tests pass, >80% coverage
```

### Module Implementation Steps

Each core module follows this pattern:

```
Step 1: Data Models
  - Input/output models specific to module
  - Verify: Models instantiate correctly

Step 2: Module Class - Constructor
  - Initialize with dependencies
  - Verify: Module instantiates

Step 3: Module Class - Core Logic (per major method)
  - Step 3a: First core method
  - Step 3b: Second core method
  - Step 3c: etc.
  - Verify: Each method works in isolation

Step 4: Module Class - Orchestration
  - Main entry point that coordinates operations
  - Verify: Full workflow executes

Step 5: Error Handling & Logging
  - Add try/except blocks
  - Add logging throughout
  - Verify: Errors handled gracefully

Step 6: Unit Tests
  - Full test coverage
  - Verify: Tests pass

Step 7: Integration with Adjacent Modules
  - Verify data flows correctly
  - Test end-to-end with dependencies
```

---

## Development Environment

### System Specifications

| Component | Specification |
|-----------|---------------|
| CPU | AMD Ryzen 9 9950X (16 cores, 32 threads) |
| GPU | NVIDIA RTX 5070 Ti (for ML workloads) |
| RAM | 32GB DDR5 6000 MT/s |
| OS | EndeavourOS (Arch-based Linux) |
| IDE | VS Code (visual-studio-code-bin) |
| Python | 3.11+ |
| Package Manager | Poetry |

### Environment Setup

```bash
# Clone repository
git clone <repo-url> scout-code
cd scout-code

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements-dev.txt

# Verify GPU available for sentence-transformers (optional)
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"

# Ensure Ollama is running with required models
curl http://localhost:11434/api/tags
ollama pull qwen2.5:3b  # If not already pulled

# Run initial checks
make test       # Run test suite
```

### VS Code Configuration

Recommended extensions:
- Python (Microsoft)
- Pylance
- Black Formatter
- isort
- Python Test Explorer

`.vscode/settings.json`:
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.mypyEnabled": true,
  "editor.formatOnSave": true,
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"],
  "[python]": {
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  }
}
```

### GPU Acceleration for Embeddings

The sentence-transformers model can use CUDA for faster embedding generation:

```python
# In vector_store.py initialization
from sentence_transformers import SentenceTransformer
import torch

# Auto-detect GPU
device = "cuda" if torch.cuda.is_available() else "cpu"
self._embedding_model = SentenceTransformer(
    settings.embedding_model,
    device=device
)
logger.info(f"Embedding model loaded on {device}")
```

---

## Working with Claude Code

### Effective Prompts for Each Phase

#### Phase 1: Review Context

```
Review the current state of [component]. I need to understand:
1. What files exist and their structure
2. What patterns are established
3. What interfaces are defined

Start by listing relevant files and showing key sections.
```

#### Phase 2: Analyze Step

```
I'm implementing [step description] for [component].

Based on the specification in [spec file] and the existing code,
analyze what exactly needs to be implemented in this step.

Break it down into subtasks and identify:
- Dependencies that must exist
- Edge cases to handle
- What to explicitly defer
```

#### Phase 3: Implement Code

```
Implement [specific subtask] following the patterns established in 
[reference file].

Requirements:
- Match existing code style
- Add full type hints
- Include docstrings
- Handle errors appropriately

Show me the complete implementation for this subtask only.
```

#### Phase 4: Verify Result

```
Verify the implementation of [component/method]:

1. Check for syntax errors
2. Verify type hints with mypy
3. Run the relevant tests
4. Check that it integrates with [adjacent component]

Report any issues found.
```

### Incremental Session Pattern

A typical Claude Code session follows this pattern:

```
Human: Let's implement [Component]. Start with Phase 1 - review context.

Claude: [Reviews files, identifies patterns, summarizes current state]