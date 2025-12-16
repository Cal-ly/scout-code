# Work Package 4: Web Interface Updates

## Overview

This work package updates the web interface to work with the new normalized database schema and improves the user experience with a proper user menu and tabbed profile editor.

**Prerequisites:** 
- WP1-3 complete (database schema, service, Collector integration, API routes)

**Reference:** See `docs/tasks/REFACTOR_GUIDE.md` for architectural context.

**Time Estimate:** 4-5 hours

---

## Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `templates/partials/navbar.html` | UPDATE | Replace profile switcher with user menu |
| `templates/profiles_list.html` | REWRITE | Use new API, show completeness scores |
| `templates/profile_edit.html` | REWRITE | Tabbed editor for normalized data |
| `templates/index.html` | UPDATE | Show active profile info correctly |
| `static/js/common.js` | UPDATE | New API calls, user menu logic |
| `static/css/common.css` | UPDATE | Add tab styles, completeness widget |

---

## Part 1: Navbar Update

**Update file:** `src/web/templates/partials/navbar.html`

### Changes

Replace the profile switcher dropdown with a simpler user menu. Profile switching will be done from the Profiles page, not the navbar.

```html
<!-- Scout Navigation Bar -->
<nav class="navbar">
    <a href="/" class="navbar-brand">
        <div class="navbar-brand-icon">S</div>
        <span class="navbar-brand-text">Scout</span>
    </a>

    <div class="navbar-nav">
        <a href="/" class="nav-link" data-page="dashboard">Dashboard</a>
        <a href="/profiles" class="nav-link" data-page="profiles">Profiles</a>
        <a href="/applications" class="nav-link" data-page="applications">Applications</a>
        <a href="/metrics" class="nav-link" data-page="metrics">Metrics</a>
        <a href="/logs" class="nav-link" data-page="logs">Logs</a>
        <a href="/diagnostics" class="nav-link" data-page="diagnostics">Diagnostics</a>
    </div>

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
                <div class="user-dropdown-divider"></div>
                <a href="/profiles" class="user-dropdown-item">
                    <span class="dropdown-icon">&#128100;</span>
                    Manage Profiles
                </a>
                <button class="user-dropdown-item disabled" disabled>
                    <span class="dropdown-icon">&#9881;</span>
                    Settings
                    <span class="coming-soon-badge">Soon</span>
                </button>
                <div class="user-dropdown-divider"></div>
                <button class="user-dropdown-item disabled" disabled>
                    <span class="dropdown-icon">&#128682;</span>
                    Log Out
                    <span class="coming-soon-badge">Soon</span>
                </button>
            </div>
        </div>
    </div>
</nav>
```

---

## Part 2: Profiles List Page

**Rewrite file:** `src/web/templates/profiles_list.html`

### Key Changes

1. Use new `/api/v1/profiles` endpoint that returns normalized data
2. Show profile completeness score on each card
3. Add "Set Active" button to non-active profiles
4. Show skill/experience/education counts
5. Remove archived concept (not in new schema)
6. Add profile creation button that goes to tabbed editor

### Template Structure

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Scout - Manage Profiles</title>
    <link rel="stylesheet" href="/static/css/common.css">
    <style>
        /* Page-specific styles */
        .page-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
        }
        .page-header h2 {
            margin: 0;
        }

        /* Summary stats row */
        .summary-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
            margin-bottom: 1.5rem;
        }
        .summary-stat {
            background: #fff;
            border-radius: 8px;
            padding: 1rem;
            text-align: center;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .summary-stat-value {
            font-size: 1.5rem;
            font-weight: 700;
            color: #2563eb;
        }
        .summary-stat-label {
            font-size: 0.85rem;
            color: #666;
        }

        /* Active profile banner */
        .active-banner {
            background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
            border: 2px solid #10b981;
            border-radius: 8px;
            padding: 1rem 1.25rem;
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }
        .active-banner-icon {
            font-size: 1.5rem;
        }
        .active-banner-text {
            flex: 1;
        }
        .active-banner-text strong {
            color: #065f46;
        }
        .active-banner-text .subtitle {
            color: #047857;
            font-size: 0.9rem;
        }

        /* Profile cards */
        .profiles-grid {
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }
        .profile-card {
            background: #fff;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            padding: 1.25rem;
            display: flex;
            gap: 1rem;
            transition: all 0.2s;
            border: 2px solid transparent;
        }
        .profile-card:hover {
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        .profile-card.active {
            border-color: #10b981;
            background: linear-gradient(135deg, #fff 0%, #f0fdf4 100%);
        }
        
        .profile-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-top: 0.25rem;
            flex-shrink: 0;
        }
        .profile-indicator.active { background: #10b981; }
        .profile-indicator.inactive { background: #e5e7eb; }
        
        .profile-content {
            flex: 1;
            min-width: 0;
        }
        .profile-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 0.5rem;
            gap: 1rem;
        }
        .profile-name {
            font-size: 1.1rem;
            font-weight: 600;
            color: #1a1a1a;
        }
        .profile-title {
            color: #666;
            font-size: 0.9rem;
        }
        .profile-slug {
            color: #9ca3af;
            font-size: 0.8rem;
            font-family: monospace;
        }
        
        /* Completeness indicator */
        .completeness-indicator {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.35rem 0.75rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        .completeness-indicator.excellent {
            background: #d1fae5;
            color: #065f46;
        }
        .completeness-indicator.good {
            background: #dbeafe;
            color: #1e40af;
        }
        .completeness-indicator.fair {
            background: #fef3c7;
            color: #92400e;
        }
        .completeness-indicator.needs_work {
            background: #fee2e2;
            color: #991b1b;
        }
        
        .profile-stats {
            display: flex;
            flex-wrap: wrap;
            gap: 1rem;
            margin: 0.75rem 0;
        }
        .stat {
            display: flex;
            align-items: center;
            gap: 0.25rem;
            font-size: 0.85rem;
            color: #666;
        }
        .stat-icon {
            font-size: 0.9rem;
        }
        .stat-value {
            font-weight: 600;
            color: #374151;
        }
        
        .profile-badges {
            display: flex;
            gap: 0.5rem;
            margin-top: 0.5rem;
        }
        .badge {
            font-size: 0.75rem;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-weight: 500;
        }
        .badge-active {
            background: #d1fae5;
            color: #065f46;
        }
        .badge-demo {
            background: #e5e7eb;
            color: #6b7280;
        }
        
        .profile-actions {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
            align-items: flex-end;
        }
        .actions-row {
            display: flex;
            gap: 0.5rem;
        }

        /* Empty state */
        .empty-state {
            text-align: center;
            padding: 3rem;
            background: #fff;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .empty-state-icon {
            font-size: 3rem;
            margin-bottom: 1rem;
        }
        .empty-state h3 {
            color: #374151;
            margin-bottom: 0.5rem;
        }
        .empty-state p {
            color: #6b7280;
            margin-bottom: 1.5rem;
        }

        /* Delete modal */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.5);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 1000;
        }
        .modal-overlay.show {
            display: flex;
        }
        .modal {
            background: #fff;
            border-radius: 8px;
            padding: 1.5rem;
            max-width: 400px;
            width: 90%;
        }
        .modal h3 {
            margin: 0 0 1rem 0;
        }
        .modal p {
            color: #666;
            margin-bottom: 1.5rem;
        }
        .modal-actions {
            display: flex;
            gap: 0.75rem;
            justify-content: flex-end;
        }

        .hidden { display: none !important; }
    </style>
</head>
<body>
    {% include 'partials/navbar.html' %}

    <main class="container">
        <!-- Page Header -->
        <div class="page-header">
            <h2>Your Profiles</h2>
            <a href="/profiles/new" class="btn btn-primary">+ Create Profile</a>
        </div>

        <!-- Summary Stats -->
        <div class="summary-stats" id="summary-stats">
            <div class="summary-stat">
                <div class="summary-stat-value" id="stat-total">0</div>
                <div class="summary-stat-label">Total Profiles</div>
            </div>
            <div class="summary-stat">
                <div class="summary-stat-value" id="stat-active-score">-</div>
                <div class="summary-stat-label">Active Profile Score</div>
            </div>
            <div class="summary-stat">
                <div class="summary-stat-value" id="stat-applications">0</div>
                <div class="summary-stat-label">Total Applications</div>
            </div>
        </div>

        <!-- Active Profile Banner -->
        <div class="active-banner hidden" id="active-banner">
            <span class="active-banner-icon">✓</span>
            <div class="active-banner-text">
                <strong id="active-profile-name">No active profile</strong><br>
                <span class="subtitle" id="active-profile-title">-</span>
            </div>
            <a href="#" id="active-profile-edit-link" class="btn btn-sm btn-secondary">Edit</a>
        </div>

        <!-- Loading State -->
        <div class="loading" id="loading-state">
            <div class="spinner"></div>
        </div>

        <!-- Empty State -->
        <div class="empty-state hidden" id="empty-state">
            <div class="empty-state-icon">📋</div>
            <h3>No Profiles Yet</h3>
            <p>Create your first profile to start matching jobs and generating tailored applications.</p>
            <a href="/profiles/new" class="btn btn-primary">Create Your First Profile</a>
        </div>

        <!-- Profiles Grid -->
        <div class="profiles-grid hidden" id="profiles-grid">
            <!-- Profiles will be inserted here by JS -->
        </div>
    </main>

    <!-- Delete Confirmation Modal -->
    <div class="modal-overlay" id="delete-modal">
        <div class="modal">
            <h3>Delete Profile?</h3>
            <p>This will permanently delete <strong id="delete-profile-name"></strong> and all its data. This action cannot be undone.</p>
            <div class="modal-actions">
                <button class="btn btn-secondary" onclick="closeDeleteModal()">Cancel</button>
                <button class="btn btn-danger" id="confirm-delete-btn">Delete</button>
            </div>
        </div>
    </div>

    <!-- Toast Container -->
    <div class="toast-container" id="toast-container"></div>

    <script src="/static/js/common.js"></script>
    <script>
        // State
        let profiles = [];
        let activeProfile = null;
        let deleteTargetSlug = null;

        // DOM Elements
        const loadingState = document.getElementById('loading-state');
        const emptyState = document.getElementById('empty-state');
        const profilesGrid = document.getElementById('profiles-grid');
        const activeBanner = document.getElementById('active-banner');

        // Initialize
        document.addEventListener('DOMContentLoaded', loadProfiles);

        async function loadProfiles() {
            loadingState.classList.remove('hidden');
            emptyState.classList.add('hidden');
            profilesGrid.classList.add('hidden');

            try {
                const response = await fetch('/api/v1/profiles');
                if (!response.ok) throw new Error('Failed to load profiles');

                const data = await response.json();
                profiles = data.profiles || [];
                activeProfile = profiles.find(p => p.is_active) || null;

                // Update stats
                document.getElementById('stat-total').textContent = profiles.length;
                
                // Calculate total applications
                const totalApps = profiles.reduce((sum, p) => sum + (p.stats?.application_count || 0), 0);
                document.getElementById('stat-applications').textContent = totalApps;

                // Update active banner
                if (activeProfile) {
                    activeBanner.classList.remove('hidden');
                    document.getElementById('active-profile-name').textContent = activeProfile.name;
                    document.getElementById('active-profile-title').textContent = activeProfile.title || 'No title set';
                    document.getElementById('active-profile-edit-link').href = `/profiles/${activeProfile.slug}/edit`;
                    
                    // Fetch completeness for active profile
                    try {
                        const compResponse = await fetch(`/api/v1/profiles/${activeProfile.slug}/completeness`);
                        if (compResponse.ok) {
                            const comp = await compResponse.json();
                            document.getElementById('stat-active-score').textContent = `${comp.overall_score}%`;
                        }
                    } catch (e) {
                        console.warn('Could not fetch completeness:', e);
                    }
                } else {
                    activeBanner.classList.add('hidden');
                    document.getElementById('stat-active-score').textContent = '-';
                }

                loadingState.classList.add('hidden');

                if (profiles.length === 0) {
                    emptyState.classList.remove('hidden');
                } else {
                    profilesGrid.classList.remove('hidden');
                    await renderProfiles();
                }

            } catch (error) {
                console.error('Error loading profiles:', error);
                loadingState.classList.add('hidden');
                showToast('error', 'Error', 'Failed to load profiles');
            }
        }

        async function renderProfiles() {
            // Fetch completeness for all profiles
            const completenessMap = {};
            await Promise.all(profiles.map(async (profile) => {
                try {
                    const response = await fetch(`/api/v1/profiles/${profile.slug}/completeness`);
                    if (response.ok) {
                        completenessMap[profile.slug] = await response.json();
                    }
                } catch (e) {
                    console.warn(`Could not fetch completeness for ${profile.slug}`);
                }
            }));

            profilesGrid.innerHTML = profiles.map(profile => {
                const isActive = profile.is_active;
                const comp = completenessMap[profile.slug];
                const stats = profile.stats || {};

                return `
                    <div class="profile-card ${isActive ? 'active' : ''}" data-slug="${escapeHtml(profile.slug)}">
                        <div class="profile-indicator ${isActive ? 'active' : 'inactive'}"></div>
                        <div class="profile-content">
                            <div class="profile-header">
                                <div>
                                    <div class="profile-name">${escapeHtml(profile.name)}</div>
                                    <div class="profile-title">${escapeHtml(profile.title || 'No title')}</div>
                                    <div class="profile-slug">${escapeHtml(profile.slug)}</div>
                                </div>
                                ${comp ? `
                                    <div class="completeness-indicator ${comp.level}">
                                        ${comp.overall_score}% ${capitalizeFirst(comp.level.replace('_', ' '))}
                                    </div>
                                ` : ''}
                            </div>
                            <div class="profile-stats">
                                <div class="stat">
                                    <span class="stat-icon">🛠</span>
                                    <span><span class="stat-value">${stats.skill_count || 0}</span> skills</span>
                                </div>
                                <div class="stat">
                                    <span class="stat-icon">💼</span>
                                    <span><span class="stat-value">${stats.experience_count || 0}</span> experiences</span>
                                </div>
                                <div class="stat">
                                    <span class="stat-icon">🎓</span>
                                    <span><span class="stat-value">${stats.education_count || 0}</span> education</span>
                                </div>
                                <div class="stat">
                                    <span class="stat-icon">📄</span>
                                    <span><span class="stat-value">${stats.application_count || 0}</span> applications</span>
                                </div>
                                ${stats.avg_compatibility_score ? `
                                    <div class="stat">
                                        <span class="stat-icon">⭐</span>
                                        <span><span class="stat-value">${stats.avg_compatibility_score.toFixed(0)}%</span> avg score</span>
                                    </div>
                                ` : ''}
                            </div>
                            <div class="profile-badges">
                                ${isActive ? '<span class="badge badge-active">Active</span>' : ''}
                                ${profile.is_demo ? '<span class="badge badge-demo">Demo</span>' : ''}
                            </div>
                        </div>
                        <div class="profile-actions">
                            <div class="actions-row">
                                <a href="/profiles/${escapeHtml(profile.slug)}/edit" class="btn btn-sm btn-primary">Edit</a>
                                ${!isActive ? `
                                    <button class="btn btn-sm btn-secondary" onclick="activateProfile('${escapeHtml(profile.slug)}')">
                                        Set Active
                                    </button>
                                ` : ''}
                            </div>
                            <div class="actions-row">
                                ${!isActive ? `
                                    <button class="btn btn-sm btn-danger-outline" onclick="showDeleteModal('${escapeHtml(profile.slug)}', '${escapeHtml(profile.name)}')">
                                        Delete
                                    </button>
                                ` : ''}
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        }

        async function activateProfile(slug) {
            try {
                showToast('info', 'Activating', 'Setting profile as active...');

                const response = await fetch(`/api/v1/profiles/${encodeURIComponent(slug)}/activate`, {
                    method: 'POST'
                });

                if (!response.ok) throw new Error('Failed to activate profile');

                const result = await response.json();
                showToast('success', 'Activated', result.message);
                
                // Reload to show updated state
                await loadProfiles();

            } catch (error) {
                console.error('Error activating profile:', error);
                showToast('error', 'Error', 'Failed to activate profile');
            }
        }

        function showDeleteModal(slug, name) {
            deleteTargetSlug = slug;
            document.getElementById('delete-profile-name').textContent = name;
            document.getElementById('delete-modal').classList.add('show');

            document.getElementById('confirm-delete-btn').onclick = async () => {
                await deleteProfile(slug);
                closeDeleteModal();
            };
        }

        function closeDeleteModal() {
            document.getElementById('delete-modal').classList.remove('show');
            deleteTargetSlug = null;
        }

        async function deleteProfile(slug) {
            try {
                const response = await fetch(`/api/v1/profiles/${encodeURIComponent(slug)}`, {
                    method: 'DELETE'
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Failed to delete');
                }

                showToast('success', 'Deleted', 'Profile has been deleted');
                await loadProfiles();

            } catch (error) {
                console.error('Error deleting profile:', error);
                showToast('error', 'Error', error.message || 'Failed to delete profile');
            }
        }

        function capitalizeFirst(str) {
            if (!str) return '';
            return str.charAt(0).toUpperCase() + str.slice(1);
        }
    </script>
</body>
</html>
```

---

## Part 3: Tabbed Profile Editor

**Rewrite file:** `src/web/templates/profile_edit.html`

This is the largest change - a completely new tabbed editor for the normalized profile data.

### Key Features

1. **5 Tabs:** Overview, Skills, Experience, Education, Certifications
2. **Inline editing** for each section
3. **Reorderable items** with up/down buttons
4. **Add/Remove** functionality for list items
5. **Completeness widget** showing score and suggestions
6. **Save button** sends full profile via PUT

### Template Structure

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Scout - Edit Profile</title>
    <link rel="stylesheet" href="/static/css/common.css">
    <style>
        /* Profile Editor Styles */
        .editor-container {
            display: grid;
            grid-template-columns: 1fr 300px;
            gap: 1.5rem;
            max-width: 1200px;
            margin: 0 auto;
        }
        
        @media (max-width: 900px) {
            .editor-container {
                grid-template-columns: 1fr;
            }
            .sidebar {
                order: -1;
            }
        }

        /* Tabs */
        .editor-tabs {
            display: flex;
            border-bottom: 2px solid #e5e7eb;
            margin-bottom: 1.5rem;
            overflow-x: auto;
        }
        .editor-tab {
            padding: 0.75rem 1.25rem;
            font-size: 0.95rem;
            font-weight: 500;
            color: #666;
            background: none;
            border: none;
            border-bottom: 2px solid transparent;
            cursor: pointer;
            transition: all 0.2s;
            margin-bottom: -2px;
            white-space: nowrap;
        }
        .editor-tab:hover {
            color: #2563eb;
        }
        .editor-tab.active {
            color: #2563eb;
            border-bottom-color: #2563eb;
        }
        .editor-tab .tab-count {
            background: #e5e7eb;
            color: #666;
            font-size: 0.75rem;
            padding: 0.1rem 0.4rem;
            border-radius: 10px;
            margin-left: 0.5rem;
        }
        .editor-tab.active .tab-count {
            background: #dbeafe;
            color: #2563eb;
        }

        /* Tab Content */
        .tab-content {
            display: none;
        }
        .tab-content.active {
            display: block;
        }

        /* Form styles */
        .form-row {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 1rem;
        }
        .form-group {
            margin-bottom: 1rem;
        }
        .form-group label {
            display: block;
            font-weight: 500;
            color: #374151;
            margin-bottom: 0.5rem;
        }
        .form-group input,
        .form-group textarea,
        .form-group select {
            width: 100%;
            padding: 0.75rem;
            border: 1px solid #d1d5db;
            border-radius: 6px;
            font-size: 0.95rem;
        }
        .form-group input:focus,
        .form-group textarea:focus,
        .form-group select:focus {
            outline: none;
            border-color: #2563eb;
            box-shadow: 0 0 0 3px rgba(37,99,235,0.1);
        }
        .form-group textarea {
            min-height: 100px;
            resize: vertical;
        }
        .form-hint {
            font-size: 0.8rem;
            color: #6b7280;
            margin-top: 0.25rem;
        }

        /* Item cards (for skills, experiences, etc.) */
        .items-list {
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
        }
        .item-card {
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 1rem;
        }
        .item-card-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 0.75rem;
        }
        .item-card-title {
            font-weight: 600;
            color: #1f2937;
        }
        .item-card-subtitle {
            font-size: 0.9rem;
            color: #6b7280;
        }
        .item-card-actions {
            display: flex;
            gap: 0.25rem;
        }
        .item-card-actions button {
            padding: 0.25rem 0.5rem;
            font-size: 0.8rem;
            background: #fff;
            border: 1px solid #d1d5db;
            border-radius: 4px;
            cursor: pointer;
        }
        .item-card-actions button:hover {
            background: #f3f4f6;
        }
        .item-card-actions button.delete:hover {
            background: #fee2e2;
            border-color: #fecaca;
            color: #dc2626;
        }

        /* Expandable item card */
        .item-card.expandable .item-card-header {
            cursor: pointer;
        }
        .item-card-body {
            display: none;
            padding-top: 0.75rem;
            border-top: 1px solid #e5e7eb;
            margin-top: 0.75rem;
        }
        .item-card.expanded .item-card-body {
            display: block;
        }

        /* Achievement list */
        .achievements-list {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }
        .achievement-item {
            display: flex;
            gap: 0.5rem;
            align-items: center;
        }
        .achievement-item input {
            flex: 1;
        }

        /* Add item button */
        .add-item-btn {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.75rem 1rem;
            background: #f9fafb;
            border: 2px dashed #d1d5db;
            border-radius: 8px;
            color: #6b7280;
            cursor: pointer;
            transition: all 0.2s;
            width: 100%;
            justify-content: center;
        }
        .add-item-btn:hover {
            border-color: #2563eb;
            color: #2563eb;
            background: #eff6ff;
        }

        /* Sidebar */
        .sidebar {
            position: sticky;
            top: 1rem;
        }
        .sidebar-card {
            background: #fff;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            padding: 1.25rem;
            margin-bottom: 1rem;
        }
        .sidebar-card h3 {
            font-size: 1rem;
            margin: 0 0 1rem 0;
            color: #374151;
        }

        /* Completeness widget */
        .completeness-score {
            text-align: center;
            margin-bottom: 1rem;
        }
        .completeness-circle {
            width: 100px;
            height: 100px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 0.5rem;
            font-size: 1.5rem;
            font-weight: 700;
        }
        .completeness-circle.excellent { background: #d1fae5; color: #065f46; }
        .completeness-circle.good { background: #dbeafe; color: #1e40af; }
        .completeness-circle.fair { background: #fef3c7; color: #92400e; }
        .completeness-circle.needs_work { background: #fee2e2; color: #991b1b; }
        
        .completeness-level {
            font-weight: 600;
            margin-bottom: 1rem;
        }
        .suggestions-list {
            text-align: left;
        }
        .suggestion-item {
            display: flex;
            gap: 0.5rem;
            align-items: flex-start;
            font-size: 0.85rem;
            color: #6b7280;
            margin-bottom: 0.5rem;
        }
        .suggestion-item::before {
            content: "💡";
            flex-shrink: 0;
        }

        /* Action buttons */
        .editor-actions {
            display: flex;
            gap: 1rem;
            margin-top: 1.5rem;
            padding-top: 1.5rem;
            border-top: 1px solid #e5e7eb;
        }
        .editor-actions .btn-primary {
            flex: 2;
        }
        .editor-actions .btn-secondary {
            flex: 1;
        }

        /* Loading overlay */
        .loading-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(255,255,255,0.8);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 1000;
        }
        .loading-overlay.show {
            display: flex;
        }

        .hidden { display: none !important; }
    </style>
</head>
<body>
    {% include 'partials/navbar.html' %}

    <main class="container">
        <!-- Page Header -->
        <div class="page-header" style="margin-bottom: 1.5rem;">
            <div>
                <h2 id="page-title">Edit Profile</h2>
                <p id="page-subtitle" style="color: #666; margin: 0;">Update your professional information</p>
            </div>
            <a href="/profiles" class="btn btn-secondary">← Back to Profiles</a>
        </div>

        <div class="editor-container">
            <!-- Main Editor -->
            <div class="editor-main">
                <div class="card">
                    <!-- Tabs -->
                    <div class="editor-tabs">
                        <button class="editor-tab active" data-tab="overview" onclick="switchTab('overview')">
                            Overview
                        </button>
                        <button class="editor-tab" data-tab="skills" onclick="switchTab('skills')">
                            Skills <span class="tab-count" id="skills-count">0</span>
                        </button>
                        <button class="editor-tab" data-tab="experience" onclick="switchTab('experience')">
                            Experience <span class="tab-count" id="experience-count">0</span>
                        </button>
                        <button class="editor-tab" data-tab="education" onclick="switchTab('education')">
                            Education <span class="tab-count" id="education-count">0</span>
                        </button>
                        <button class="editor-tab" data-tab="certifications" onclick="switchTab('certifications')">
                            Certifications <span class="tab-count" id="certifications-count">0</span>
                        </button>
                    </div>

                    <!-- Overview Tab -->
                    <div class="tab-content active" id="tab-overview">
                        <div class="form-row">
                            <div class="form-group">
                                <label for="profile-name">Profile Name *</label>
                                <input type="text" id="profile-name" placeholder="e.g., Backend Focus" required>
                                <p class="form-hint">A name to identify this profile</p>
                            </div>
                            <div class="form-group">
                                <label for="profile-title">Professional Title</label>
                                <input type="text" id="profile-title" placeholder="e.g., Senior Software Engineer">
                            </div>
                        </div>
                        <div class="form-row">
                            <div class="form-group">
                                <label for="profile-email">Email</label>
                                <input type="email" id="profile-email" placeholder="your.email@example.com">
                            </div>
                            <div class="form-group">
                                <label for="profile-phone">Phone</label>
                                <input type="tel" id="profile-phone" placeholder="+1-555-0123">
                            </div>
                        </div>
                        <div class="form-group">
                            <label for="profile-location">Location</label>
                            <input type="text" id="profile-location" placeholder="e.g., San Francisco, CA">
                        </div>
                        <div class="form-group">
                            <label for="profile-summary">Professional Summary</label>
                            <textarea id="profile-summary" rows="5" placeholder="Write a compelling summary of your professional background, key strengths, and career goals..."></textarea>
                            <p class="form-hint">200+ characters recommended for best results</p>
                        </div>
                    </div>

                    <!-- Skills Tab -->
                    <div class="tab-content" id="tab-skills">
                        <div class="items-list" id="skills-list">
                            <!-- Skills populated by JS -->
                        </div>
                        <button class="add-item-btn" onclick="addSkill()">
                            + Add Skill
                        </button>
                    </div>

                    <!-- Experience Tab -->
                    <div class="tab-content" id="tab-experience">
                        <div class="items-list" id="experience-list">
                            <!-- Experiences populated by JS -->
                        </div>
                        <button class="add-item-btn" onclick="addExperience()">
                            + Add Experience
                        </button>
                    </div>

                    <!-- Education Tab -->
                    <div class="tab-content" id="tab-education">
                        <div class="items-list" id="education-list">
                            <!-- Education populated by JS -->
                        </div>
                        <button class="add-item-btn" onclick="addEducation()">
                            + Add Education
                        </button>
                    </div>

                    <!-- Certifications Tab -->
                    <div class="tab-content" id="tab-certifications">
                        <div class="items-list" id="certifications-list">
                            <!-- Certifications populated by JS -->
                        </div>
                        <button class="add-item-btn" onclick="addCertification()">
                            + Add Certification
                        </button>
                    </div>

                    <!-- Actions -->
                    <div class="editor-actions">
                        <button class="btn btn-primary" onclick="saveProfile()">
                            Save Profile
                        </button>
                        <a href="/profiles" class="btn btn-secondary">Cancel</a>
                    </div>
                </div>
            </div>

            <!-- Sidebar -->
            <div class="sidebar">
                <!-- Completeness Score -->
                <div class="sidebar-card">
                    <h3>Profile Completeness</h3>
                    <div class="completeness-score" id="completeness-widget">
                        <div class="completeness-circle needs_work" id="completeness-circle">
                            <span id="completeness-score">0%</span>
                        </div>
                        <div class="completeness-level" id="completeness-level">Loading...</div>
                    </div>
                    <div class="suggestions-list" id="suggestions-list">
                        <!-- Suggestions populated by JS -->
                    </div>
                </div>

                <!-- Quick Stats -->
                <div class="sidebar-card">
                    <h3>Quick Stats</h3>
                    <div style="font-size: 0.9rem; color: #666;">
                        <p><strong id="stat-skills">0</strong> skills</p>
                        <p><strong id="stat-experience">0</strong> experiences</p>
                        <p><strong id="stat-education">0</strong> education entries</p>
                        <p><strong id="stat-certifications">0</strong> certifications</p>
                    </div>
                </div>
            </div>
        </div>
    </main>

    <!-- Loading Overlay -->
    <div class="loading-overlay" id="loading-overlay">
        <div class="spinner"></div>
    </div>

    <!-- Toast Container -->
    <div class="toast-container" id="toast-container"></div>

    <script src="/static/js/common.js"></script>
    <script>
        // Get profile slug from URL
        const pathParts = window.location.pathname.split('/');
        const isNewProfile = pathParts.includes('new');
        const profileSlug = isNewProfile ? null : pathParts[pathParts.indexOf('profiles') + 1];

        // Profile data state
        let profileData = {
            name: '',
            title: '',
            email: '',
            phone: '',
            location: '',
            summary: '',
            skills: [],
            experiences: [],
            education: [],
            certifications: [],
            languages: []
        };

        // Skill levels for dropdown
        const skillLevels = [
            { value: '', label: 'Select level' },
            { value: 'beginner', label: 'Beginner' },
            { value: 'intermediate', label: 'Intermediate' },
            { value: 'advanced', label: 'Advanced' },
            { value: 'expert', label: 'Expert' }
        ];

        // Initialize
        document.addEventListener('DOMContentLoaded', async () => {
            if (isNewProfile) {
                document.getElementById('page-title').textContent = 'Create New Profile';
                document.getElementById('page-subtitle').textContent = 'Add your professional information';
                updateTabCounts();
                updateCompleteness();
            } else {
                await loadProfile();
            }
        });

        // Tab switching
        function switchTab(tabName) {
            // Update tab buttons
            document.querySelectorAll('.editor-tab').forEach(tab => {
                tab.classList.toggle('active', tab.dataset.tab === tabName);
            });
            // Update tab content
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.toggle('active', content.id === `tab-${tabName}`);
            });
        }

        // Load existing profile
        async function loadProfile() {
            showLoading(true);
            try {
                const response = await fetch(`/api/v1/profiles/${profileSlug}`);
                if (!response.ok) throw new Error('Profile not found');

                const data = await response.json();
                profileData = {
                    name: data.name || '',
                    title: data.title || '',
                    email: data.email || '',
                    phone: data.phone || '',
                    location: data.location || '',
                    summary: data.summary || '',
                    skills: data.skills || [],
                    experiences: data.experiences || [],
                    education: data.education || [],
                    certifications: data.certifications || [],
                    languages: data.languages || []
                };

                // Populate form
                document.getElementById('profile-name').value = profileData.name;
                document.getElementById('profile-title').value = profileData.title;
                document.getElementById('profile-email').value = profileData.email;
                document.getElementById('profile-phone').value = profileData.phone;
                document.getElementById('profile-location').value = profileData.location;
                document.getElementById('profile-summary').value = profileData.summary;

                // Render lists
                renderSkills();
                renderExperiences();
                renderEducation();
                renderCertifications();
                updateTabCounts();

                // Update completeness from API response
                if (data.completeness) {
                    displayCompleteness(data.completeness);
                }

            } catch (error) {
                console.error('Error loading profile:', error);
                showToast('error', 'Error', 'Failed to load profile');
            } finally {
                showLoading(false);
            }
        }

        // Update tab counts
        function updateTabCounts() {
            document.getElementById('skills-count').textContent = profileData.skills.length;
            document.getElementById('experience-count').textContent = profileData.experiences.length;
            document.getElementById('education-count').textContent = profileData.education.length;
            document.getElementById('certifications-count').textContent = profileData.certifications.length;

            // Quick stats
            document.getElementById('stat-skills').textContent = profileData.skills.length;
            document.getElementById('stat-experience').textContent = profileData.experiences.length;
            document.getElementById('stat-education').textContent = profileData.education.length;
            document.getElementById('stat-certifications').textContent = profileData.certifications.length;
        }

        // =====================================================================
        // SKILLS
        // =====================================================================

        function renderSkills() {
            const list = document.getElementById('skills-list');
            list.innerHTML = profileData.skills.map((skill, index) => `
                <div class="item-card" data-index="${index}">
                    <div class="form-row" style="margin-bottom: 0;">
                        <div class="form-group" style="margin-bottom: 0;">
                            <input type="text" value="${escapeHtml(skill.name)}" 
                                   placeholder="Skill name" 
                                   onchange="updateSkill(${index}, 'name', this.value)">
                        </div>
                        <div class="form-group" style="margin-bottom: 0;">
                            <select onchange="updateSkill(${index}, 'level', this.value)">
                                ${skillLevels.map(l => `
                                    <option value="${l.value}" ${skill.level === l.value ? 'selected' : ''}>
                                        ${l.label}
                                    </option>
                                `).join('')}
                            </select>
                        </div>
                        <div class="form-group" style="margin-bottom: 0; max-width: 100px;">
                            <input type="number" value="${skill.years || ''}" 
                                   placeholder="Years" min="0" max="50"
                                   onchange="updateSkill(${index}, 'years', this.value ? parseInt(this.value) : null)">
                        </div>
                        <div class="item-card-actions">
                            <button onclick="moveSkill(${index}, -1)" ${index === 0 ? 'disabled' : ''}>↑</button>
                            <button onclick="moveSkill(${index}, 1)" ${index === profileData.skills.length - 1 ? 'disabled' : ''}>↓</button>
                            <button class="delete" onclick="removeSkill(${index})">×</button>
                        </div>
                    </div>
                </div>
            `).join('');
        }

        function addSkill() {
            profileData.skills.push({ name: '', level: null, years: null, category: null });
            renderSkills();
            updateTabCounts();
        }

        function updateSkill(index, field, value) {
            profileData.skills[index][field] = value;
        }

        function moveSkill(index, direction) {
            const newIndex = index + direction;
            if (newIndex < 0 || newIndex >= profileData.skills.length) return;
            [profileData.skills[index], profileData.skills[newIndex]] = 
            [profileData.skills[newIndex], profileData.skills[index]];
            renderSkills();
        }

        function removeSkill(index) {
            profileData.skills.splice(index, 1);
            renderSkills();
            updateTabCounts();
        }

        // =====================================================================
        // EXPERIENCES
        // =====================================================================

        function renderExperiences() {
            const list = document.getElementById('experience-list');
            list.innerHTML = profileData.experiences.map((exp, index) => `
                <div class="item-card expandable expanded" data-index="${index}">
                    <div class="item-card-header" onclick="toggleItemCard(this)">
                        <div>
                            <div class="item-card-title">${escapeHtml(exp.title) || 'New Experience'}</div>
                            <div class="item-card-subtitle">${escapeHtml(exp.company) || 'Company'} • ${exp.start_date || 'Start'} - ${exp.end_date || 'Present'}</div>
                        </div>
                        <div class="item-card-actions" onclick="event.stopPropagation()">
                            <button onclick="moveExperience(${index}, -1)" ${index === 0 ? 'disabled' : ''}>↑</button>
                            <button onclick="moveExperience(${index}, 1)" ${index === profileData.experiences.length - 1 ? 'disabled' : ''}>↓</button>
                            <button class="delete" onclick="removeExperience(${index})">×</button>
                        </div>
                    </div>
                    <div class="item-card-body">
                        <div class="form-row">
                            <div class="form-group">
                                <label>Job Title *</label>
                                <input type="text" value="${escapeHtml(exp.title)}" 
                                       placeholder="e.g., Senior Software Engineer"
                                       onchange="updateExperience(${index}, 'title', this.value)">
                            </div>
                            <div class="form-group">
                                <label>Company *</label>
                                <input type="text" value="${escapeHtml(exp.company)}" 
                                       placeholder="Company name"
                                       onchange="updateExperience(${index}, 'company', this.value)">
                            </div>
                        </div>
                        <div class="form-row">
                            <div class="form-group">
                                <label>Start Date</label>
                                <input type="text" value="${escapeHtml(exp.start_date || '')}" 
                                       placeholder="YYYY-MM"
                                       onchange="updateExperience(${index}, 'start_date', this.value)">
                            </div>
                            <div class="form-group">
                                <label>End Date</label>
                                <input type="text" value="${escapeHtml(exp.end_date || '')}" 
                                       placeholder="YYYY-MM or leave empty for current"
                                       onchange="updateExperience(${index}, 'end_date', this.value || null)">
                            </div>
                        </div>
                        <div class="form-group">
                            <label>Description</label>
                            <textarea rows="3" placeholder="Describe your role and responsibilities..."
                                      onchange="updateExperience(${index}, 'description', this.value)">${escapeHtml(exp.description || '')}</textarea>
                        </div>
                        <div class="form-group">
                            <label>Key Achievements</label>
                            <div class="achievements-list">
                                ${(exp.achievements || []).map((ach, achIndex) => `
                                    <div class="achievement-item">
                                        <input type="text" value="${escapeHtml(ach)}" 
                                               placeholder="Achievement..."
                                               onchange="updateExperienceAchievement(${index}, ${achIndex}, this.value)">
                                        <button class="btn btn-sm" onclick="removeExperienceAchievement(${index}, ${achIndex})">×</button>
                                    </div>
                                `).join('')}
                            </div>
                            <button class="btn btn-sm btn-secondary" style="margin-top: 0.5rem;" 
                                    onclick="addExperienceAchievement(${index})">+ Add Achievement</button>
                        </div>
                    </div>
                </div>
            `).join('');
        }

        function addExperience() {
            profileData.experiences.push({
                title: '',
                company: '',
                start_date: '',
                end_date: null,
                description: '',
                achievements: []
            });
            renderExperiences();
            updateTabCounts();
        }

        function updateExperience(index, field, value) {
            profileData.experiences[index][field] = value;
            // Update header display
            renderExperiences();
        }

        function moveExperience(index, direction) {
            const newIndex = index + direction;
            if (newIndex < 0 || newIndex >= profileData.experiences.length) return;
            [profileData.experiences[index], profileData.experiences[newIndex]] = 
            [profileData.experiences[newIndex], profileData.experiences[index]];
            renderExperiences();
        }

        function removeExperience(index) {
            profileData.experiences.splice(index, 1);
            renderExperiences();
            updateTabCounts();
        }

        function addExperienceAchievement(expIndex) {
            if (!profileData.experiences[expIndex].achievements) {
                profileData.experiences[expIndex].achievements = [];
            }
            profileData.experiences[expIndex].achievements.push('');
            renderExperiences();
        }

        function updateExperienceAchievement(expIndex, achIndex, value) {
            profileData.experiences[expIndex].achievements[achIndex] = value;
        }

        function removeExperienceAchievement(expIndex, achIndex) {
            profileData.experiences[expIndex].achievements.splice(achIndex, 1);
            renderExperiences();
        }

        function toggleItemCard(header) {
            header.closest('.item-card').classList.toggle('expanded');
        }

        // =====================================================================
        // EDUCATION (similar pattern to experiences)
        // =====================================================================

        function renderEducation() {
            const list = document.getElementById('education-list');
            list.innerHTML = profileData.education.map((edu, index) => `
                <div class="item-card expandable expanded" data-index="${index}">
                    <div class="item-card-header" onclick="toggleItemCard(this)">
                        <div>
                            <div class="item-card-title">${escapeHtml(edu.degree) || 'Degree'} ${edu.field ? `in ${escapeHtml(edu.field)}` : ''}</div>
                            <div class="item-card-subtitle">${escapeHtml(edu.institution) || 'Institution'}</div>
                        </div>
                        <div class="item-card-actions" onclick="event.stopPropagation()">
                            <button onclick="moveEducation(${index}, -1)" ${index === 0 ? 'disabled' : ''}>↑</button>
                            <button onclick="moveEducation(${index}, 1)" ${index === profileData.education.length - 1 ? 'disabled' : ''}>↓</button>
                            <button class="delete" onclick="removeEducation(${index})">×</button>
                        </div>
                    </div>
                    <div class="item-card-body">
                        <div class="form-row">
                            <div class="form-group">
                                <label>Institution *</label>
                                <input type="text" value="${escapeHtml(edu.institution)}" 
                                       placeholder="University/School name"
                                       onchange="updateEducation(${index}, 'institution', this.value)">
                            </div>
                        </div>
                        <div class="form-row">
                            <div class="form-group">
                                <label>Degree</label>
                                <input type="text" value="${escapeHtml(edu.degree || '')}" 
                                       placeholder="e.g., Bachelor of Science"
                                       onchange="updateEducation(${index}, 'degree', this.value)">
                            </div>
                            <div class="form-group">
                                <label>Field of Study</label>
                                <input type="text" value="${escapeHtml(edu.field || '')}" 
                                       placeholder="e.g., Computer Science"
                                       onchange="updateEducation(${index}, 'field', this.value)">
                            </div>
                        </div>
                        <div class="form-row">
                            <div class="form-group">
                                <label>Start Date</label>
                                <input type="text" value="${escapeHtml(edu.start_date || '')}" 
                                       placeholder="YYYY-MM"
                                       onchange="updateEducation(${index}, 'start_date', this.value)">
                            </div>
                            <div class="form-group">
                                <label>End Date</label>
                                <input type="text" value="${escapeHtml(edu.end_date || '')}" 
                                       placeholder="YYYY-MM"
                                       onchange="updateEducation(${index}, 'end_date', this.value)">
                            </div>
                            <div class="form-group">
                                <label>GPA</label>
                                <input type="text" value="${escapeHtml(edu.gpa || '')}" 
                                       placeholder="e.g., 3.8"
                                       onchange="updateEducation(${index}, 'gpa', this.value)">
                            </div>
                        </div>
                    </div>
                </div>
            `).join('');
        }

        function addEducation() {
            profileData.education.push({
                institution: '',
                degree: '',
                field: '',
                start_date: '',
                end_date: '',
                gpa: '',
                achievements: []
            });
            renderEducation();
            updateTabCounts();
        }

        function updateEducation(index, field, value) {
            profileData.education[index][field] = value;
            renderEducation();
        }

        function moveEducation(index, direction) {
            const newIndex = index + direction;
            if (newIndex < 0 || newIndex >= profileData.education.length) return;
            [profileData.education[index], profileData.education[newIndex]] = 
            [profileData.education[newIndex], profileData.education[index]];
            renderEducation();
        }

        function removeEducation(index) {
            profileData.education.splice(index, 1);
            renderEducation();
            updateTabCounts();
        }

        // =====================================================================
        // CERTIFICATIONS
        // =====================================================================

        function renderCertifications() {
            const list = document.getElementById('certifications-list');
            list.innerHTML = profileData.certifications.map((cert, index) => `
                <div class="item-card" data-index="${index}">
                    <div class="form-row" style="margin-bottom: 0.5rem;">
                        <div class="form-group" style="margin-bottom: 0;">
                            <input type="text" value="${escapeHtml(cert.name)}" 
                                   placeholder="Certification name"
                                   onchange="updateCertification(${index}, 'name', this.value)">
                        </div>
                        <div class="form-group" style="margin-bottom: 0;">
                            <input type="text" value="${escapeHtml(cert.issuer || '')}" 
                                   placeholder="Issuing organization"
                                   onchange="updateCertification(${index}, 'issuer', this.value)">
                        </div>
                        <div class="item-card-actions">
                            <button onclick="moveCertification(${index}, -1)" ${index === 0 ? 'disabled' : ''}>↑</button>
                            <button onclick="moveCertification(${index}, 1)" ${index === profileData.certifications.length - 1 ? 'disabled' : ''}>↓</button>
                            <button class="delete" onclick="removeCertification(${index})">×</button>
                        </div>
                    </div>
                    <div class="form-row">
                        <div class="form-group" style="margin-bottom: 0;">
                            <input type="text" value="${escapeHtml(cert.date_obtained || '')}" 
                                   placeholder="Date obtained (YYYY-MM)"
                                   onchange="updateCertification(${index}, 'date_obtained', this.value)">
                        </div>
                        <div class="form-group" style="margin-bottom: 0;">
                            <input type="text" value="${escapeHtml(cert.expiry_date || '')}" 
                                   placeholder="Expiry date (optional)"
                                   onchange="updateCertification(${index}, 'expiry_date', this.value)">
                        </div>
                    </div>
                </div>
            `).join('');
        }

        function addCertification() {
            profileData.certifications.push({
                name: '',
                issuer: '',
                date_obtained: '',
                expiry_date: '',
                credential_url: ''
            });
            renderCertifications();
            updateTabCounts();
        }

        function updateCertification(index, field, value) {
            profileData.certifications[index][field] = value;
        }

        function moveCertification(index, direction) {
            const newIndex = index + direction;
            if (newIndex < 0 || newIndex >= profileData.certifications.length) return;
            [profileData.certifications[index], profileData.certifications[newIndex]] = 
            [profileData.certifications[newIndex], profileData.certifications[index]];
            renderCertifications();
        }

        function removeCertification(index) {
            profileData.certifications.splice(index, 1);
            renderCertifications();
            updateTabCounts();
        }

        // =====================================================================
        // COMPLETENESS
        // =====================================================================

        async function updateCompleteness() {
            if (!profileSlug) {
                // For new profiles, show placeholder
                document.getElementById('completeness-score').textContent = '-';
                document.getElementById('completeness-level').textContent = 'Save to see score';
                document.getElementById('completeness-circle').className = 'completeness-circle needs_work';
                return;
            }

            try {
                const response = await fetch(`/api/v1/profiles/${profileSlug}/completeness`);
                if (response.ok) {
                    const data = await response.json();
                    displayCompleteness(data);
                }
            } catch (error) {
                console.error('Error fetching completeness:', error);
            }
        }

        function displayCompleteness(data) {
            document.getElementById('completeness-score').textContent = `${data.overall_score}%`;
            document.getElementById('completeness-level').textContent = 
                data.level.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
            document.getElementById('completeness-circle').className = 
                `completeness-circle ${data.level}`;

            const suggestionsList = document.getElementById('suggestions-list');
            if (data.top_suggestions && data.top_suggestions.length > 0) {
                suggestionsList.innerHTML = data.top_suggestions.map(s => 
                    `<div class="suggestion-item">${escapeHtml(s)}</div>`
                ).join('');
            } else {
                suggestionsList.innerHTML = '<div style="color: #10b981; text-align: center;">Looking great! ✓</div>';
            }
        }

        // =====================================================================
        // SAVE PROFILE
        // =====================================================================

        async function saveProfile() {
            // Gather form data
            profileData.name = document.getElementById('profile-name').value.trim();
            profileData.title = document.getElementById('profile-title').value.trim();
            profileData.email = document.getElementById('profile-email').value.trim();
            profileData.phone = document.getElementById('profile-phone').value.trim();
            profileData.location = document.getElementById('profile-location').value.trim();
            profileData.summary = document.getElementById('profile-summary').value.trim();

            // Validate
            if (!profileData.name) {
                showToast('error', 'Error', 'Profile name is required');
                switchTab('overview');
                document.getElementById('profile-name').focus();
                return;
            }

            // Filter out empty items
            profileData.skills = profileData.skills.filter(s => s.name && s.name.trim());
            profileData.experiences = profileData.experiences.filter(e => e.title && e.company);
            profileData.education = profileData.education.filter(e => e.institution);
            profileData.certifications = profileData.certifications.filter(c => c.name);

            showLoading(true);

            try {
                let response;
                if (isNewProfile) {
                    response = await fetch('/api/v1/profiles', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            ...profileData,
                            set_active: false
                        })
                    });
                } else {
                    response = await fetch(`/api/v1/profiles/${profileSlug}`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(profileData)
                    });
                }

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Failed to save profile');
                }

                const savedProfile = await response.json();
                
                showToast('success', 'Saved', 'Profile saved successfully');

                // Redirect to profiles list after short delay
                setTimeout(() => {
                    window.location.href = '/profiles';
                }, 1000);

            } catch (error) {
                console.error('Error saving profile:', error);
                showToast('error', 'Error', error.message || 'Failed to save profile');
            } finally {
                showLoading(false);
            }
        }

        // =====================================================================
        // UTILITIES
        // =====================================================================

        function showLoading(show) {
            document.getElementById('loading-overlay').classList.toggle('show', show);
        }
    </script>
</body>
</html>
```

---

## Part 4: Update common.js

**Update file:** `src/web/static/js/common.js`

### Key Changes

1. Remove `loadProfilesList()` and `updateNavbarProfileSwitcher()` 
2. Add `loadCurrentUser()` and `loadActiveProfile()` for navbar
3. Add `toggleUserMenu()` function
4. Update initialization

```javascript
/**
 * Scout - Common JavaScript
 * Shared utilities for all pages
 */

// =============================================================================
// GLOBAL STATE
// =============================================================================

window.Scout = window.Scout || {
    currentUser: null,
    activeProfile: null,
    notificationPollInterval: null,
    seenNotifications: new Set()
};

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatRelativeDate(dateStr) {
    if (!dateStr) return 'Unknown';
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now - date;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    
    return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
    });
}

function capitalizeFirst(str) {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function getScoreClass(score) {
    if (score >= 80) return 'excellent';
    if (score >= 60) return 'strong';
    if (score >= 40) return 'moderate';
    return 'weak';
}

// =============================================================================
// TOAST NOTIFICATIONS
// =============================================================================

function showToast(type, title, message, autoDismiss = true, dismissSeconds = 5) {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div class="toast-content">
            <div class="toast-title">${escapeHtml(title)}</div>
            <div class="toast-message">${escapeHtml(message)}</div>
        </div>
        <button class="toast-close" onclick="this.parentElement.remove()">&times;</button>
    `;
    container.appendChild(toast);

    if (autoDismiss) {
        setTimeout(() => toast.remove(), dismissSeconds * 1000);
    }

    return toast;
}

// =============================================================================
// NAVBAR - USER & PROFILE
// =============================================================================

async function loadCurrentUser() {
    try {
        const response = await fetch('/api/v1/user');
        if (response.ok) {
            window.Scout.currentUser = await response.json();
            updateNavbarUser();
        }
    } catch (error) {
        console.error('Error loading user:', error);
    }
}

async function loadActiveProfile() {
    try {
        const response = await fetch('/api/v1/profiles/active');
        if (response.ok) {
            const data = await response.json();
            window.Scout.activeProfile = data;
            updateNavbarActiveProfile();
        }
    } catch (error) {
        console.error('Error loading active profile:', error);
    }
}

function updateNavbarUser() {
    const user = window.Scout.currentUser;
    if (!user) return;

    const nameEl = document.getElementById('navbar-user-name');
    const avatarEl = document.getElementById('navbar-user-avatar');
    const emailEl = document.getElementById('navbar-user-email');

    if (nameEl) nameEl.textContent = user.display_name || user.username;
    if (avatarEl) avatarEl.textContent = (user.display_name || user.username || 'U')[0].toUpperCase();
    if (emailEl) emailEl.textContent = user.email || '';
}

function updateNavbarActiveProfile() {
    const profile = window.Scout.activeProfile;
    const nameEl = document.getElementById('navbar-active-name');
    const containerEl = document.getElementById('navbar-active-profile');

    if (!profile) {
        if (nameEl) nameEl.textContent = 'No active profile';
        if (containerEl) containerEl.classList.add('inactive');
        return;
    }

    if (nameEl) nameEl.textContent = profile.name;
    if (containerEl) containerEl.classList.remove('inactive');
}

function toggleUserMenu(event) {
    event.stopPropagation();
    const dropdown = document.getElementById('navbar-user-dropdown');
    if (dropdown) {
        dropdown.classList.toggle('show');
    }
}

// =============================================================================
// NOTIFICATION POLLING
// =============================================================================

function startNotificationPolling(interval = 3000) {
    if (window.Scout.notificationPollInterval) {
        clearInterval(window.Scout.notificationPollInterval);
    }
    window.Scout.notificationPollInterval = setInterval(fetchNotifications, interval);
    fetchNotifications();
}

function stopNotificationPolling() {
    if (window.Scout.notificationPollInterval) {
        clearInterval(window.Scout.notificationPollInterval);
        window.Scout.notificationPollInterval = null;
    }
}

async function fetchNotifications() {
    try {
        const response = await fetch('/api/v1/notifications?unread_only=true');
        if (!response.ok) return;

        const data = await response.json();

        data.notifications.forEach(notification => {
            if (!window.Scout.seenNotifications.has(notification.id)) {
                window.Scout.seenNotifications.add(notification.id);
                showNotificationToast(notification);
            }
        });
    } catch (error) {
        console.error('Notification fetch error:', error);
    }
}

function showNotificationToast(notification) {
    const toast = showToast(
        notification.type,
        notification.title,
        notification.message,
        notification.auto_dismiss !== false,
        notification.dismiss_after_seconds || 5
    );

    toast.querySelector('.toast-close').addEventListener('click', () => {
        markNotificationRead(notification.id);
    });
}

async function markNotificationRead(notificationId) {
    try {
        await fetch(`/api/v1/notifications/${notificationId}/read`, { method: 'POST' });
    } catch (error) {
        console.error('Failed to mark notification as read:', error);
    }
}

// =============================================================================
// INITIALIZATION
// =============================================================================

document.addEventListener('DOMContentLoaded', () => {
    // Load navbar data
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

## Part 5: CSS Updates

**Update file:** `src/web/static/css/common.css`

Add these styles for the new navbar and components:

```css
/* Add to existing common.css */

/* =============================================================================
   NAVBAR - USER MENU
   ============================================================================= */

.navbar-right {
    display: flex;
    align-items: center;
    gap: 1rem;
}

.navbar-active-profile {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0.75rem;
    background: rgba(16, 185, 129, 0.1);
    border-radius: 6px;
    font-size: 0.85rem;
    color: #065f46;
}

.navbar-active-profile.inactive {
    background: rgba(107, 114, 128, 0.1);
    color: #6b7280;
}

.active-profile-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #10b981;
}

.navbar-active-profile.inactive .active-profile-dot {
    background: #9ca3af;
}

.navbar-user-menu {
    position: relative;
}

.navbar-user-btn {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem;
    background: none;
    border: none;
    cursor: pointer;
    border-radius: 6px;
    transition: background 0.2s;
}

.navbar-user-btn:hover {
    background: rgba(0, 0, 0, 0.05);
}

.user-avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: #2563eb;
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 600;
    font-size: 0.9rem;
}

.user-name {
    font-weight: 500;
    color: #374151;
}

.navbar-arrow {
    color: #9ca3af;
    font-size: 0.75rem;
}

.user-dropdown {
    position: absolute;
    top: 100%;
    right: 0;
    margin-top: 0.5rem;
    background: #fff;
    border-radius: 8px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
    min-width: 220px;
    display: none;
    z-index: 1000;
}

.user-dropdown.show {
    display: block;
}

.user-dropdown-header {
    padding: 1rem;
    border-bottom: 1px solid #e5e7eb;
}

.user-email {
    font-size: 0.85rem;
    color: #6b7280;
}

.user-dropdown-divider {
    height: 1px;
    background: #e5e7eb;
}

.user-dropdown-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    width: 100%;
    padding: 0.75rem 1rem;
    background: none;
    border: none;
    text-align: left;
    font-size: 0.9rem;
    color: #374151;
    cursor: pointer;
    text-decoration: none;
    transition: background 0.2s;
}

.user-dropdown-item:hover:not(.disabled) {
    background: #f3f4f6;
}

.user-dropdown-item.disabled {
    color: #9ca3af;
    cursor: not-allowed;
}

.dropdown-icon {
    font-size: 1rem;
    width: 20px;
    text-align: center;
}

.coming-soon-badge {
    margin-left: auto;
    font-size: 0.7rem;
    padding: 0.15rem 0.4rem;
    background: #e5e7eb;
    color: #6b7280;
    border-radius: 4px;
}

/* =============================================================================
   BUTTON VARIANTS
   ============================================================================= */

.btn-danger-outline {
    background: transparent;
    border: 1px solid #ef4444;
    color: #ef4444;
}

.btn-danger-outline:hover {
    background: #fef2f2;
}
```

---

## Part 6: Update Page Routes

**Update file:** `src/web/routes/pages.py`

Add/update routes for the new profile URLs:

```python
# Add these routes

@router.get("/profiles/new")
async def profile_new_page(request: Request):
    """Create new profile page."""
    return templates.TemplateResponse("profile_edit.html", {"request": request})


@router.get("/profiles/{slug}/edit")
async def profile_edit_page(request: Request, slug: str):
    """Edit profile page."""
    return templates.TemplateResponse("profile_edit.html", {"request": request})
```

---

## Validation Steps

### 1. Static File Check

```bash
# Verify files exist and have no syntax errors
python -c "
import json
# Test JS syntax by trying to read it
with open('src/web/static/js/common.js') as f:
    content = f.read()
    print(f'common.js: {len(content)} chars')
print('Static files OK')
"
```

### 2. Template Render Check

```bash
# Start server and test pages load
# (Run manually in browser)
# - http://localhost:8000/profiles
# - http://localhost:8000/profiles/new
# - http://localhost:8000/profiles/backend-focus/edit
```

### 3. API Integration Check

```bash
# Test that pages call correct API endpoints
curl -s http://localhost:8000/api/v1/profiles | python -m json.tool | head -20
curl -s http://localhost:8000/api/v1/user | python -m json.tool
curl -s http://localhost:8000/api/v1/profiles/backend-focus/completeness | python -m json.tool
```

---

## Completion Checklist

- [ ] `partials/navbar.html` updated with user menu
- [ ] `profiles_list.html` rewritten for normalized data
- [ ] `profile_edit.html` rewritten with tabbed editor
- [ ] `index.html` updated (if needed)
- [ ] `common.js` updated with new navbar functions
- [ ] `common.css` updated with new styles
- [ ] `pages.py` routes added for /profiles/new and /profiles/{slug}/edit
- [ ] All pages load without JS errors
- [ ] Profile list shows completeness scores
- [ ] Profile editor tabs work
- [ ] Save button creates/updates profiles
- [ ] Code committed

```bash
git add src/web/
git commit -m "WP4: Update web interface for normalized profile schema

- Replace navbar profile switcher with user menu
- Rewrite profiles list with completeness scores
- New tabbed profile editor for normalized data
- Update common.js for new API structure
- Add new button styles and components

Part of user/profile refactor - see docs/tasks/REFACTOR_GUIDE.md"
```

---

## Notes

### Browser Testing Priority

1. **Profiles List** (`/profiles`) - Most critical, ensure all cards render
2. **Profile Editor** (`/profiles/{slug}/edit`) - Test tab switching, save
3. **Create Profile** (`/profiles/new`) - Test creation flow
4. **Navbar** - Ensure user menu works on all pages

### Known Limitations for PoC

1. No drag-and-drop reordering (uses up/down buttons instead)
2. No inline validation beyond required fields
3. No auto-save / draft functionality
4. Languages tab omitted (can add later)
