// ============================================================================
// docs/js/main.js - Main Application Entry Point
// ============================================================================

// ============================================================================
// IMPORTS
// ============================================================================
import { DEBUG_LEVELS, log } from './modules/logger.js';
import { initializePage } from './modules/pageTemplate.js';
import { createTeamHeader } from './modules/teamHeader.js';
import { teamConfig } from './config/teamConfig.js';
import { checkAuthStatus, updateAuthUI } from './modules/auth.js';
import { CommentManager } from './modules/comments.js';
import { formatDate, debounce, escapeHTML } from './modules/utils.js';
import { config } from './config/config.js';

// ============================================================================
// MAIN APPLICATION INITIALIZATION
// ============================================================================
async function initializeApp() {
    try {
        log(DEBUG_LEVELS.INFO, 'Initializing app...');

        const h1Element = document.querySelector('h1[data-page-name]');
        if (!h1Element) {
            throw new Error('Page configuration not found');
        }

        const pageName = h1Element.dataset.pageName;
        let pageTitle = h1Element.textContent;
        
        // Determine data file path based on meta tag or page name
        const dataFileMeta = document.querySelector('meta[name="data-file"]');
        let dataFile;
        
        if (dataFileMeta) {
            dataFile = dataFileMeta.content;
            log(DEBUG_LEVELS.INFO, `Loading data from ${dataFile}`);
        } else {
            // Handle different data file types based on page name
            dataFile = determineDataFile(pageName);
            log(DEBUG_LEVELS.INFO, `Determined data file: ${dataFile}`);
        }

        const pageConfig = {
            pageTitle: pageTitle,
            pageName: pageName,
            dataFile: dataFile
        };

        log(DEBUG_LEVELS.INFO, 'Page config:', pageConfig);

        // Load and validate data
        const data = await loadProgramData(dataFile);
        if (data.metadata?.timestamp) {
            updateTimestamp(data.metadata.timestamp);
        }

        // Create header if top item exists
        if (data.topItem) {
            createTeamHeader(data.topItem);
        }

        // Initialize page with data
        const page = initializePage(pageConfig);
        await page.initialize(data);

        // Setup additional features
        await checkAuthStatus();
        await loadComments();
        setupEventListeners();

    } catch (error) {
        log(DEBUG_LEVELS.ERROR, 'App initialization failed:', error);
        updateLoadingState(false, error.message);
    }
}

// ============================================================================
// DATA LOADING AND VALIDATION
// ============================================================================
async function loadProgramData(dataFile) {
    if (!dataFile) {
        throw new Error('No data file specified');
    }
    
    log(DEBUG_LEVELS.INFO, 'Loading program data from', dataFile);
    updateLoadingState(true);
    
    try {
        const response = await fetch(dataFile);
        
        if (!response.ok) {
            if (response.status === 404) {
                throw new Error(`Data file not found: ${dataFile}. Please check the file path and ensure the file exists.`);
            }
            throw new Error(`Failed to load data (HTTP ${response.status}): ${response.statusText}`);
        }
        
        let data;
        try {
            data = await response.json();
        } catch (parseError) {
            throw new Error(`Invalid JSON in data file: ${parseError.message}`);
        }
        
        validateDataStructure(data);
        
        return {
            items: data.items,
            topItem: data.topItem || null,
            metadata: data.metadata
        };

    } catch (error) {
        log(DEBUG_LEVELS.ERROR, 'Error loading program data:', error);
        throw error;
    } finally {
        updateLoadingState(false);
    }
}

function validateDataStructure(data) {
    if (!data?.metadata) {
        throw new Error('Invalid data format: Missing metadata section');
    }
    if (!data?.items || !Array.isArray(data.items)) {
        throw new Error('Invalid data format: Missing or invalid items array');
    }
    if (data.items.length === 0) {
        throw new Error('No data items found in response');
    }
}

// ============================================================================
// DATA FILE DETERMINATION
// ============================================================================
function determineDataFile(pageName) {
    // Default data directory path
    const baseDataPath = '/data';  // Direct path to data directory
    
    try {
        // Handle different page types
        if (pageName.includes('+')) {
            // All-time programs with season threshold
            const thresholdMatch = pageName.match(/(\d+)\+/);
            if (!thresholdMatch) {
                throw new Error('Invalid season threshold format');
            }
            const threshold = thresholdMatch[1];
            return `${baseDataPath}/all-time-programs-${threshold}.json`;
        } else if (pageName.includes('decade')) {
            // Decade-specific data
            const decadeMatch = pageName.match(/(\d{4}s)/);
            if (!decadeMatch) {
                throw new Error('Invalid decade format');
            }
            const decade = decadeMatch[1];
            return `${baseDataPath}/decade-teams-${decade}.json`;
        } else if (pageName.includes('state')) {
            // State-specific data
            const stateMatch = pageName.match(/state-(.*)/);
            if (!stateMatch) {
                throw new Error('Invalid state format');
            }
            const state = stateMatch[1];
            return `${baseDataPath}/state-teams-${state}.json`;
        } else if (pageName.includes('current')) {
            // Current season data
            return `${baseDataPath}/current-season-teams.json`;
        }
        
        // Default to all-time programs with 50+ seasons
        return `${baseDataPath}/all-time-programs-50.json`;
    } catch (error) {
        log(DEBUG_LEVELS.ERROR, 'Error determining data file:', error);
        // Default to a safe fallback
        return `${baseDataPath}/all-time-programs-50.json`;
    }
}

// ============================================================================
// TABLE POPULATION AND DISPLAY
// ============================================================================
function populateTable(data) {
    const tableBody = document.getElementById('programsTableBody');
    if (!tableBody) return;

    // Determine data type from metadata
    const dataType = data.metadata.type || 'unknown';
    const isTeamData = dataType.includes('teams');

    try {
        tableBody.innerHTML = data.items.map(item => {
            return isTeamData ? createTeamRow(item) : createProgramRow(item);
        }).join('');
    } catch (error) {
        log(DEBUG_LEVELS.ERROR, 'Error populating table:', error);
        tableBody.innerHTML = `
            <tr>
                <td colspan="11" class="text-center text-danger">
                    Error displaying data. Please try refreshing the page.
                </td>
            </tr>`;
    }
}

function createTeamRow(item) {
    return `
    <tr>
        <td>${item.rank}</td>
        <td>${item.team}</td>
        <td>${item.season}</td>
        <td>${formatNumber(item.combined)}</td>
        <td>${formatNumber(item.margin)}</td>
        <td>${formatNumber(item.win_loss)}</td>
        <td>${formatNumber(item.offense)}</td>
        <td>${formatNumber(item.defense)}</td>
        <td>${item.games_played}</td>
        <td>${item.state}</td>
        <td>
            <button class="btn btn-sm btn-primary" onclick="viewDetails('${encodeURIComponent(item.team)}')">
                Details
            </button>
        </td>
    </tr>`;
}

function createProgramRow(item) {
    return `
    <tr>
        <td>${item.rank}</td>
        <td>${item.program}</td>
        <td>${item.seasons}</td>
        <td>${formatNumber(item.combined)}</td>
        <td>${formatNumber(item.margin)}</td>
        <td>${formatNumber(item.win_loss)}</td>
        <td>${formatNumber(item.offense)}</td>
        <td>${formatNumber(item.defense)}</td>
        <td>${item.state}</td>
        <td>
            <button class="btn btn-sm btn-primary" onclick="viewDetails('${encodeURIComponent(item.program)}')">
                Details
            </button>
        </td>
    </tr>`;
}

// ============================================================================
// COMMENTS FUNCTIONALITY
// ============================================================================
async function loadComments() {
    try {
        log(DEBUG_LEVELS.INFO, 'Loading comments');
        
        // Check if we're in development mode
        const isDev = window.location.hostname === 'localhost' || 
                     window.location.hostname === '127.0.0.1';
        
        if (isDev) {
            log(DEBUG_LEVELS.INFO, 'Development mode: Using mock comments');
            // Use mock data in development
            displayComments([
                {
                    author_email: 'test@example.com',
                    created_at: new Date().toISOString(),
                    text: 'This is a mock comment for development.'
                }
            ]);
            return;
        }

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
            commentsList.innerHTML = '<div class="alert alert-danger">Comments temporarily unavailable</div>';
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
                <small class="text-muted">${formatDate(comment.created_at)}</small>
            </div>
            <div class="mt-2">${escapeHTML(comment.text)}</div>
        </div>
    `).join('');
}

async function submitComment() {
    const textElement = document.getElementById('commentText');
    const text = textElement?.value?.trim();

    if (!text) {
        alert('Please enter a comment');
        return;
    }

    try {
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

// ============================================================================
// EVENT LISTENERS AND UI UPDATES
// ============================================================================
function setupEventListeners() {
    const submitButton = document.getElementById('submitComment');
    if (submitButton) {
        submitButton.addEventListener('click', submitComment);
    }

    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(handleSearch, 300));
    }
}

function handleSearch(event) {
    // Implementation moved to pageTemplate.js for better organization
}

// ============================================================================
// LOADING STATE MANAGEMENT
// ============================================================================
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
                    <p>Loading data...</p>
                </div>
            </div>`;
    } else if (errorMessage) {
        header.innerHTML = `
            <div class="container">
                <div class="alert alert-danger">${escapeHTML(errorMessage)}</div>
            </div>`;
    }
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================
function formatNumber(value) {
    return typeof value === 'number' ? value.toFixed(3) : value;
}

function updateTimestamp(timestamp) {
    const element = document.getElementById('lastUpdated');
    if (element && timestamp) {
        element.textContent = new Date(timestamp).toLocaleDateString();
    }
}

function viewDetails(teamName) {
    const decodedName = decodeURIComponent(teamName);
    log(DEBUG_LEVELS.INFO, 'Viewing details for:', decodedName);
    // TODO: Implement details view modal or navigation
    alert(`Details for ${decodedName} coming soon!`);
}

// ============================================================================
// INITIALIZATION AND EXPORTS
// ============================================================================
document.addEventListener('DOMContentLoaded', initializeApp);

// Add viewDetails to window object for onclick handlers
window.viewDetails = viewDetails;

export {
    updateLoadingState,
    determineDataFile,
    updateTimestamp,
    viewDetails,
    loadComments,
    displayComments,
    submitComment,
    populateTable
};



