// main.js

// SECTION 1: CONFIGURATION AND CONSTANTS
export const DEBUG_LEVELS = {
    ERROR: 'ERROR',
    WARN: 'WARN',
    INFO: 'INFO',
    DEBUG: 'DEBUG'
};

export const DEBUG_CONFIG = {
    enabled: true,
    level: DEBUG_LEVELS.INFO
};

// Repository and API paths (declare once)
export const REPO_BASE = '/static-football-rankings';
export const API_BASE = 'https://static-football-rankings.vercel.app/api';
export const LOGIN_API_BASE = `${API_BASE}/auth`;

// Global state (declare and export once)
export let isLoggedIn = false;
export let userName = '';

// SECTION 2: LOGGING
export function log(level, message, data = null) {
    // ... (keep existing log function)
}

// SECTION 3: AUTHENTICATION HANDLERS
export async function checkLoginStatus() {
    // ... (keep existing checkLoginStatus function)
}

function updateAuthUI() {
    // ... (keep existing updateAuthUI function)
}

function handleLogin() {
    // ... (keep existing handleLogin function)
}

async function handleLogout() {
    // ... (keep existing handleLogout function)
}

function showAuthError(message) {
    // ... (keep existing showAuthError function)
}

// SECTION 4: COMMENTS FUNCTIONALITY
export async function loadComments() {
    // ... (keep existing loadComments function)
}

export async function submitComment() {
    // ... (keep existing submitComment function)
}

function displayComments(commentsArray = []) {
    // ... (keep existing displayComments function)
}

// SECTION 5: UTILITY FUNCTIONS
function escapeHTML(str) {
    // ... (keep existing escapeHTML function)
}

function getTimeAgo(date) {
    // ... (keep existing getTimeAgo function)
}

// Export the necessary functions and variables
export {
    handleLogin,
    handleLogout,
    updateAuthUI,
    showAuthError
};
