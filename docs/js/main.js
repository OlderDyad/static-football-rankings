// docs/js/main.js

import { initializePage } from './modules/pageTemplate.js';
import { createTeamHeader } from './modules/teamHeader.js';
import { teamConfig } from './config/teamConfig.js';
import { DEBUG_LEVELS, log } from './modules/logger.js'; // Import logging functions

// Main initialization function
async function initializeApp() {
    try {
        log(DEBUG_LEVELS.INFO, 'Initializing app...');

        // Get page configuration from HTML
        const h1Element = document.querySelector('h1[data-page-name]');
        if (!h1Element) {
            throw new Error('Page configuration not found');
        }

        const pageName = h1Element.dataset.pageName;
        const threshold = pageName.match(/(\d+)\+/)?.[1] || '50'; // Extract threshold from pageName

        const pageConfig = {
            pageTitle: `Top High School Football Programs (${threshold}+ seasons)`,
            dataFile: `/static-football-rankings/data/all-time-programs-${threshold}.json`
        };

        log(DEBUG_LEVELS.INFO, 'Page config:', pageConfig);

        // Initialize the page using the template
        const page = initializePage(pageConfig);
        await page.initialize();

    } catch (error) {
        log(DEBUG_LEVELS.ERROR, 'App initialization failed:', error);
        // Update loading state with error message (assuming updateLoadingState is defined elsewhere)
        updateLoadingState(false, error.message); 
    }
}

// Update loading state
function updateLoadingState(isLoading, errorMessage = '') {
    const header = document.querySelector('.team-header');
    if (!header) return;

    if (isLoading) {
        header.innerHTML = `
            <div class="container">
                <div class="text-center">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p>Loading program data...</p>
                </div>
            </div>`;
    } else if (errorMessage) {
        header.innerHTML = `
            <div class="container">
                <div class="alert alert-danger">${errorMessage}</div>
            </div>`;
    } else {
        // Clear the loading state (optional)
        header.innerHTML = ''; 
    }
}

// Auth status check
export async function checkLoginStatus() {
    try {
        log(DEBUG_LEVELS.INFO, 'Starting login status check');
        const response = await fetch('/api/auth/status', {
            credentials: 'include'
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        return data.isLoggedIn;
    } catch (error) {
        log(DEBUG_LEVELS.ERROR, 'Login status check failed:', error);
        return false;
    }
}

// Comments functionality
export async function loadComments() {
    try {
        log(DEBUG_LEVELS.INFO, 'Loading comments');
        const response = await fetch('/api/comments', {
            credentials: 'include'
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const comments = await response.json();
        displayComments(comments);
    } catch (error) {
        log(DEBUG_LEVELS.ERROR, 'Comments loading failed:', error);
        const commentsList = document.getElementById('commentsList');
        if (commentsList) {
            commentsList.innerHTML = '<div class="alert alert-danger">Error loading comments</div>';
        }
    }
}

function displayComments(comments) {
    const commentsList = document.getElementById('commentsList');
    if (!commentsList) return;

    commentsList.innerHTML = comments.map(comment => `
        <div class="comment mb-3 p-3 border rounded">
            <div class="d-flex justify-content-between">
                <strong>${comment.author_email}</strong>
                <small class="text-muted">${new Date(comment.created_at).toLocaleDateString()}</small>
            </div>
            <div class="mt-2">${comment.text}</div>
        </div>
    `).join('');
}

// timestamp
function updateTimestamp(timestamp) {
    const element = document.getElementById('lastUpdated');
    if (element && timestamp) {
        element.textContent = new Date(timestamp).toLocaleDateString();
    }
}

export async function submitComment() {
    // ... existing comment submission code ...
}

// Start the application when DOM is ready
document.addEventListener('DOMContentLoaded', initializeApp);

