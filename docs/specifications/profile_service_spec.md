# Profile System Expansion - Claude Code Implementation Specification
## **Local-First Architecture Edition**

## Context & Overview

You are expanding the user profile system for Scout, an AI-powered job application automation system running **entirely on local hardware** with Ollama-based LLM inference. The current system uses a single `data/profile.yaml` file. This expansion adds **multi-profile management, compatibility scoring, and enhanced CRUD operations** while maintaining local-first architecture and PoC simplicity.

**Project Location**: Scout PoC codebase  
**Module**: Profile Management System (Expansion)  
**Dependencies**: Existing profile system (Collector module), ChromaDB vector store, Ollama (qwen2.5:3b), YAML file storage, diagnostic API infrastructure

## Current State

The Scout PoC has:
- Single profile loaded from `data/profile.yaml`
- Collector module handles profile loading and indexing
- ChromaDB stores profile embeddings for semantic matching
- Ollama provides local LLM inference (qwen2.5:3b model)
- Comprehensive diagnostic API endpoints (`/api/diagnostics`, `/api/diagnostics/profile`, etc.)
- Pipeline modules: Collector, Rinser, Analyzer, Creator, Formatter

**Existing Profile Structure** (`data/profile.yaml`):
```yaml
name: "Alex Jensen"
email: "alex@example.com"
title: "Senior Backend Developer"
years_experience: 5.0
skills: [...]
experience: [...]
education: [...]
certifications: [...]
```

## Objective

Extend the profile system to support:
1. **Multi-profile management** with file-based storage
2. **Active profile selection** with per-application override
3. **Compatibility scoring** using local vector similarity (LLM optional)
4. **Enhanced profile viewing** (YAML, formatted, chunks)
5. **Usage statistics** tracked in SQLite
6. **Profile lifecycle** (duplicate, archive, restore)
7. **Diagnostic endpoints** for profile validation

## Success Criteria

- [ ] Users can create, read, update, archive multiple profile YAML files
- [ ] One profile designated as "active" (symlinked to `data/profile.yaml`)
- [ ] Profile list page shows all profiles with key statistics
- [ ] Compatibility score calculates job-profile match using vector similarity (0-100%)
- [ ] Optional LLM-enhanced analysis for deep insights (user accepts latency)
- [ ] Profile usage stats track applications generated and avg scores
- [ ] Quick profile switcher in app header for seamless switching
- [ ] Application generation allows profile override via dropdown
- [ ] Archive/restore prevents accidental data loss
- [ ] Diagnostic endpoints validate profile integrity

## Technical Specifications

### File System Structure

**Profile Storage**:
```
/data
  /profiles
    active.yaml                    # Symlink to current active profile
    alex_senior_backend.yaml       # Individual profile files
    alex_junior_fullstack.yaml
    alex_freelancer.yaml
    .archived/                     # Archived profiles
      old_profile_20250101.yaml
```

**Profile Metadata Database** (SQLite - for statistics only):
```sql
CREATE TABLE profile_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename VARCHAR(255) UNIQUE NOT NULL,  -- e.g., "alex_senior_backend.yaml"
    profile_name VARCHAR(100) NOT NULL,     -- From YAML "name" field
    is_active BOOLEAN DEFAULT FALSE,
    is_archived BOOLEAN DEFAULT FALSE,
    file_hash VARCHAR(64),                  -- SHA256 for change detection
    indexed_at TIMESTAMP,                   -- Last ChromaDB indexing
    usage_count INTEGER DEFAULT 0,
    avg_compatibility_score DECIMAL(5,2),
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX idx_active_profile ON profile_metadata(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_archived ON profile_metadata(is_archived);
```

**Why Hybrid Approach?**
- YAML files: Source of truth, human-readable, git-friendly, portable
- SQLite metadata: Fast queries for stats, listing, sorting
- ChromaDB: Vector embeddings for semantic search
- Symlink pattern: Backward compatible with existing `profile.yaml` loading

### Database Schema

#### 1. Profile Metadata Table (above)

#### 2. Compatibility Scores Table

```sql
CREATE TABLE compatibility_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_filename VARCHAR(255) NOT NULL,
    job_id INTEGER NOT NULL,
    overall_score DECIMAL(5,2) NOT NULL,
    skills_match_score DECIMAL(5,2),
    experience_match_score DECIMAL(5,2),
    domain_match_score DECIMAL(5,2),
    matched_chunks TEXT,              -- JSON array of matched sections
    missing_requirements TEXT,        -- JSON array of unmatched requirements
    recommendation VARCHAR(20),       -- 'strong' | 'good' | 'weak' | 'poor'
    calculation_method VARCHAR(20),   -- 'vector' | 'llm_enhanced'
    compute_time_ms INTEGER,          -- Track inference time, not cost
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,             -- 7-day cache (compute-expensive)
    FOREIGN KEY (profile_filename) REFERENCES profile_metadata(filename),
    UNIQUE(profile_filename, job_id)
);

CREATE INDEX idx_compatibility_expires ON compatibility_scores(expires_at);
CREATE INDEX idx_compatibility_profile ON compatibility_scores(profile_filename);
```

**Cache Duration Rationale**:
- 7 days instead of 24 hours (computation expensive, not API costs)
- Invalidate on profile file changes (detected via file_hash)
- Longer cache reduces thermal load on Pi 5

#### 3. Profile Usage Log Table

```sql
CREATE TABLE profile_usage_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_filename VARCHAR(255) NOT NULL,
    job_id INTEGER NOT NULL,
    action_type VARCHAR(50) NOT NULL,  -- 'compatibility_check' | 'application_generated'
    compatibility_score DECIMAL(5,2),
    compute_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (profile_filename) REFERENCES profile_metadata(filename)
);

CREATE INDEX idx_usage_profile ON profile_usage_log(profile_filename);
CREATE INDEX idx_usage_date ON profile_usage_log(created_at);
```

### API Endpoints

#### Profile Management Endpoints

##### 1. GET `/api/profiles`

**Purpose**: List all profiles (excludes archived unless requested)

**Query Params**:
- `include_archived` (boolean, default: false)
- `sort_by` (string: 'name' | 'created' | 'usage' | 'score', default: 'created')
- `sort_order` (string: 'asc' | 'desc', default: 'desc')

**Response**:
```json
{
    "profiles": [
        {
            "filename": "alex_senior_backend.yaml",
            "profile_name": "Alex Jensen",
            "title": "Senior Backend Developer",
            "is_active": true,
            "is_archived": false,
            "years_experience": 5.0,
            "skill_count": 15,
            "usage_count": 23,
            "avg_compatibility_score": 78.5,
            "last_used_at": "2025-12-14T10:30:00Z",
            "created_at": "2025-12-01T09:00:00Z",
            "updated_at": "2025-12-10T14:20:00Z",
            "indexed": true
        }
    ],
    "active_profile": "alex_senior_backend.yaml",
    "total_count": 4,
    "archived_count": 1
}
```

##### 2. GET `/api/profiles/{filename}`

**Purpose**: Get detailed profile information

**Response**:
```json
{
    "filename": "alex_senior_backend.yaml",
    "profile_data": {
        "name": "Alex Jensen",
        "email": "alex@example.com",
        "title": "Senior Backend Developer",
        "years_experience": 5.0,
        "skills": [...],
        "experience": [...],
        "education": [...],
        "certifications": [...]
    },
    "metadata": {
        "is_active": true,
        "is_archived": false,
        "indexed": true,
        "indexed_at": "2025-12-14T08:00:00Z",
        "usage_count": 23,
        "avg_compatibility_score": 78.5,
        "last_used_at": "2025-12-14T10:30:00Z"
    },
    "chunks": [
        {
            "index": 0,
            "text": "5+ years of Python backend development...",
            "source": "experience[0]"
        }
    ]
}
```

##### 3. POST `/api/profiles`

**Purpose**: Create new profile from YAML content or uploaded file

**Request Body** (Option A - Direct YAML):
```json
{
    "filename": "alex_freelancer.yaml",
    "yaml_content": "name: Alex Jensen\nemail: ...",
    "set_as_active": true
}
```

**Request Body** (Option B - File Upload):
```
Content-Type: multipart/form-data
file: profile.yaml
set_as_active: true
```

**Validation**:
- Filename: Must end in `.yaml`, unique, safe characters only
- YAML: Valid syntax, required fields (name, email, skills)
- Auto-generate filename if not provided: `{name_slug}_{timestamp}.yaml`

**Process**:
1. Validate YAML structure
2. Write to `/data/profiles/{filename}`
3. Calculate file hash (SHA256)
4. Insert metadata into SQLite
5. If `set_as_active=true`, update symlink and deactivate others
6. Trigger background indexing via Collector module
7. Return created profile

**Response**:
```json
{
    "filename": "alex_freelancer.yaml",
    "profile_name": "Alex Jensen",
    "is_active": true,
    "indexed": false,
    "created_at": "2025-12-14T11:00:00Z"
}
```

##### 4. PUT `/api/profiles/{filename}`

**Purpose**: Update existing profile

**Request Body**:
```json
{
    "yaml_content": "name: Alex Jensen\n...",  // Optional - update content
    "set_as_active": true                       // Optional - change active status
}
```

**Process**:
1. Validate YAML if content provided
2. If content changed:
   - Write to file
   - Update file_hash
   - Clear ChromaDB embeddings for old version
   - Trigger re-indexing
   - Invalidate all compatibility scores
3. If `set_as_active` changed:
   - Update symlink
   - Deactivate other profiles
4. Update metadata in SQLite
5. Return updated profile

**Response**: Same as GET `/api/profiles/{filename}`

##### 5. POST `/api/profiles/{filename}/duplicate`

**Purpose**: Clone profile as starting point for variant

**Request Body**:
```json
{
    "new_filename": "alex_healthcare_specialist.yaml"  // Optional
}
```

**Process**:
1. Read source profile YAML
2. Auto-generate filename if not provided: `{original}_copy_{timestamp}.yaml`
3. Write to new file
4. Insert metadata (reset usage stats)
5. Mark as not active, not indexed
6. Trigger indexing
7. Return new profile

**Response**: Same as POST `/api/profiles`

##### 6. POST `/api/profiles/{filename}/archive`

**Purpose**: Archive profile (soft delete)

**Process**:
1. Move file to `/data/profiles/.archived/`
2. Set `is_archived=true` in metadata
3. If was active, deactivate (no auto-activation of another)
4. Remove embeddings from ChromaDB
5. Keep compatibility scores (for history)
6. Return success

**Response**:
```json
{
    "success": true,
    "filename": "alex_old_profile.yaml",
    "archived_path": ".archived/alex_old_profile.yaml",
    "archived_at": "2025-12-14T12:00:00Z"
}
```

##### 7. POST `/api/profiles/{filename}/restore`

**Purpose**: Restore archived profile

**Process**:
1. Move file from `.archived/` back to `/data/profiles/`
2. Set `is_archived=false`
3. Trigger re-indexing
4. Return restored profile

**Response**: Same as GET `/api/profiles/{filename}`

##### 8. POST `/api/profiles/{filename}/activate`

**Purpose**: Set profile as active

**Process**:
1. Deactivate all other profiles
2. Update symlink `data/profiles/active.yaml` → `{filename}`
3. Set `is_active=true` in metadata
4. Reload Collector module (optional, or wait for next startup)
5. Return success

**Response**:
```json
{
    "success": true,
    "active_profile": "alex_senior_backend.yaml",
    "previous_active": "alex_junior_fullstack.yaml",
    "collector_reloaded": true
}
```

##### 9. DELETE `/api/profiles/{filename}`

**Purpose**: Permanently delete profile (requires confirmation)

**Query Param**: `confirm=true` (safety check)

**Process**:
1. Verify not active (refuse to delete active profile)
2. Delete file from disk
3. Delete metadata from SQLite
4. Delete embeddings from ChromaDB
5. Delete compatibility scores
6. Delete usage logs
7. Return success

**Response**:
```json
{
    "success": true,
    "filename": "alex_old_profile.yaml",
    "deleted_at": "2025-12-14T13:00:00Z"
}
```

#### Compatibility Scoring Endpoints

##### 10. POST `/api/compatibility/check`

**Purpose**: Calculate compatibility score between profile and job (LOCAL VECTOR-ONLY FOR POC)

**Request Body**:
```json
{
    "profile_filename": "alex_senior_backend.yaml",
    "job_id": 42,
    "method": "vector"  // 'vector' (default, fast) | 'llm_enhanced' (slow, user warned)
}
```

**Process**:

**Step 1: Check Cache**
- Query `compatibility_scores` for profile + job
- If found and not expired (7 days), return cached
- If expired, delete and proceed

**Step 2: Vector Similarity Calculation** (ALWAYS RUNS)

1. **Fetch job posting** from database
2. **Chunk job posting** (paragraph-based, same as profile)
3. **Embed job chunks** via sentence-transformers (local model)
4. **Query ChromaDB** for profile chunks similar to job chunks
5. **Calculate scores**:
   ```python
   # Overall: Average of top-5 best-matching profile chunks
   overall_score = mean([max(similarities) for job_chunk in job_chunks])
   
   # Component scores (heuristic-based for PoC)
   skills_chunks = [c for c in job_chunks if contains_skill_keywords(c)]
   skills_score = mean([max_similarity(c, profile_chunks) for c in skills_chunks])
   
   experience_chunks = [c for c in job_chunks if contains_experience_keywords(c)]
   experience_score = mean([max_similarity(c, profile_chunks) for c in experience_chunks])
   
   # Domain: Keyword overlap approach
   domain_keywords = extract_domain_keywords(job_text)
   domain_score = percentage_keywords_in_profile(domain_keywords, profile_chunks)
   ```
6. **Identify matched chunks** (similarity > 0.7)
7. **Identify missing requirements** (no chunk > 0.6 similarity)
8. **Determine recommendation**:
   - Strong Match: 80-100%
   - Good Match: 60-79%
   - Weak Match: 40-59%
   - Poor Match: 0-39%

**Step 3: LLM-Enhanced Analysis** (OPTIONAL - Only if `method='llm_enhanced'`)

**WARNING TO USER**: "This analysis may take 30-90 seconds on Raspberry Pi, or 10-30 seconds on development machine."

1. **Prepare prompt**:
```
Analyze job-candidate compatibility.

Job Posting:
{job_text}

Candidate Profile Highlights (Top Matches):
{top_5_matched_chunks}

Vector Similarity Scores:
- Overall: {overall_score}%
- Skills: {skills_score}%
- Experience: {experience_score}%

Provide JSON:
{
    "adjusted_score": float (0-100),
    "recommendation": "strong|good|weak|poor",
    "strengths": [str],
    "gaps": [str],
    "brief_analysis": str (max 200 words)
}
```

2. **Call Ollama** (qwen2.5:3b) via local endpoint
3. **Parse JSON response** (with fallback if parsing fails)
4. **Track compute time** (not cost)

**Step 4: Cache Result**
1. Insert into `compatibility_scores`
2. Set `expires_at = now + 7 days`
3. Log usage in `profile_usage_log`
4. Track compute time

**Response**:
```json
{
    "profile_filename": "alex_senior_backend.yaml",
    "job_id": 42,
    "overall_score": 78.5,
    "component_scores": {
        "skills_match": 85.0,
        "experience_match": 75.0,
        "domain_match": 68.0
    },
    "recommendation": "good",
    "matched_chunks": [
        {
            "chunk_index": 2,
            "text": "5+ years Python backend development with FastAPI...",
            "similarity": 0.89,
            "source": "experience[0]"
        }
    ],
    "missing_requirements": [
        "Healthcare domain experience",
        "HIPAA compliance knowledge"
    ],
    "calculation_method": "vector",
    "compute_time_ms": 2340,
    "cached": false,
    "calculated_at": "2025-12-14T12:30:00Z",
    "llm_analysis": null  // Only populated if method='llm_enhanced'
}
```

**LLM-Enhanced Response** (when requested):
```json
{
    // ... same as above, plus:
    "llm_analysis": {
        "adjusted_score": 82.0,  // LLM may adjust vector score
        "strengths": [
            "Strong Python and FastAPI expertise aligns perfectly with tech stack",
            "Extensive experience with REST APIs and microservices architecture"
        ],
        "gaps": [
            "No healthcare domain experience mentioned",
            "Limited cloud infrastructure experience visible"
        ],
        "brief_analysis": "The candidate shows excellent technical alignment with the role's requirements. Their 5+ years of Python backend development and specific FastAPI experience are ideal matches. However, the role's healthcare focus may require domain knowledge that isn't evident in the profile. Consider emphasizing any healthcare projects or HIPAA-related work if applicable."
    },
    "compute_time_ms": 45230  // Much longer with LLM
}
```

##### 11. GET `/api/profiles/{filename}/statistics`

**Purpose**: Get usage statistics for profile

**Response**:
```json
{
    "profile_filename": "alex_senior_backend.yaml",
    "profile_name": "Alex Jensen",
    "usage_count": 23,
    "compatibility_checks": 47,
    "applications_generated": 23,
    "avg_compatibility_score": 78.5,
    "score_distribution": {
        "strong": 8,
        "good": 12,
        "weak": 3,
        "poor": 0
    },
    "last_used_at": "2025-12-14T10:30:00Z",
    "most_common_job_titles": [
        "Senior Backend Developer",
        "Lead Software Engineer",
        "Python Tech Lead"
    ],
    "avg_compute_time_ms": 2450
}
```

#### Diagnostic Endpoints (Following Existing Pattern)

##### 12. GET `/api/diagnostics/profiles`

**Purpose**: Validate all profiles' integrity and indexing status

**Response**:
```json
{
    "overall": "ok" | "degraded",
    "active_profile": "alex_senior_backend.yaml",
    "profiles": [
        {
            "filename": "alex_senior_backend.yaml",
            "status": "ok" | "warning" | "error",
            "is_active": true,
            "file_exists": true,
            "yaml_valid": true,
            "indexed": true,
            "chunk_count": 12,
            "last_indexed": "2025-12-14T08:00:00Z",
            "file_hash_match": true,
            "issues": []
        }
    ],
    "total_profiles": 4,
    "profiles_needing_reindex": 0,
    "archived_profiles": 1
}
```

**Status Meanings**:
- `ok`: File exists, YAML valid, indexed, hash matches
- `warning`: File exists but needs re-indexing (hash mismatch)
- `error`: File missing, YAML corrupt, or indexing failed

##### 13. POST `/api/diagnostics/profiles/{filename}/reindex`

**Purpose**: Force re-indexing of specific profile

**Response**:
```json
{
    "success": true,
    "filename": "alex_senior_backend.yaml",
    "chunks_created": 12,
    "duration_ms": 3450,
    "indexed_at": "2025-12-14T14:30:00Z"
}
```

##### 14. POST `/api/diagnostics/profiles/reindex-all`

**Purpose**: Re-index all non-archived profiles (admin operation)

**Response**:
```json
{
    "success": true,
    "profiles_processed": 4,
    "total_chunks": 48,
    "total_duration_ms": 14200,
    "errors": []
}
```

##### 15. GET `/api/diagnostics/profiles/{filename}/validate`

**Purpose**: Deep validation of profile structure and content

**Response**:
```json
{
    "filename": "alex_senior_backend.yaml",
    "valid": true,
    "checks": [
        {
            "check": "file_exists",
            "passed": true,
            "message": "File found at /data/profiles/alex_senior_backend.yaml"
        },
        {
            "check": "yaml_syntax",
            "passed": true,
            "message": "YAML parses correctly"
        },
        {
            "check": "required_fields",
            "passed": true,
            "message": "All required fields present: name, email, skills"
        },
        {
            "check": "skills_array",
            "passed": true,
            "message": "Found 15 skills"
        },
        {
            "check": "experience_array",
            "passed": true,
            "message": "Found 3 experience entries"
        },
        {
            "check": "indexed_in_chromadb",
            "passed": true,
            "message": "12 chunks found in vector store"
        },
        {
            "check": "file_hash_current",
            "passed": true,
            "message": "File unchanged since last index"
        }
    ],
    "warnings": [],
    "errors": []
}
```

### Frontend Components & Pages

#### 1. Profile List Page (`/profiles`)

**Route**: `/profiles`

**Layout**:
```
┌─────────────────────────────────────────────┐
│  Your Profiles                [+ New Profile]│
├─────────────────────────────────────────────┤
│  🟢 Active: alex_senior_backend.yaml         │
├─────────────────────────────────────────────┤
│  Sort by: [Usage ▼]  [Show Archived ☐]      │
├─────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────┐│
│  │ 🟢 Alex Jensen                   [⋮]    ││
│  │ Senior Backend Developer                ││
│  │ alex_senior_backend.yaml                ││
│  │ 15 skills • 5.0 yrs exp • ✓ Indexed     ││
│  │ Used 23 times • Avg score: 78.5%        ││
│  │ Last used: 2 hours ago                  ││
│  │ [View] [Edit] [Check Compatibility]     ││
│  └─────────────────────────────────────────┘│
│                                              │
│  ┌─────────────────────────────────────────┐│
│  │ ⚪ Alex Jensen                   [⋮]    ││
│  │ Junior Fullstack Developer              ││
│  │ alex_junior_fullstack.yaml              ││
│  │ 8 skills • 2.0 yrs exp • ⚠ Needs Reindex││
│  │ Used 5 times • Avg score: 64.2%         ││
│  │ Last used: 5 days ago                   ││
│  │ [View] [Edit] [Set Active]              ││
│  └─────────────────────────────────────────┘│
└─────────────────────────────────────────────┘
```

**Features**:
- Profile cards showing YAML filename + parsed name/title
- Visual active indicator (green dot)
- Indexing status badge (✓ Indexed | ⚠ Needs Reindex | ❌ Not Indexed)
- Sort controls (usage, score, created date, name)
- Toggle to show archived profiles
- Quick actions menu (⋮):
  - Set as Active
  - Duplicate
  - Archive
  - Restore (if archived)
  - Delete (with confirmation)
- Empty state: "Create your first profile to get started"

#### 2. Profile Detail/View Page (`/profiles/{filename}`)

**Route**: `/profiles/{filename}`

**Layout**:
```
┌─────────────────────────────────────────────────────┐
│  ← Back to Profiles                                  │
├─────────────────────────────────────────────────────┤
│  Alex Jensen                       🟢 Active Profile │
│  Senior Backend Developer                            │
│  alex_senior_backend.yaml                            │
│  [Edit YAML] [Duplicate] [Set Active] [Archive]      │
├─────────────────────────────────────────────────────┤
│  📊 Statistics                                       │
│  • Used in 23 applications                           │
│  • Average compatibility: 78.5%                      │
│  • Avg compute time: 2.4s                            │
│  • Last used: 2 hours ago                            │
│  • Created: Dec 1, 2025                              │
│  • Indexed: ✓ (12 chunks, Dec 14 08:00)             │
├─────────────────────────────────────────────────────┤
│  📝 Profile Content                                  │
│  [Formatted] [YAML Source] [Indexed Chunks]          │
│                                                       │
│  ┌───────────────────────────────────────────────┐  │
│  │ Name: Alex Jensen                              │  │
│  │ Email: alex@example.com                        │  │
│  │ Title: Senior Backend Developer                │  │
│  │ Experience: 5.0 years                           │  │
│  │                                                 │  │
│  │ Skills:                                         │  │
│  │ • Python, FastAPI, Django                       │  │
│  │ • PostgreSQL, Redis, MongoDB                    │  │
│  │ • Docker, Kubernetes, AWS                       │  │
│  │ [... 15 skills total ...]                       │  │
│  │                                                 │  │
│  │ Experience:                                     │  │
│  │ Senior Backend Developer @ TechCorp             │  │
│  │ 2020-Present • Copenhagen, Denmark              │  │
│  │ • Built microservices architecture...           │  │
│  │ [... experience entries ...]                    │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

**View Modes**:

**Formatted View** (Default):
- Structured display of YAML fields
- Readable sections (Skills, Experience, Education, etc.)
- Easy scanning

**YAML Source View**:
- Raw YAML file content
- Monospace font with syntax highlighting
- "Copy to Clipboard" button
- "Download" button

**Indexed Chunks View**:
- Shows how Collector chunked the profile
- Each chunk with index, source field, similarity preview
- Helps users understand semantic matching

**Actions**:
- "Edit YAML": Opens editor (or downloads for external editing)
- "Validate Profile": Runs diagnostic check
- "Force Reindex": Triggers re-indexing

#### 3. Profile Create/Edit Page (`/profiles/create` and `/profiles/{filename}/edit`)

**Route**: `/profiles/create` or `/profiles/{filename}/edit`

**Two Creation Methods**:

**Method A: Upload YAML File**
```
┌─────────────────────────────────────────────────────┐
│  Create New Profile                  [Cancel] [Save]│
├─────────────────────────────────────────────────────┤
│  Upload Profile YAML                                 │
│  ┌───────────────────────────────────────────────┐  │
│  │  [📁 Click or drag YAML file here]            │  │
│  └───────────────────────────────────────────────┘  │
│  Or use a template: [Junior Dev] [Senior Dev] [Lead]│
│                                                       │
│  ☐ Set as active profile                             │
│  [Cancel] [Upload & Index]                           │
└─────────────────────────────────────────────────────┘
```

**Method B: Edit in Browser** (Advanced)
```
┌─────────────────────────────────────────────────────┐
│  Edit Profile YAML                   [Cancel] [Save]│
├─────────────────────────────────────────────────────┤
│  Filename: alex_senior_backend.yaml                  │
│                                                       │
│  ┌───────────────────────────────────────────────┐  │
│  │ name: "Alex Jensen"                            │  │
│  │ email: "alex@example.com"                      │  │
│  │ title: "Senior Backend Developer"              │  │
│  │ years_experience: 5.0                           │  │
│  │ skills:                                         │  │
│  │   - Python                                      │  │
│  │   - FastAPI                                     │  │
│  │   - ...                                         │  │
│  │ [Syntax-highlighted YAML editor]                │  │
│  └───────────────────────────────────────────────┘  │
│  ✓ YAML syntax valid                                 │
│  ☐ Set as active profile                             │
│  [Validate] [Cancel] [Save & Index]                  │
└─────────────────────────────────────────────────────┘
```

**Features**:
- **YAML editor** with syntax highlighting (Monaco or CodeMirror)
- **Real-time validation** (YAML syntax, required fields)
- **Template starters** for common profile types
- **File upload** for external editing workflow
- **Download template** button (provides example YAML)

**Validation Feedback**:
- ✓ YAML syntax valid
- ✓ Required fields present (name, email, skills)
- ⚠ Warning: No experience entries (still valid)
- ❌ Error: Invalid YAML syntax at line 12

#### 4. Compatibility Score Modal/Panel

**Trigger**: "Check Compatibility" button on job detail page

**Layout** (Modal):
```
┌─────────────────────────────────────────────────────┐
│  Compatibility Score                           [✕]  │
├─────────────────────────────────────────────────────┤
│  Job: Senior Backend Engineer @ TechCorp             │
│  Profile: alex_senior_backend.yaml                   │
│                                                       │
│  [Method: Vector Similarity ▼]                       │
│  (Alternative: LLM-Enhanced - may take 30-90s)       │
├─────────────────────────────────────────────────────┤
│                   78.5%                              │
│              Good Match ⭐⭐⭐                         │
│                                                       │
│  Calculated in 2.3 seconds                           │
├─────────────────────────────────────────────────────┤
│  Component Scores:                                   │
│  ━━━━━━━━━━━━━━━━━━━ 85% Required Skills            │
│  ━━━━━━━━━━━━━━━━━ 75% Experience Level             │
│  ━━━━━━━━━━━━━ 68% Domain Knowledge                 │
├─────────────────────────────────────────────────────┤
│  ✓ Strong Matches:                                   │
│  • "5+ years Python backend with FastAPI" (89%)      │
│    from experience[0]                                │
│  • "PostgreSQL, Redis, MongoDB expertise" (87%)      │
│    from skills                                       │
│  • "Docker & Kubernetes production experience" (84%) │
│    from experience[1]                                │
│                                                       │
│  ⚠ Potential Gaps:                                   │
│  • Healthcare domain experience (not found)          │
│  • HIPAA compliance knowledge (weak match: 42%)      │
├─────────────────────────────────────────────────────┤
│  [Get LLM-Enhanced Analysis] [Try Different Profile] │
│  [Generate Application]                              │
└─────────────────────────────────────────────────────┘
```

**LLM-Enhanced Analysis** (After user confirms latency):
```
┌─────────────────────────────────────────────────────┐
│  🤖 LLM-Enhanced Analysis                            │
│  ⏱ Processed in 42.3 seconds                        │
├─────────────────────────────────────────────────────┤
│  Adjusted Score: 82% (↑ from vector: 78.5%)         │
│                                                       │
│  Key Strengths:                                      │
│  • Strong Python and FastAPI expertise aligns        │
│    perfectly with the role's tech stack              │
│  • Extensive REST API and microservices experience   │
│    matches core responsibilities                     │
│                                                       │
│  Areas for Consideration:                            │
│  • Healthcare domain knowledge not evident in        │
│    profile - consider emphasizing any related work   │
│  • Limited cloud infrastructure mentions despite     │
│    strong DevOps skills                              │
│                                                       │
│  Brief Analysis:                                     │
│  The candidate shows excellent technical alignment   │
│  with 5+ years of Python backend development and     │
│  specific FastAPI experience. However, the role's    │
│  healthcare focus may benefit from domain knowledge  │
│  that isn't currently visible in the profile.        │
│  Consider highlighting any healthcare projects or    │
│  HIPAA-related work if applicable.                   │
├─────────────────────────────────────────────────────┤
│  [Generate Application] [Close]                      │
└─────────────────────────────────────────────────────┘
```

**Features**:
- **Method selector**: Vector (fast) vs LLM-Enhanced (slow, warned)
- **Compute time display**: Helps set expectations
- **Matched chunks**: Shows which profile sections matched
- **Source references**: Links to profile YAML sections
- **Missing requirements**: Clear gap analysis
- **LLM insights** (optional): Richer analysis with caveats

#### 5. Quick Profile Switcher (Header Component)

**Location**: Global app header (top-right)

**Layout**:
```
┌──────────────────────────────────┐
│  Scout                     [User]│
│                                   │
│  [🟢 alex_senior_backend.yaml ▼] │
└──────────────────────────────────┘
     │
     ▼ (Dropdown opens)
┌──────────────────────────────────┐
│  🟢 alex_senior_backend.yaml      │
│     Alex Jensen - Senior Backend  │
│     23 apps • 78.5% avg           │
├──────────────────────────────────┤
│  ⚪ alex_junior_fullstack.yaml    │
│     Alex Jensen - Junior          │
│     5 apps • 64.2% avg            │
├──────────────────────────────────┤
│  ⚪ alex_freelancer.yaml           │
│     Alex Jensen - Freelancer      │
│     12 apps • 71.8% avg           │
├──────────────────────────────────┤
│  + Create New Profile             │
│  ⚙ Manage Profiles                │
└──────────────────────────────────┘
```

**Features**:
- Shows filename + parsed name/title
- Green dot for active profile
- Quick stats (usage + avg score)
- Click profile → Activate (API call + symlink update)
- "Create New" → Navigate to `/profiles/create`
- "Manage Profiles" → Navigate to `/profiles`
- Toast notification on switch: "Activated alex_freelancer.yaml"

#### 6. Application Generation - Profile Override

**Location**: Application generation modal/page

**Enhancement to Existing Flow**:
```
┌─────────────────────────────────────────────────────┐
│  Generate Application                                │
├─────────────────────────────────────────────────────┤
│  Job: Senior Backend Engineer @ TechCorp             │
│                                                       │
│  Using Profile:                                      │
│  ┌───────────────────────────────────────────────┐  │
│  │ 🟢 alex_senior_backend.yaml ▼                  │  │
│  │    Alex Jensen - Senior Backend Developer      │  │
│  └───────────────────────────────────────────────┘  │
│                                                       │
│  ⚪ Use active profile (default)                     │
│  ⚪ Choose different profile for this application    │
│     └─ (Shows dropdown when selected)                │
│                                                       │
│  [Check Compatibility First] [Generate Application]  │
└─────────────────────────────────────────────────────┘
```

**Behavior**:
- Default: Uses active profile (symlinked `active.yaml`)
- Radio toggle to choose different profile
- Dropdown lists all profiles with name/title
- "Check Compatibility First" → Opens compatibility modal
- Proceeds to generation with selected profile

### Compatibility Scoring Implementation Details

#### Vector Similarity Approach (Local, Fast)

**Algorithm** (ChromaDB + sentence-transformers):

1. **Job Chunking**:
   ```python
   # Same strategy as profile chunking in Collector
   job_chunks = chunk_text(job_posting, method='paragraph')
   # Tag chunks heuristically:
   # - "requirements" if contains: "required", "must have", "experience with"
   # - "responsibilities" if contains: "you will", "responsibilities", "day-to-day"
   # - "nice-to-have" if contains: "preferred", "bonus", "nice to have"
   ```

2. **Embedding & Search**:
   ```python
   from sentence_transformers import SentenceTransformer
   
   model = SentenceTransformer('all-MiniLM-L6-v2')  # Local model
   job_embeddings = model.encode(job_chunks)
   
   # Query ChromaDB for each job chunk
   results = []
   for job_emb, job_chunk in zip(job_embeddings, job_chunks):
       matches = chromadb_collection.query(
           query_embeddings=[job_emb],
           n_results=5
       )
       results.append({
           'job_chunk': job_chunk,
           'matches': matches,
           'max_similarity': max(matches['distances'][0])
       })
   ```

3. **Score Calculation**:
   ```python
   # Overall: Average of top-5 job chunks' best matches
   top_5 = sorted(results, key=lambda x: x['max_similarity'], reverse=True)[:5]
   overall_score = mean([r['max_similarity'] for r in top_5]) * 100
   
   # Skills: Focus on requirement chunks
   req_chunks = [r for r in results if r['job_chunk']['type'] == 'requirements']
   skills_score = mean([r['max_similarity'] for r in req_chunks]) * 100
   
   # Experience: Focus on responsibility chunks (needs relevant profile experience)
   resp_chunks = [r for r in results if r['job_chunk']['type'] == 'responsibilities']
   experience_score = mean([r['max_similarity'] for r in resp_chunks]) * 100
   
   # Domain: Keyword extraction + overlap
   domain_keywords = extract_keywords(job_text, category='domain')  # e.g., "healthcare", "fintech"
   profile_text = flatten_profile_to_text(profile)
   domain_score = jaccard_similarity(domain_keywords, profile_text) * 100
   ```

4. **Matched Chunks**:
   ```python
   matched_chunks = [
       {
           'chunk_index': match['id'],
           'text': match['document'],
           'similarity': match['distance'],
           'source': match['metadata']['source']  # e.g., "experience[0]"
       }
       for match in all_matches if match['distance'] > 0.7
   ]
   ```

5. **Missing Requirements**:
   ```python
   missing = []
   for req_chunk in requirement_chunks:
       best_match_score = max_similarity(req_chunk, profile_chunks)
       if best_match_score < 0.6:
           missing.append(extract_key_phrase(req_chunk))
   ```

**Performance Expectations**:
- Sentence-transformers encoding: ~500ms (local CPU)
- ChromaDB queries: ~200ms per chunk
- Total for 10-job chunk: ~2-3 seconds
- **Acceptable for PoC** ✓

#### LLM-Enhanced Analysis (Ollama, Slow)

**When to Use**: User explicitly requests, accepts latency warning

**Prompt Engineering**:
```python
def generate_llm_prompt(job_text, profile_chunks, vector_scores):
    prompt = f"""Analyze the compatibility between this job posting and candidate profile.

JOB POSTING:
{job_text[:1500]}  # Truncate to control token count

CANDIDATE PROFILE (Top Matching Sections):
{format_chunks(profile_chunks[:5])}

VECTOR SIMILARITY ANALYSIS:
- Overall Match: {vector_scores['overall']}%
- Skills Match: {vector_scores['skills']}%
- Experience Match: {vector_scores['experience']}%
- Domain Match: {vector_scores['domain']}%

TASK:
Provide a concise compatibility analysis in JSON format:
{{
    "adjusted_score": <float 0-100>,
    "recommendation": "<strong|good|weak|poor>",
    "strengths": ["<brief point>", ...],  // Max 3 items
    "gaps": ["<brief point>", ...],       // Max 3 items
    "brief_analysis": "<200 word summary>"
}}

Focus on actionable insights. Be specific about why the candidate matches or doesn't match."""
    
    return prompt
```

**Ollama Integration**:
```python
import requests
import time

def call_ollama_analysis(prompt):
    start_time = time.time()
    
    response = requests.post(
        'http://localhost:11434/api/generate',
        json={
            'model': 'qwen2.5:3b',
            'prompt': prompt,
            'stream': False,
            'options': {
                'temperature': 0.3,  # Low temp for structured output
                'top_p': 0.9
            }
        },
        timeout=120  # 2-minute timeout
    )
    
    elapsed_ms = int((time.time() - start_time) * 1000)
    
    if response.status_code == 200:
        text = response.json()['response']
        # Extract JSON (handle markdown code fences)
        json_str = extract_json_from_text(text)
        analysis = json.loads(json_str)
        return analysis, elapsed_ms
    else:
        raise Exception(f"Ollama error: {response.status_code}")
```

**Fallback Strategy**:
```python
try:
    llm_analysis, compute_time = call_ollama_analysis(prompt)
except Exception as e:
    logger.warning(f"LLM analysis failed: {e}, falling back to vector-only")
    llm_analysis = None
    compute_time = 0
    # Return vector scores only
```

**Performance Expectations**:
- **Raspberry Pi 5**: 30-90 seconds (CPU inference)
- **Dev machine (RTX 5070 Ti)**: 10-30 seconds (GPU inference if Ollama configured)
- **User warning**: "This may take up to 2 minutes. Coffee break recommended ☕"

### File System Operations

#### Profile Creation

```python
import yaml
import hashlib
from pathlib import Path

def create_profile(yaml_content: str, filename: str = None, set_active: bool = False):
    # Parse YAML
    profile_data = yaml.safe_load(yaml_content)
    
    # Auto-generate filename if not provided
    if not filename:
        name_slug = slugify(profile_data['name'])
        timestamp = int(time.time())
        filename = f"{name_slug}_{timestamp}.yaml"
    
    # Validate filename
    if not filename.endswith('.yaml'):
        filename += '.yaml'
    if not is_safe_filename(filename):
        raise ValueError("Invalid filename")
    
    # Write to file
    profile_path = Path('/data/profiles') / filename
    if profile_path.exists():
        raise FileExistsError(f"Profile {filename} already exists")
    
    with open(profile_path, 'w') as f:
        yaml.dump(profile_data, f, default_flow_style=False, sort_keys=False)
    
    # Calculate file hash
    file_hash = calculate_file_hash(profile_path)
    
    # Insert metadata
    db.execute("""
        INSERT INTO profile_metadata 
        (filename, profile_name, is_active, file_hash, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (filename, profile_data['name'], set_active, file_hash, datetime.now()))
    
    # Set as active if requested
    if set_active:
        activate_profile(filename)
    
    # Trigger indexing (async)
    index_profile_background(filename)
    
    return filename

def calculate_file_hash(filepath: Path) -> str:
    """SHA256 hash for change detection"""
    with open(filepath, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()
```

#### Profile Activation (Symlink Management)

```python
def activate_profile(filename: str):
    # Deactivate all others
    db.execute("UPDATE profile_metadata SET is_active = FALSE")
    
    # Set new active
    db.execute("UPDATE profile_metadata SET is_active = TRUE WHERE filename = ?", (filename,))
    
    # Update symlink
    active_link = Path('/data/profiles/active.yaml')
    target_path = Path('/data/profiles') / filename
    
    if active_link.exists() or active_link.is_symlink():
        active_link.unlink()
    
    active_link.symlink_to(target_path)
    
    # Optionally reload Collector module
    # (or wait for next startup when Collector reads active.yaml)
    reload_collector_if_needed()
    
    return True
```

#### Profile Archiving

```python
def archive_profile(filename: str):
    source = Path('/data/profiles') / filename
    archived_dir = Path('/data/profiles/.archived')
    archived_dir.mkdir(exist_ok=True)
    destination = archived_dir / filename
    
    # Move file
    source.rename(destination)
    
    # Update metadata
    db.execute("""
        UPDATE profile_metadata 
        SET is_archived = TRUE, is_active = FALSE 
        WHERE filename = ?
    """, (filename,))
    
    # Remove from ChromaDB
    chromadb_collection.delete(where={"profile_filename": filename})
    
    return str(destination)

def restore_profile(filename: str):
    source = Path('/data/profiles/.archived') / filename
    destination = Path('/data/profiles') / filename
    
    if destination.exists():
        raise FileExistsError("Cannot restore - file already exists")
    
    # Move file back
    source.rename(destination)
    
    # Update metadata
    db.execute("""
        UPDATE profile_metadata 
        SET is_archived = FALSE 
        WHERE filename = ?
    """, (filename,))
    
    # Re-index
    index_profile_background(filename)
    
    return True
```

### Diagnostic Integration

Following the existing diagnostic pattern from the API guide:

#### GET `/api/diagnostics/profiles`

```python
@app.get("/api/diagnostics/profiles")
async def diagnose_profiles():
    profiles = db.execute("SELECT * FROM profile_metadata WHERE is_archived = FALSE").fetchall()
    
    results = []
    overall_status = "ok"
    
    for profile in profiles:
        filename = profile['filename']
        file_path = Path('/data/profiles') / filename
        
        issues = []
        status = "ok"
        
        # Check file exists
        file_exists = file_path.exists()
        if not file_exists:
            issues.append("File missing from disk")
            status = "error"
        
        # Check YAML validity
        yaml_valid = False
        try:
            with open(file_path) as f:
                yaml.safe_load(f)
            yaml_valid = True
        except Exception as e:
            issues.append(f"YAML parse error: {e}")
            status = "error"
        
        # Check file hash (detect changes)
        current_hash = calculate_file_hash(file_path) if file_exists else None
        hash_match = current_hash == profile['file_hash']
        if not hash_match and file_exists:
            issues.append("File modified since last index")
            status = "warning"
        
        # Check indexing
        chunk_count = chromadb_collection.count(where={"profile_filename": filename})
        indexed = chunk_count > 0
        if not indexed:
            issues.append("Not indexed in ChromaDB")
            status = "warning"
        
        results.append({
            "filename": filename,
            "status": status,
            "is_active": profile['is_active'],
            "file_exists": file_exists,
            "yaml_valid": yaml_valid,
            "indexed": indexed,
            "chunk_count": chunk_count,
            "last_indexed": profile['indexed_at'],
            "file_hash_match": hash_match,
            "issues": issues
        })
        
        if status == "error":
            overall_status = "degraded"
    
    active_profile = db.execute(
        "SELECT filename FROM profile_metadata WHERE is_active = TRUE"
    ).fetchone()
    
    return {
        "overall": overall_status,
        "active_profile": active_profile['filename'] if active_profile else None,
        "profiles": results,
        "total_profiles": len(results),
        "profiles_needing_reindex": len([p for p in results if not p['file_hash_match']]),
        "archived_profiles": db.execute("SELECT COUNT(*) FROM profile_metadata WHERE is_archived = TRUE").fetchone()[0]
    }
```

#### POST `/api/diagnostics/profiles/{filename}/validate`

```python
@app.get("/api/diagnostics/profiles/{filename}/validate")
async def validate_profile(filename: str):
    checks = []
    
    # File exists
    file_path = Path('/data/profiles') / filename
    checks.append({
        "check": "file_exists",
        "passed": file_path.exists(),
        "message": f"File {'found' if file_path.exists() else 'not found'} at {file_path}"
    })
    
    if not file_path.exists():
        return {"filename": filename, "valid": False, "checks": checks, "warnings": [], "errors": ["File not found"]}
    
    # YAML syntax
    try:
        with open(file_path) as f:
            profile_data = yaml.safe_load(f)
        checks.append({"check": "yaml_syntax", "passed": True, "message": "YAML parses correctly"})
    except Exception as e:
        checks.append({"check": "yaml_syntax", "passed": False, "message": f"YAML error: {e}"})
        return {"filename": filename, "valid": False, "checks": checks, "warnings": [], "errors": [str(e)]}
    
    # Required fields
    required_fields = ['name', 'email', 'skills']
    missing = [f for f in required_fields if f not in profile_data]
    checks.append({
        "check": "required_fields",
        "passed": len(missing) == 0,
        "message": f"All required fields present" if not missing else f"Missing: {missing}"
    })
    
    # Skills array
    skills_count = len(profile_data.get('skills', []))
    checks.append({
        "check": "skills_array",
        "passed": skills_count > 0,
        "message": f"Found {skills_count} skills"
    })
    
    # Experience array
    exp_count = len(profile_data.get('experience', []))
    checks.append({
        "check": "experience_array",
        "passed": exp_count > 0,
        "message": f"Found {exp_count} experience entries"
    })
    
    # ChromaDB indexing
    chunk_count = chromadb_collection.count(where={"profile_filename": filename})
    checks.append({
        "check": "indexed_in_chromadb",
        "passed": chunk_count > 0,
        "message": f"{chunk_count} chunks found in vector store"
    })
    
    # File hash
    metadata = db.execute("SELECT file_hash FROM profile_metadata WHERE filename = ?", (filename,)).fetchone()
    current_hash = calculate_file_hash(file_path)
    hash_match = current_hash == metadata['file_hash'] if metadata else False
    checks.append({
        "check": "file_hash_current",
        "passed": hash_match,
        "message": "File unchanged since last index" if hash_match else "File modified, needs reindex"
    })
    
    all_passed = all(c['passed'] for c in checks)
    
    return {
        "filename": filename,
        "valid": all_passed,
        "checks": checks,
        "warnings": [c['message'] for c in checks if not c['passed'] and c['check'] != 'file_exists'],
        "errors": [c['message'] for c in checks if not c['passed'] and c['check'] == 'file_exists']
    }
```

### Implementation Approach (Phased)

#### Phase 1: File System & Database Foundation (2-3 hours)
**Goal**: Multi-profile storage and metadata tracking

**Tasks**:
1. Create database migration for `profile_metadata`, `compatibility_scores`, `profile_usage_log`
2. Implement file system functions:
   - `create_profile()`, `update_profile()`, `archive_profile()`, `restore_profile()`
   - `activate_profile()` (symlink management)
   - `calculate_file_hash()` for change detection
3. Implement metadata CRUD operations
4. Test with 3-5 mock profiles
5. Verify symlink activation works

**Success Criteria**:
- Can create multiple YAML profiles
- Active symlink updates correctly
- Metadata tracks all profiles
- Archive/restore moves files properly

#### Phase 2: API Endpoints - Profile Management (3-4 hours)
**Goal**: RESTful API for profile operations

**Tasks**:
1. Implement GET `/api/profiles` (list with sorting/filtering)
2. Implement GET `/api/profiles/{filename}` (detail view)
3. Implement POST `/api/profiles` (create from YAML)
4. Implement PUT `/api/profiles/{filename}` (update)
5. Implement POST `/api/profiles/{filename}/duplicate`
6. Implement POST `/api/profiles/{filename}/activate`
7. Implement POST `/api/profiles/{filename}/archive`
8. Implement POST `/api/profiles/{filename}/restore`
9. Implement DELETE `/api/profiles/{filename}`
10. Write integration tests for all endpoints

**Success Criteria**:
- All CRUD operations functional
- Proper error handling (file not found, invalid YAML, etc.)
- Returns appropriate HTTP status codes
- Activation updates Collector module state

#### Phase 3: Compatibility Scoring - Vector Only (3-4 hours)
**Goal**: Fast, local vector similarity scoring

**Tasks**:
1. Implement job text chunking (mirror profile chunking)
2. Create `compatibility_service.py`:
   - `calculate_vector_similarity()`
   - `calculate_component_scores()`
   - `identify_matched_chunks()`
   - `identify_missing_requirements()`
   - `determine_recommendation()`
3. Implement caching logic (check, store, invalidate)
4. Implement POST `/api/compatibility/check` (vector-only)
5. Test with 5-10 job postings against multiple profiles
6. Validate scores make intuitive sense

**Success Criteria**:
- Vector scores calculated in <5 seconds
- Component breakdown meaningful
- Cache reduces redundant calculations
- Matched chunks correctly identified

#### Phase 4: Compatibility Scoring - LLM Enhancement (2-3 hours)
**Goal**: Optional deep analysis via Ollama

**Tasks**:
1. Design LLM prompt template
2. Implement Ollama API integration
3. Add `method='llm_enhanced'` support to compatibility endpoint
4. Implement JSON parsing with fallback
5. Track compute time (not cost)
6. Add user warning for latency
7. Test on dev machine (faster) and Pi (slower)

**Success Criteria**:
- LLM provides actionable insights
- JSON parsing robust
- Graceful fallback to vector-only on error
- Compute time tracked and displayed

#### Phase 5: Usage Statistics (2 hours)
**Goal**: Track profile performance

**Tasks**:
1. Implement usage logging triggers:
   - On compatibility check → insert log entry
   - On application generation → increment usage_count
2. Create statistics calculation queries
3. Implement GET `/api/profiles/{filename}/statistics`
4. Test with mock usage data
5. Validate calculations correct

**Success Criteria**:
- Statistics accurate
- Queries fast (<100ms)
- Score distribution calculated correctly

#### Phase 6: Diagnostic Endpoints (2 hours)
**Goal**: Profile health checking

**Tasks**:
1. Implement GET `/api/diagnostics/profiles`
2. Implement GET `/api/diagnostics/profiles/{filename}/validate`
3. Implement POST `/api/diagnostics/profiles/{filename}/reindex`
4. Implement POST `/api/diagnostics/profiles/reindex-all`
5. Add to existing diagnostic infrastructure
6. Test validation with corrupted YAML, missing files

**Success Criteria**:
- Diagnostics catch common issues
- Clear error messages
- Reindex operations work
- Integrates with existing `/api/diagnostics` pattern

#### Phase 7: Frontend - Profile Management UI (4-5 hours)
**Goal**: User-friendly profile CRUD

**Tasks**:
1. Create profile list page (`/profiles`)
   - Profile cards with metrics
   - Sort/filter controls
   - Quick actions menu
2. Create profile detail page (`/profiles/{filename}`)
   - Formatted/YAML/Chunks view modes
   - Statistics panel
   - Action buttons
3. Create profile create/edit page
   - YAML upload
   - In-browser editor (Monaco/CodeMirror)
   - Validation feedback
   - Template starters
4. Wire up API calls
5. Add loading/error states
6. Test on mobile (responsive)

**Success Criteria**:
- All CRUD operations work in UI
- YAML editor functional
- Validation provides clear feedback
- Mobile-friendly

#### Phase 8: Frontend - Compatibility Scoring UI (3-4 hours)
**Goal**: Visual compatibility analysis

**Tasks**:
1. Create compatibility score modal
   - Score display with breakdown
   - Method selector (vector/LLM)
   - Matched chunks visualization
   - Missing requirements
2. Add "Check Compatibility" button to job pages
3. Implement LLM analysis flow with latency warning
4. Add loading states (especially for LLM - show spinner + timer)
5. Wire up API calls
6. Test with various score ranges

**Success Criteria**:
- Clear score visualization
- LLM latency warning effective
- Smooth async operations
- Matched chunks clearly shown

#### Phase 9: Frontend - Quick Switcher & Overrides (2 hours)
**Goal**: Seamless profile switching

**Tasks**:
1. Create quick switcher header component
   - Dropdown with profile list
   - Active indicator
   - Quick stats
2. Integrate into app layout
3. Add profile override to application generation
   - Dropdown in generation modal
   - Radio toggle
4. Implement activation API calls
5. Add toast notifications

**Success Criteria**:
- One-click profile switching
- Visual feedback on activation
- Override works in generation flow
- No page reloads

#### Phase 10: Integration & Polish (3-4 hours)
**Goal**: Smooth end-to-end flows

**Tasks**:
1. Test complete user journeys:
   - Create profile → Activate → Check compatibility → Generate app
   - Switch profile → Check compatibility → Choose different → Generate
   - Update profile → Verify reindex → Check old scores invalidated
   - Archive → Restore → Verify functionality
2. Performance optimization:
   - Cache API responses client-side
   - Debounce search/sort
   - Lazy-load profile lists
3. UI/UX polish:
   - Consistent styling
   - Smooth transitions
   - Helpful empty states
   - Clear error messages
4. Documentation:
   - API endpoint docs
   - User guide for profile management
   - Diagnostic usage guide

**Success Criteria**:
- All flows smooth and intuitive
- No performance issues with 10+ profiles
- Professional visual polish
- Clear documentation

### Testing Requirements

#### Unit Tests

**Profile Service**:
```python
def test_create_profile_generates_filename():
    """Should auto-generate filename from name if not provided"""
    
def test_create_profile_duplicate_fails():
    """Should raise error if filename already exists"""
    
def test_activate_profile_updates_symlink():
    """Should update active.yaml symlink to target"""
    
def test_archive_profile_moves_file():
    """Should move file to .archived/ directory"""
    
def test_update_profile_invalidates_scores():
    """Should clear compatibility scores when YAML changes"""
    
def test_file_hash_detects_changes():
    """Should detect when file modified externally"""
```

**Compatibility Service**:
```python
def test_vector_similarity_returns_0_100():
    """Should return scores in valid range"""
    
def test_matched_chunks_above_threshold():
    """Should only include chunks > 0.7 similarity"""
    
def test_missing_requirements_below_threshold():
    """Should identify requirements with no match > 0.6"""
    
def test_cache_hit_returns_stored_score():
    """Should return cached score if not expired"""
    
def test_cache_invalidation_on_profile_update():
    """Should delete scores when profile changes"""
    
def test_llm_fallback_on_error():
    """Should return vector scores if Ollama fails"""
```

**Usage Statistics**:
```python
def test_avg_score_calculation():
    """Should correctly average all scores"""
    
def test_usage_count_increment():
    """Should increment on application generation"""
    
def test_score_distribution():
    """Should categorize scores into buckets correctly"""
```

#### Integration Tests

**Full Profile Lifecycle**:
```python
def test_create_activate_update_archive_restore():
    """End-to-end profile management"""
    
def test_multi_profile_compatibility():
    """Check same job against 3 profiles, verify different scores"""
    
def test_profile_switch_in_generation():
    """Override active profile during application generation"""
```

**API Endpoints**:
```python
def test_profile_list_sorting():
    """Verify all sort options return correct order"""
    
def test_compatibility_check_caching():
    """First call calculates, second returns cached"""
    
def test_activate_deactivates_previous():
    """POST /activate switches active flag correctly"""
    
def test_diagnostic_detects_missing_file():
    """Diagnostics endpoint flags missing YAML"""
```

#### Manual Testing Scenarios

1. **Multi-Profile Workflow**:
   - Create 3 profiles: Junior, Senior, Lead
   - Check compatibility of same job with all three
   - Verify scores differ meaningfully
   - Generate application with non-active profile

2. **Cache Behavior**:
   - Check compatibility (should calculate)
   - Check again immediately (should return cached)
   - Update profile
   - Check again (should recalculate)

3. **Symlink Activation**:
   - Create profile, set active
   - Verify `active.yaml` points to correct file
   - Switch to different profile
   - Verify symlink updated
   - Restart Scout service
   - Verify Collector loaded correct profile

4. **LLM Analysis Latency**:
   - Check compatibility with vector method (note time)
   - Request LLM-enhanced analysis
   - Observe compute time (should be 10-90s depending on hardware)
   - Verify LLM insights add value

5. **Archive & Restore**:
   - Create profile, use in 5 applications
   - Archive
   - Verify not shown in default list
   - Restore
   - Verify usage stats preserved
   - Verify re-indexed

6. **Diagnostics**:
   - Corrupt a YAML file (invalid syntax)
   - Call `/api/diagnostics/profiles`
   - Verify error detected
   - Call `/api/diagnostics/profiles/{filename}/validate`
   - Verify specific error shown

7. **Edge Cases**:
   - Create profile with minimal YAML (only required fields)
   - Create profile with maximal data (many skills, experiences)
   - Try to delete active profile (should refuse or warn)
   - Try to activate archived profile (should refuse)
   - Externally modify YAML file
   - Verify diagnostic detects hash mismatch

### Constraints & Guardrails

**PoC Simplifications**:
- Single user assumption (no multi-user, no auth)
- YAML files on disk (not cloud storage)
- Local LLM only (no API fallback)
- Synchronous operations (acceptable for PoC latency)
- Basic YAML editor (not full IDE features)
- No collaborative editing
- No real-time updates (polling acceptable)

**Local Hardware Considerations**:
- **Thermal management**: LLM analysis stresses Pi 5, monitor temps
- **Compute budgets**: Track ms, not dollars
- **Ollama availability**: Graceful degradation if service down
- **Storage limits**: YAML files small, but monitor `/data` usage
- **Network**: All local, no external API calls

**Future Enhancements** (explicitly deferred):
- Multi-user support with authentication
- Cloud storage sync (Dropbox, Google Drive)
- Real-time collaborative editing
- Profile versioning/git integration
- Advanced YAML templates with conditional logic
- Automated profile optimization suggestions
- Profile export to PDF/DOCX
- Resume parsing (upload PDF → generate YAML)
- Batch compatibility scoring (score all jobs at once)
- Advanced caching (Redis LRU)
- Distributed inference (offload LLM to cloud when Pi busy)

**Code Quality Standards**:
- Type hints on all functions
- Comprehensive docstrings
- Error logging with context
- Unit tests for core logic
- Integration tests for API flows
- YAML validation with clear error messages
- File system error handling (permissions, disk full, etc.)

### Success Metrics

**Functional Metrics**:
- Profile CRUD success rate: 100%
- Vector compatibility accuracy: >80% correlation with manual assessment
- LLM analysis quality: Useful insights in >85% of cases
- Cache hit rate: >50% for repeated checks
- Symlink activation success: 100%
- Diagnostic detection rate: 100% for known issues

**Performance Metrics**:
- Profile list load: <500ms for 20 profiles
- Vector compatibility: <5s
- LLM compatibility (Pi 5): <90s
- LLM compatibility (dev machine): <30s
- Profile indexing: <10s for typical profile
- Activation (symlink update): <200ms

**User Experience Metrics**:
- Time to create profile: <5 minutes
- Time to check compatibility: <10 seconds (vector), <90s (LLM on Pi)
- Profile switching: 1 click + <1s response
- Error recovery: Clear guidance provided
- Mobile responsiveness: Full functionality

**System Health Metrics**:
- Pi 5 CPU temp during LLM: <80°C (throttle if needed)
- Ollama uptime: >95%
- ChromaDB query latency: <500ms
- File system errors: 0 (proper error handling)

## Summary

This specification implements a **local-first, multi-profile management system** for Scout, adapted for deployment on Raspberry Pi 5 with Ollama-based LLM inference. The design prioritizes:

1. **YAML-first storage**: Human-readable, git-friendly, portable profiles
2. **Vector-based matching**: Fast, local semantic similarity (2-5s)
3. **Optional LLM enhancement**: Deep insights when user accepts latency (30-90s)
4. **Hybrid metadata**: SQLite for stats, ChromaDB for embeddings, YAML for truth
5. **Diagnostic integration**: Follows existing `/api/diagnostics` patterns
6. **Thermal awareness**: Tracks compute time, not API costs
7. **Graceful degradation**: Falls back to vector-only if Ollama unavailable

**Key Innovations**:
- **Symlink-based activation**: Backward compatible with single-profile Collector
- **File hash change detection**: Automatic reindexing when YAML modified externally
- **Compute time tracking**: Monitors inference latency instead of dollar costs
- **7-day cache**: Longer expiry justified by compute expense
- **Latency-aware UX**: Clear warnings before long LLM operations

**Critical Success Factors**:
1. Vector similarity scores must be accurate and actionable (main use case)
2. LLM analysis must provide value beyond vector scores (justify latency)
3. Profile management must feel natural (YAML editing + UI CRUD)
4. Diagnostic endpoints must catch issues before user sees errors
5. Thermal management must prevent Pi 5 throttling during intensive operations