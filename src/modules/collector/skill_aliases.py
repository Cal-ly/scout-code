"""
Skill alias mapping for improved job-profile matching.

Provides normalization and expansion of skill terminology to handle
common variations in how skills are referenced in job postings vs profiles.

Example:
    >>> from src.modules.collector.skill_aliases import normalize_skill_name, expand_skill_query
    >>> normalize_skill_name("k8s")
    'kubernetes'
    >>> expand_skill_query("kubernetes")
    ['kubernetes', 'k8s', 'kube']
"""

# Canonical skill name -> list of aliases (lowercase)
SKILL_ALIASES: dict[str, list[str]] = {
    # Programming Languages
    "python": ["python3", "python 3", "py", "python3.x", "python 3.x", "python 3.11", "python 3.12", "python 3.13"],
    "javascript": ["js", "es6", "es2015", "ecmascript", "vanilla js"],
    "typescript": ["ts"],
    "golang": ["go"],
    "csharp": ["c#", "c sharp", ".net", "dotnet"],
    "cplusplus": ["c++", "cpp"],
    "rust": ["rustlang"],
    "java": ["jdk", "jre"],
    "ruby": ["rb"],
    "php": ["php8", "php7"],
    "swift": ["swift5"],
    "kotlin": ["kt"],
    # Databases
    "postgresql": ["postgres", "psql", "pg"],
    "mysql": ["mariadb"],
    "mongodb": ["mongo"],
    "redis": ["redis cache"],
    "elasticsearch": ["elastic", "es", "opensearch"],
    "sqlite": ["sqlite3"],
    "cassandra": ["apache cassandra"],
    "dynamodb": ["dynamo", "amazon dynamodb"],
    # Cloud & Infrastructure
    "kubernetes": ["k8s", "kube"],
    "docker": ["containers", "containerization"],
    "aws": ["amazon web services", "amazon aws"],
    "gcp": ["google cloud", "google cloud platform"],
    "azure": ["microsoft azure", "ms azure"],
    "terraform": ["tf", "iac", "infrastructure as code"],
    "ansible": ["ansible automation"],
    "jenkins": ["jenkins ci"],
    "github actions": ["gha", "gh actions"],
    "gitlab ci": ["gitlab cicd"],
    # Frameworks & Libraries
    "fastapi": ["fast api", "fastapi python"],
    "django": ["django python", "django framework"],
    "flask": ["flask python"],
    "react": ["reactjs", "react.js", "react js"],
    "vue": ["vuejs", "vue.js", "vue js"],
    "angular": ["angularjs", "angular.js"],
    "nodejs": ["node", "node.js", "node js"],
    "express": ["expressjs", "express.js"],
    "spring": ["spring boot", "spring framework", "springboot"],
    "nextjs": ["next.js", "next js"],
    "svelte": ["sveltejs", "svelte.js"],
    # Data & ML
    "machine learning": ["ml", "machine-learning"],
    "artificial intelligence": ["ai"],
    "deep learning": ["dl", "neural networks"],
    "pandas": ["pandas python"],
    "numpy": ["numpy python"],
    "pytorch": ["torch"],
    "tensorflow": ["tf ml", "keras"],
    "scikit-learn": ["sklearn", "scikit learn"],
    "natural language processing": ["nlp"],
    "computer vision": ["cv", "image recognition"],
    "large language models": ["llm", "llms", "generative ai", "genai"],
    # Tools & Practices
    "git": ["github", "gitlab", "version control", "gitflow"],
    "ci/cd": ["cicd", "continuous integration", "continuous deployment", "devops"],
    "agile": ["scrum", "kanban", "sprint"],
    "rest api": ["restful", "rest", "restful api"],
    "graphql": ["gql"],
    "linux": ["unix", "ubuntu", "debian", "centos", "rhel"],
    "bash": ["shell", "shell scripting", "sh"],
    "powershell": ["pwsh", "ps1"],
    "vim": ["neovim", "nvim"],
    # Testing
    "pytest": ["py.test"],
    "jest": ["jest testing"],
    "selenium": ["selenium webdriver"],
    "cypress": ["cypress testing"],
    "unit testing": ["unit tests", "tdd"],
    # Soft Skills (common variations)
    "communication": ["written communication", "verbal communication"],
    "leadership": ["team leadership", "tech lead", "team lead"],
    "mentoring": ["mentorship", "coaching"],
    "problem solving": ["problem-solving", "analytical thinking"],
    "project management": ["pm", "project planning"],
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
    """
    Return list of all canonical skill names.

    Returns:
        List of canonical skill names from the alias dictionary.
    """
    return list(SKILL_ALIASES.keys())


def is_known_skill(skill: str) -> bool:
    """
    Check if a skill (or alias) is in our knowledge base.

    Args:
        skill: Skill name or alias to check.

    Returns:
        True if the skill or one of its aliases is known.
    """
    return skill.lower().strip() in _ALIAS_TO_CANONICAL


def get_canonical_name(skill: str) -> str | None:
    """
    Get the canonical name for a skill if it's known.

    Args:
        skill: Skill name or alias.

    Returns:
        Canonical name if known, None otherwise.
    """
    skill_lower = skill.lower().strip()
    if skill_lower in _ALIAS_TO_CANONICAL:
        return _ALIAS_TO_CANONICAL[skill_lower]
    return None
