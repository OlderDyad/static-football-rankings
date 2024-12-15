// docs/js/main.js

import { DEBUG_LEVELS, log } from './modules/logger.js';
import { initializePage } from './modules/pageTemplate.js';
import { createTeamHeader } from './modules/teamHeader.js';
import { teamConfig } from './config/teamConfig.js';
import { checkAuthStatus, updateAuthUI } from './modules/auth.js';
import { CommentManager } from './modules/comments.js';
import { formatDate, debounce, escapeHTML } from './modules/utils.js';
import { config } from './config/config.js';

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
        const threshold = pageName.match(/(\d+)\+/)?.[1] || '50';

        const pageConfig = {
            pageTitle: `Top High School Football Programs (${threshold}+ seasons)`,
            dataFile: config.getPath('data', `all-time-programs-${threshold}.json`)
        };

        log(DEBUG_LEVELS.INFO, 'Page config:', pageConfig);

        // Initialize the page using the template
        const page = initializePage(pageConfig);
        await page.initialize();

        // Initialize auth
        await checkAuthStatus();

        // Set up comment submission
        const submitButton = document.getElementById('submitComment');
        if (submitButton) {
            submitButton.addEventListener('click', submitComment);
        }

    } catch (error) {
        log(DEBUG_LEVELS.ERROR, 'App initialization failed:', error);
        updateLoadingState(false, error.message);
    }
}

// Loading state management
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
    }
}

// loadProgramData

async function loadProgramData(dataFile) {
    log(DEBUG_LEVELS.INFO, 'Loading program data from', dataFile);
    try {
        const response = await fetch(dataFile);
        if (!response.ok) {
            log(DEBUG_LEVELS.ERROR, `Failed to load data: ${response.status} ${response.statusText}`);
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();

        if (!data || !data.programs) {
            log(DEBUG_LEVELS.ERROR, 'Invalid data format:', data);
            throw new Error('Invalid data format: Missing "programs" array');
        }

        return data.programs;
    } catch (error) {
        log(DEBUG_LEVELS.ERROR, 'Error loading program data:', error);
        return [];  // Return empty array instead of undefined
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
                <strong>${escapeHTML(comment.author_email)}</strong>
                <small class="text-muted">${new Date(comment.created_at).toLocaleDateString()}</small>
            </div>
            <div class="mt-2">${escapeHTML(comment.text)}</div>
        </div>
    `).join('');
}

// Comment submission
export async function submitComment() {
    const textElement = document.getElementById('commentText');
    const text = textElement?.value?.trim();

    if (!text) {
        alert('Please enter a comment');
        return;
    }

    try {
        log(DEBUG_LEVELS.INFO, 'Submitting comment');
        const response = await fetch('/api/comments', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({ text })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        textElement.value = '';
        await loadComments();
    } catch (error) {
        log(DEBUG_LEVELS.ERROR, 'Comment submission failed:', error);
        alert('Error submitting comment. Please try again.');
    }
}

// Utility function for timestamp
function updateTimestamp(timestamp) {
    const element = document.getElementById('lastUpdated');
    if (element && timestamp) {
        element.textContent = new Date(timestamp).toLocaleDateString();
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', initializeApp);

// Exports
export {
    updateLoadingState,
    updateTimestamp,
    displayComments
};

