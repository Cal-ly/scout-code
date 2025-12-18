# Database Service - Current State

This document describes the SQLite database service implementation for Scout's persistence layer.

## Overview

The Database Service provides SQLite-based persistence with a normalized User/Profile architecture, enabling multi-profile support where a single user can have multiple career personas (profiles) for different job application strategies.

| Component | Details |
|-----------|---------|
| Location | `src/services/database/` |
| Database | SQLite (`data/scout.db`) |
| Schema Version | 2 |
| Dependencies | None |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Web Interface                             │
│  (Profile Switcher, Profile Editor, Applications List)       │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    API Routes                                │
│  /api/v1/profiles/*   /api/v1/jobs/*                        │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  Database Service                            │
│  - User operations (get, create)                             │
│  - Profile CRUD with normalized data                         │
│  - Application CRUD                                          │
│  - Active profile management                                 │
│  - Profile completeness scoring                              │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   SQLite (data/scout.db)                     │
│  Tables: users, profiles, profile_skills,                    │
│          profile_experiences, profile_education,             │
│          profile_certifications, profile_languages,          │
│          applications, settings                              │
└─────────────────────────────────────────────────────────────┘
```

---

## File Structure

```
src/services/database/
├── __init__.py          # Public exports
├── service.py           # Main DatabaseService class (~1200 lines)
├── models.py            # Pydantic models and enums
├── schemas.py           # SQL schema definitions
├── migrations.py        # Database initialization and migrations
├── completeness.py      # Profile completeness scoring algorithm
├── exceptions.py        # Custom exceptions
└── demo_data.py         # Test User + 3 demo profiles
```

---

## Database Schema (v2)

### `users` Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Auto-increment ID |
| `username` | TEXT | UNIQUE NOT NULL | Login identifier |
| `email` | TEXT | | Email address |
| `display_name` | TEXT | | Display name |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation time |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last update time |

### `profiles` Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Auto-increment ID |
| `user_id` | INTEGER | REFERENCES users(id) | Owner user |
| `slug` | TEXT | UNIQUE NOT NULL | URL-safe identifier |
| `name` | TEXT | NOT NULL | Display name |
| `title` | TEXT | | Job title |
| `email` | TEXT | | Contact email |
| `phone` | TEXT | | Phone number |
| `location` | TEXT | | Location |
| `summary` | TEXT | | Professional summary |
| `is_active` | INTEGER | DEFAULT 0 | Active profile flag (0/1) |
| `is_demo` | INTEGER | DEFAULT 0 | Demo profile flag (0/1) |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation time |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last update time |

### `profile_skills` Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Auto-increment ID |
| `profile_id` | INTEGER | REFERENCES profiles(id) ON DELETE CASCADE | Parent profile |
| `name` | TEXT | NOT NULL | Skill name |
| `level` | TEXT | CHECK(level IN (...)) | beginner/intermediate/advanced/expert |
| `years` | INTEGER | | Years of experience |
| `category` | TEXT | | Skill category (e.g., "Programming") |
| `sort_order` | INTEGER | DEFAULT 0 | Display order |

### `profile_experiences` Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Auto-increment ID |
| `profile_id` | INTEGER | REFERENCES profiles(id) ON DELETE CASCADE | Parent profile |
| `title` | TEXT | NOT NULL | Job title |
| `company` | TEXT | NOT NULL | Company name |
| `start_date` | TEXT | | Start date (YYYY-MM) |
| `end_date` | TEXT | | End date (YYYY-MM or NULL for current) |
| `description` | TEXT | | Role description |
| `achievements` | TEXT | | JSON array of achievements |
| `sort_order` | INTEGER | DEFAULT 0 | Display order |

### `profile_education` Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Auto-increment ID |
| `profile_id` | INTEGER | REFERENCES profiles(id) ON DELETE CASCADE | Parent profile |
| `institution` | TEXT | NOT NULL | School/university name |
| `degree` | TEXT | | Degree type (B.S., M.S., etc.) |
| `field` | TEXT | | Field of study |
| `start_date` | TEXT | | Start date |
| `end_date` | TEXT | | End date |
| `gpa` | TEXT | | GPA |
| `achievements` | TEXT | | JSON array of achievements |
| `sort_order` | INTEGER | DEFAULT 0 | Display order |

### `profile_certifications` Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Auto-increment ID |
| `profile_id` | INTEGER | REFERENCES profiles(id) ON DELETE CASCADE | Parent profile |
| `name` | TEXT | NOT NULL | Certification name |
| `issuer` | TEXT | | Issuing organization |
| `date_obtained` | TEXT | | Date obtained |
| `expiry_date` | TEXT | | Expiration date |
| `credential_url` | TEXT | | Verification URL |
| `sort_order` | INTEGER | DEFAULT 0 | Display order |

### `profile_languages` Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Auto-increment ID |
| `profile_id` | INTEGER | REFERENCES profiles(id) ON DELETE CASCADE | Parent profile |
| `language` | TEXT | NOT NULL | Language name |
| `proficiency` | TEXT | CHECK(proficiency IN (...)) | basic/conversational/professional/fluent/native |
| `sort_order` | INTEGER | DEFAULT 0 | Display order |

### `applications` Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Auto-increment ID |
| `user_id` | INTEGER | REFERENCES users(id) | Owner user |
| `profile_id` | INTEGER | REFERENCES profiles(id) | Profile used |
| `job_id` | TEXT | UNIQUE NOT NULL | Pipeline job ID |
| `job_title` | TEXT | | Extracted job title |
| `company_name` | TEXT | | Extracted company name |
| `status` | TEXT | DEFAULT 'pending' | pending/running/completed/failed |
| `compatibility_score` | REAL | | Match score (0-100) |
| `cv_path` | TEXT | | Path to generated CV PDF |
| `cover_letter_path` | TEXT | | Path to cover letter PDF |
| `job_text` | TEXT | | Original job posting text |
| `analysis_data` | TEXT | | JSON: AnalysisResult data |
| `pipeline_data` | TEXT | | JSON: Pipeline step results |
| `error_message` | TEXT | | Error details if failed |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Record creation |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last update |
| `started_at` | TIMESTAMP | | Pipeline start time |
| `completed_at` | TIMESTAMP | | Pipeline completion time |

### `settings` Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `key` | TEXT | PRIMARY KEY | Setting key |
| `value` | TEXT | NOT NULL | Setting value (JSON-serialized) |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last update |

**Known Setting Keys:**

| Key | Type | Description |
|-----|------|-------------|
| `active_profile_id` | int | ID of the currently active profile |
| `schema_version` | int | Current database schema version (2) |
| `demo_data_loaded` | bool | Whether demo profiles have been seeded |

---

## Models

### User Models

```python
class User(BaseModel):
    """Database user record."""
    id: int
    username: str
    email: str | None = None
    display_name: str | None = None
    created_at: datetime
    updated_at: datetime

class UserCreate(BaseModel):
    """Data for creating a new user."""
    username: str
    email: str | None = None
    display_name: str | None = None
```

### Profile Models

```python
class Profile(BaseModel):
    """Full profile with all related data."""
    id: int
    user_id: int
    slug: str
    name: str
    title: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    summary: str | None = None
    is_active: bool = False
    is_demo: bool = False
    created_at: datetime
    updated_at: datetime
    # Related data
    skills: list[Skill] = []
    experiences: list[Experience] = []
    education: list[Education] = []
    certifications: list[Certification] = []
    languages: list[Language] = []

class ProfileSummary(BaseModel):
    """Profile with aggregated stats (for list views)."""
    id: int
    user_id: int
    slug: str
    name: str
    title: str | None = None
    is_active: bool = False
    is_demo: bool = False
    created_at: datetime
    updated_at: datetime
    # Computed stats
    skill_count: int = 0
    experience_count: int = 0
    education_count: int = 0
    certification_count: int = 0
    language_count: int = 0
    application_count: int = 0
    completed_application_count: int = 0
    avg_compatibility_score: float | None = None
```

### Application Models

```python
class ApplicationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class Application(BaseModel):
    """Database application record."""
    id: int
    job_id: str
    user_id: int | None = None
    profile_id: int | None = None
    job_text: str | None = None
    job_title: str | None = None
    company_name: str | None = None
    status: ApplicationStatus
    compatibility_score: float | None = None
    cv_path: str | None = None
    cover_letter_path: str | None = None
    analysis_data: dict | None = None
    pipeline_data: dict | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    # Joined fields
    profile_name: str | None = None
    profile_slug: str | None = None
```

---

## Main Class: DatabaseService

```python
class DatabaseService:
    """SQLite persistence for users, profiles, and applications."""

    def __init__(self, db_path: Path = DEFAULT_DB_PATH): ...

    async def initialize(self) -> None:
        """Initialize database, run migrations, seed demo data."""

    async def close(self) -> None:
        """Close database connection."""

    async def reset(self) -> None:
        """Reset database to fresh state. WARNING: Deletes all data!"""

    # Settings
    async def get_settings(self) -> Settings: ...
    async def set_setting(self, key: str, value: Any) -> None: ...

    # User operations
    async def get_user(self, user_id: int) -> User: ...
    async def get_user_by_username(self, username: str) -> User | None: ...
    async def get_current_user(self) -> User: ...
    async def create_user(self, data: UserCreate) -> User: ...

    # Profile operations
    async def list_profiles(self, user_id: int | None = None) -> list[ProfileSummary]: ...
    async def get_profile(self, profile_id: int) -> Profile: ...
    async def get_profile_by_slug(self, slug: str) -> Profile: ...
    async def get_active_profile(self, user_id: int | None = None) -> Profile | None: ...
    async def create_profile(self, user_id: int, data: ProfileCreate) -> Profile: ...
    async def update_profile(self, slug: str, data: ProfileUpdate) -> Profile: ...
    async def delete_profile(self, slug: str) -> None: ...
    async def activate_profile(self, slug: str) -> Profile: ...
    async def get_profile_completeness(self, slug: str) -> ProfileCompleteness: ...

    # Application operations
    async def list_applications(
        self,
        user_id: int | None = None,
        profile_id: int | None = None,
        status: ApplicationStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Application], int]: ...
    async def get_application(self, job_id: str) -> Application: ...
    async def get_application_by_id(self, app_id: int) -> Application: ...
    async def create_application(self, data: ApplicationCreate) -> Application: ...
    async def update_application(self, job_id: str, data: ApplicationUpdate) -> Application: ...
    async def delete_application(self, job_id: str) -> None: ...
```

---

## Key Features

### 1. User/Profile Separation

Users own multiple profiles, enabling different career personas:

```python
# One user can have multiple profiles
user = await db.get_current_user()  # Returns Test User
profiles = await db.list_profiles(user.id)
# Returns: Backend Focus, Full Stack, DevOps Specialist
```

### 2. Normalized Profile Data

Profile data is stored in separate related tables instead of a JSON blob:

```python
profile = await db.get_profile_by_slug("backend-focus")
print(f"Skills: {len(profile.skills)}")  # 12 skills
print(f"Experience: {len(profile.experiences)}")  # 3 experiences
print(f"Education: {len(profile.education)}")  # 1 education
```

### 3. Demo Data Seeding

Test User with 3 demo profiles is auto-created on first startup:

```python
DEMO_PROFILES = [
    BACKEND_FOCUS_PROFILE,    # Senior Backend Engineer
    FULLSTACK_FOCUS_PROFILE,  # Full Stack Developer
    DEVOPS_FOCUS_PROFILE,     # DevOps Engineer
]
DEFAULT_ACTIVE_PROFILE_SLUG = "backend-focus"
```

### 4. Profile Completeness Scoring

Profiles are scored based on section completeness:

```python
completeness = await db.get_profile_completeness("backend-focus")
print(f"Score: {completeness.overall_score}%")  # 91%
print(f"Level: {completeness.level}")  # excellent
```

Scoring weights:
- Contact info: 15%
- Summary: 15%
- Skills: 20%
- Experience: 25%
- Education: 15%
- Certifications: 5%
- Languages: 5%

### 5. Schema Migrations

Database migrations run automatically on startup:

```python
def run_migrations(conn: sqlite3.Connection) -> None:
    """Run pending migrations from current to target version."""
    current = get_schema_version(conn)
    if current < 2:
        _migrate_v1_to_v2(conn)  # Destructive for PoC
```

### 6. Singleton Pattern

```python
# Get singleton instance
db = await get_database_service()

# Reset singleton (for testing)
reset_database_service()
```

---

## Usage Examples

### Basic Usage

```python
from src.services.database import get_database_service

# Get singleton instance
db = await get_database_service()

# Get current user (test_user for PoC)
user = await db.get_current_user()

# Get active profile with all data
profile = await db.get_active_profile()
print(f"Active: {profile.name} ({profile.slug})")
print(f"Skills: {len(profile.skills)}")
```

### Profile Management

```python
from src.services.database import (
    get_database_service,
    ProfileCreate,
    ProfileUpdate,
    SkillCreate,
    SkillLevel,
)

db = await get_database_service()
user = await db.get_current_user()

# Create new profile
new_profile = await db.create_profile(user.id, ProfileCreate(
    name="ML Engineer",
    title="Machine Learning Engineer",
    summary="ML specialist with 5 years of experience...",
    skills=[
        SkillCreate(name="Python", level=SkillLevel.EXPERT, years=5),
        SkillCreate(name="TensorFlow", level=SkillLevel.ADVANCED, years=3),
    ],
))
print(f"Created: {new_profile.slug}")

# Update profile
await db.update_profile("ml-engineer", ProfileUpdate(
    title="Senior ML Engineer",
    skills=[
        SkillCreate(name="Python", level=SkillLevel.EXPERT, years=6),
        SkillCreate(name="PyTorch", level=SkillLevel.ADVANCED, years=4),
    ],
))

# Activate profile
await db.activate_profile("ml-engineer")

# Delete profile
await db.delete_profile("ml-engineer")
```

### Application Tracking

```python
from src.services.database import (
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationStatus,
)

db = await get_database_service()
user = await db.get_current_user()
profile = await db.get_active_profile()

# Create application when pipeline starts
app = await db.create_application(ApplicationCreate(
    job_id="abc12345",
    user_id=user.id,
    profile_id=profile.id,
    job_text="Software Engineer at Example Corp...",
))

# Update when pipeline completes
await db.update_application("abc12345", ApplicationUpdate(
    status=ApplicationStatus.COMPLETED,
    job_title="Software Engineer",
    company_name="Example Corp",
    compatibility_score=78.5,
    cv_path="data/outputs/cv_abc12345.pdf",
    cover_letter_path="data/outputs/cover_letter_abc12345.pdf",
))

# List applications with filtering
apps, total = await db.list_applications(
    user_id=user.id,
    status=ApplicationStatus.COMPLETED,
    limit=10,
)
```

---

## Exceptions

```python
class DatabaseError(Exception):
    """Base exception for database operations."""

class MigrationError(DatabaseError):
    """Schema migration failed."""

class UserNotFoundError(DatabaseError):
    """User not found by ID or username."""

class ProfileNotFoundError(DatabaseError):
    """Profile not found by ID or slug."""

class ProfileSlugExistsError(DatabaseError):
    """Profile with this slug already exists."""

class ApplicationNotFoundError(DatabaseError):
    """Application not found by job_id."""

class NoActiveProfileError(DatabaseError):
    """No active profile set for user."""
```

---

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `db_path` | `data/scout.db` | SQLite database file path |

The database file and parent directory are created automatically if they don't exist.

---

## Testing

Run tests:
```bash
pytest tests/test_database_service.py -v
```

Key test areas:
- User CRUD operations
- Profile CRUD with related data
- Application CRUD operations
- Active profile switching
- Demo data seeding
- Profile completeness scoring
- Schema migrations
- Error handling

---

*Last updated: December 17, 2025*
*Schema Version: 2 (User/Profile architecture)*
*Updated: Added known settings keys documentation*
