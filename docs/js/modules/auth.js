// docs/js/modules/auth.js
import { isDevelopment, mockAuth, endpoints } from '../config/development.js';
import { DEBUG_LEVELS, log } from './logger.js';

export async function checkAuthStatus() {
    // Use mock auth during development
    if (isDevelopment) {
        log(DEBUG_LEVELS.INFO, 'Using mock auth in development mode');
        return mockAuth;
    }

    try {
        const response = await fetch(`${endpoints.api}${endpoints.auth.status}`, {
            credentials: 'include'
        });
        if (!response.ok) throw new Error('Auth check failed');
        return await response.json();
    } catch (error) {
        log(DEBUG_LEVELS.ERROR, 'Auth check error:', error);
        return { isAuthenticated: false, user: null };
    }
}

export function updateAuthUI(authStatus = { isAuthenticated: false, user: null }) {
    const authContainer = document.getElementById('authContainer');
    const commentForm = document.getElementById('commentForm');
    
    if (!authContainer) {
        log(DEBUG_LEVELS.WARN, 'Auth container not found');
        return;
    }

    if (authStatus.isAuthenticated && authStatus.user) {
        authContainer.innerHTML = `
            <div class="logged-in">
                <span>Welcome, ${authStatus.user.email || 'User'}</span>
                <button class="btn btn-outline-primary btn-sm" onclick="handleLogout()">Logout</button>
            </div>`;
        if (commentForm) commentForm.style.display = 'block';
    } else {
        authContainer.innerHTML = `
            <div class="logged-out">
                <button class="btn btn-primary btn-sm" onclick="handleLogin()">Login to Comment</button>
            </div>`;
        if (commentForm) commentForm.style.display = 'none';
    }
}

// Add these to window for onclick handlers
window.handleLogin = () => {
    if (isDevelopment) {
        log(DEBUG_LEVELS.INFO, 'Login clicked in development mode');
        mockAuth.isAuthenticated = true;
        mockAuth.user = { email: 'test@example.com' };
        updateAuthUI(mockAuth);
    } else {
        window.location.href = `${endpoints.api}${endpoints.auth.login}`;
    }
};

window.handleLogout = () => {
    if (isDevelopment) {
        log(DEBUG_LEVELS.INFO, 'Logout clicked in development mode');
        mockAuth.isAuthenticated = false;
        mockAuth.user = null;
        updateAuthUI(mockAuth);
    } else {
        window.location.href = `${endpoints.api}${endpoints.auth.logout}`;
    }
};