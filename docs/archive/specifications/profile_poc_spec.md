# Profile System - Claude Code Implementation Specification

## Context & Overview

You are implementing the user profile system for Scout, an AI-powered job application automation system. This is a **Proof of Concept (PoC)** implementation focused on validating the core value proposition of semantic profile matching against job requirements.

**Project Location**: Scout PoC codebase
**Module**: Profile Management System
**Dependencies**: S4 Vector Store Service (ChromaDB), SQLite database, S1 LLM Service (for future enhancements)

## Current State

The Scout PoC has established:
- FastAPI backend structure
- SQLite database for core data storage
- ChromaDB via S4 Vector Store Service for embeddings
- Basic API routing patterns
- sentence-transformers embedding model integration

## Objective

Implement a minimal profile management system that:
1. **Blocks** job application generation when no profile exists
2. Allows users to create/update a single free-form experience profile
3. Indexes profile content into vector embeddings for semantic matching
4. Provides clear user feedback about profile status

## Success Criteria

- [ ] Dashboard displays blocking warning when no profile exists
- [ ] Profile creation page accepts free-form text input (100-10,000 chars)
- [ ] Profile text is stored in SQLite, embedded in ChromaDB, saved as file
- [ ] Profile chunks are semantically searchable via Vector Store Service
- [ ] Profile update flow clears old embeddings and creates new ones
- [ ] API endpoints follow RESTful conventions
- [ ] All operations log appropriately for debugging

## Technical Specifications

### Database Schema (SQLite)

Create new table `user_profiles`:

```
Table: user_profiles
- id: INTEGER PRIMARY KEY AUTOINCREMENT
- user_id: INTEGER (default 1 for PoC single-user)
- raw_text: TEXT NOT NULL
- is_indexed: BOOLEAN DEFAULT FALSE
- chunk_count: INTEGER DEFAULT 0
- created_at: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
- updated_at: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
- character_count: INTEGER
```

**Constraints**:
- Only one profile per user_id (unique constraint on user_id)
- character_count matches len(raw_text)
- chunk_count matches number of embeddings created

### Vector Store Integration (ChromaDB)

**Collection**: `user_profiles`

**Chunk Strategy**:
- Split profile text by double newlines (`\n\n`) to preserve paragraph structure
- Fall back to sentence boundaries if paragraphs exceed 500 characters
- Each chunk embedded separately via S4 Vector Store Service

**Metadata per chunk**:
```python
{
    "profile_id": int,
    "chunk_index": int,
    "chunk_type": "paragraph" | "sentence",
    "created_at": ISO timestamp,
    "character_count": int
}
```

### File System Storage

**Location**: `/data/profiles/profile_{id}.txt`

**Purpose**: Simple backup/debugging (PoC only)

**Content**: Raw profile text as-is

### API Endpoints

Implement under `/api/profile` route group:

#### 1. GET `/api/profile/status`

**Purpose**: Check if profile exists and is indexed

**Response**:
```json
{
    "exists": boolean,
    "is_indexed": boolean,
    "profile_id": int | null,
    "chunk_count": int,
    "character_count": int,
    "last_updated": ISO timestamp | null
}
```

#### 2. POST `/api/profile/create`

**Purpose**: Create new profile (or update if exists for user)

**Request Body**:
```json
{
    "profile_text": string
}
```

**Validation**:
- Min 100 characters
- Max 10,000 characters
- Strip leading/trailing whitespace

**Process**:
1. Validate input
2. Insert/update SQLite record (is_indexed=FALSE initially)
3. Save to `/data/profiles/profile_{id}.txt`
4. Trigger indexing asynchronously (or synchronously for PoC simplicity)
5. Return profile_id and status

**Response**:
```json
{
    "profile_id": int,
    "status": "created" | "updated",
    "is_indexed": boolean,
    "chunk_count": int
}
```

#### 3. POST `/api/profile/index`

**Purpose**: Chunk and embed profile text

**Request Body**:
```json
{
    "profile_id": int
}
```

**Process**:
1. Fetch profile from SQLite
2. If already indexed, clear old embeddings from ChromaDB
3. Chunk text using paragraph/sentence strategy
4. Embed each chunk via S4 Vector Store Service
5. Store embeddings in ChromaDB with metadata
6. Update SQLite: is_indexed=TRUE, chunk_count=N
7. Return success status

**Response**:
```json
{
    "success": boolean,
    "chunks_created": int,
    "profile_id": int
}
```

#### 4. GET `/api/profile/retrieve`

**Purpose**: Get current profile data

**Query Params**: None (single user for PoC)

**Response**:
```json
{
    "profile_id": int,
    "profile_text": string,
    "is_indexed": boolean,
    "chunk_count": int,
    "character_count": int,
    "created_at": ISO timestamp,
    "updated_at": ISO timestamp
}
```

### Frontend Components

#### Dashboard Warning Component

**Condition**: Display when `profile.exists === false`

**UI Behavior**:
- Full-width banner at top of dashboard
- Warning icon + clear message
- Blocks access to job application features
- "Create Profile" button links to `/profile/create`

**Example Message**:
> ⚠️ **Profile Required**: Create your professional profile to start matching jobs and generating applications.

**Visual Treatment**:
- Prominent but not alarming (info/warning level, not error)
- Sticky position if dashboard scrolls
- Cannot be dismissed (hard requirement)

#### Profile Creation/Edit Page

**Route**: `/profile/create` (same component handles edit)

**UI Elements**:
1. **Header**: "Create Your Professional Profile"
2. **Instructions**: Brief explanation (2-3 sentences) about what to include
3. **Text Area**:
   - Placeholder with example structure
   - Character counter (current / max 10,000)
   - Min 100 char validation indicator
   - Auto-growing height (within limits)
4. **Action Buttons**:
   - "Save & Index Profile" (primary action)
   - "Cancel" (returns to dashboard)
5. **Loading State**: Show during indexing process
6. **Success State**: Confirmation with link back to dashboard

**Validation Display**:
- Real-time character count
- Error messages below text area
- Disable submit button if validation fails

### Chunking Implementation Details

**Primary Strategy** (Paragraph-based):
```python
chunks = profile_text.split('\n\n')
chunks = [c.strip() for c in chunks if c.strip()]
```

**Secondary Strategy** (If paragraph > 500 chars):
```python
# Use sentence boundaries from sentence-transformers or simple split
# Target chunk size: 200-500 characters
```

**Edge Cases**:
- Empty profile → reject at validation
- No paragraph breaks → treat as single chunk
- Very short paragraphs → combine adjacent chunks if total < 100 chars

### Error Handling

**Profile Creation Errors**:
- Validation failure → 400 Bad Request with specific message
- Database write failure → 500 with retry suggestion
- File system write failure → Log warning, continue (non-critical)

**Indexing Errors**:
- Embedding service unavailable → Mark is_indexed=FALSE, return error
- ChromaDB connection failure → Rollback, return error
- Partial chunk failure → Rollback all, return error (atomic operation)

**User Feedback**:
- Clear error messages in UI
- Suggest next steps (e.g., "Try again" or "Contact support")
- Log all errors with context for debugging

## Implementation Approach

### Phase 1: Database & File Storage
1. Create SQLite migration for `user_profiles` table
2. Implement file storage functions (save/read `/data/profiles/`)
3. Test database CRUD operations

### Phase 2: API Endpoints
1. Implement `/status` endpoint (read-only, simplest)
2. Implement `/create` endpoint with validation
3. Implement `/retrieve` endpoint
4. Test API flows with mock data

### Phase 3: Vector Indexing
1. Implement chunking logic with tests
2. Integrate with S4 Vector Store Service for embedding
3. Implement `/index` endpoint
4. Test full create → index → retrieve flow

### Phase 4: Frontend Integration
1. Create dashboard warning component
2. Create profile creation/edit page
3. Wire up API calls with loading/error states
4. Test complete user flow

### Phase 5: Integration Testing
1. Test profile creation → job matching flow
2. Verify blocking behavior when no profile
3. Test profile update → re-indexing flow
4. Validate chunk search quality

## Constraints & Guardrails

**PoC Simplifications**:
- Single user only (user_id=1)
- No authentication/authorization
- No profile versioning/history
- No profile export/import
- Synchronous indexing (acceptable for PoC)

**Future Enhancements** (explicitly deferred):
- Multi-profile support
- Structured field extraction via LLM
- Profile completeness scoring
- Profile suggestions/templates
- Profile analytics dashboard

**Code Quality**:
- Type hints on all functions
- Docstrings for public functions
- Error logging with context
- Unit tests for chunking logic
- Integration tests for full flow

## Testing Requirements

**Unit Tests**:
- Chunking logic with various inputs
- Validation logic (min/max length)
- Database operations (CRUD)

**Integration Tests**:
- Full profile creation flow
- Profile update → re-index flow
- API endpoint responses
- ChromaDB embedding storage/retrieval

**Manual Testing Scenarios**:
1. Create profile with valid text → verify indexed
2. Attempt job application without profile → verify blocked
3. Update existing profile → verify old embeddings cleared
4. Create profile with edge cases (very long, minimal, lots of newlines)

## File Structure

```
/backend
  /api
    /routes
      profile.py          # New route group
  /services
    profile_service.py    # Business logic
    profile_chunker.py    # Text chunking utilities
  /models
    profile.py            # Pydantic models
  /migrations
    003_create_user_profiles.sql  # New migration

/frontend
  /src
    /components
      ProfileWarning.vue  # Dashboard warning
    /views
      ProfileCreate.vue   # Profile creation page
    /services
      profileApi.ts       # API client functions

/data
  /profiles              # Profile text files
```

## Success Metrics

**Functional**:
- Profile creation success rate: 100% for valid input
- Indexing completion time: < 5 seconds for typical profile
- Chunk retrieval accuracy: Relevant chunks in top-5 results

**User Experience**:
- Time to create first profile: < 3 minutes
- Warning clarity: Users understand blocking reason
- Update flow: Seamless re-indexing without data loss

## Questions to Resolve During Implementation

If you encounter these scenarios, prioritize simplicity for PoC:

1. **Should indexing be synchronous or asynchronous?**
   - PoC: Synchronous (simpler, acceptable for ~5 sec operation)
   - Future: Async with job queue

2. **How to handle concurrent profile updates?**
   - PoC: Last-write-wins (single user assumption)
   - Future: Optimistic locking with version numbers

3. **Should chunks overlap for better matching?**
   - PoC: No overlap (simpler)
   - Future: Sliding window with 10% overlap

## Summary

This specification implements a minimal, functional profile system that proves the core value proposition: semantic matching of user experience against job requirements. The implementation prioritizes simplicity and clarity while maintaining a structure that supports future enhancements.

**Key Design Decisions**:
- Single free-form text input (proves concept faster)
- Triple storage for redundancy and different use cases
- Blocking UX to ensure data quality
- Clean API boundaries for future expansion

**Next Steps After Implementation**:
1. Validate profile → job matching quality
2. Gather user feedback on profile creation UX
3. Consider structured field extraction if needed
4. Plan multi-profile support based on user demand
