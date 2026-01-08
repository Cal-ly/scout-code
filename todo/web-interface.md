# Web Interface TODOs

## Overview
The Scout web interface provides a clean, functional UI for the job application pipeline. This document tracks improvements, bugs, and enhancement requests.

**Status**: PoC Complete - Consolidation Phase

---

## Recently Completed (Dec 14, 2025)

### Navigation & Structure
- [x] Created shared static directory (`src/web/static/css/`, `src/web/static/js/`)
- [x] Extracted common CSS to `common.css`
- [x] Extracted common JavaScript to `common.js`
- [x] Created navbar partial (`partials/navbar.html`)
- [x] Added navbar to all pages (index, applications, profiles_list, profile_edit, logs)
- [x] Added dedicated logs page (`/logs`)
- [x] Updated page routes in `pages.py`
- [x] Mounted static files in `main.py`

### Bug Fixes
- [x] Fixed date field handling (uses `submitted_at` with `created_at` fallback)
- [x] Ensured profile list pages work with single-profile API

---

## Outstanding Issues (Priority Order)

### High Priority

- [ ] **Profile Switcher Activation**: The `/api/profiles/{filename}/activate` endpoint is not implemented. Navbar switcher gracefully falls back but doesn't actually switch profiles.
  - **Workaround**: Single-profile mode works; multi-profile is PoC-deferred
  - **Location**: `common.js:switchToProfile()`, needs backend route

- [ ] **Progress Bar Reliability**: On Raspberry Pi, long-running tasks may show stale progress if polling fails
  - **Root cause**: 1-second poll interval + potential network issues
  - **Suggestion**: Add exponential backoff on poll failures

### Medium Priority

- [ ] **Keyboard Accessibility**: Modal dialogs need ESC key handling
  - **Location**: `common.css` modal styles, needs JS handler

- [ ] **Colorblind-friendly Indicators**: Score badges rely on color alone
  - **Suggestion**: Add icons or patterns to distinguish score levels

- [ ] **Log Page Filtering**: Add date range filtering for logs
  - **Location**: `logs.html`, would need API enhancement

### Low Priority / Nice-to-Have

- [ ] **Dark Mode**: User preference for dark/light theme
  - **Effort**: Medium - need CSS variables + localStorage

- [ ] **Export Applications**: Download history as CSV/JSON
  - **Location**: Applications page, new endpoint needed

- [ ] **Profile Templates**: Pre-fill with industry-specific templates
  - **Status**: Templates exist in `profile_edit.html`, could expand

- [ ] **Responsive Improvements**: Better mobile experience
  - **Status**: Basic responsive CSS exists, needs refinement

---

## Deferred (Out of PoC Scope)

These items are explicitly deferred per `docs/guides/Scout_PoC_Scope_Document.md`:

- [-] **WebSocket Updates**: Real-time push instead of polling
- [-] **Multi-Profile Management**: Full API for multiple profiles
- [-] **File Upload**: Upload job postings as files
- [-] **DOCX Output**: Currently PDF only
- [-] **Email Notifications**: In-app toast only for PoC

---

## Technical Notes

### File Locations
```
src/web/
├── main.py              # FastAPI app, static file mounting
├── routes/
│   ├── pages.py         # HTML page routes
│   ├── api.py           # REST API endpoints
│   └── profile.py       # Profile API (single-profile)
├── templates/
│   ├── partials/
│   │   └── navbar.html  # Shared navigation
│   ├── index.html       # Dashboard
│   ├── applications.html
│   ├── profiles_list.html
│   ├── profile_edit.html
│   └── logs.html        # Dedicated log viewer
└── static/
    ├── css/
    │   └── common.css   # Shared styles
    └── js/
        └── common.js    # Shared utilities
```

### CSS/JS Organization
- **common.css**: Navbar, cards, buttons, badges, toast, modals, utilities
- **common.js**: Toast notifications, profile loading, notification polling
- Page-specific styles remain inline in `<style>` tags

### API Dependencies
- `/api/profile/status` - Check profile existence
- `/api/profile/retrieve` - Get profile text
- `/api/jobs` - List all applications
- `/api/status/{job_id}` - Pipeline status polling
- `/api/notifications` - Toast notifications
- `/api/logs` - Log entries

---

*Last updated: January 2026*
