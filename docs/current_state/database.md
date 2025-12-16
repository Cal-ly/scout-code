# Database Service - Current State

This document describes the SQLite database service implementation for Scout's persistence layer.

## Overview

The Database Service provides SQLite-based persistence for user profiles and job applications, enabling multi-profile support with data that survives server restarts.

| Component | Details |
|-----------|---------|
| Location | `src/services/database/` |
| Database | SQLite (`data/scout.db`) |
| Test Count | ~50 |
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
│  - Profile CRUD                                              │
│  - Application CRUD                                          │
│  - Active profile management                                 │
│  - ChromaDB re-indexing triggers                             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   SQLite (data/scout.db)                     │
│  Tables: profiles, applications                              │
└─────────────────────────────────────────────────────────────┘
```

---

## File Structure

```
src/services/database/
├── __init__.py          # Public exports
├── service.py           # Main DatabaseService class
├── models.py            # Pydantic models and enums
├── exceptions.py        # Custom exceptions
└── demo_profiles.py     # Demo profile data
```

---

## Database Schema

### `profiles` Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Auto-increment ID |
| `slug` | TEXT | UNIQUE NOT NULL | URL-safe identifier |
| `name` | TEXT | NOT NULL | Display name |
| `full_name` | TEXT | | Full name |
| `email` | TEXT | | Email address |
| `phone` | TEXT | | Phone number |
| `location` | TEXT | | Location |
| `title` | TEXT | | Job title |
| `summary` | TEXT | | Professional summary |
| `profile_data` | TEXT | | JSON: Full UserProfile model |
| `is_active` | INTEGER | DEFAULT 0 | Active profile flag (0/1) |
| `is_demo` | INTEGER | DEFAULT 0 | Demo profile flag (0/1) |
| `created_at` | TEXT | | ISO timestamp |
| `updated_at` | TEXT | | ISO timestamp |

### `applications` Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Auto-increment ID |
| `job_id` | TEXT | UNIQUE NOT NULL | Pipeline job ID |
| `profile_id` | INTEGER | FOREIGN KEY | References profiles(id) |
| `job_text` | TEXT | | Original job posting text |
| `job_title` | TEXT | | Extracted job title |
| `company_name` | TEXT | | Extracted company name |
| `status` | TEXT | | pending/running/completed/failed |
| `compatibility_score` | REAL | | Match score (0-100) |
| `cv_path` | TEXT | | Path to generated CV PDF |
| `cover_letter_path` | TEXT | | Path to cover letter PDF |
| `analysis_data` | TEXT | | JSON: AnalysisResult data |
| `pipeline_data` | TEXT | | JSON: Pipeline step results |
| `error_message` | TEXT | | Error details if failed |
| `started_at` | TEXT | | Pipeline start timestamp |
| `completed_at` | TEXT | | Pipeline completion timestamp |
| `created_at` | TEXT | | Record creation timestamp |

---

## Models

### Profile Model

```python
class Profile(BaseModel):
    """Database profile record."""
    id: int
    slug: str
    name: str
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    title: str | None = None
    summary: str | None = None
    profile_data: dict[str, Any]  # Full UserProfile as dict
    is_active: bool = False
    is_demo: bool = False
    created_at: datetime
    updated_at: datetime
    stats: ProfileStats | None = None  # Computed on read

class ProfileStats(BaseModel):
    """Profile statistics computed from applications."""
    total_applications: int = 0
    completed_applications: int = 0
    avg_compatibility_score: float | None = None
```

### Application Model

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
    profile_id: int
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
```

---

## Main Class: DatabaseService

```python
class DatabaseService:
    """SQLite persistence for profiles and applications."""

    def __init__(
        self,
        db_path: Path | None = None,  # Default: data/scout.db
    ): ...

    async def initialize(self) -> None:
        """
        Initialize database:
        1. Create data directory if needed
        2. Create tables if not exist
        3. Seed demo profiles if empty
        """

    async def shutdown(self) -> None:
        """Close database connection."""

    # Profile operations
    async def list_profiles(self) -> list[Profile]: ...
    async def get_profile_by_slug(self, slug: str) -> Profile: ...
    async def get_active_profile(self) -> Profile | None: ...
    async def set_active_profile(self, slug: str) -> Profile: ...
    async def create_profile(self, data: ProfileCreate) -> Profile: ...
    async def update_profile(self, slug: str, data: ProfileUpdate) -> Profile: ...
    async def delete_profile(self, slug: str) -> None: ...

    # Application operations
    async def list_applications(
        self,
        profile_id: int | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Application], int]: ...
    async def get_application_by_job_id(self, job_id: str) -> Application | None: ...
    async def create_application(self, data: ApplicationCreate) -> Application: ...
    async def update_application(self, job_id: str, data: ApplicationUpdate) -> Application: ...
```

---

## Key Features

### 1. Auto-Migration

Tables are created automatically on first startup:

```python
async def _ensure_schema(self) -> None:
    """Create tables if they don't exist."""
    async with aiosqlite.connect(self._db_path) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                ...
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT UNIQUE NOT NULL,
                profile_id INTEGER REFERENCES profiles(id),
                ...
            )
        ''')
        await db.commit()
```

### 2. Demo Profile Seeding

Three demo profiles are auto-created when the database is empty:

```python
DEMO_PROFILES = [
    {
        "name": "Emma Chen",
        "slug": "emma-chen",
        "title": "AI/ML Engineer",
        "email": "emma.chen@example.com",
        # ... full profile data
    },
    {
        "name": "Marcus Andersen",
        "slug": "marcus-andersen",
        "title": "Backend/DevOps Engineer",
        # ...
    },
    {
        "name": "Sofia Martinez",
        "slug": "sofia-martinez",
        "title": "Full-Stack Developer",
        # ...
    },
]
```

### 3. Slug Generation

Profile slugs are generated from names for human-readable URLs:

```python
def generate_slug(name: str) -> str:
    """Convert name to URL-safe slug."""
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    return slug

# Examples:
# "Emma Chen" -> "emma-chen"
# "Dr. John Smith III" -> "dr-john-smith-iii"
```

### 4. Active Profile Pattern

Only one profile can be active at a time. Switching triggers ChromaDB re-indexing:

```python
async def set_active_profile(self, slug: str) -> Profile:
    """Activate a profile and re-index to ChromaDB."""
    async with aiosqlite.connect(self._db_path) as db:
        # Clear all active flags
        await db.execute("UPDATE profiles SET is_active = 0")

        # Set new active profile
        await db.execute(
            "UPDATE profiles SET is_active = 1 WHERE slug = ?",
            (slug,)
        )
        await db.commit()

    # Trigger ChromaDB re-indexing
    profile = await self.get_profile_by_slug(slug)
    await self._reindex_to_chromadb(profile)

    return profile
```

### 5. Profile-Scoped Applications

Applications are linked to profiles via foreign key:

```python
async def list_applications(
    self,
    profile_id: int | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Application], int]:
    """List applications, optionally filtered by profile."""
    query = "SELECT * FROM applications"
    params = []

    if profile_id is not None:
        query += " WHERE profile_id = ?"
        params.append(profile_id)

    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    # ... execute query
```

---

## Usage Examples

### Basic Usage

```python
from src.services.database import get_database_service

# Get singleton instance
db = await get_database_service()

# Get active profile
profile = await db.get_active_profile()
print(f"Active: {profile.name} ({profile.slug})")

# List all profiles
profiles = await db.list_profiles()
for p in profiles:
    print(f"- {p.name}: {p.stats.total_applications} apps")
```

### Profile Management

```python
# Create new profile
from src.services.database import ProfileCreate

new_profile = await db.create_profile(ProfileCreate(
    name="John Doe",
    email="john@example.com",
    title="Software Engineer",
    profile_data={
        "name": "John Doe",
        "skills": [{"name": "Python", "level": "expert"}],
        # ...
    }
))
print(f"Created: {new_profile.slug}")

# Switch active profile
await db.set_active_profile("john-doe")

# Update profile
from src.services.database import ProfileUpdate

await db.update_profile("john-doe", ProfileUpdate(
    title="Senior Software Engineer"
))

# Delete profile (cannot delete active)
await db.delete_profile("old-profile")
```

### Application Tracking

```python
from src.services.database import ApplicationCreate, ApplicationUpdate, ApplicationStatus

# Create application record when pipeline starts
app = await db.create_application(ApplicationCreate(
    job_id="abc12345",
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
    completed_at=datetime.now(),
))

# List applications for profile
apps, total = await db.list_applications(
    profile_id=profile.id,
    limit=10,
    offset=0
)
```

---

## Integration Points

### Pipeline Orchestrator

The Pipeline Orchestrator creates and updates application records:

```python
# In jobs.py API route
async def _execute_pipeline(...):
    db = await get_database_service()

    # Mark as running
    await db.update_application(job_id, ApplicationUpdate(
        status=ApplicationStatus.RUNNING,
        started_at=datetime.now(),
    ))

    try:
        result = await orchestrator.execute(input_data)

        # Save completed result
        await db.update_application(job_id, ApplicationUpdate(
            status=ApplicationStatus.COMPLETED,
            job_title=result.job_title,
            company_name=result.company_name,
            compatibility_score=result.compatibility_score,
            cv_path=result.cv_path,
            cover_letter_path=result.cover_letter_path,
            completed_at=datetime.now(),
        ))
    except Exception as e:
        await db.update_application(job_id, ApplicationUpdate(
            status=ApplicationStatus.FAILED,
            error_message=str(e),
            completed_at=datetime.now(),
        ))
```

### Collector Module

The Collector can load profiles from the database:

```python
# In collector.py
async def load_profile_from_db(self) -> UserProfile | None:
    """Load the active profile from database."""
    from src.services.database import get_database_service

    db = await get_database_service()
    active = await db.get_active_profile()

    if active is None:
        return None

    self._profile = UserProfile(**active.profile_data)
    return self._profile
```

### Web Interface

The navbar profile switcher uses the profiles API:

```javascript
// In common.js
async function loadProfilesList() {
    const response = await fetch('/api/v1/profiles');
    const data = await response.json();
    window.Scout.profilesList = data.profiles || [];
    window.Scout.activeProfileSlug = data.active_profile_slug;
    updateNavbarProfileSwitcher();
}

async function switchToProfile(slug) {
    await fetch(`/api/v1/profiles/${slug}/activate`, { method: 'POST' });
    // Shows toast, reloads page
}
```

---

## Exceptions

```python
class DatabaseError(Exception):
    """Base exception for database operations."""
    pass

class ProfileNotFoundError(DatabaseError):
    """Profile with given slug not found."""
    pass

class ApplicationNotFoundError(DatabaseError):
    """Application with given job_id not found."""
    pass

class CannotDeleteActiveProfileError(DatabaseError):
    """Cannot delete the currently active profile."""
    pass
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
pytest tests/test_database.py -v
```

Key test areas:
- Profile CRUD operations
- Application CRUD operations
- Active profile switching
- Demo profile seeding
- Slug generation
- Foreign key constraints
- Error handling

---

*Last updated: December 16, 2025*
*Database: SQLite with aiosqlite for async access*
