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
// NAVBAR - USER & PROFILE
// =============================================================================

/**
 * Load current user from API
 */
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

/**
 * Load active profile from API
 */
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

/**
 * Update navbar user display
 */
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

/**
 * Update navbar active profile indicator
 */
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

/**
 * Toggle user menu dropdown
 */
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
        await fetch(`/api/v1/notifications/${notificationId}/read`, {
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
    // Load navbar data
    loadCurrentUser();
    loadActiveProfile();

    // Start notification polling
    startNotificationPolling();

    // Close dropdowns when clicking outside
    document.addEventListener('click', (e) => {
        // Close user menu if clicking outside
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
