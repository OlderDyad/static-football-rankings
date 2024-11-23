/**
 * main.js - Football Rankings Application
 * Version: 1.0.0
 * Last Updated: 2024-11-22
 */

//=============================================================================
// SECTION 1: CONFIGURATION AND CONSTANTS
//=============================================================================

const REPO_BASE = '/static-football-rankings';
const IMAGE_BASE = `${REPO_BASE}/docs/images`;
const DEFAULT_PLACEHOLDER = `${IMAGE_BASE}/placeholder-image.jpg`;
const ITEMS_PER_PAGE = 100;

// API Configuration
const API_BASE = (() => {
    const possibleUrls = [
        'https://static-football-rankings.vercel.app/api'
    ];
    return possibleUrls[0];
})();

const LOGIN_API_BASE = `${API_BASE}/auth`;

//=============================================================================
// SECTION 2: GLOBAL STATE MANAGEMENT
//=============================================================================

let currentPage = 1;
let programsData = [];
let isLoggedIn = false;
let userName = '';

//=============================================================================
// SECTION 3: AUTHENTICATION HANDLERS
//=============================================================================

async function checkLoginStatus() {
    console.log("Checking login status...");
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
        console.log("Login status data:", data);

        isLoggedIn = Boolean(data.loggedIn);
        userName = data.user?.name || '';
        console.log(`Auth state: logged in = ${isLoggedIn}, user = ${userName}`);

        if (isLoggedIn) {
            showLoggedInState();
        } else {
            showLoggedOutState();
        }

        return data;
    } catch (error) {
        console.error("Error checking login status:", error);
        isLoggedIn = false;
        userName = '';
        showLoggedOutState();
        return { loggedIn: false, user: null };
    }
}

function showLoggedInState() {
    console.log('Showing logged in state');
    const loginArea = document.getElementById('loginArea');
    const commentForm = document.getElementById('commentForm');
    const authorName = document.getElementById('authorName');

    if (loginArea) {
        loginArea.innerHTML = `
            <div class="d-flex align-items-center justify-content-between">
                <span class="me-2">Welcome, ${userName}</span>
                <button id="logoutButton" class="btn btn-outline-secondary btn-sm">Logout</button>
            </div>
        `;
        const logoutButton = document.getElementById('logoutButton');
        if (logoutButton) {
            logoutButton.addEventListener('click', handleLogout);
        }
    }

    if (commentForm) {
        commentForm.style.display = 'block';
    }

    if (authorName) {
        authorName.textContent = userName || 'Anonymous';
    }
}

//=============================================================================
// SECTION 3: AUTHENTICATION HANDLERS
//=============================================================================

function showLoggedInState() {
    console.log('Showing logged in state');
    const authContainer = document.getElementById('authContainer');
    const commentForm = document.getElementById('commentForm');
    const authorName = document.getElementById('authorName');

    if (authContainer) {
        authContainer.innerHTML = `
            <div class="d-flex align-items-center justify-content-between">
                <span class="me-2">Welcome, ${userName}</span>
                <button id="logoutButton" class="btn btn-outline-secondary btn-sm">Logout</button>
            </div>
        `;
        const logoutButton = document.getElementById('logoutButton');
        if (logoutButton) {
            logoutButton.addEventListener('click', handleLogout);
        }
    }

    if (commentForm) {
        commentForm.style.display = 'block';
    }

    if (authorName) {
        authorName.textContent = userName || 'Anonymous';
    }
}

function showLoggedOutState() {
    console.log('Showing logged out state');
    const authContainer = document.getElementById('authContainer');
    const commentForm = document.getElementById('commentForm');

    if (authContainer) {
        authContainer.innerHTML = `
            <div class="d-flex align-items-center">
                <button id="loginButton" class="btn btn-primary d-flex align-items-center gap-2">
                    <img src="${REPO_BASE}/docs/images/google-logo.png" 
                         alt="" 
                         style="height: 18px; width: 18px;"
                         onerror="this.style.display='none'"
                    />
                    <span>Sign in with Google</span>
                </button>
            </div>
        `;
        const loginButton = document.getElementById('loginButton');
        if (loginButton) {
            loginButton.addEventListener('click', handleLogin);
        }
    } else {
        console.error('Auth container not found');
    }

    if (commentForm) {
        commentForm.style.display = 'none';
    }
}

function handleLogin() {
    console.log('Initiating Google login...');
    try {
        window.location.href = `${LOGIN_API_BASE}/google?t=${Date.now()}`;
    } catch (error) {
        console.error('Login error:', error);
        const authContainer = document.getElementById('authContainer');
        if (authContainer) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'alert alert-danger mt-2';
            errorDiv.textContent = 'Login failed. Please try again.';
            authContainer.appendChild(errorDiv);
            setTimeout(() => errorDiv.remove(), 3000);
        }
    }
}

async function handleLogout() {
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
        showLoggedOutState();
        await loadComments();
    } catch (error) {
        console.error('Logout error:', error);
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger mt-2';
        errorDiv.textContent = 'Logout failed. Please try again.';
        const authContainer = document.getElementById('authContainer');
        if (authContainer) {
            authContainer.appendChild(errorDiv);
            setTimeout(() => errorDiv.remove(), 3000);
        }
    }
}

// Update error handling in initialization code
const authErrorHandler = (error) => {
    const authContainer = document.getElementById('authContainer');
    if (authContainer) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger mt-2';
        errorDiv.textContent = error === 'auth_failed' 
            ? 'Authentication failed. Please try again.'
            : 'An error occurred. Please try again.';
        authContainer.appendChild(errorDiv);
        setTimeout(() => errorDiv.remove(), 3000);
    }
};

//=============================================================================
// SECTION 4: UTILITY FUNCTIONS
//=============================================================================

function getImagePath(relativePath, isPlaceholder = false) {
    if (!relativePath || isPlaceholder) {
        const placeholderPath = `${IMAGE_BASE}/placeholder-image.jpg`;
        console.log('Using placeholder:', placeholderPath);
        return placeholderPath;
    }

    const cleanPath = relativePath.replace(/^images\//, '');
    const normalizedPath = cleanPath.replace(/^Teams\//, 'teams/');
    const fullPath = `${IMAGE_BASE}/${normalizedPath}`;
    console.log('Constructed path:', fullPath);
    return fullPath;
}

function updateLoadingState(isLoading, errorMessage = '') {
    const header = document.querySelector('.team-header');
    if (!header) {
        console.error('Team header element not found');
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
            </div>`;
    } else if (errorMessage) {
        header.innerHTML = `
            <div class="container">
                <div class="alert alert-danger">${errorMessage}</div>
            </div>`;
    }
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

//=============================================================================
// SECTION 5: CORE DATA LOADING AND DISPLAY
//=============================================================================

async function initializeRankings() {
    console.log('Initializing rankings...');
    try {
        updateLoadingState(true);
        const response = await fetch('data/all-time-programs-fifty.json');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        programsData = await response.json();
        console.log('Data loaded, programs count:', programsData.length);

        if (programsData.length > 0) {
            await updateTeamHeader(programsData[0]);
            setupPagination();
            displayCurrentPage();
        }

        updateLoadingState(false);
    } catch (error) {
        console.error('Error initializing rankings:', error);
        updateLoadingState(false, error.message);
    }
}

//=============================================================================
// SECTION 5: CORE DATA LOADING AND DISPLAY (continued)
//=============================================================================

async function updateTeamHeader(program) {
    console.log('Updating team header for:', program.Team);
    const header = document.querySelector('.team-header');
    if (!header) {
        console.error('Team header element not found');
        return;
    }

    header.innerHTML = `
        <div class="container">
            <div class="row align-items-center">
                <div class="col-md-3">
                    <img src="${getImagePath(program.LogoURL)}"
                         alt="${program.Team} Logo"
                         class="img-fluid team-logo"
                         style="max-height: 100px;"
                         onerror="this.src='${DEFAULT_PLACEHOLDER}'" />
                </div>
                <div class="col-md-6 text-center">
                    <h2 class="team-name">${program.Team}</h2>
                    <p class="team-mascot">${program.Mascot || ''}</p>
                    <div class="team-stats">
                        <small>Seasons: ${program.Seasons} | Combined Rating: ${program.AvgCombined.toFixed(3)}</small>
                    </div>
                </div>
                <div class="col-md-3 text-right">
                    <img src="${getImagePath(program.School_Logo_URL)}"
                         alt="${program.Team} School Logo"
                         class="img-fluid school-logo"
                         style="max-height: 100px;"
                         onerror="this.src='${DEFAULT_PLACEHOLDER}'" />
                </div>
            </div>
        </div>
    `;

    header.style.backgroundColor = program.PrimaryColor || '#000000';
    header.style.color = program.SecondaryColor || '#FFFFFF';
}

//=============================================================================
// SECTION 6: SEARCH AND PAGINATION FUNCTIONS
//=============================================================================

function handleSearch(event) {
    const searchTerm = event.target.value.toLowerCase();
    console.log('Searching for:', searchTerm);

    const filteredPrograms = programsData.filter(program =>
        program.Team.toLowerCase().includes(searchTerm) ||
        program.State.toLowerCase().includes(searchTerm)
    );

    currentPage = 1;
    setupPagination(filteredPrograms);
    displayCurrentPage(filteredPrograms);
}

function setupPagination(data = programsData) {
    console.log('Setting up pagination with data length:', data.length);
    const paginationElement = document.getElementById('pagination');
    if (!paginationElement) {
        console.warn('Creating pagination element');
        const nav = document.createElement('nav');
        nav.innerHTML = '<ul class="pagination" id="pagination"></ul>';
        const tableContainer = document.querySelector('.table-responsive');
        if (tableContainer) {
            tableContainer.after(nav);
        }
        return setupPagination(data);
    }

    const totalPages = Math.ceil(data.length / ITEMS_PER_PAGE);
    paginationElement.innerHTML = '';

    // Add Previous button
    const prevLi = document.createElement('li');
    prevLi.className = `page-item ${currentPage === 1 ? 'disabled' : ''}`;
    prevLi.innerHTML = `
        <button class="page-link" ${currentPage === 1 ? 'disabled' : ''}>Previous</button>
    `;
    prevLi.addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            displayCurrentPage(data);
            setupPagination(data);
        }
    });
    paginationElement.appendChild(prevLi);

    // Add page numbers
    for (let i = 1; i <= totalPages; i++) {
        const li = document.createElement('li');
        li.className = `page-item ${currentPage === i ? 'active' : ''}`;
        li.innerHTML = `<button class="page-link">${i}</button>`;
        li.addEventListener('click', () => {
            currentPage = i;
            displayCurrentPage(data);
            setupPagination(data);
        });
        paginationElement.appendChild(li);
    }

    // Add Next button
    const nextLi = document.createElement('li');
    nextLi.className = `page-item ${currentPage === totalPages ? 'disabled' : ''}`;
    nextLi.innerHTML = `
        <button class="page-link" ${currentPage === totalPages ? 'disabled' : ''}>Next</button>
    `;
    nextLi.addEventListener('click', () => {
        if (currentPage < totalPages) {
            currentPage++;
            displayCurrentPage(data);
            setupPagination(data);
        }
    });
    paginationElement.appendChild(nextLi);
}

function displayCurrentPage(data = programsData) {
    console.log('Displaying page:', currentPage);
    const tableBody = document.getElementById('programsTableBody');
    if (!tableBody) {
        console.error('Table body element not found');
        return;
    }

    const start = (currentPage - 1) * ITEMS_PER_PAGE;
    const end = start + ITEMS_PER_PAGE;
    const currentData = data.slice(start, end);

    tableBody.innerHTML = '';

    currentData.forEach(program => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${program.Rank}</td>
            <td>${program.Team}</td>
            <td>${program.AvgCombined.toFixed(3)}</td>
            <td>${program.AvgMargin.toFixed(3)}</td>
            <td>${program.AvgWinLoss.toFixed(3)}</td>
            <td>${program.AvgOffense.toFixed(3)}</td>
            <td>${program.AvgDefense.toFixed(3)}</td>
            <td>${program.State}</td>
            <td>${program.Seasons}</td>
            <td>
                <button onclick="showProgramDetails('${program.Team}')"
                        class="btn btn-primary btn-sm">View Details</button>
            </td>
        `;
        tableBody.appendChild(row);
    });
}

//=============================================================================
// SECTION 7: COMMENTS SYSTEM
//=============================================================================

function displayComments(commentsData = []) {
    console.log('Displaying comments:', commentsData);
    const commentsContainer = document.getElementById('commentsList');
    
    if (!commentsContainer) {
        console.error('Comments container not found');
        return;
    }

    if (!Array.isArray(commentsData) || commentsData.length === 0) {
        commentsContainer.innerHTML = '<p class="text-muted">No comments yet. Be the first to comment!</p>';
        return;
    }

    const commentHTML = commentsData.map(comment => {
        const timestamp = new Date(comment.timestamp);
        return `
            <div class="comment mb-3 p-3 border rounded">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <strong>${comment.author || 'Anonymous'}</strong>
                        <small class="text-muted ms-2">${getTimeAgo(timestamp)}</small>
                    </div>
                </div>
                <div class="mt-2">
                    ${escapeHTML(comment.text)}
                </div>
            </div>
        `;
    }).join('');

    commentsContainer.innerHTML = commentHTML;
}

async function loadComments() {
    console.log('Loading comments...');
    const commentsContainer = document.getElementById('commentsList');
    if (!commentsContainer) return;

    try {
        const response = await fetch(`${API_BASE}/comments`, {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        });

        console.log('Response status:', response.status);
        console.log('Response type:', response.type);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('Comments data:', data);

        const comments = Array.isArray(data) ? data : (data.comments || []);
        displayComments(comments);
    } catch (error) {
        console.error('Error loading comments:', error);
        commentsContainer.innerHTML = `
            <div class="alert alert-warning">
                Error loading comments. Please try again later.
            </div>
        `;
    }
}

async function submitComment() {
    if (!isLoggedIn) {
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-warning';
        alertDiv.textContent = 'Please sign in to post comments';
        const commentForm = document.getElementById('commentForm');
        if (commentForm) {
            commentForm.insertBefore(alertDiv, commentForm.firstChild);
            setTimeout(() => alertDiv.remove(), 3000);
        }
        return;
    }

    const textElement = document.getElementById('commentText');
    const text = textElement?.value?.trim();
    
    if (!text) {
        console.log('No comment text provided');
        return;
    }
    
    updateCommentFormState(true);
    
    const pageIdentifier = document.querySelector('h1')?.dataset.pageName || 'unknown-page';
    
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
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            console.log('Comment submitted successfully');
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
        console.error('Error submitting comment:', error);
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger mt-2';
        errorDiv.textContent = 'Unable to submit comment. Please try again later.';
        textElement.parentNode.insertBefore(errorDiv, textElement.nextSibling);
        
        setTimeout(() => errorDiv.remove(), 3000);
    } finally {
        updateCommentFormState(false);
    }
}

function updateCommentFormState(isSubmitting) {
    const submitButton = document.getElementById('submitComment');
    const textElement = document.getElementById('commentText');
    
    if (!submitButton || !textElement) {
        console.warn('Comment form elements not found');
        return;
    }
    
    submitButton.disabled = isSubmitting;
    submitButton.innerHTML = isSubmitting 
        ? '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Posting...'
        : 'Post Comment';
    textElement.disabled = isSubmitting;
}

//=============================================================================
// SECTION 8: PROGRAM DETAILS
//=============================================================================

function showProgramDetails(teamName) {
    console.log(`Showing details for team: ${teamName}`);
    // Implementation for program details view will go here
}

//=============================================================================
// SECTION 9: MAIN INITIALIZATION
//=============================================================================

document.addEventListener('DOMContentLoaded', async function() {
    try {
        console.log('Starting application initialization...');
        
        // Check for auth errors first
        const urlParams = new URLSearchParams(window.location.search);
        const error = urlParams.get('error');
        if (error) {
            console.log('Auth error detected:', error);
            const loginArea = document.getElementById('loginArea');
            if (loginArea) {
                const errorDiv = document.createElement('div');
                errorDiv.className = 'alert alert-danger mt-2';
                errorDiv.textContent = error === 'auth_failed' 
                    ? 'Authentication failed. Please try again.'
                    : 'An error occurred. Please try again.';
                loginArea.appendChild(errorDiv);
                setTimeout(() => errorDiv.remove(), 3000);
            }
        }

        // Initialize components in order
        await checkLoginStatus();
        await initializeRankings();
        await loadComments();

        // Set up event listeners
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.addEventListener('input', handleSearch);
        }

        const submitButton = document.getElementById('submitComment');
        if (submitButton) {
            submitButton.addEventListener('click', submitComment);
        }

        console.log('Application initialization complete');
    } catch (error) {
        console.error('Initialization error:', error);
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger';
        errorDiv.textContent = 'Failed to initialize application. Please refresh the page.';
        document.body.insertBefore(errorDiv, document.body.firstChild);
    }
});
