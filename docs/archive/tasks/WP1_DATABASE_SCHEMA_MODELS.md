# Work Package 1: Database Schema & Models

## Overview

This work package implements the database schema refactor to separate User identity from Profile career data. It includes:
1. New SQLite schema with normalized tables
2. Pydantic models for all entities
3. Profile completeness scoring algorithm
4. Exception classes
5. Module exports

**Reference:** See `docs/tasks/REFACTOR_GUIDE.md` for full architectural context.

**Time Estimate:** 2-3 hours

---

## Pre-Implementation Checklist

Before starting, verify:
```bash
cd /path/to/scout-code
git status  # Should be clean
pytest tests/test_database_service.py -v  # Current tests pass
```

Create a feature branch:
```bash
git checkout -b feature/user-profile-refactor
```

---

## File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `src/services/database/schemas.py` | CREATE | SQL schema definitions |
| `src/services/database/models.py` | REWRITE | All Pydantic models |
| `src/services/database/completeness.py` | CREATE | Completeness scoring |
| `src/services/database/exceptions.py` | UPDATE | Add new exceptions |
| `src/services/database/__init__.py` | UPDATE | Export new models |

---

## Part 1: SQL Schema (`schemas.py`)

**Create file:** `src/services/database/schemas.py`

### Requirements

1. Define `SCHEMA_VERSION = 2` (increment from current v1)

2. Create `SCHEMA_SQL` constant with all tables:

**Tables to create:**

```
users
├── id (INTEGER PRIMARY KEY AUTOINCREMENT)
├── username (TEXT UNIQUE NOT NULL)
├── email (TEXT)
├── display_name (TEXT)
├── created_at (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
└── updated_at (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)

profiles
├── id (INTEGER PRIMARY KEY AUTOINCREMENT)
├── user_id (INTEGER NOT NULL, FK → users.id ON DELETE CASCADE)
├── slug (TEXT UNIQUE NOT NULL)
├── name (TEXT NOT NULL)
├── title (TEXT)
├── email (TEXT)
├── phone (TEXT)
├── location (TEXT)
├── summary (TEXT)
├── is_active (INTEGER DEFAULT 0)
├── is_demo (INTEGER DEFAULT 0)
├── created_at (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
└── updated_at (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)

profile_skills
├── id (INTEGER PRIMARY KEY AUTOINCREMENT)
├── profile_id (INTEGER NOT NULL, FK → profiles.id ON DELETE CASCADE)
├── name (TEXT NOT NULL)
├── level (TEXT, CHECK IN ('beginner','intermediate','advanced','expert'))
├── years (INTEGER)
├── category (TEXT)
└── sort_order (INTEGER DEFAULT 0)

profile_experiences
├── id (INTEGER PRIMARY KEY AUTOINCREMENT)
├── profile_id (INTEGER NOT NULL, FK → profiles.id ON DELETE CASCADE)
├── title (TEXT NOT NULL)
├── company (TEXT NOT NULL)
├── start_date (TEXT)
├── end_date (TEXT)
├── description (TEXT)
├── achievements (TEXT)  -- JSON array
└── sort_order (INTEGER DEFAULT 0)

profile_education
├── id (INTEGER PRIMARY KEY AUTOINCREMENT)
├── profile_id (INTEGER NOT NULL, FK → profiles.id ON DELETE CASCADE)
├── institution (TEXT NOT NULL)
├── degree (TEXT)
├── field (TEXT)
├── start_date (TEXT)
├── end_date (TEXT)
├── gpa (TEXT)
├── achievements (TEXT)  -- JSON array
└── sort_order (INTEGER DEFAULT 0)

profile_certifications
├── id (INTEGER PRIMARY KEY AUTOINCREMENT)
├── profile_id (INTEGER NOT NULL, FK → profiles.id ON DELETE CASCADE)
├── name (TEXT NOT NULL)
├── issuer (TEXT)
├── date_obtained (TEXT)
├── expiry_date (TEXT)
├── credential_url (TEXT)
└── sort_order (INTEGER DEFAULT 0)

profile_languages
├── id (INTEGER PRIMARY KEY AUTOINCREMENT)
├── profile_id (INTEGER NOT NULL, FK → profiles.id ON DELETE CASCADE)
├── language (TEXT NOT NULL)
├── proficiency (TEXT, CHECK IN ('basic','conversational','professional','fluent','native'))
└── sort_order (INTEGER DEFAULT 0)

applications (UPDATE existing)
├── ... (keep existing columns)
├── user_id (INTEGER, FK → users.id)  -- ADD THIS
└── profile_id (INTEGER, FK → profiles.id)  -- KEEP THIS

settings (keep existing structure)
```

3. Create indexes:
   - `idx_profiles_user_id` on profiles(user_id)
   - `idx_profiles_slug` on profiles(slug)
   - `idx_profiles_is_active` on profiles(is_active)
   - `idx_profile_skills_profile_id` on profile_skills(profile_id)
   - `idx_profile_experiences_profile_id` on profile_experiences(profile_id)
   - `idx_profile_education_profile_id` on profile_education(profile_id)
   - `idx_applications_user_id` on applications(user_id)
   - `idx_applications_profile_id` on applications(profile_id)
   - `idx_applications_job_id` on applications(job_id)

4. Add helper function:
```python
def get_drop_tables_sql() -> str:
    """Return SQL to drop all tables (for testing/reset)."""
    # Return DROP TABLE IF EXISTS for all tables in reverse dependency order
```

### Implementation Notes

- Use `TEXT` for dates (SQLite doesn't have native datetime)
- Use `INTEGER` for booleans (0/1)
- All foreign keys should have `ON DELETE CASCADE`
- The `achievements` columns store JSON arrays as TEXT

---

## Part 2: Pydantic Models (`models.py`)

**Rewrite file:** `src/services/database/models.py`

### Requirements

#### Enums

```python
class SkillLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

class LanguageProficiency(str, Enum):
    BASIC = "basic"
    CONVERSATIONAL = "conversational"
    PROFESSIONAL = "professional"
    FLUENT = "fluent"
    NATIVE = "native"

class ApplicationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"  # Keep for backward compat
    PROCESSING = "processing"  # Alias
    COMPLETED = "completed"
    FAILED = "failed"
```

#### User Models

```python
class UserBase(BaseModel):
    username: str
    email: str | None = None
    display_name: str | None = None

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
```

#### Skill Models

```python
class SkillBase(BaseModel):
    name: str
    level: SkillLevel | None = None
    years: int | None = None
    category: str | None = None
    sort_order: int = 0

class SkillCreate(SkillBase):
    pass

class Skill(SkillBase):
    id: int
    profile_id: int
    
    model_config = ConfigDict(from_attributes=True)
```

#### Experience Models

```python
class ExperienceBase(BaseModel):
    title: str
    company: str
    start_date: str | None = None
    end_date: str | None = None  # None = current position
    description: str | None = None
    achievements: list[str] = Field(default_factory=list)
    sort_order: int = 0

class ExperienceCreate(ExperienceBase):
    pass

class Experience(ExperienceBase):
    id: int
    profile_id: int
    
    model_config = ConfigDict(from_attributes=True)
```

#### Education Models

```python
class EducationBase(BaseModel):
    institution: str
    degree: str | None = None
    field: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    gpa: str | None = None
    achievements: list[str] = Field(default_factory=list)
    sort_order: int = 0

class EducationCreate(EducationBase):
    pass

class Education(EducationBase):
    id: int
    profile_id: int
    
    model_config = ConfigDict(from_attributes=True)
```

#### Certification Models

```python
class CertificationBase(BaseModel):
    name: str
    issuer: str | None = None
    date_obtained: str | None = None
    expiry_date: str | None = None
    credential_url: str | None = None
    sort_order: int = 0

class CertificationCreate(CertificationBase):
    pass

class Certification(CertificationBase):
    id: int
    profile_id: int
    
    model_config = ConfigDict(from_attributes=True)
```

#### Language Models

```python
class LanguageBase(BaseModel):
    language: str
    proficiency: LanguageProficiency | None = None
    sort_order: int = 0

class LanguageCreate(LanguageBase):
    pass

class Language(LanguageBase):
    id: int
    profile_id: int
    
    model_config = ConfigDict(from_attributes=True)
```

#### Profile Models

```python
class ProfileBase(BaseModel):
    name: str
    title: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    summary: str | None = None

class ProfileCreate(ProfileBase):
    """Create profile with all related data."""
    slug: str | None = None  # Auto-generated from name if not provided
    skills: list[SkillCreate] = Field(default_factory=list)
    experiences: list[ExperienceCreate] = Field(default_factory=list)
    education: list[EducationCreate] = Field(default_factory=list)
    certifications: list[CertificationCreate] = Field(default_factory=list)
    languages: list[LanguageCreate] = Field(default_factory=list)

class ProfileUpdate(BaseModel):
    """Update profile - all fields optional. 
    If a list field is provided, it REPLACES existing data.
    If a list field is None, existing data is preserved.
    """
    name: str | None = None
    slug: str | None = None
    title: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    summary: str | None = None
    skills: list[SkillCreate] | None = None
    experiences: list[ExperienceCreate] | None = None
    education: list[EducationCreate] | None = None
    certifications: list[CertificationCreate] | None = None
    languages: list[LanguageCreate] | None = None

class Profile(ProfileBase):
    """Full profile with all related data."""
    id: int
    user_id: int
    slug: str
    is_active: bool = False
    is_demo: bool = False
    created_at: datetime
    updated_at: datetime
    
    # Related data
    skills: list[Skill] = Field(default_factory=list)
    experiences: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    languages: list[Language] = Field(default_factory=list)
    
    model_config = ConfigDict(from_attributes=True)

class ProfileSummary(BaseModel):
    """Lightweight profile for list views."""
    id: int
    user_id: int
    slug: str
    name: str
    title: str | None = None
    is_active: bool = False
    is_demo: bool = False
    created_at: datetime
    updated_at: datetime
    
    # Counts
    skill_count: int = 0
    experience_count: int = 0
    education_count: int = 0
    certification_count: int = 0
    language_count: int = 0
    
    # Application stats
    application_count: int = 0
    completed_application_count: int = 0
    avg_compatibility_score: float | None = None
    
    model_config = ConfigDict(from_attributes=True)
```

#### Completeness Models

```python
class CompletenessSection(BaseModel):
    """Completeness score for a profile section."""
    name: str
    score: int  # Points earned
    max_score: int  # Maximum possible points
    items_present: int
    items_recommended: int
    suggestions: list[str] = Field(default_factory=list)

class ProfileCompleteness(BaseModel):
    """Overall profile completeness assessment."""
    overall_score: int  # 0-100 percentage
    level: str  # "excellent", "good", "fair", "needs_work"
    sections: list[CompletenessSection] = Field(default_factory=list)
    top_suggestions: list[str] = Field(default_factory=list)  # Top 3
```

#### Application Models (Updated)

```python
class ApplicationBase(BaseModel):
    job_title: str | None = None
    company_name: str | None = None

class ApplicationCreate(ApplicationBase):
    job_id: str
    user_id: int
    profile_id: int
    job_text: str

class ApplicationUpdate(BaseModel):
    job_title: str | None = None
    company_name: str | None = None
    status: ApplicationStatus | None = None
    compatibility_score: float | None = None
    cv_path: str | None = None
    cover_letter_path: str | None = None
    analysis_data: dict[str, Any] | None = None
    pipeline_data: dict[str, Any] | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

class Application(ApplicationBase):
    id: int
    job_id: str
    user_id: int
    profile_id: int
    job_text: str
    status: ApplicationStatus = ApplicationStatus.PENDING
    compatibility_score: float | None = None
    cv_path: str | None = None
    cover_letter_path: str | None = None
    analysis_data: dict[str, Any] | None = None
    pipeline_data: dict[str, Any] | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    
    # Joined fields
    profile_name: str | None = None
    profile_slug: str | None = None
    
    model_config = ConfigDict(from_attributes=True)
```

#### Settings Model (Keep existing)

```python
class Settings(BaseModel):
    """Application settings."""
    active_profile_id: int | None = None
    schema_version: int = 2
    demo_data_loaded: bool = False
```

### Implementation Notes

- Import `from pydantic import BaseModel, Field, ConfigDict`
- Use `datetime` from standard library
- Use `typing.Any` for dict values
- All models should have docstrings
- List fields use `Field(default_factory=list)` not `= []`

---

## Part 3: Completeness Scoring (`completeness.py`)

**Create file:** `src/services/database/completeness.py`

### Algorithm Overview

```
Total: 100 points

Basic Info (15 points):
- name: 5 points (required)
- title: 4 points
- email: 3 points
- location: 3 points

Summary (10 points):
- Present and 200+ chars: 10 points
- Present and 100-199 chars: 7 points
- Present and 50-99 chars: 4 points
- Present but < 50 chars: 2 points
- Missing: 0 points

Skills (25 points):
- 10+ skills: 25 points
- 5-9 skills: 15 + (count - 5) * 2 points
- 1-4 skills: count * 3 points
- 0 skills: 0 points
- Bonus suggestions for missing levels/years

Experience (25 points):
- 4+ entries: 25 points
- 2-3 entries: 15 + (count - 2) * 5 points
- 1 entry: 8 points
- 0 entries: 0 points
- Suggestions for missing descriptions/achievements

Education (10 points):
- 1+ entries: 10 points
- 0 entries: 0 points

Certifications (10 points - bonus):
- 3+ certs: 10 points
- 1-2 certs: count * 3 points
- 0 certs: 0 points (not penalized)

Languages (5 points - bonus):
- 1+ languages: 5 points
- 0 languages: 0 points (not penalized)
```

### Required Functions

```python
def calculate_completeness(profile: Profile) -> ProfileCompleteness:
    """Calculate completeness score for a profile.
    
    Args:
        profile: Full Profile with all related data loaded.
        
    Returns:
        ProfileCompleteness with section scores and suggestions.
    """

def _score_basic_info(profile: Profile) -> CompletenessSection:
    """Score basic info fields (name, title, email, location)."""

def _score_summary(profile: Profile) -> CompletenessSection:
    """Score professional summary."""

def _score_skills(profile: Profile) -> CompletenessSection:
    """Score skills section."""

def _score_experience(profile: Profile) -> CompletenessSection:
    """Score experience section."""

def _score_education(profile: Profile) -> CompletenessSection:
    """Score education section."""

def _score_certifications(profile: Profile) -> CompletenessSection:
    """Score certifications section (bonus)."""

def _score_languages(profile: Profile) -> CompletenessSection:
    """Score languages section (bonus)."""

def _get_level(score: int) -> str:
    """Convert percentage score to level string.
    
    Returns:
        - "excellent" for 90-100
        - "good" for 70-89
        - "fair" for 50-69
        - "needs_work" for 0-49
    """
```

### Implementation Notes

- Import Profile and completeness models from `.models`
- Each section scorer returns a `CompletenessSection`
- Suggestions should be actionable (e.g., "Add at least 5 skills" not "Skills section incomplete")
- Limit suggestions to 2 per section
- `top_suggestions` should be the first 3 suggestions overall, prioritized by section weight

---

## Part 4: Exceptions (`exceptions.py`)

**Update file:** `src/services/database/exceptions.py`

### Add/Update Exceptions

```python
"""Database service exceptions."""


class DatabaseError(Exception):
    """Base exception for database operations."""
    pass


class MigrationError(DatabaseError):
    """Database migration failed."""
    pass


class UserNotFoundError(DatabaseError):
    """User not found in database."""
    def __init__(self, identifier: str | int):
        self.identifier = identifier
        super().__init__(f"User not found: {identifier}")


class ProfileNotFoundError(DatabaseError):
    """Profile not found in database."""
    def __init__(self, identifier: str | int):
        self.identifier = identifier
        super().__init__(f"Profile not found: {identifier}")


class ProfileSlugExistsError(DatabaseError):
    """Profile with this slug already exists."""
    def __init__(self, slug: str):
        self.slug = slug
        super().__init__(f"Profile with slug already exists: {slug}")


# Keep for backward compatibility
ProfileExistsError = ProfileSlugExistsError


class ApplicationNotFoundError(DatabaseError):
    """Application not found in database."""
    def __init__(self, identifier: str | int):
        self.identifier = identifier
        super().__init__(f"Application not found: {identifier}")


class NoActiveProfileError(DatabaseError):
    """No active profile set for user."""
    def __init__(self, user_id: int):
        self.user_id = user_id
        super().__init__(f"No active profile for user: {user_id}")
```

---

## Part 5: Module Exports (`__init__.py`)

**Update file:** `src/services/database/__init__.py`

```python
"""Database service - SQLite persistence for users, profiles, and applications."""

from .service import DatabaseService, get_database_service, reset_database_service
from .schemas import SCHEMA_SQL, SCHEMA_VERSION, get_drop_tables_sql
from .models import (
    # Enums
    SkillLevel,
    LanguageProficiency,
    ApplicationStatus,
    # User
    User,
    UserCreate,
    # Profile components
    Skill,
    SkillCreate,
    SkillBase,
    Experience,
    ExperienceCreate,
    ExperienceBase,
    Education,
    EducationCreate,
    EducationBase,
    Certification,
    CertificationCreate,
    CertificationBase,
    Language,
    LanguageCreate,
    LanguageBase,
    # Profile
    Profile,
    ProfileCreate,
    ProfileUpdate,
    ProfileBase,
    ProfileSummary,
    # Completeness
    ProfileCompleteness,
    CompletenessSection,
    # Application
    Application,
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationBase,
    # Settings
    Settings,
)
from .completeness import calculate_completeness
from .exceptions import (
    DatabaseError,
    MigrationError,
    UserNotFoundError,
    ProfileNotFoundError,
    ProfileSlugExistsError,
    ProfileExistsError,  # Backward compat alias
    ApplicationNotFoundError,
    NoActiveProfileError,
)

__all__ = [
    # Service
    "DatabaseService",
    "get_database_service",
    "reset_database_service",
    # Schema
    "SCHEMA_SQL",
    "SCHEMA_VERSION",
    "get_drop_tables_sql",
    # Enums
    "SkillLevel",
    "LanguageProficiency",
    "ApplicationStatus",
    # User models
    "User",
    "UserCreate",
    # Component models
    "Skill",
    "SkillCreate",
    "SkillBase",
    "Experience",
    "ExperienceCreate",
    "ExperienceBase",
    "Education",
    "EducationCreate",
    "EducationBase",
    "Certification",
    "CertificationCreate",
    "CertificationBase",
    "Language",
    "LanguageCreate",
    "LanguageBase",
    # Profile models
    "Profile",
    "ProfileCreate",
    "ProfileUpdate",
    "ProfileBase",
    "ProfileSummary",
    # Completeness
    "ProfileCompleteness",
    "CompletenessSection",
    "calculate_completeness",
    # Application models
    "Application",
    "ApplicationCreate",
    "ApplicationUpdate",
    "ApplicationBase",
    # Settings
    "Settings",
    # Exceptions
    "DatabaseError",
    "MigrationError",
    "UserNotFoundError",
    "ProfileNotFoundError",
    "ProfileSlugExistsError",
    "ProfileExistsError",
    "ApplicationNotFoundError",
    "NoActiveProfileError",
]
```

---

## Validation Steps

After implementation, verify:

### 1. Syntax Check
```bash
python -c "from src.services.database import schemas, models, completeness, exceptions"
```

### 2. Import Check
```bash
python -c "from src.services.database import *; print('All exports working')"
```

### 3. Model Validation
```bash
python -c "
from src.services.database.models import (
    User, UserCreate,
    Profile, ProfileCreate, ProfileUpdate, ProfileSummary,
    Skill, Experience, Education, Certification, Language,
    Application, ApplicationCreate,
    ProfileCompleteness, CompletenessSection
)

# Test User creation
user = User(id=1, username='test', created_at='2025-01-01', updated_at='2025-01-01')
print(f'User: {user.username}')

# Test Profile creation
profile = Profile(
    id=1, user_id=1, slug='test', name='Test Profile',
    is_active=True, is_demo=False,
    created_at='2025-01-01', updated_at='2025-01-01'
)
print(f'Profile: {profile.name}')

# Test ProfileCreate with nested data
create_data = ProfileCreate(
    name='New Profile',
    skills=[{'name': 'Python', 'level': 'expert'}],
    experiences=[{'title': 'Engineer', 'company': 'Corp'}],
)
print(f'ProfileCreate skills: {len(create_data.skills)}')

print('All model tests passed!')
"
```

### 4. Completeness Test
```bash
python -c "
from src.services.database.models import Profile, Skill, Experience
from src.services.database.completeness import calculate_completeness

# Create a minimal profile
profile = Profile(
    id=1, user_id=1, slug='test', name='Test',
    is_active=True, is_demo=False,
    created_at='2025-01-01', updated_at='2025-01-01',
    skills=[Skill(id=1, profile_id=1, name='Python', level='expert')],
)

result = calculate_completeness(profile)
print(f'Completeness: {result.overall_score}% ({result.level})')
print(f'Suggestions: {result.top_suggestions}')
"
```

---

## Notes for Next Work Package

After this WP is complete, WP2 will:
1. Update `migrations.py` to use new schema
2. Rewrite `service.py` with all CRUD operations
3. Create `demo_data.py` with Test User and 3 profiles
4. Write comprehensive tests

**Do NOT modify these files in WP1:**
- `service.py` - Will be rewritten in WP2
- `demo_data.py` - Will be rewritten in WP2
- `migrations.py` - Will be updated in WP2

---

## Completion Checklist

- [ ] `schemas.py` created with all tables and indexes
- [ ] `models.py` rewritten with all Pydantic models
- [ ] `completeness.py` created with scoring algorithm
- [ ] `exceptions.py` updated with new exceptions
- [ ] `__init__.py` updated with all exports
- [ ] All syntax checks pass
- [ ] All import checks pass
- [ ] Model validation tests pass
- [ ] Completeness test passes
- [ ] Code committed to feature branch

```bash
git add src/services/database/
git commit -m "WP1: Add database schema, models, and completeness scoring

- New normalized schema with users, profiles, and related tables
- Pydantic models for all entities with proper validation
- Profile completeness scoring algorithm
- Updated exceptions for new error cases"
```
