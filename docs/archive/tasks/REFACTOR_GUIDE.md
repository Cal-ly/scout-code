## Phase 1: Database Schema Refactor - Implementation Spec

### Overview

This specification covers the complete database layer refactor, including:
- New SQLite schema with normalized tables
- Pydantic models for User and Profile entities
- DatabaseService rewrite with full CRUD operations
- Demo data seeding (Test User + 3 profile personas)
- Profile completeness scoring
- Comprehensive test coverage

---

### File Structure (Target State)

```
src/services/database/
├── __init__.py              # Public exports
├── service.py               # DatabaseService class (rewrite)
├── models.py                # Pydantic models (rewrite)
├── schemas.py               # SQLite schema definitions (NEW)
├── completeness.py          # Profile completeness scoring (NEW)
├── demo_data.py             # Demo user and profiles (rewrite)
└── exceptions.py            # Custom exceptions (update)
```

---

### Part 1: Schema Definitions

**File:** `src/services/database/schemas.py` (NEW)

```sql
-- Users table (identity/auth - future)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT,
    display_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Profiles table (career personas/CVs)
CREATE TABLE IF NOT EXISTS profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    title TEXT,
    email TEXT,
    phone TEXT,
    location TEXT,
    summary TEXT,
    is_active BOOLEAN DEFAULT 0,
    is_demo BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Profile skills (normalized)
CREATE TABLE IF NOT EXISTS profile_skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    level TEXT CHECK(level IN ('beginner', 'intermediate', 'advanced', 'expert')),
    years INTEGER,
    category TEXT,
    sort_order INTEGER DEFAULT 0
);

-- Profile experiences (normalized)
CREATE TABLE IF NOT EXISTS profile_experiences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    start_date TEXT,
    end_date TEXT,
    description TEXT,
    achievements TEXT,  -- JSON array of strings
    sort_order INTEGER DEFAULT 0
);

-- Profile education (normalized)
CREATE TABLE IF NOT EXISTS profile_education (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    institution TEXT NOT NULL,
    degree TEXT,
    field TEXT,
    start_date TEXT,
    end_date TEXT,
    gpa TEXT,
    achievements TEXT,  -- JSON array of strings
    sort_order INTEGER DEFAULT 0
);

-- Profile certifications (normalized)
CREATE TABLE IF NOT EXISTS profile_certifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    issuer TEXT,
    date_obtained TEXT,
    expiry_date TEXT,
    credential_url TEXT,
    sort_order INTEGER DEFAULT 0
);

-- Profile languages (normalized)
CREATE TABLE IF NOT EXISTS profile_languages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    language TEXT NOT NULL,
    proficiency TEXT CHECK(proficiency IN ('basic', 'conversational', 'professional', 'fluent', 'native')),
    sort_order INTEGER DEFAULT 0
);

-- Applications (updated with user_id)
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    profile_id INTEGER REFERENCES profiles(id),
    job_id TEXT UNIQUE NOT NULL,
    job_title TEXT,
    company_name TEXT,
    status TEXT DEFAULT 'pending',
    compatibility_score REAL,
    cv_path TEXT,
    cover_letter_path TEXT,
    job_text TEXT,
    analysis_data TEXT,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_profiles_user_id ON profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_profiles_slug ON profiles(slug);
CREATE INDEX IF NOT EXISTS idx_profiles_is_active ON profiles(is_active);
CREATE INDEX IF NOT EXISTS idx_profile_skills_profile_id ON profile_skills(profile_id);
CREATE INDEX IF NOT EXISTS idx_profile_experiences_profile_id ON profile_experiences(profile_id);
CREATE INDEX IF NOT EXISTS idx_profile_education_profile_id ON profile_education(profile_id);
CREATE INDEX IF NOT EXISTS idx_applications_user_id ON applications(user_id);
CREATE INDEX IF NOT EXISTS idx_applications_profile_id ON applications(profile_id);
CREATE INDEX IF NOT EXISTS idx_applications_job_id ON applications(job_id);
```

---

### Part 2: Pydantic Models

**File:** `src/services/database/models.py` (REWRITE)

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
    PROCESSING = "processing"
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

#### Profile Component Models

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


class ExperienceBase(BaseModel):
    title: str
    company: str
    start_date: str | None = None
    end_date: str | None = None  # None = current position
    description: str | None = None
    achievements: list[str] = []
    sort_order: int = 0

class ExperienceCreate(ExperienceBase):
    pass

class Experience(ExperienceBase):
    id: int
    profile_id: int

    model_config = ConfigDict(from_attributes=True)


class EducationBase(BaseModel):
    institution: str
    degree: str | None = None
    field: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    gpa: str | None = None
    achievements: list[str] = []
    sort_order: int = 0

class EducationCreate(EducationBase):
    pass

class Education(EducationBase):
    id: int
    profile_id: int

    model_config = ConfigDict(from_attributes=True)


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
    slug: str | None = None  # Auto-generated from name if not provided
    skills: list[SkillCreate] = []
    experiences: list[ExperienceCreate] = []
    education: list[EducationCreate] = []
    certifications: list[CertificationCreate] = []
    languages: list[LanguageCreate] = []

class ProfileUpdate(BaseModel):
    """Full profile update - replaces all fields."""
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
    id: int
    user_id: int
    slug: str
    is_active: bool
    is_demo: bool
    created_at: datetime
    updated_at: datetime
    
    # Related data (loaded separately)
    skills: list[Skill] = []
    experiences: list[Experience] = []
    education: list[Education] = []
    certifications: list[Certification] = []
    languages: list[Language] = []

    model_config = ConfigDict(from_attributes=True)


class ProfileSummary(BaseModel):
    """Lightweight profile for list views."""
    id: int
    slug: str
    name: str
    title: str | None
    is_active: bool
    is_demo: bool
    created_at: datetime
    updated_at: datetime
    
    # Stats
    skill_count: int = 0
    experience_count: int = 0
    education_count: int = 0
    certification_count: int = 0
    application_count: int = 0
    avg_compatibility_score: float | None = None

    model_config = ConfigDict(from_attributes=True)
```

#### Completeness Models

```python
class CompletenessSection(BaseModel):
    """Completeness for a single profile section."""
    name: str
    score: int  # 0-100
    max_score: int
    items_present: int
    items_recommended: int
    suggestions: list[str] = []

class ProfileCompleteness(BaseModel):
    """Overall profile completeness assessment."""
    overall_score: int  # 0-100
    level: str  # "excellent", "good", "fair", "needs_work"
    sections: list[CompletenessSection]
    top_suggestions: list[str]  # Top 3 actionable suggestions
```

#### Application Models (Updated)

```python
class ApplicationBase(BaseModel):
    job_id: str
    job_title: str | None = None
    company_name: str | None = None
    job_text: str | None = None

class ApplicationCreate(ApplicationBase):
    user_id: int
    profile_id: int

class ApplicationUpdate(BaseModel):
    status: ApplicationStatus | None = None
    compatibility_score: float | None = None
    cv_path: str | None = None
    cover_letter_path: str | None = None
    analysis_data: dict | None = None
    completed_at: datetime | None = None

class Application(ApplicationBase):
    id: int
    user_id: int
    profile_id: int
    status: ApplicationStatus
    compatibility_score: float | None
    cv_path: str | None
    cover_letter_path: str | None
    analysis_data: dict | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
```

---

### Part 3: Profile Completeness Scoring

**File:** `src/services/database/completeness.py` (NEW)

#### Scoring Algorithm

```python
"""
Profile Completeness Scoring

Weights (total = 100):
- Basic Info (name, title, email, location): 15 points
- Summary: 10 points
- Skills: 25 points (min 5 recommended, max credit at 10+)
- Experience: 25 points (min 2 recommended, max credit at 4+)
- Education: 10 points (min 1 recommended)
- Certifications: 10 points (bonus, 0 required but adds value)
- Languages: 5 points (bonus)

Levels:
- 90-100: "excellent" - Ready for any application
- 70-89: "good" - Solid profile, minor improvements possible
- 50-69: "fair" - Functional but could be stronger
- 0-49: "needs_work" - Missing critical information
"""

def calculate_completeness(profile: Profile) -> ProfileCompleteness:
    """Calculate profile completeness with actionable suggestions."""
    sections = []
    suggestions = []
    
    # Basic Info (15 points)
    basic_info = _score_basic_info(profile)
    sections.append(basic_info)
    suggestions.extend(basic_info.suggestions)
    
    # Summary (10 points)
    summary = _score_summary(profile)
    sections.append(summary)
    suggestions.extend(summary.suggestions)
    
    # Skills (25 points)
    skills = _score_skills(profile)
    sections.append(skills)
    suggestions.extend(skills.suggestions)
    
    # Experience (25 points)
    experience = _score_experience(profile)
    sections.append(experience)
    suggestions.extend(experience.suggestions)
    
    # Education (10 points)
    education = _score_education(profile)
    sections.append(education)
    suggestions.extend(education.suggestions)
    
    # Certifications (10 points)
    certifications = _score_certifications(profile)
    sections.append(certifications)
    suggestions.extend(certifications.suggestions)
    
    # Languages (5 points)
    languages = _score_languages(profile)
    sections.append(languages)
    suggestions.extend(languages.suggestions)
    
    # Calculate overall
    total_score = sum(s.score for s in sections)
    max_score = sum(s.max_score for s in sections)
    overall_score = int((total_score / max_score) * 100) if max_score > 0 else 0
    
    level = _get_level(overall_score)
    top_suggestions = suggestions[:3]  # Top 3 most impactful
    
    return ProfileCompleteness(
        overall_score=overall_score,
        level=level,
        sections=sections,
        top_suggestions=top_suggestions,
    )
```

#### Section Scoring Functions

```python
def _score_basic_info(profile: Profile) -> CompletenessSection:
    """Score basic info fields (15 points max)."""
    max_score = 15
    fields = [
        (profile.name, 5, "Add your full name"),
        (profile.title, 4, "Add a professional title"),
        (profile.email, 3, "Add contact email"),
        (profile.location, 3, "Add your location"),
    ]
    
    score = sum(points for value, points, _ in fields if value)
    present = sum(1 for value, _, _ in fields if value)
    suggestions = [msg for value, _, msg in fields if not value]
    
    return CompletenessSection(
        name="Basic Info",
        score=score,
        max_score=max_score,
        items_present=present,
        items_recommended=4,
        suggestions=suggestions,
    )

def _score_summary(profile: Profile) -> CompletenessSection:
    """Score professional summary (10 points max)."""
    max_score = 10
    score = 0
    suggestions = []
    
    if profile.summary:
        length = len(profile.summary)
        if length >= 200:
            score = 10
        elif length >= 100:
            score = 7
            suggestions.append("Expand summary to 200+ characters for better impact")
        elif length >= 50:
            score = 4
            suggestions.append("Summary is brief - aim for 200+ characters")
        else:
            score = 2
            suggestions.append("Summary too short - describe your professional background")
    else:
        suggestions.append("Add a professional summary highlighting your expertise")
    
    return CompletenessSection(
        name="Summary",
        score=score,
        max_score=max_score,
        items_present=1 if profile.summary else 0,
        items_recommended=1,
        suggestions=suggestions,
    )

def _score_skills(profile: Profile) -> CompletenessSection:
    """Score skills section (25 points max)."""
    max_score = 25
    count = len(profile.skills)
    suggestions = []
    
    # Scoring: 5 skills = 15 points, 10+ skills = 25 points
    if count >= 10:
        score = 25
    elif count >= 5:
        score = 15 + ((count - 5) * 2)  # 15-25 points
    elif count >= 1:
        score = count * 3  # 3-12 points
    else:
        score = 0
        suggestions.append("Add at least 5 relevant skills")
    
    # Check for skill levels
    skills_with_level = sum(1 for s in profile.skills if s.level)
    if count > 0 and skills_with_level < count * 0.5:
        suggestions.append("Add proficiency levels to your skills")
    
    # Check for years
    skills_with_years = sum(1 for s in profile.skills if s.years)
    if count > 0 and skills_with_years < count * 0.3:
        suggestions.append("Add years of experience to key skills")
    
    return CompletenessSection(
        name="Skills",
        score=min(score, max_score),
        max_score=max_score,
        items_present=count,
        items_recommended=10,
        suggestions=suggestions[:2],  # Max 2 suggestions
    )

def _score_experience(profile: Profile) -> CompletenessSection:
    """Score experience section (25 points max)."""
    max_score = 25
    count = len(profile.experiences)
    suggestions = []
    
    # Scoring: 2 experiences = 15 points, 4+ = 25 points
    if count >= 4:
        score = 25
    elif count >= 2:
        score = 15 + ((count - 2) * 5)  # 15-25 points
    elif count == 1:
        score = 8
        suggestions.append("Add more work experience entries")
    else:
        score = 0
        suggestions.append("Add your work experience")
    
    # Check for descriptions
    with_desc = sum(1 for e in profile.experiences if e.description)
    if count > 0 and with_desc < count:
        suggestions.append("Add descriptions to all experience entries")
    
    # Check for achievements
    with_achievements = sum(1 for e in profile.experiences if e.achievements)
    if count > 0 and with_achievements < count * 0.5:
        suggestions.append("Add achievements to highlight your impact")
    
    return CompletenessSection(
        name="Experience",
        score=min(score, max_score),
        max_score=max_score,
        items_present=count,
        items_recommended=4,
        suggestions=suggestions[:2],
    )

def _score_education(profile: Profile) -> CompletenessSection:
    """Score education section (10 points max)."""
    max_score = 10
    count = len(profile.education)
    suggestions = []
    
    if count >= 1:
        score = 10
    else:
        score = 0
        suggestions.append("Add your educational background")
    
    return CompletenessSection(
        name="Education",
        score=score,
        max_score=max_score,
        items_present=count,
        items_recommended=1,
        suggestions=suggestions,
    )

def _score_certifications(profile: Profile) -> CompletenessSection:
    """Score certifications section (10 points bonus)."""
    max_score = 10
    count = len(profile.certifications)
    
    # Bonus section - not required but adds value
    if count >= 3:
        score = 10
    elif count >= 1:
        score = count * 3  # 3-9 points
    else:
        score = 0
    
    suggestions = []
    if count == 0:
        suggestions.append("Consider adding relevant certifications")
    
    return CompletenessSection(
        name="Certifications",
        score=score,
        max_score=max_score,
        items_present=count,
        items_recommended=3,
        suggestions=suggestions,
    )

def _score_languages(profile: Profile) -> CompletenessSection:
    """Score languages section (5 points bonus)."""
    max_score = 5
    count = len(profile.languages)
    
    if count >= 1:
        score = 5
    else:
        score = 0
    
    suggestions = []
    if count == 0:
        suggestions.append("Add languages you speak")
    
    return CompletenessSection(
        name="Languages",
        score=score,
        max_score=max_score,
        items_present=count,
        items_recommended=1,
        suggestions=suggestions,
    )

def _get_level(score: int) -> str:
    """Get completeness level from score."""
    if score >= 90:
        return "excellent"
    elif score >= 70:
        return "good"
    elif score >= 50:
        return "fair"
    else:
        return "needs_work"
```

---

### Part 4: Demo Data

**File:** `src/services/database/demo_data.py` (REWRITE)

```python
"""
Demo data for Scout - Test User with 3 profile personas.

These profiles demonstrate different career positioning strategies:
1. Backend Focus - Emphasizes backend/infrastructure skills
2. Full Stack - Balanced frontend + backend
3. DevOps Specialist - Infrastructure and automation focus
"""

TEST_USER = {
    "username": "test_user",
    "email": "test@scout.local",
    "display_name": "Test User",
}

DEMO_PROFILES = [
    {
        "slug": "backend-focus",
        "name": "Backend Focus",
        "title": "Senior Backend Engineer",
        "email": "backend.dev@example.com",
        "phone": "+1-555-0101",
        "location": "San Francisco, CA",
        "summary": "Backend engineer with 8+ years of experience building scalable distributed systems. Specialized in Python and Go, with deep expertise in API design, database optimization, and cloud infrastructure. Proven track record of improving system performance and reliability at scale.",
        "is_active": True,
        "is_demo": True,
        "skills": [
            {"name": "Python", "level": "expert", "years": 8, "category": "Programming"},
            {"name": "Go", "level": "advanced", "years": 4, "category": "Programming"},
            {"name": "PostgreSQL", "level": "expert", "years": 7, "category": "Database"},
            {"name": "Redis", "level": "advanced", "years": 5, "category": "Database"},
            {"name": "MongoDB", "level": "intermediate", "years": 3, "category": "Database"},
            {"name": "Docker", "level": "advanced", "years": 5, "category": "DevOps"},
            {"name": "Kubernetes", "level": "intermediate", "years": 2, "category": "DevOps"},
            {"name": "AWS", "level": "advanced", "years": 5, "category": "Cloud"},
            {"name": "REST API Design", "level": "expert", "years": 7, "category": "Architecture"},
            {"name": "gRPC", "level": "advanced", "years": 3, "category": "Architecture"},
            {"name": "Message Queues", "level": "advanced", "years": 4, "category": "Architecture"},
            {"name": "System Design", "level": "advanced", "years": 5, "category": "Architecture"},
        ],
        "experiences": [
            {
                "title": "Senior Backend Engineer",
                "company": "TechScale Inc.",
                "start_date": "2021-03",
                "end_date": None,
                "description": "Lead backend engineer for core platform services handling 10M+ daily requests.",
                "achievements": [
                    "Reduced API latency by 60% through query optimization and caching strategies",
                    "Designed and implemented event-driven architecture processing 5M events/day",
                    "Mentored team of 4 junior engineers on best practices and code review",
                    "Led migration from monolith to microservices, improving deployment frequency 10x",
                ],
            },
            {
                "title": "Backend Engineer",
                "company": "DataFlow Systems",
                "start_date": "2018-06",
                "end_date": "2021-02",
                "description": "Built and maintained data pipeline infrastructure for analytics platform.",
                "achievements": [
                    "Developed real-time data ingestion system handling 100K events/second",
                    "Implemented automated testing pipeline reducing bug escape rate by 40%",
                    "Optimized database queries reducing average response time from 2s to 200ms",
                ],
            },
            {
                "title": "Software Developer",
                "company": "StartupHub",
                "start_date": "2016-01",
                "end_date": "2018-05",
                "description": "Full-stack development for B2B SaaS platform.",
                "achievements": [
                    "Built RESTful API serving 50+ enterprise clients",
                    "Implemented OAuth 2.0 authentication system",
                    "Reduced deployment time from 2 hours to 15 minutes with CI/CD",
                ],
            },
        ],
        "education": [
            {
                "institution": "University of California, Berkeley",
                "degree": "B.S.",
                "field": "Computer Science",
                "start_date": "2012-08",
                "end_date": "2016-05",
                "gpa": "3.7",
                "achievements": ["Dean's List", "Senior thesis on distributed systems"],
            },
        ],
        "certifications": [
            {"name": "AWS Solutions Architect - Associate", "issuer": "Amazon Web Services", "date_obtained": "2022-03"},
            {"name": "Kubernetes Administrator (CKA)", "issuer": "CNCF", "date_obtained": "2023-01"},
        ],
        "languages": [
            {"language": "English", "proficiency": "native"},
            {"language": "Spanish", "proficiency": "conversational"},
        ],
    },
    {
        "slug": "fullstack-focus",
        "name": "Full Stack",
        "title": "Full Stack Developer",
        "email": "fullstack.dev@example.com",
        "phone": "+1-555-0102",
        "location": "Austin, TX",
        "summary": "Versatile full-stack developer with 6 years of experience building end-to-end web applications. Strong expertise in React/TypeScript frontend and Python/Node.js backend. Passionate about creating intuitive user experiences backed by robust, scalable systems.",
        "is_active": False,
        "is_demo": True,
        "skills": [
            {"name": "TypeScript", "level": "expert", "years": 5, "category": "Programming"},
            {"name": "JavaScript", "level": "expert", "years": 6, "category": "Programming"},
            {"name": "Python", "level": "advanced", "years": 4, "category": "Programming"},
            {"name": "React", "level": "expert", "years": 5, "category": "Frontend"},
            {"name": "Next.js", "level": "advanced", "years": 3, "category": "Frontend"},
            {"name": "Vue.js", "level": "intermediate", "years": 2, "category": "Frontend"},
            {"name": "Node.js", "level": "advanced", "years": 4, "category": "Backend"},
            {"name": "FastAPI", "level": "advanced", "years": 2, "category": "Backend"},
            {"name": "PostgreSQL", "level": "advanced", "years": 4, "category": "Database"},
            {"name": "GraphQL", "level": "advanced", "years": 3, "category": "API"},
            {"name": "Tailwind CSS", "level": "expert", "years": 3, "category": "Frontend"},
            {"name": "Testing (Jest/Pytest)", "level": "advanced", "years": 4, "category": "Quality"},
        ],
        "experiences": [
            {
                "title": "Full Stack Developer",
                "company": "WebCraft Studios",
                "start_date": "2020-08",
                "end_date": None,
                "description": "Lead developer for client projects ranging from e-commerce to SaaS platforms.",
                "achievements": [
                    "Delivered 15+ production applications for clients across various industries",
                    "Implemented component library reducing development time by 30%",
                    "Built real-time collaboration features using WebSockets",
                    "Achieved 95+ Lighthouse scores on all delivered projects",
                ],
            },
            {
                "title": "Frontend Developer",
                "company": "DigitalFirst Agency",
                "start_date": "2018-03",
                "end_date": "2020-07",
                "description": "Frontend specialist building responsive web applications.",
                "achievements": [
                    "Migrated legacy jQuery codebase to React, improving performance 3x",
                    "Introduced TypeScript adoption across team of 8 developers",
                    "Created accessibility-first component patterns meeting WCAG 2.1 AA",
                ],
            },
        ],
        "education": [
            {
                "institution": "University of Texas at Austin",
                "degree": "B.S.",
                "field": "Computer Science",
                "start_date": "2014-08",
                "end_date": "2018-05",
                "gpa": "3.5",
                "achievements": [],
            },
        ],
        "certifications": [
            {"name": "Meta Frontend Developer Professional", "issuer": "Meta", "date_obtained": "2022-06"},
        ],
        "languages": [
            {"language": "English", "proficiency": "native"},
        ],
    },
    {
        "slug": "devops-focus",
        "name": "DevOps Specialist",
        "title": "DevOps Engineer",
        "email": "devops.eng@example.com",
        "phone": "+1-555-0103",
        "location": "Seattle, WA",
        "summary": "DevOps engineer with 5 years of experience building and maintaining cloud infrastructure. Expert in Kubernetes, Terraform, and CI/CD pipelines. Focused on reliability, automation, and enabling development teams to ship faster with confidence.",
        "is_active": False,
        "is_demo": True,
        "skills": [
            {"name": "Kubernetes", "level": "expert", "years": 4, "category": "Orchestration"},
            {"name": "Terraform", "level": "expert", "years": 4, "category": "IaC"},
            {"name": "AWS", "level": "expert", "years": 5, "category": "Cloud"},
            {"name": "GCP", "level": "advanced", "years": 3, "category": "Cloud"},
            {"name": "Docker", "level": "expert", "years": 5, "category": "Containers"},
            {"name": "Python", "level": "advanced", "years": 4, "category": "Programming"},
            {"name": "Bash/Shell", "level": "expert", "years": 6, "category": "Programming"},
            {"name": "GitHub Actions", "level": "expert", "years": 3, "category": "CI/CD"},
            {"name": "ArgoCD", "level": "advanced", "years": 2, "category": "CI/CD"},
            {"name": "Prometheus/Grafana", "level": "advanced", "years": 3, "category": "Monitoring"},
            {"name": "Helm", "level": "advanced", "years": 3, "category": "Orchestration"},
            {"name": "Linux Administration", "level": "expert", "years": 6, "category": "Systems"},
        ],
        "experiences": [
            {
                "title": "Senior DevOps Engineer",
                "company": "CloudNative Corp",
                "start_date": "2022-01",
                "end_date": None,
                "description": "Lead infrastructure engineer for multi-region Kubernetes platform.",
                "achievements": [
                    "Designed and implemented multi-region K8s platform serving 200+ microservices",
                    "Reduced infrastructure costs by 40% through right-sizing and spot instances",
                    "Achieved 99.99% uptime SLA through automated failover and monitoring",
                    "Implemented GitOps workflow reducing deployment errors by 80%",
                ],
            },
            {
                "title": "DevOps Engineer",
                "company": "ScaleUp Technologies",
                "start_date": "2019-06",
                "end_date": "2021-12",
                "description": "Built and maintained CI/CD infrastructure for SaaS platform.",
                "achievements": [
                    "Migrated on-premise infrastructure to AWS, reducing ops burden by 60%",
                    "Implemented infrastructure-as-code with Terraform for all environments",
                    "Built automated security scanning into CI pipeline",
                ],
            },
        ],
        "education": [
            {
                "institution": "University of Washington",
                "degree": "B.S.",
                "field": "Information Systems",
                "start_date": "2015-09",
                "end_date": "2019-06",
                "gpa": "3.6",
                "achievements": [],
            },
        ],
        "certifications": [
            {"name": "AWS Solutions Architect - Professional", "issuer": "Amazon Web Services", "date_obtained": "2022-08"},
            {"name": "Certified Kubernetes Administrator (CKA)", "issuer": "CNCF", "date_obtained": "2021-03"},
            {"name": "HashiCorp Terraform Associate", "issuer": "HashiCorp", "date_obtained": "2021-09"},
        ],
        "languages": [
            {"language": "English", "proficiency": "native"},
            {"language": "Mandarin", "proficiency": "conversational"},
        ],
    },
]
```

---

### Part 5: DatabaseService Interface

**File:** `src/services/database/service.py` (REWRITE)

#### Class Signature

```python
class DatabaseService:
    """SQLite persistence for users, profiles, and applications."""

    def __init__(self, db_path: Path | None = None):
        """Initialize with optional custom database path.
        
        Default: data/scout.db
        """
        
    async def initialize(self) -> None:
        """Create tables and seed demo data if needed."""
        
    async def shutdown(self) -> None:
        """Close database connection."""

    # === User Operations ===
    
    async def get_user(self, user_id: int) -> User:
        """Get user by ID. Raises UserNotFoundError if not found."""
        
    async def get_user_by_username(self, username: str) -> User | None:
        """Get user by username. Returns None if not found."""
        
    async def get_current_user(self) -> User:
        """Get the current user (Test User for PoC).
        
        In future, this will use session/auth context.
        For now, returns the single test user.
        """
        
    async def create_user(self, data: UserCreate) -> User:
        """Create a new user."""
        
    async def update_user(self, user_id: int, data: UserUpdate) -> User:
        """Update user fields."""

    # === Profile Operations ===
    
    async def list_profiles(self, user_id: int | None = None) -> list[ProfileSummary]:
        """List profiles for a user (or current user if not specified).
        
        Returns ProfileSummary with stats (skill_count, application_count, etc.)
        """
        
    async def get_profile(self, profile_id: int) -> Profile:
        """Get full profile with all related data."""
        
    async def get_profile_by_slug(self, slug: str) -> Profile:
        """Get full profile by slug. Raises ProfileNotFoundError if not found."""
        
    async def get_active_profile(self, user_id: int | None = None) -> Profile | None:
        """Get the active profile for a user. Returns None if no active profile."""
        
    async def create_profile(self, user_id: int, data: ProfileCreate) -> Profile:
        """Create a new profile with all related data.
        
        Auto-generates slug from name if not provided.
        """
        
    async def update_profile(self, slug: str, data: ProfileUpdate) -> Profile:
        """Update profile - replaces provided fields and related data.
        
        If skills/experiences/etc. are provided, they REPLACE existing data.
        If not provided (None), existing data is preserved.
        """
        
    async def delete_profile(self, slug: str) -> None:
        """Delete profile and all related data. Raises ProfileNotFoundError if not found."""
        
    async def activate_profile(self, slug: str) -> Profile:
        """Set profile as active, deactivating others for the same user.
        
        Returns the activated profile.
        Triggers vector store re-indexing (via event/callback).
        """
        
    async def get_profile_completeness(self, slug: str) -> ProfileCompleteness:
        """Calculate and return profile completeness score."""

    # === Application Operations ===
    
    async def list_applications(
        self,
        user_id: int | None = None,
        profile_id: int | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Application], int]:
        """List applications with pagination.
        
        Can filter by user_id (all user's applications) or profile_id (specific profile).
        Returns (applications, total_count).
        """
        
    async def get_application(self, job_id: str) -> Application:
        """Get application by job_id. Raises ApplicationNotFoundError if not found."""
        
    async def create_application(self, data: ApplicationCreate) -> Application:
        """Create a new application record."""
        
    async def update_application(self, job_id: str, data: ApplicationUpdate) -> Application:
        """Update application status and results."""

    # === Internal Helpers ===
    
    async def _seed_demo_data(self) -> None:
        """Seed test user and demo profiles on first run."""
        
    async def _load_profile_relations(self, profile_id: int) -> dict:
        """Load skills, experiences, etc. for a profile."""
        
    async def _save_profile_relations(self, profile_id: int, data: ProfileCreate | ProfileUpdate) -> None:
        """Save/replace related data for a profile."""
        
    def _generate_slug(self, name: str) -> str:
        """Generate URL-safe slug from name."""
```

---

### Part 6: Exceptions

**File:** `src/services/database/exceptions.py` (UPDATE)

```python
"""Database service exceptions."""

class DatabaseError(Exception):
    """Base exception for database operations."""
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

class ApplicationNotFoundError(DatabaseError):
    """Application not found in database."""
    def __init__(self, job_id: str):
        self.job_id = job_id
        super().__init__(f"Application not found: {job_id}")

class NoActiveProfileError(DatabaseError):
    """No active profile set for user."""
    def __init__(self, user_id: int):
        self.user_id = user_id
        super().__init__(f"No active profile for user: {user_id}")
```

---

### Part 7: Public Exports

**File:** `src/services/database/__init__.py` (UPDATE)

```python
"""Database service - SQLite persistence for users, profiles, and applications."""

from .service import DatabaseService, get_database_service
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
    Experience,
    ExperienceCreate,
    Education,
    EducationCreate,
    Certification,
    CertificationCreate,
    Language,
    LanguageCreate,
    # Profile
    Profile,
    ProfileCreate,
    ProfileUpdate,
    ProfileSummary,
    # Completeness
    ProfileCompleteness,
    CompletenessSection,
    # Application
    Application,
    ApplicationCreate,
    ApplicationUpdate,
)
from .exceptions import (
    DatabaseError,
    UserNotFoundError,
    ProfileNotFoundError,
    ProfileSlugExistsError,
    ApplicationNotFoundError,
    NoActiveProfileError,
)
from .completeness import calculate_completeness

__all__ = [
    # Service
    "DatabaseService",
    "get_database_service",
    # Enums
    "SkillLevel",
    "LanguageProficiency", 
    "ApplicationStatus",
    # Models
    "User",
    "UserCreate",
    "Skill",
    "SkillCreate",
    "Experience",
    "ExperienceCreate",
    "Education",
    "EducationCreate",
    "Certification",
    "CertificationCreate",
    "Language",
    "LanguageCreate",
    "Profile",
    "ProfileCreate",
    "ProfileUpdate",
    "ProfileSummary",
    "ProfileCompleteness",
    "CompletenessSection",
    "Application",
    "ApplicationCreate",
    "ApplicationUpdate",
    # Functions
    "calculate_completeness",
    # Exceptions
    "DatabaseError",
    "UserNotFoundError",
    "ProfileNotFoundError",
    "ProfileSlugExistsError",
    "ApplicationNotFoundError",
    "NoActiveProfileError",
]
```

---

### Part 8: Test Requirements

**File:** `tests/services/database/` structure

```
tests/services/database/
├── __init__.py
├── conftest.py              # Fixtures (temp db, test user, test profiles)
├── test_service_user.py     # User CRUD tests
├── test_service_profile.py  # Profile CRUD tests
├── test_service_relations.py # Skills, experiences, etc. tests
├── test_service_application.py # Application tests
├── test_completeness.py     # Completeness scoring tests
└── test_demo_data.py        # Demo data seeding tests
```

#### Key Test Cases

```python
# test_service_user.py
- test_create_user
- test_get_user_by_id
- test_get_user_by_username
- test_get_current_user_returns_test_user
- test_user_not_found_raises_error

# test_service_profile.py
- test_create_profile_minimal
- test_create_profile_with_all_fields
- test_create_profile_auto_generates_slug
- test_create_profile_duplicate_slug_raises_error
- test_get_profile_by_slug
- test_get_profile_includes_relations
- test_list_profiles_returns_summaries
- test_list_profiles_includes_stats
- test_update_profile_basic_fields
- test_update_profile_replaces_skills
- test_update_profile_preserves_unset_relations
- test_delete_profile_cascades
- test_delete_profile_not_found_raises_error

# test_service_relations.py
- test_profile_skills_crud
- test_profile_experiences_crud
- test_profile_education_crud
- test_profile_certifications_crud
- test_profile_languages_crud
- test_relations_deleted_with_profile

# test_service_application.py
- test_create_application
- test_update_application_status
- test_list_applications_by_user
- test_list_applications_by_profile
- test_application_links_to_user_and_profile

# test_completeness.py
- test_completeness_empty_profile
- test_completeness_minimal_profile
- test_completeness_full_profile
- test_completeness_levels (excellent, good, fair, needs_work)
- test_completeness_suggestions_prioritized
- test_completeness_section_scores

# test_demo_data.py
- test_demo_data_seeded_on_init
- test_test_user_created
- test_three_demo_profiles_created
- test_backend_focus_is_active
- test_demo_profiles_have_complete_data
```

---