// main.js

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

export function log(level, message, data = null) {
    if (!DEBUG_CONFIG.enabled) return;

    const timestamp = new Date().toISOString().split('T')[1].slice(0, -1);
    const prefix = `[${timestamp}][${level}]`;

    switch (level) {
        case DEBUG_LEVELS.ERROR:
            console.error(`${prefix} ${message}`, data || '');
            break;
        case DEBUG_LEVELS.WARN:
            console.warn(`${prefix} ${message}`, data || '');
            break;
        case DEBUG_LEVELS.INFO:
        case DEBUG_LEVELS.DEBUG:
            if (DEBUG_CONFIG.level === DEBUG_LEVELS.DEBUG || level === DEBUG_LEVELS.INFO) {
                console.log(`${prefix} ${message}`, data || '');
            }
            break;
    }
}

export const REPO_BASE = '/static-football-rankings';
export const API_BASE = 'https://static-football-rankings.vercel.app/api';
export const LOGIN_API_BASE = `${API_BASE}/auth`;

let isLoggedIn = false;
let userName = '';

export async function checkLoginStatus() {
    log(DEBUG_LEVELS.INFO, 'Checking login status');
    try {
        const response = await fetch(`${LOGIN_API_BASE}/status`, {
            method: "GET",
            credentials: "include",
            headers: {
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        log(DEBUG_LEVELS.DEBUG, 'Login status response', data);

        isLoggedIn = Boolean(data.loggedIn);
        userName = data.user?.name || '';

        updateAuthUI();
        return data;
    } catch (error) {
        log(DEBUG_LEVELS.ERROR, 'Login status check failed', error);
        isLoggedIn = false;
        userName = '';
        updateAuthUI();
        return { loggedIn: false, user: null };
    }
}

function updateAuthUI() {
    log(DEBUG_LEVELS.DEBUG, 'Updating authentication UI', { isLoggedIn });
    const authContainer = document.getElementById('authContainer');
    if (!authContainer) {
        log(DEBUG_LEVELS.ERROR, 'Auth container not found');
        return;
    }

    if (isLoggedIn) {
        authContainer.innerHTML = `
            <div class="d-flex align-items-center justify-content-between">
                <span class="me-2">Welcome, ${escapeHTML(userName)}</span>
                <button id="logoutButton" class="btn btn-outline-secondary btn-sm">Logout</button>
            </div>
        `;
        const logoutButton = document.getElementById('logoutButton');
        if (logoutButton) {
            logoutButton.addEventListener('click', handleLogout);
        }

        const commentForm = document.getElementById('commentForm');
        if (commentForm) {
            commentForm.style.display = 'block';
        }

        const authorName = document.getElementById('authorName');
        if (authorName) {
            authorName.textContent = userName || 'Anonymous';
        }
    } else {
        authContainer.innerHTML = `
            <div class="d-flex align-items-center">
                <button id="loginButton" class="btn btn-primary d-flex align-items-center gap-2">
                    <img src="${REPO_BASE}/docs/images/google-logo.png" 
                         alt="Google Logo" 
                         style="height: 18px; width: 18px;"
                         onerror="this.style.display='none'" />
                    <span>Sign in with Google</span>
                </button>
            </div>
        `;
        const loginButton = document.getElementById('loginButton');
        if (loginButton) {
            loginButton.addEventListener('click', handleLogin);
        }

        const commentForm = document.getElementById('commentForm');
        if (commentForm) {
            commentForm.style.display = 'none';
        }
    }
}

function handleLogin() {
    log(DEBUG_LEVELS.INFO, 'Initiating Google login');
    try {
        const currentPath = window.location.pathname;
        const loginUrl = `${LOGIN_API_BASE}/google?t=${Date.now()}&redirect=${encodeURIComponent(currentPath)}`;
        window.location.href = loginUrl;
    } catch (error) {
        log(DEBUG_LEVELS.ERROR, 'Login failed', error);
        showAuthError("Login failed. Please try again.");
    }
}

async function handleLogout() {
    log(DEBUG_LEVELS.INFO, 'Processing logout request');
    try {
        const response = await fetch(`${LOGIN_API_BASE}/logout`, {
            method: 'POST',
            credentials: 'include',
            headers: {
                "Content-Type": "application/json"
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        isLoggedIn = false;
        userName = '';
        updateAuthUI();
        await loadComments();
    } catch (error) {
        log(DEBUG_LEVELS.ERROR, 'Logout failed', error);
        showAuthError("Logout failed. Please try again.");
    }
}

function showAuthError(message) {
    log(DEBUG_LEVELS.WARN, 'Auth error occurred', { message });
    const authContainer = document.getElementById('authContainer');
    if (authContainer) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger mt-2';
        errorDiv.textContent = message;
        authContainer.appendChild(errorDiv);
        setTimeout(() => errorDiv.remove(), 3000);
    }
}

// main.js

// Keep these exports
export const API_BASE = 'https://static-football-rankings.vercel.app/api';
export let isLoggedIn = false;
export let userName = '';

// Keep loadComments with added logging
export async function loadComments() {
    log(DEBUG_LEVELS.INFO, 'Loading comments');
    const commentsContainer = document.getElementById('commentsList');
    if (!commentsContainer) {
        log(DEBUG_LEVELS.ERROR, 'Comments container not found');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/comments`, {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        });

        log(DEBUG_LEVELS.DEBUG, 'Comments response status:', response.status);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        log(DEBUG_LEVELS.DEBUG, 'Comments data:', data);
        const comments = Array.isArray(data.comments) ? data.comments : [];
        displayComments(comments);
    } catch (error) {
        log(DEBUG_LEVELS.ERROR, 'Error loading comments', error);
        commentsContainer.innerHTML = `
            <div class="alert alert-warning">
                Error loading comments. Please try again later.
            </div>
        `;
    }
}

// Enhanced submitComment with better logging
export async function submitComment() {
    log(DEBUG_LEVELS.INFO, 'Submit comment called');
    
    if (!isLoggedIn) {
        log(DEBUG_LEVELS.WARN, 'Comment attempted while not logged in');
        showAuthError('Please sign in to post comments');
        return;
    }

    const textElement = document.getElementById('commentText');
    const text = textElement?.value?.trim();
    
    if (!text) {
        log(DEBUG_LEVELS.WARN, 'Empty comment attempted');
        return;
    }

    const pageIdentifier = document.querySelector('h1')?.dataset.pageName || 'unknown-page';
    log(DEBUG_LEVELS.DEBUG, 'Submitting comment for page:', pageIdentifier);

    try {
        const response = await fetch(`${API_BASE}/comments`, {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                text,
                author: userName || 'Anonymous',
                programName: pageIdentifier,
                timestamp: new Date().toISOString()
            })
        });

        log(DEBUG_LEVELS.DEBUG, 'Comment submission response:', response.status);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        log(DEBUG_LEVELS.DEBUG, 'Comment submission result:', result);

        if (result.success) {
            textElement.value = '';
            const successDiv = document.createElement('div');
            successDiv.className = 'alert alert-success mt-2';
            successDiv.textContent = 'Comment posted successfully!';
            textElement.parentNode.insertBefore(successDiv, textElement.nextSibling);
            setTimeout(() => successDiv.remove(), 3000);
            
            await loadComments();
        } else {
            throw new Error(result.error || 'Failed to submit comment');
        }
    } catch (error) {
        log(DEBUG_LEVELS.ERROR, 'Comment submission error:', error);
        showAuthError('Unable to submit comment. Please try again later.');
    }
}

// Keep these helper functions
function displayComments(commentsArray = []) {
    const commentsContainer = document.getElementById('commentsList');
    if (!commentsContainer) return;

    if (commentsArray.length === 0) {
        commentsContainer.innerHTML = '<p class="text-muted">No comments yet. Be the first to comment!</p>';
        return;
    }

    const commentsHTML = commentsArray.map(comment => {
        const timestamp = new Date(comment.timestamp || Date.now());
        return `
            <div class="comment mb-3 p-3 border rounded">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <strong>${escapeHTML(comment.author || 'Anonymous')}</strong>
                        <small class="text-muted ms-2">${getTimeAgo(timestamp)}</small>
                    </div>
                </div>
                <div class="mt-2">
                    ${escapeHTML(comment.text || '')}
                </div>
            </div>
        `;
    }).join('');

    commentsContainer.innerHTML = commentsHTML;
}

function escapeHTML(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function getTimeAgo(date) {
    const now = new Date();
    const diffInSeconds = Math.floor((now - date) / 1000);
    const diffInMinutes = Math.floor(diffInSeconds / 60);
    const diffInHours = Math.floor(diffInMinutes / 60);
    const diffInDays = Math.floor(diffInHours / 24);

    if (diffInSeconds < 60) return 'Just now';
    if (diffInMinutes < 60) return `${diffInMinutes}m ago`;
    if (diffInHours < 24) return `${diffInHours}h ago`;
    if (diffInDays < 7) return `${diffInDays}d ago`;

    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}