# Web Interface - Current State

This document describes the current implementation of Scout's web interface.

## Overview

Scout uses FastAPI with Jinja2 templates for server-side rendering. The frontend is vanilla JavaScript with no framework dependencies.

### Technology Stack
| Component | Technology |
|-----------|------------|
| Backend | FastAPI 0.100+ |
| Templates | Jinja2 |
| Styling | Custom CSS (common.css) |
| JavaScript | Vanilla JS (common.js) |
| Icons | Unicode symbols |

## File Structure

```
src/web/
├── main.py              # FastAPI application setup
├── dependencies.py      # Dependency injection (JobStore, etc.)
├── schemas.py           # Pydantic request/response schemas
├── log_handler.py       # Memory-based log handler for UI
├── routes/
│   ├── __init__.py
│   ├── pages.py         # HTML page routes (with legacy redirects)
│   └── api/
│       └── v1/
│           ├── __init__.py
│           ├── jobs.py          # Job pipeline endpoints
│           ├── profiles.py      # Profile management (normalized schema)
│           ├── user.py          # User identity endpoints
│           ├── notifications.py # Notifications
│           ├── logs.py          # Log retrieval
│           ├── metrics.py       # Performance metrics
│           └── diagnostics.py   # Component diagnostics
├── templates/
│   ├── partials/
│   │   └── navbar.html      # Navigation with user menu
│   ├── index.html           # Dashboard (main page)
│   ├── applications.html    # Applications list
│   ├── profiles_list.html   # Profile management with completeness scores
│   ├── profile_edit.html    # Tabbed profile editor
│   ├── metrics.html         # Performance metrics dashboard
│   ├── logs.html            # Application logs viewer
│   └── diagnostics.html     # System diagnostics page
└── static/
    ├── css/
    │   └── common.css   # Shared styles (user menu, completeness badges)
    └── js/
        └── common.js    # Shared JS (user/profile loading, notifications)
```

---

## Data Architecture

The web interface uses a **normalized User/Profile schema**:

| Entity | Purpose |
|--------|---------|
| **User** | Identity (username, email, display_name) |
| **Profile** | Career data (skills, experience, education) |

- One User can have multiple Profiles
- One Profile is marked as "active" at a time
- Profiles have completeness scores calculated from filled fields

### Key API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/user` | GET | Get current user identity |
| `/api/v1/profiles` | GET | List all profiles with metadata |
| `/api/v1/profiles/active` | GET | Get active profile |
| `/api/v1/profiles/{slug}` | GET | Get full profile data |
| `/api/v1/profiles/{slug}/completeness` | GET | Get completeness score |
| `/api/v1/profiles/{slug}/activate` | POST | Set as active profile |
| `/api/v1/profiles/{slug}` | DELETE | Delete profile |

---

## FastAPI Application

**Location:** `src/web/main.py`

### Application Setup
```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(
    title="Scout",
    description="Intelligent Job Application System",
    version="1.0.0",
)

# Static files
app.mount("/static", StaticFiles(directory="src/web/static"), name="static")

# Include routers
app.include_router(api_router)
app.include_router(profile_router)
app.include_router(notifications_router)
app.include_router(pages_router)
```

### Startup/Shutdown Events
```python
@app.on_event("startup")
async def startup():
    """Initialize services on startup."""
    # Initialize pipeline orchestrator
    await get_pipeline_orchestrator()
    # Initialize job store
    await get_store()
    # Initialize notification service
    await get_notification_service()

@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    # Services handle their own cleanup
    pass
```

---

## Templates

### Base Layout (via Partials)

All pages include the shared navbar:
```html
{% include 'partials/navbar.html' %}
```

### Navbar (`partials/navbar.html`)
Contains:
- Scout logo/branding
- Navigation links (Dashboard, Profiles, Applications, Metrics, Logs, Diagnostics)
- Active page indicator (highlights current page)
- **Active Profile Indicator**: Shows currently active profile name with green dot
- **User Menu**: User avatar dropdown with profile management links

```html
<!-- Navbar Right Section -->
<div class="navbar-right">
    <!-- Active Profile Indicator -->
    <div class="navbar-active-profile" id="navbar-active-profile">
        <span class="active-profile-dot"></span>
        <span class="active-profile-name" id="navbar-active-name">Loading...</span>
    </div>

    <!-- User Menu -->
    <div class="navbar-user-menu">
        <button class="navbar-user-btn" onclick="toggleUserMenu(event)">
            <span class="user-avatar" id="navbar-user-avatar">T</span>
            <span class="user-name" id="navbar-user-name">Test User</span>
            <span class="navbar-arrow">&#9662;</span>
        </button>
        <div class="user-dropdown" id="navbar-user-dropdown">
            <div class="user-dropdown-header">
                <div class="user-email" id="navbar-user-email">test@scout.local</div>
            </div>
            <a href="/profiles" class="user-dropdown-item">Manage Profiles</a>
            <button class="user-dropdown-item disabled" disabled>
                Settings <span class="coming-soon-badge">Soon</span>
            </button>
            <button class="user-dropdown-item disabled" disabled>
                Log Out <span class="coming-soon-badge">Soon</span>
            </button>
        </div>
    </div>
</div>
```

### Pages

#### 1. Dashboard (`index.html`)
**Route:** `/`

Main application page with:
- Profile status indicator
- Job posting text input
- Profile override dropdown (select which profile to use)
- Quick Score button (fast compatibility check)
- Generate Application button
- Progress section (4-step pipeline with status)
- Results section (score, download buttons)
- Error handling with retry

**Key JavaScript Functions:**
```javascript
// Check profile status
async function checkProfileStatus() { ... }

// Update profile dropdown from API
async function updateProfileSelect() { ... }

// Calculate quick compatibility score
async function calculateQuickScore() { ... }

// Submit job for full processing
async function startProcessing() { ... }

// Poll for pipeline status
function startPolling() { ... }

// Update progress UI
function updateProgress(status) { ... }

// Show results with download links
function showResults(status) { ... }
```

#### 2. Applications (`applications.html`)
**Route:** `/applications`

Lists all generated applications with:
- Summary stats (total, completed, processing, avg score)
- Sort controls (date, score, company, status)
- Filter controls (search, show failed)
- Application cards with score indicator
- Download buttons (CV, Cover Letter)
- Pagination

#### 3. Profiles List (`profiles_list.html`)
**Route:** `/profiles`

Profile management page with:
- Summary stats (total profiles, profiles with scores)
- Profile cards showing:
  - Profile name and slug
  - **Completeness badge** (color-coded: excellent/good/fair/needs_work)
  - Active profile indicator (green badge)
  - Stats row (skills count, experience count, education count)
- Actions: Edit, Activate, Delete (with confirmation modal)
- Create new profile button

**Key JavaScript Functions:**
```javascript
// Load profiles with completeness scores
async function loadProfiles() {
    const response = await fetch('/api/v1/profiles');
    const data = await response.json();
    // Fetch completeness for each profile
    for (const profile of data.profiles) {
        const compResponse = await fetch(`/api/v1/profiles/${profile.slug}/completeness`);
        profile.completeness = await compResponse.json();
    }
}

// Activate a profile
async function activateProfile(slug) {
    await fetch(`/api/v1/profiles/${slug}/activate`, { method: 'POST' });
}

// Delete with confirmation
async function deleteProfile(slug) {
    if (confirm('Delete this profile?')) {
        await fetch(`/api/v1/profiles/${slug}`, { method: 'DELETE' });
    }
}
```

**Completeness Levels:**
| Level | Score Range | Color |
|-------|-------------|-------|
| Excellent | 80-100% | Green (#10b981) |
| Good | 60-79% | Blue (#2563eb) |
| Fair | 40-59% | Yellow (#f59e0b) |
| Needs Work | 0-39% | Red (#ef4444) |

#### 4. Profile Editor (`profile_edit.html`)
**Route:** `/profiles/new`, `/profiles/{slug}/edit`

**Tabbed interface** for profile editing (5 tabs):

| Tab | Contents |
|-----|----------|
| **Overview** | Name, title, email, phone, location, summary |
| **Skills** | Dynamic list with proficiency levels (1-5) and years |
| **Experience** | Job entries with company, title, dates, achievements |
| **Education** | Degree entries with institution, field, dates, GPA |
| **Certifications** | Certification entries with name, issuer, dates |

**Key Features:**
- Add/remove items in each list section
- Reorder items via drag or move buttons
- Completeness widget in sidebar (real-time score)
- Field validation
- Save button creates/updates profile via API

**Key JavaScript Functions:**
```javascript
// Load existing profile data
async function loadProfile(slug) {
    const response = await fetch(`/api/v1/profiles/${slug}`);
    return await response.json();
}

// Save profile (POST for new, PUT for existing)
async function saveProfile() {
    const method = isNewProfile ? 'POST' : 'PUT';
    const url = isNewProfile ? '/api/v1/profiles' : `/api/v1/profiles/${slug}`;
    await fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(profileData)
    });
}

// Add dynamic list items
function addSkill() { ... }
function addExperience() { ... }
function addEducation() { ... }
function addCertification() { ... }

// Update completeness widget
async function updateCompleteness() {
    const response = await fetch(`/api/v1/profiles/${slug}/completeness`);
    const data = await response.json();
    // Update sidebar widget
}
```

#### 5. Metrics Dashboard (`metrics.html`)
**Route:** `/metrics`

Performance metrics dashboard with:
- Summary stats (total calls, tokens, success rate)
- Daily metrics chart
- System metrics (CPU, memory, temperature)
- Model comparison table

#### 6. Logs (`logs.html`)
**Route:** `/logs`

Application logs viewer with:
- Level filtering (ERROR, WARNING, INFO, DEBUG)
- Auto-refresh toggle
- Clear/Copy buttons
- Color-coded log entries

#### 7. Diagnostics (`diagnostics.html`)
**Route:** `/diagnostics`

System diagnostics page with:
- Component health status (green/red indicators)
- Active profile information
- Quick tests (profile access, vector search, LLM connection, templates)
- Test results with duration metrics

---

## Shared CSS (`static/css/common.css`)

### CSS Variables
```css
:root {
    --color-primary: #2563eb;
    --color-success: #10b981;
    --color-warning: #f59e0b;
    --color-error: #ef4444;
    --color-text: #1a1a1a;
    --color-text-muted: #666;
    --color-bg: #f5f5f5;
    --color-card: #fff;
}
```

### Key Classes
```css
/* Layout */
.container { max-width: 900px; margin: 0 auto; }
.container-narrow { max-width: 800px; }

/* Cards */
.card { background: #fff; border-radius: 8px; box-shadow: ... }

/* Buttons */
.btn { padding: 0.75rem 1.25rem; border-radius: 6px; }
.btn-primary { background: var(--color-primary); color: #fff; }
.btn-secondary { background: #e5e7eb; color: #374151; }
.btn-danger { background: var(--color-error); color: #fff; }
.btn-danger-outline { border: 1px solid var(--color-error); color: var(--color-error); }

/* Forms */
.form-control { width: 100%; padding: 0.75rem; border-radius: 6px; }
textarea { min-height: 200px; resize: vertical; }

/* Score/Completeness badges */
.score-badge { padding: 0.5rem 1rem; font-size: 1.5rem; }
.score-excellent, .completeness-excellent { background: #d1fae5; color: #065f46; }
.score-strong, .completeness-good { background: #dbeafe; color: #1e40af; }
.score-moderate, .completeness-fair { background: #fef3c7; color: #92400e; }
.score-weak, .completeness-needs_work { background: #fee2e2; color: #991b1b; }

/* User Menu */
.navbar-user-menu { position: relative; }
.navbar-user-btn { display: flex; align-items: center; gap: 0.5rem; }
.user-avatar {
    width: 32px; height: 32px;
    border-radius: 50%;
    background: #2563eb; color: #fff;
}
.user-dropdown {
    position: absolute; right: 0; top: 100%;
    background: #fff; border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}
.coming-soon-badge {
    font-size: 0.65rem;
    background: #e5e7eb;
    padding: 0.1rem 0.3rem;
}

/* Active Profile Indicator */
.navbar-active-profile { display: flex; align-items: center; gap: 0.5rem; }
.active-profile-dot {
    width: 8px; height: 8px;
    background: #10b981;
    border-radius: 50%;
}

/* Toasts */
.toast-container { position: fixed; bottom: 1rem; right: 1rem; }
.toast { min-width: 300px; padding: 1rem; border-radius: 8px; }

/* Modals */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); }
.modal { background: #fff; border-radius: 12px; max-width: 500px; }

/* Loading */
.spinner { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* Utilities */
.hidden { display: none !important; }
```

---

## Shared JavaScript (`static/js/common.js`)

### Global Namespace
```javascript
window.Scout = window.Scout || {
    currentUser: null,        // User identity from /api/v1/user
    activeProfile: null,      // Active profile from /api/v1/profiles/active
    notificationPollInterval: null,
    seenNotifications: new Set()
};
```

### Utility Functions
```javascript
// HTML escaping (XSS prevention)
function escapeHtml(text) { ... }

// Date formatting
function formatRelativeDate(dateStr) { ... }  // "Today", "2 days ago", etc.

// Capitalize first letter
function capitalizeFirst(str) { ... }

// Score class helper
function getScoreClass(score) { ... }  // Returns: excellent, strong, moderate, weak

// Toast notifications
function showToast(type, title, message, autoDismiss, dismissSeconds) { ... }
```

### User & Profile Loading
```javascript
// Load current user from API
async function loadCurrentUser() {
    const response = await fetch('/api/v1/user');
    if (response.ok) {
        window.Scout.currentUser = await response.json();
        updateNavbarUser();
    }
}

// Load active profile from API
async function loadActiveProfile() {
    const response = await fetch('/api/v1/profiles/active');
    if (response.ok) {
        window.Scout.activeProfile = await response.json();
        updateNavbarActiveProfile();
    }
}

// Update navbar user display
function updateNavbarUser() {
    const user = window.Scout.currentUser;
    // Update avatar, name, email in navbar
}

// Update navbar active profile indicator
function updateNavbarActiveProfile() {
    const profile = window.Scout.activeProfile;
    // Update profile name and dot visibility
}

// Toggle user menu dropdown
function toggleUserMenu(event) {
    event.stopPropagation();
    const dropdown = document.getElementById('navbar-user-dropdown');
    dropdown.classList.toggle('show');
}
```

### Notification Polling
```javascript
// Start polling for notifications
function startNotificationPolling(interval = 3000) { ... }

// Stop notification polling
function stopNotificationPolling() { ... }

// Fetch and display notifications
async function fetchNotifications() { ... }

// Show notification as toast
function showNotificationToast(notification) { ... }

// Mark notification as read
async function markNotificationRead(notificationId) { ... }
```

### Initialization
```javascript
document.addEventListener('DOMContentLoaded', () => {
    // Load user and profile data
    loadCurrentUser();
    loadActiveProfile();

    // Start notification polling
    startNotificationPolling();

    // Close dropdowns when clicking outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.navbar-user-menu')) {
            const dropdown = document.getElementById('navbar-user-dropdown');
            if (dropdown) dropdown.classList.remove('show');
        }
    });

    // Set active nav link based on current path
    const currentPath = window.location.pathname;
    document.querySelectorAll('.nav-link').forEach(link => {
        const href = link.getAttribute('href');
        if (href === currentPath || (href !== '/' && currentPath.startsWith(href))) {
            link.classList.add('active');
        }
    });
});
```

---

## Log Handler

**Location:** `src/web/log_handler.py`

Custom logging handler that stores logs in memory for UI display:

```python
class MemoryLogHandler(logging.Handler):
    """In-memory log handler for web UI display."""

    def __init__(self, max_entries: int = 1000):
        self.entries: deque[LogEntry] = deque(maxlen=max_entries)

    def emit(self, record: logging.LogRecord) -> None:
        entry = LogEntry(
            timestamp=datetime.fromtimestamp(record.created),
            level=record.levelname,
            logger=record.name,
            message=self.format(record),
        )
        self.entries.append(entry)

    def get_entries(
        self,
        level: str | None = None,
        limit: int = 100,
    ) -> list[LogEntry]: ...

    def clear(self) -> None: ...
```

Used by `/api/logs` endpoint to serve logs to the UI.

---

## Dependencies

**Location:** `src/web/dependencies.py`

### JobStore
In-memory store for tracking pipeline jobs:

```python
class JobStore:
    """In-memory job tracking for API."""

    def __init__(self):
        self._jobs: dict[str, PipelineResult] = {}

    def create_job(self, job_id: str) -> PipelineResult: ...
    def update_job(self, job_id: str, result: PipelineResult) -> None: ...
    def get_job(self, job_id: str) -> PipelineResult | None: ...
    def list_jobs(self) -> list[PipelineResult]: ...
```

### Dependency Injection
```python
async def get_store() -> JobStore:
    """Get singleton JobStore."""
    global _job_store
    if _job_store is None:
        _job_store = JobStore()
    return _job_store

async def get_orchestrator() -> PipelineOrchestrator:
    """Get singleton PipelineOrchestrator."""
    return await get_pipeline_orchestrator()
```

---

## Toast Notification System

### JavaScript API
```javascript
// Show toast notification
showToast('success', 'Profile Saved', 'Your profile has been saved.');
showToast('error', 'Error', 'Failed to process job posting.');
showToast('info', 'Processing', 'Your application is being generated...');
showToast('warning', 'Warning', 'Profile completeness is low.');
```

### Auto-dismiss
Toasts auto-dismiss after 5 seconds by default. Can be configured per notification.

### Backend Notifications
The S8 Notification Service pushes notifications that are polled by the frontend and displayed as toasts.

---

## Polling Strategy

For long-running pipeline operations:

```javascript
// Start polling for status updates
function startPolling() {
    pollInterval = setInterval(async () => {
        const response = await fetch(`/api/v1/jobs/${currentJobId}`);
        const status = await response.json();
        updateProgress(status);

        if (status.status === 'completed' || status.status === 'failed') {
            clearInterval(pollInterval);
            // Show results or error
        }
    }, 1000);  // Poll every 1 second
}
```

**Note:** WebSocket was deferred for PoC simplicity.

---

## Responsive Design

The interface is designed for desktop use primarily, but includes basic responsive considerations:
- Max-width containers
- Flexible grid layouts
- Media queries for smaller screens (limited)

---

*Last updated: December 17, 2025*
*No changes from December 16, 2025*
