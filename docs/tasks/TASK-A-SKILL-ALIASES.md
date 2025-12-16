# Task: Skill Intelligence (Aliases/Synonyms)

## Overview

**Task ID:** SCOUT-SKILL-ALIASES  
**Priority:** High  
**Estimated Effort:** 30-45 minutes  
**Dependencies:** None  

Add skill synonym/alias handling to the Collector module so that job requirements match profile skills even when terminology differs (e.g., "Python 3.x" matches "Python", "k8s" matches "Kubernetes").

---

## Context

### Current State
- Location: `/home/cally/projects/scout-code/`
- Collector module: `src/modules/collector/`
- Skills are matched via semantic similarity using ChromaDB embeddings
- Exact terminology differences reduce match scores unnecessarily
- Example: Job requires "PostgreSQL", profile has "Postgres" → suboptimal match

### Problem
Semantic embeddings help but don't fully solve terminology variance:
- "k8s" and "Kubernetes" have different embeddings
- "JS" and "JavaScript" may not score highly
- Version-specific terms like "Python 3.11" vs "Python" reduce scores

### Solution
Add a skill alias system that:
1. Normalizes skill names during indexing
2. Expands search queries to include aliases
3. Maintains backward compatibility with existing profiles

---

## Implementation Requirements

### 1. Create Skill Aliases Module

**File:** `src/modules/collector/skill_aliases.py`

```python
"""
Skill alias mapping for improved job-profile matching.

Provides normalization and expansion of skill terminology to handle
common variations in how skills are referenced in job postings vs profiles.
"""

# Canonical skill name -> list of aliases (lowercase)
SKILL_ALIASES: dict[str, list[str]] = {
    # Programming Languages
    "python": ["python3", "python 3", "py", "python3.x", "python 3.x", "python 3.11", "python 3.12"],
    "javascript": ["js", "es6", "es2015", "ecmascript", "vanilla js"],
    "typescript": ["ts"],
    "golang": ["go"],
    "csharp": ["c#", "c sharp", ".net", "dotnet"],
    "cplusplus": ["c++", "cpp"],
    "rust": ["rustlang"],
    
    # Databases
    "postgresql": ["postgres", "psql", "pg"],
    "mysql": ["mariadb"],
    "mongodb": ["mongo"],
    "redis": ["redis cache"],
    "elasticsearch": ["elastic", "es"],
    
    # Cloud & Infrastructure
    "kubernetes": ["k8s", "kube"],
    "docker": ["containers", "containerization"],
    "aws": ["amazon web services", "amazon aws"],
    "gcp": ["google cloud", "google cloud platform"],
    "azure": ["microsoft azure", "ms azure"],
    "terraform": ["tf", "iac"],
    
    # Frameworks & Libraries
    "fastapi": ["fast api", "fastapi python"],
    "django": ["django python", "django framework"],
    "react": ["reactjs", "react.js", "react js"],
    "vue": ["vuejs", "vue.js", "vue js"],
    "angular": ["angularjs", "angular.js"],
    "nodejs": ["node", "node.js", "node js"],
    "express": ["expressjs", "express.js"],
    
    # Data & ML
    "machine learning": ["ml", "machine-learning"],
    "artificial intelligence": ["ai"],
    "deep learning": ["dl", "neural networks"],
    "pandas": ["pandas python"],
    "numpy": ["numpy python"],
    "pytorch": ["torch"],
    "tensorflow": ["tf", "keras"],
    
    # Tools & Practices
    "git": ["github", "gitlab", "version control"],
    "ci/cd": ["cicd", "continuous integration", "continuous deployment", "devops"],
    "agile": ["scrum", "kanban"],
    "rest api": ["restful", "rest", "restful api"],
    "graphql": ["gql"],
    
    # Soft Skills (common variations)
    "communication": ["written communication", "verbal communication"],
    "leadership": ["team leadership", "tech lead", "team lead"],
    "mentoring": ["mentorship", "coaching"],
}

# Build reverse lookup: alias -> canonical name
_ALIAS_TO_CANONICAL: dict[str, str] = {}
for canonical, aliases in SKILL_ALIASES.items():
    _ALIAS_TO_CANONICAL[canonical.lower()] = canonical
    for alias in aliases:
        _ALIAS_TO_CANONICAL[alias.lower()] = canonical


def normalize_skill_name(skill: str) -> str:
    """
    Normalize a skill name to its canonical form.
    
    Args:
        skill: Raw skill name (e.g., "Python 3.x", "k8s")
        
    Returns:
        Canonical skill name (e.g., "python", "kubernetes")
        or original lowercase if no mapping exists.
    
    Example:
        >>> normalize_skill_name("Python 3.11")
        'python'
        >>> normalize_skill_name("k8s")
        'kubernetes'
        >>> normalize_skill_name("FastAPI")
        'fastapi'
    """
    skill_lower = skill.lower().strip()
    return _ALIAS_TO_CANONICAL.get(skill_lower, skill_lower)


def expand_skill_query(skill: str) -> list[str]:
    """
    Expand a skill name to include all known aliases.
    
    Used when searching to match against any terminology variant.
    
    Args:
        skill: Skill name to expand
        
    Returns:
        List containing the canonical name plus all aliases.
        
    Example:
        >>> expand_skill_query("kubernetes")
        ['kubernetes', 'k8s', 'kube']
        >>> expand_skill_query("Python")
        ['python', 'python3', 'python 3', 'py', ...]
    """
    canonical = normalize_skill_name(skill)
    
    # Start with canonical name
    expanded = [canonical]
    
    # Add all aliases if this is a known skill
    if canonical in SKILL_ALIASES:
        expanded.extend(SKILL_ALIASES[canonical])
    
    return list(set(expanded))  # Dedupe


def get_all_canonical_skills() -> list[str]:
    """Return list of all canonical skill names."""
    return list(SKILL_ALIASES.keys())


def is_known_skill(skill: str) -> bool:
    """Check if a skill (or alias) is in our knowledge base."""
    return skill.lower().strip() in _ALIAS_TO_CANONICAL
```

### 2. Integrate with Collector Module

**File:** `src/modules/collector/collector.py`

Modify the following methods:

#### 2.1 Update imports

```python
from src.modules.collector.skill_aliases import (
    normalize_skill_name,
    expand_skill_query,
)
```

#### 2.2 Enhance `_index_skills()` method

When indexing skills, add normalized name and aliases to metadata:

```python
async def _index_skills(self) -> int:
    """Index user skills in vector store with alias metadata."""
    if not self._profile:
        return 0

    documents = []
    metadatas = []
    ids = []

    for idx, skill in enumerate(self._profile.skills):
        doc_id = f"skill_{idx}"
        
        # Normalize the skill name
        canonical_name = normalize_skill_name(skill.name)
        aliases = expand_skill_query(skill.name)
        
        # Create searchable text with aliases
        searchable_text = skill.to_searchable_text()
        # Append aliases for better embedding coverage
        alias_text = f" Also known as: {', '.join(aliases)}"
        enhanced_text = searchable_text + alias_text

        documents.append(enhanced_text)
        metadatas.append({
            "type": "skill",
            "name": skill.name,
            "canonical_name": canonical_name,
            "aliases": ",".join(aliases),  # Store as comma-separated
            "level": skill.level.value,
            "years": skill.years or 0,
        })
        ids.append(doc_id)

    if documents:
        await self._vector_store.add_documents(
            collection_name=COLLECTION_NAME,
            documents=documents,
            metadatas=metadatas,
            ids=ids,
        )

    return len(documents)
```

#### 2.3 Enhance `search_skills()` method

Expand search queries to include aliases:

```python
async def search_skills(
    self,
    requirement: str,
    top_k: int = 5,
    min_score: float = 0.3,
) -> list[SearchMatch]:
    """
    Search for skills matching a requirement.
    
    Expands the requirement to include skill aliases for better matching.
    """
    # Expand the requirement to include aliases
    expanded_terms = expand_skill_query(requirement)
    
    # Create enhanced query with all variants
    if len(expanded_terms) > 1:
        enhanced_query = f"{requirement} ({', '.join(expanded_terms)})"
    else:
        enhanced_query = requirement
    
    results = await self._vector_store.search(
        collection_name=COLLECTION_NAME,
        query=enhanced_query,
        n_results=top_k,
        where={"type": "skill"},
    )
    
    matches = []
    for doc, metadata, score in zip(
        results.documents, results.metadatas, results.scores
    ):
        if score >= min_score:
            matches.append(SearchMatch(
                id=metadata.get("id", ""),
                content=doc,
                match_type="skill",
                score=score,
                metadata=metadata,
            ))
    
    return matches
```

### 3. Update Module Exports

**File:** `src/modules/collector/__init__.py`

Add exports for the new module:

```python
from src.modules.collector.skill_aliases import (
    normalize_skill_name,
    expand_skill_query,
    get_all_canonical_skills,
    is_known_skill,
    SKILL_ALIASES,
)
```

### 4. Add Tests

**File:** `tests/test_skill_aliases.py`

```python
"""Tests for skill alias functionality."""

import pytest

from src.modules.collector.skill_aliases import (
    normalize_skill_name,
    expand_skill_query,
    is_known_skill,
    SKILL_ALIASES,
)


class TestNormalizeSkillName:
    """Tests for normalize_skill_name function."""

    def test_normalize_exact_match(self):
        """Canonical names return themselves."""
        assert normalize_skill_name("python") == "python"
        assert normalize_skill_name("kubernetes") == "kubernetes"

    def test_normalize_alias(self):
        """Aliases normalize to canonical name."""
        assert normalize_skill_name("k8s") == "kubernetes"
        assert normalize_skill_name("py") == "python"
        assert normalize_skill_name("js") == "javascript"
        assert normalize_skill_name("postgres") == "postgresql"

    def test_normalize_case_insensitive(self):
        """Normalization is case-insensitive."""
        assert normalize_skill_name("Python") == "python"
        assert normalize_skill_name("KUBERNETES") == "kubernetes"
        assert normalize_skill_name("PostgreSQL") == "postgresql"

    def test_normalize_with_version(self):
        """Version-specific names normalize correctly."""
        assert normalize_skill_name("Python 3.11") == "python"
        assert normalize_skill_name("python3") == "python"

    def test_normalize_unknown_skill(self):
        """Unknown skills return lowercase original."""
        assert normalize_skill_name("SomeObscureFramework") == "someobscureframework"
        assert normalize_skill_name("CustomTool") == "customtool"

    def test_normalize_strips_whitespace(self):
        """Whitespace is stripped."""
        assert normalize_skill_name("  python  ") == "python"
        assert normalize_skill_name("\tk8s\n") == "kubernetes"


class TestExpandSkillQuery:
    """Tests for expand_skill_query function."""

    def test_expand_known_skill(self):
        """Known skills expand to include aliases."""
        expanded = expand_skill_query("kubernetes")
        assert "kubernetes" in expanded
        assert "k8s" in expanded
        assert "kube" in expanded

    def test_expand_from_alias(self):
        """Aliases expand to full set."""
        expanded = expand_skill_query("k8s")
        assert "kubernetes" in expanded
        assert "k8s" in expanded

    def test_expand_unknown_skill(self):
        """Unknown skills return single-item list."""
        expanded = expand_skill_query("unknownskill")
        assert expanded == ["unknownskill"]

    def test_expand_case_insensitive(self):
        """Expansion is case-insensitive."""
        expanded = expand_skill_query("PYTHON")
        assert "python" in expanded
        assert "py" in expanded

    def test_expand_no_duplicates(self):
        """Expanded list has no duplicates."""
        expanded = expand_skill_query("python")
        assert len(expanded) == len(set(expanded))


class TestIsKnownSkill:
    """Tests for is_known_skill function."""

    def test_canonical_is_known(self):
        """Canonical names are known."""
        assert is_known_skill("python") is True
        assert is_known_skill("kubernetes") is True

    def test_alias_is_known(self):
        """Aliases are known."""
        assert is_known_skill("k8s") is True
        assert is_known_skill("py") is True

    def test_unknown_not_known(self):
        """Unknown skills are not known."""
        assert is_known_skill("randomthing") is False

    def test_case_insensitive(self):
        """Check is case-insensitive."""
        assert is_known_skill("PYTHON") is True
        assert is_known_skill("K8S") is True


class TestSkillAliasesCoverage:
    """Tests for alias dictionary coverage."""

    def test_common_languages_covered(self):
        """Common programming languages have aliases."""
        languages = ["python", "javascript", "typescript", "golang"]
        for lang in languages:
            assert lang in SKILL_ALIASES, f"{lang} should be in aliases"

    def test_common_databases_covered(self):
        """Common databases have aliases."""
        databases = ["postgresql", "mongodb", "redis"]
        for db in databases:
            assert db in SKILL_ALIASES, f"{db} should be in aliases"

    def test_cloud_providers_covered(self):
        """Cloud providers have aliases."""
        clouds = ["aws", "gcp", "azure", "kubernetes"]
        for cloud in clouds:
            assert cloud in SKILL_ALIASES, f"{cloud} should be in aliases"
```

---

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/modules/collector/skill_aliases.py` | Create | New alias mapping module |
| `src/modules/collector/collector.py` | Modify | Integrate alias expansion |
| `src/modules/collector/__init__.py` | Modify | Export new functions |
| `tests/test_skill_aliases.py` | Create | Unit tests for aliases |

---

## Testing Instructions

```bash
cd /home/cally/projects/scout-code
source venv/bin/activate

# Run new tests
pytest tests/test_skill_aliases.py -v

# Run full collector tests to ensure no regression
pytest tests/test_collector.py -v

# Verify integration
python -c "
from src.modules.collector.skill_aliases import normalize_skill_name, expand_skill_query

# Test normalization
print('Normalization tests:')
print(f'  k8s -> {normalize_skill_name(\"k8s\")}')
print(f'  Python 3.11 -> {normalize_skill_name(\"Python 3.11\")}')
print(f'  postgres -> {normalize_skill_name(\"postgres\")}')

# Test expansion
print('\nExpansion tests:')
print(f'  kubernetes: {expand_skill_query(\"kubernetes\")}')
print(f'  python: {expand_skill_query(\"python\")[:5]}...')
"
```

---

## Success Criteria

1. ✅ `normalize_skill_name("k8s")` returns `"kubernetes"`
2. ✅ `normalize_skill_name("Python 3.11")` returns `"python"`
3. ✅ `expand_skill_query("kubernetes")` includes `["kubernetes", "k8s", "kube"]`
4. ✅ All existing collector tests pass
5. ✅ New tests in `test_skill_aliases.py` pass
6. ✅ No changes to profile YAML schema required

---

## Constraints

- Do NOT modify the `UserProfile` or `Skill` Pydantic models
- Do NOT require profile YAML changes
- Keep alias dictionary maintainable (single source of truth)
- Ensure backward compatibility with existing indexed profiles

---

## Environment

- SSH access: `ssh cally@192.168.1.21`
- Project path: `/home/cally/projects/scout-code`
- Virtual env: `source venv/bin/activate`
- Python: 3.11+
- Test runner: `pytest`
