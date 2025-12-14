/**
 * Scout - Common JavaScript
 * Shared utilities for all pages
 */

// =============================================================================
// GLOBAL STATE
// =============================================================================

window.Scout = window.Scout || {
    profilesList: [],
    activeProfileFilename: null,
    notificationPollInterval: null,
    seenNotifications: new Set()
};

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Format a date string relative to now
 */
function formatRelativeDate(dateStr) {
    if (!dateStr) return 'Unknown';
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now - date;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
        return 'Today';
    } else if (diffDays === 1) {
        return 'Yesterday';
    } else if (diffDays < 7) {
        return `${diffDays} days ago`;
    } else {
        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
        });
    }
}

/**
 * Capitalize first letter of a string
 */
function capitalizeFirst(str) {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1);
}

/**
 * Get score classification
 */
function getScoreClass(score) {
    if (score >= 80) return 'excellent';
    if (score >= 60) return 'strong';
    if (score >= 40) return 'moderate';
    return 'weak';
}

// =============================================================================
// TOAST NOTIFICATIONS
// =============================================================================

/**
 * Show a toast notification
 */
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
// PROFILE MANAGEMENT
// =============================================================================

/**
 * Load profiles list from API
 */
async function loadProfilesList() {
    try {
        // Try new multi-profile API first
        const response = await fetch('/api/profiles?include_archived=false');
        if (response.ok) {
            const data = await response.json();
            window.Scout.profilesList = data.profiles || [];
            window.Scout.activeProfileFilename = data.active_profile;
            updateNavbarProfileSwitcher();
            return;
        }
    } catch (e) {
        console.log('Multi-profile API not available, trying single profile');
    }

    // Fallback to single profile API
    try {
        const statusResponse = await fetch('/api/profile/status');
        if (statusResponse.ok) {
            const status = await statusResponse.json();
            if (status.exists) {
                const profileResponse = await fetch('/api/profile/retrieve');
                if (profileResponse.ok) {
                    const profileData = await profileResponse.json();
                    window.Scout.profilesList = [{
                        filename: 'profile.yaml',
                        profile_name: extractProfileName(profileData.profile_text) || 'My Profile',
                        is_indexed: status.is_indexed,
                        usage_count: 0,
                        avg_compatibility_score: null
                    }];
                    window.Scout.activeProfileFilename = 'profile.yaml';
                    updateNavbarProfileSwitcher();
                }
            }
        }
    } catch (error) {
        console.error('Error loading profile:', error);
    }
}

/**
 * Extract name from profile YAML text
 */
function extractProfileName(text) {
    if (!text) return null;
    const match = text.match(/^name:\s*["']?([^"'\n]+)["']?/mi);
    return match ? match[1].trim() : null;
}

/**
 * Update the navbar profile switcher UI
 */
function updateNavbarProfileSwitcher() {
    const switcherName = document.getElementById('navbar-profile-name');
    const switcherIndicator = document.getElementById('navbar-profile-indicator');
    const dropdownList = document.getElementById('navbar-profile-list');

    if (!switcherName || !switcherIndicator || !dropdownList) return;

    const profiles = window.Scout.profilesList;
    const activeFilename = window.Scout.activeProfileFilename;

    if (profiles.length === 0) {
        switcherName.textContent = 'No Profiles';
        switcherIndicator.classList.remove('active');
        dropdownList.innerHTML = '<p style="padding: 1rem; color: #6b7280; text-align: center;">No profiles yet</p>';
        return;
    }

    // Find active profile
    const activeProfile = profiles.find(p => p.filename === activeFilename);
    if (activeProfile) {
        switcherName.textContent = activeProfile.profile_name || activeProfile.filename;
        switcherIndicator.classList.add('active');
    } else {
        switcherName.textContent = 'Select Profile';
        switcherIndicator.classList.remove('active');
    }

    // Populate dropdown
    dropdownList.innerHTML = profiles.map(profile => {
        const isActive = profile.filename === activeFilename;
        return `
            <button class="profile-dropdown-item ${isActive ? 'active' : ''}"
                    onclick="switchToProfile('${escapeHtml(profile.filename)}')">
                <span class="indicator ${isActive ? 'active' : 'inactive'}"></span>
                <div class="info">
                    <div class="name">${escapeHtml(profile.profile_name || profile.filename)}</div>
                    <div class="meta">${profile.usage_count || 0} apps</div>
                </div>
            </button>
        `;
    }).join('');
}

/**
 * Toggle the profile dropdown
 */
function toggleProfileDropdown(event) {
    event.stopPropagation();
    const dropdown = document.getElementById('navbar-profile-dropdown');
    if (dropdown) {
        dropdown.classList.toggle('show');
    }
}

/**
 * Switch to a different profile
 */
async function switchToProfile(filename) {
    try {
        const response = await fetch(`/api/profiles/${encodeURIComponent(filename)}/activate`, {
            method: 'POST'
        });

        if (!response.ok) throw new Error('Failed to switch profile');

        window.Scout.activeProfileFilename = filename;
        updateNavbarProfileSwitcher();

        // Close dropdown
        const dropdown = document.getElementById('navbar-profile-dropdown');
        if (dropdown) dropdown.classList.remove('show');

        // Show toast
        const profile = window.Scout.profilesList.find(p => p.filename === filename);
        showToast('success', 'Profile Activated', `Now using: ${profile?.profile_name || filename}`);

    } catch (error) {
        console.error('Error switching profile:', error);
        showToast('error', 'Error', 'Failed to switch profile');
    }
}

// =============================================================================
// NOTIFICATION POLLING
// =============================================================================

/**
 * Start polling for notifications
 */
function startNotificationPolling(interval = 3000) {
    if (window.Scout.notificationPollInterval) {
        clearInterval(window.Scout.notificationPollInterval);
    }

    window.Scout.notificationPollInterval = setInterval(fetchNotifications, interval);
    fetchNotifications(); // Initial fetch
}

/**
 * Stop notification polling
 */
function stopNotificationPolling() {
    if (window.Scout.notificationPollInterval) {
        clearInterval(window.Scout.notificationPollInterval);
        window.Scout.notificationPollInterval = null;
    }
}

/**
 * Fetch notifications from API
 */
async function fetchNotifications() {
    try {
        const response = await fetch('/api/notifications?unread_only=true');
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

/**
 * Show a notification as a toast
 */
function showNotificationToast(notification) {
    const toast = showToast(
        notification.type,
        notification.title,
        notification.message,
        notification.auto_dismiss !== false,
        notification.dismiss_after_seconds || 5
    );

    // Mark as read when dismissed
    toast.querySelector('.toast-close').addEventListener('click', () => {
        markNotificationRead(notification.id);
    });
}

/**
 * Mark a notification as read
 */
async function markNotificationRead(notificationId) {
    try {
        await fetch(`/api/notifications/${notificationId}/read`, {
            method: 'POST'
        });
    } catch (error) {
        console.error('Failed to mark notification as read:', error);
    }
}

// =============================================================================
// INITIALIZATION
// =============================================================================

document.addEventListener('DOMContentLoaded', () => {
    // Load profiles for switcher
    loadProfilesList();

    // Start notification polling
    startNotificationPolling();

    // Close dropdowns when clicking outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.navbar-profile-switcher')) {
            const dropdown = document.getElementById('navbar-profile-dropdown');
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
