// C:\Users\demck\OneDrive\Football_2024\static-football-rankings\docs\js\main.js

// ============= 1. CORE FUNCTIONALITY =============

// Add at the top of the file
import { teamConfig } from '../config/teamConfig.js';

// Configuration
const ITEMS_PER_PAGE = 100;
let currentPage = 1;
let programsData = [];
const API_BASE_URL = 'https://static-football-rankings.vercel.app';

// Debug settings
const DEBUG = true;
function debugLog(...args) {
    if (DEBUG) {
        console.log('[DEBUG]', ...args);
    }
}

// Timestamp Update
function updateTimestamp() {
    const today = new Date();
    const formattedDate = today.toLocaleDateString('en-US', {
        month: '2-digit',
        day: '2-digit',
        year: 'numeric'
    });
    const timestampElement = document.getElementById('lastUpdated');
    if (timestampElement) {
        timestampElement.textContent = formattedDate;
    } else {
        debugLog('Timestamp element not found');
    }
}

// Loading State Update
function updateLoadingState(isLoading, errorMessage = '') {
    const header = document.querySelector('.team-header');
    if (!header) {
        debugLog('Team header element not found for loading state');
        return;
    }

    if (isLoading) {
        header.innerHTML = `
            <div class="container">
                <div class="text-center">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p>Loading program data...</p>
                </div>
            </div>
        `;
    } else if (errorMessage) {
        header.innerHTML = `
            <div class="container">
                <div class="text-center text-danger">
                    <p>Error loading data: ${errorMessage}</p>
                </div>
            </div>
        `;
    }
}

// ============= 2. PROGRAM DATA HANDLING =============

async function loadProgramData() {
    debugLog('Loading program data...');
    try {
        const response = await fetch('data/all-time-programs-fifty.json');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        debugLog('Loaded JSON data:', data);
        
        if (!data || !data.programs) {
            throw new Error('Invalid data format: Missing "programs" array');
        }

        programsData = data.programs;
        debugLog(`Loaded ${programsData.length} programs`);

        // Handle top program separately
        if (data.topProgram) {
            debugLog('Top program data:', data.topProgram);
            updateTeamHeader(data.topProgram);
        } else {
            debugLog('No topProgram found in data');
        }

        return true;
    } catch (error) {
        console.error('Error loading program data:', error);
        updateLoadingState(false, error.message);
        return false;
    }
}

// ============= 3. UI UPDATE FUNCTIONS =============

// Function to be used in both main.js and pageTemplate.js
function updateTeamHeader(program) {
    log(DEBUG_LEVELS.DEBUG, 'Updating team header', { 
        team: program.team,
        logoUrl: program.LogoURL,
        schoolLogoUrl: program.School_Logo_URL
    });

    const header = document.querySelector('.team-header');
    if (!header) {
        log(DEBUG_LEVELS.ERROR, 'Team header element not found');
        return;
    }

    const headerContent = `
        <div class="container">
            <div class="row align-items-center">
                <div class="col-md-3">
                    <img src="${program.LogoURL || '/static-football-rankings/docs/images/placeholder-image.jpg'}"
                         alt="${program.team} Logo"
                         class="img-fluid team-logo"
                         style="max-height: 100px;"
                         onerror="this.src='/static-football-rankings/docs/images/placeholder-image.jpg'"
                         onload="console.log('Logo loaded successfully:', this.src)"
                         onerror="console.log('Logo failed to load:', this.src)" />
                </div>
                <div class="col-md-6 text-center">
                    <h2 class="team-name">${program.team}</h2>
                    <p class="team-mascot">${program.mascot || ''}</p>
                    <div class="team-stats">
                        <small>Seasons: ${program.seasons} | Combined Rating: ${typeof program.avgCombined === 'number' ? program.avgCombined.toFixed(3) : program.avgCombined}</small>
                    </div>
                </div>
                <div class="col-md-3 text-right">
                    <img src="${program.School_Logo_URL || '/static-football-rankings/docs/images/placeholder-image.jpg'}"
                         alt="${program.team} School Logo"
                         class="img-fluid school-logo"
                         style="max-height: 100px;"
                         onerror="this.src='/static-football-rankings/docs/images/placeholder-image.jpg'"
                         onload="console.log('School logo loaded successfully:', this.src)"
                         onerror="console.log('School logo failed to load:', this.src)" />
                </div>
            </div>
        </div>
    `;

    header.innerHTML = headerContent;
    header.style.backgroundColor = program.backgroundColor || '#000000';
    header.style.color = program.textColor || '#FFFFFF';

    log(DEBUG_LEVELS.DEBUG, 'Header update complete');
}

//function displayCurrentPage

function displayCurrentPage(data = programsData) {
    const tableBody = document.getElementById('programsTableBody');
    if (!tableBody) {
        console.error('Programs table body element not found');
        return;
    }

    const start = (currentPage - 1) * ITEMS_PER_PAGE;
    const end = start + ITEMS_PER_PAGE;
    const currentData = data.slice(start, end);
    
    tableBody.innerHTML = '';
    
    currentData.forEach(program => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${program.rank}</td>
            <td>${program.team}</td>
            <td>${typeof program.avgCombined === 'number' ? program.avgCombined.toFixed(3) : program.avgCombined}</td>
            <td>${typeof program.avgMargin === 'number' ? program.avgMargin.toFixed(3) : program.avgMargin}</td>
            <td>${typeof program.avgWinLoss === 'number' ? program.avgWinLoss.toFixed(3) : program.avgWinLoss}</td>
            <td>${typeof program.avgOffense === 'number' ? program.avgOffense.toFixed(3) : program.avgOffense}</td>
            <td>${typeof program.avgDefense === 'number' ? program.avgDefense.toFixed(3) : program.avgDefense}</td>
            <td>${program.state}</td>
            <td>${program.seasons}</td>
            <td>
                <a href="/program/${encodeURIComponent(program.team)}" 
                   class="btn btn-primary btn-sm">View Details</a>
            </td>
        `;
        tableBody.appendChild(row);
    });
}

// setupPagination function

function setupPagination(data = programsData) {
    const totalPages = Math.ceil(data.length / ITEMS_PER_PAGE);
    const paginationElement = document.getElementById('pagination');
    
    if (!paginationElement) {
        console.error('Pagination element not found');
        return;
    }
    
    paginationElement.innerHTML = '';
    
    for (let i = 1; i <= totalPages; i++) {
        const li = document.createElement('li');
        li.className = `page-item ${currentPage === i ? 'active' : ''}`;
        
        const button = document.createElement('button');
        button.className = 'page-link';
        button.textContent = i;
        button.addEventListener('click', () => {
            currentPage = i;
            displayCurrentPage(data);
            setupPagination(data);
        });
        
        li.appendChild(button);
        paginationElement.appendChild(li);
    }
}

function handleSearch(event) {
    const searchTerm = event.target.value.toLowerCase();
    const filteredPrograms = programsData.filter(program => 
        program.team.toLowerCase().includes(searchTerm) ||
        program.state.toLowerCase().includes(searchTerm)
    );
    
    currentPage = 1;
    setupPagination(filteredPrograms);
    displayCurrentPage(filteredPrograms);
}

// ============= 4. COMMENTS HANDLING =============

async function loadComments() {
    try {
        console.log('Loading comments...');
        const url = `${API_BASE_URL}/api/comments`;
        console.log('Request URL:', url);

        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            mode: 'cors'
        });

        console.log('Response status:', response.status);
        console.log('Response type:', response.type);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const comments = await response.json();
        displayComments(comments);
    } catch (error) {
        console.error('Detailed error:', error);
        const commentsList = document.getElementById('commentsList');
        if (commentsList) {
            commentsList.innerHTML = `<div class="alert alert-danger">Error loading comments. Please try again later.</div>`;
        }
    }
}

function displayComments(comments) {
    const commentsListElement = document.getElementById('commentsList');
    if (!commentsListElement) {
        console.error('Comments list element not found');
        return;
    }
    commentsListElement.innerHTML = comments.map(comment => `
        <div class="comment mb-3 p-3 border rounded">
            <div class="comment-header d-flex justify-content-between">
                <strong>${comment.author_email}</strong>
                <small class="text-muted">
                    ${new Date(comment.created_at).toLocaleDateString()}
                </small>
            </div>
            <div class="comment-body mt-2">
                ${comment.text}
            </div>
        </div>
    `).join('');
}

async function submitComment() {
    const textElement = document.getElementById('commentText');
    const emailElement = document.getElementById('commentEmail');
    
    if (!textElement || !emailElement) {
        console.error('Comment form elements not found');
        return;
    }

    const text = textElement.value.trim();
    const email = emailElement.value.trim();
    
    if (!text) {
        alert('Please enter a comment');
        return;
    }
    
    if (!email) {
        alert('Please enter your email');
        return;
    }
    
    try {
        console.log('Submitting comment...');
        const verifyResponse = await fetch(`${API_BASE_URL}/api/verify-email`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            mode: 'cors',
            body: JSON.stringify({
                email,
                pendingCommentData: {
                    text,
                    page: 'main',
                    parentId: null
                }
            })
        });
        
        console.log('Verify response status:', verifyResponse.status);
        
        if (verifyResponse.ok) {
            textElement.value = '';
            emailElement.value = '';
            alert('Please check your email to verify and post your comment.');
        } else {
            const error = await verifyResponse.json();
            alert(`Error: ${error.message || 'Failed to send verification email'}`);
        }
    } catch (error) {
        console.error('Error submitting comment:', error);
        alert('Error submitting comment. Please try again.');
    }
}

// ============= 5. INITIALIZATION =============

async function initializeApp() {
    debugLog('Initializing app...');
    
    try {
        // Show loading state
        updateLoadingState(true);
        
        // Load and process program data
        const dataLoaded = await loadProgramData();
        if (!dataLoaded) {
            throw new Error('Failed to load program data');
        }
        
        // Setup UI components
        setupPagination();
        displayCurrentPage();
        updateTimestamp();
        
        // Add event listeners
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.addEventListener('input', handleSearch);
        } else {
            debugLog('Search input element not found');
        }
        
        // Set up comment submission
        const submitButton = document.getElementById('submitComment');
        if (submitButton) {
            submitButton.addEventListener('click', submitComment);
            debugLog('Comment submit listener added');
        } else {
            debugLog('Submit comment button not found');
        }
        
        // Load comments
        loadComments();
        
        // Hide loading state
        updateLoadingState(false);
        
        debugLog('App initialization complete');
        
    } catch (error) {
        console.error('Error initializing app:', error);
        updateLoadingState(false, error.message);
    }
}

// Start the application
document.addEventListener('DOMContentLoaded', initializeApp);
