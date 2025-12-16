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
│       ├── __init__.py
│       └── v1/
│           ├── __init__.py
│           ├── jobs.py          # Job pipeline endpoints
│           ├── profiles.py      # Multi-profile management (NEW)
│           ├── profile.py       # Legacy profile endpoints
│           ├── notifications.py # Notifications
│           ├── logs.py          # Log retrieval
│           ├── metrics.py       # Performance metrics
│           └── diagnostics.py   # Component diagnostics
├── templates/
│   ├── partials/
│   │   └── navbar.html      # Navigation with profile switcher (NEW)
│   ├── index.html           # Dashboard (main page)
│   ├── applications.html    # Applications list
│   ├── profiles_list.html   # Profile management list
│   ├── profile_edit.html    # Profile editor (create/edit)
│   ├── metrics.html         # Performance metrics dashboard
│   ├── logs.html            # Application logs viewer
│   └── diagnostics.html     # System diagnostics page
└── static/
    ├── css/
    │   └── common.css   # Shared styles (profile switcher styles)
    └── js/
        └── common.js    # Shared JS (profile loading, switching)
```

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
- Scout logo/title
- Navigation links (Dashboard, Profiles, Applications, Metrics, Logs, Diagnostics)
- Active page indicator (highlights current page)
- **Profile Switcher (NEW)**: Dropdown showing all profiles with active indicator

```html
<!-- Profile Switcher Structure -->
<div class="navbar-profile-switcher">
    <button class="navbar-profile-btn" onclick="toggleProfileDropdown(event)">
        <span class="profile-indicator-dot" id="navbar-profile-indicator"></span>
        <span id="navbar-profile-name">Loading...</span>
        <span class="navbar-profile-arrow">&#9662;</span>
    </button>
    <div class="profile-dropdown" id="navbar-profile-dropdown">
        <div class="profile-dropdown-header">Switch Profile</div>
        <div class="profile-dropdown-list" id="navbar-profile-list">
            <!-- Profiles populated by JS -->
        </div>
        <div class="profile-dropdown-footer">
            <a href="/profiles" class="profile-dropdown-link">Manage Profiles</a>
            <a href="/profiles/new" class="profile-dropdown-link">+ Create Profile</a>
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
- Generate button
- Progress section (steps with status)
- Results section (score, download buttons)
- Error handling

**Key JavaScript Functions:**
```javascript
// Check profile status
async function checkProfileStatus() { ... }

// Submit job for processing
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

**Key JavaScript Functions:**
```javascript
async function loadApplications() { ... }
function sortApplications(sortBy, sortOrder) { ... }
function renderApplications() { ... }
function updatePagination() { ... }
```

#### 3. Profiles List (`profiles_list.html`)
**Route:** `/profiles`

Profile management page with:
- Summary stats (total profiles, active profile indicator)
- Profile cards with stats (application count, compatibility scores)
- Active profile badge (green indicator)
- Demo profile badge for seeded profiles
- Actions: Edit, Activate, Delete
- Create new profile button

**Key JavaScript Functions:**
```javascript
async function loadProfiles() { ... }
async function activateProfile(slug) { ... }
async function deleteProfile(slug) { ... }
function renderProfileCards() { ... }
```

#### 4. Profile Editor (`profile_edit.html`)
**Route:** `/profiles/new`, `/profiles/{slug}/edit`

Form-based profile editor (create or edit):
- Personal info section (name, email, phone, location, title)
- Summary textarea
- Dynamic skills list (add/remove)
- Dynamic experiences list (add/remove)
- Dynamic education list (add/remove)
- Certifications and languages
- Save button with validation
- Profile completeness score

**Key JavaScript Functions:**
```javascript
async function loadProfile(slug) { ... }
async function saveProfile() { ... }
function addSkillRow() { ... }
function addExperienceRow() { ... }
function validateForm() { ... }
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

/* Forms */
.form-control { width: 100%; padding: 0.75rem; border-radius: 6px; }
textarea { min-height: 200px; resize: vertical; }

/* Badges */
.badge { padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.75rem; }

/* Score badges */
.score-badge { padding: 0.5rem 1rem; font-size: 1.5rem; }
.score-excellent { background: #d1fae5; color: #065f46; }
.score-strong { background: #dbeafe; color: #1e40af; }
.score-moderate { background: #fef3c7; color: #92400e; }
.score-weak { background: #fee2e2; color: #991b1b; }

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
    profilesList: [],
    activeProfileSlug: null,
    notificationPollInterval: null,
    seenNotifications: new Set()
};
```

### Utility Functions
```javascript
// HTML escaping
function escapeHtml(text) { ... }

// Date formatting
function formatRelativeDate(dateStr) { ... }  // "Today", "2 days ago", etc.

// Score class helper
function getScoreClass(score) { ... }  // Returns: excellent, strong, moderate, weak

// Toast notifications
function showToast(type, title, message, autoDismiss, dismissSeconds) { ... }
```

### Profile Management (NEW)
```javascript
// Load profiles from API and update navbar
async function loadProfilesList() {
    const response = await fetch('/api/v1/profiles');
    const data = await response.json();
    window.Scout.profilesList = data.profiles || [];
    window.Scout.activeProfileSlug = data.active_profile_slug;
    updateNavbarProfileSwitcher();
}

// Update navbar profile switcher UI
function updateNavbarProfileSwitcher() {
    // Updates navbar profile name
    // Updates dropdown list with all profiles
    // Shows active indicator for current profile
}

// Toggle profile dropdown visibility
function toggleProfileDropdown(event) { ... }

// Switch to a different profile
async function switchToProfile(slug) {
    await fetch(`/api/v1/profiles/${slug}/activate`, { method: 'POST' });
    // Updates global state
    // Shows toast notification
    // Reloads page to reflect changes
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
```

### Initialization
```javascript
document.addEventListener('DOMContentLoaded', () => {
    // Load profiles for switcher
    loadProfilesList();

    // Start notification polling
    startNotificationPolling();

    // Close dropdowns when clicking outside
    document.addEventListener('click', (e) => { ... });

    // Set active nav link based on current path
    // ...
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
showToast('success', 'Profile Saved', 'Your profile has been saved and indexed.');
showToast('error', 'Error', 'Failed to process job posting.');
showToast('info', 'Processing', 'Your application is being generated...');
showToast('warning', 'Warning', 'Profile needs to be re-indexed.');
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
        const response = await fetch(`/api/status/${currentJobId}`);
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

*Last updated: December 16, 2025*
*Updated: Added profile switcher, new pages (metrics, diagnostics), updated routes structure*
