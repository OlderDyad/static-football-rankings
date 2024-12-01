//=============================================================================
// SECTION 1: CONFIGURATION AND CONSTANTS
//=============================================================================

// Debug Configuration
const DEBUG = true;
function debug(...args) {
    if (DEBUG) {
        console.log('[DEBUG]', ...args);
    }
}

// Repository and Image Paths
const REPO_BASE = '/static-football-rankings';
const IMAGE_BASE = `${REPO_BASE}/docs/images`;
const DEFAULT_PLACEHOLDER = `${IMAGE_BASE}/placeholder-image.jpg`;
const ITEMS_PER_PAGE = 100;

// API Configuration
const API_BASE = 'https://static-football-rankings.vercel.app/api';
const LOGIN_API_BASE = `${API_BASE}/auth`;

// Log initial configuration
debug('Configuration loaded:', {
    REPO_BASE,
    API_BASE,
    LOGIN_API_BASE
});

//=============================================================================
// SECTION 2: GLOBAL STATE MANAGEMENT
//=============================================================================

let currentPage = 1;
let programsData = [];
let isLoggedIn = false;
let userName = '';

// Log initial state
debug('Initial state:', {
    currentPage,
    isLoggedIn,
    userName
});


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
// SECTION 3.0: AUTHENTICATION UI
//=============================================================================

// Check login status
async function checkLoginStatus() {
    console.log("[DEBUG] Checking login status...");
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
        console.log("[DEBUG] Login status data:", data);

        isLoggedIn = Boolean(data.loggedIn);
        userName = data.user?.name || '';
        console.log(`[DEBUG] Auth state: logged in = ${isLoggedIn}, user = ${userName}`);

        updateAuthUI();
        return data;
    } catch (error) {
        console.error("[ERROR] Error checking login status:", error);
        isLoggedIn = false;
        userName = '';
        updateAuthUI();
        return { loggedIn: false, user: null };
    }
}

// Update the authentication UI
function updateAuthUI() {
    console.log("[DEBUG] Updating auth UI, logged in:", isLoggedIn);
    const authContainer = document.getElementById('authContainer');

    if (!authContainer) {
        console.error("[ERROR] Auth container not found");
        return;
    }

    if (isLoggedIn) {
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

// Handle login and logout
function handleLogin() {
    console.log("[DEBUG] Initiating Google login...");
    try {
        const loginUrl = `${LOGIN_API_BASE}/google?t=${Date.now()}`;
        console.log("[DEBUG] Redirecting to:", loginUrl);
        window.location.href = loginUrl;
    } catch (error) {
        console.error("[ERROR] Login error:", error);
        showAuthError("Login failed. Please try again.");
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
        updateAuthUI();
        await loadComments();
    } catch (error) {
        console.error("[ERROR] Logout error:", error);
        showAuthError("Logout failed. Please try again.");
    }
}

// Show authentication error message
function showAuthError(message) {
    const authContainer = document.getElementById('authContainer');
    if (authContainer) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger mt-2';
        errorDiv.textContent = message;
        authContainer.appendChild(errorDiv);
        setTimeout(() => errorDiv.remove(), 3000);
    }
}

//=============================================================================
// SECTION 3.1: AUTHENTICATION AND COMMENTS
//=============================================================================

// Load and display comments
async function loadComments() {
    console.log("[DEBUG] Loading comments...");
    const commentsContainer = document.getElementById('commentsList');
    if (!commentsContainer) {
        console.error("[ERROR] Comments container not found");
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

        console.log("[DEBUG] Raw response:", response);
        console.log("[DEBUG] Response status:", response.status);
        console.log("[DEBUG] Response type:", response.type);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const rawData = await response.json();
        console.log("[DEBUG] Raw data from API:", rawData);

        // Safely extract comments array
        let comments;
        if (rawData && typeof rawData === 'object') {
            comments = rawData.comments || [];
        } else {
            comments = [];
        }

        // Verify it's an array
        if (!Array.isArray(comments)) {
            console.error("[ERROR] Comments is not an array:", comments);
            comments = [];
        }

        console.log("[DEBUG] Final comments array:", comments);
        displayComments(comments);
    } catch (error) {
        console.error("[ERROR] Error loading comments:", error);
        commentsContainer.innerHTML = `
            <div class="alert alert-warning">
                Error loading comments. Please try again later.
            </div>
        `;
    }
}

// Display comments
function displayComments(commentsArray = []) {
    console.log("[DEBUG] Starting displayComments with:", commentsArray);
    const commentsContainer = document.getElementById('commentsList');
    
    if (!commentsContainer) {
        console.error("[ERROR] Comments container not found");
        return;
    }

    // Ensure we have an array
    if (!Array.isArray(commentsArray)) {
        console.error("[ERROR] Invalid comments data type:", typeof commentsArray);
        commentsContainer.innerHTML = '<div class="alert alert-warning">Error displaying comments.</div>';
        return;
    }

    // Handle empty array
    if (commentsArray.length === 0) {
        console.log("[DEBUG] No comments to display");
        commentsContainer.innerHTML = '<p class="text-muted">No comments yet. Be the first to comment!</p>';
        return;
    }

    try {
        console.log("[DEBUG] Generating HTML for comments");
        const commentsHTML = commentsArray
            .filter(comment => comment && typeof comment === 'object')
            .map(comment => {
                console.log("[DEBUG] Processing comment:", comment);
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
            })
            .join('');

        console.log("[DEBUG] Final HTML generated:", commentsHTML.substring(0, 100) + '...');
        commentsContainer.innerHTML = commentsHTML || '<p class="text-muted">No valid comments to display.</p>';
    } catch (error) {
        console.error("[ERROR] Error rendering comments:", error);
        commentsContainer.innerHTML = '<div class="alert alert-warning">Error displaying comments.</div>';
    }
}

// Helper function to escape HTML
function escapeHTML(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// Helper function for time formatting
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
// SECTION 3.2: HANDLING COMMENT SUBMISSION
//=============================================================================

// Handle comment submission
async function submitComment() {
    if (!isLoggedIn) {
        showAuthError('Please sign in to post comments');
        return;
    }

    const textElement = document.getElementById('commentText');
    const text = textElement?.value?.trim();
    
    if (!text) {
        console.log("[DEBUG] No comment text provided");
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
            console.log("[DEBUG] Comment submitted successfully");
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
        console.error("[ERROR] Error submitting comment:", error);
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger mt-2';
        errorDiv.textContent = 'Unable to submit comment. Please try again later.';
        textElement.parentNode.insertBefore(errorDiv, textElement.nextSibling);
        
        setTimeout(() => errorDiv.remove(), 3000);
    } finally {
        updateCommentFormState(false);
    }
}

// Update comment form state during submission
function updateCommentFormState(isSubmitting) {
    const submitButton = document.getElementById('submitComment');
    const textElement = document.getElementById('commentText');
    
    if (!submitButton || !textElement) {
        console.warn("[WARN] Comment form elements not found");
        return;
    }
    
    submitButton.disabled = isSubmitting;
    submitButton.innerHTML = isSubmitting 
        ? '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Posting...'
        : 'Post Comment';
    textElement.disabled = isSubmitting;
}

// Format timestamp for display
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

//=============================================================================
// SECTION 5: CORE DATA LOADING AND DISPLAY
//=============================================================================

async function initializeRankings() {
    console.log('Initializing rankings...');
    try {
        updateLoadingState(true);
        const response = await fetch('/static-football-rankings/data/all-time-programs-fifty.json');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        programsData = await response.json();
        
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

// Additional display functions needed for other pages
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

// Export functions for other modules
export {
    initializeRankings,
    updateTeamHeader,
    displayCurrentPage
};

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

// Display comments handler
function displayComments(comments = []) {
    debug('Displaying comments:', comments);
    const commentsContainer = document.getElementById('commentsList');
    
    if (!commentsContainer) {
        console.error('Comments container not found');
        return;
    }

    // Handle empty or invalid data
    if (comments.length === 0) {
        commentsContainer.innerHTML = '<p class="text-muted">No comments yet. Be the first to comment!</p>';
        return;
    }

    try {
        const commentHTML = comments.map(comment => {
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

        commentsContainer.innerHTML = commentHTML;
    } catch (error) {
        console.error('Error rendering comments:', error);
        commentsContainer.innerHTML = '<div class="alert alert-warning">Error displaying comments.</div>';
    }
}

// Load comments from API
async function loadComments() {
    debug('Loading comments...');
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

        debug('Comments response:', {
            status: response.status,
            type: response.type
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        debug('Comments data:', data);

        // Extract comments array
        const comments = Array.isArray(data.comments) ? data.comments : [];
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

// Submit new comment
async function submitComment() {
    if (!isLoggedIn) {
        showAlert('warning', 'Please sign in to post comments');
        return;
    }

    const textElement = document.getElementById('commentText');
    const text = textElement?.value?.trim();
    
    if (!text) {
        debug('No comment text provided');
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
            debug('Comment submitted successfully');
            textElement.value = '';
            showAlert('success', 'Comment posted successfully!');
            await loadComments();
        } else {
            throw new Error(result.error || 'Failed to submit comment');
        }
    } catch (error) {
        console.error('Error submitting comment:', error);
        showAlert('danger', 'Unable to submit comment. Please try again later.');
    } finally {
        updateCommentFormState(false);
    }
}

// Helper function to show alerts
function showAlert(type, message, duration = 3000) {
    const commentForm = document.getElementById('commentForm');
    if (commentForm) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} mt-2`;
        alertDiv.textContent = message;
        commentForm.insertBefore(alertDiv, commentForm.firstChild);
        setTimeout(() => alertDiv.remove(), duration);
    }
}

// Update form state during submission
function updateCommentFormState(isSubmitting) {
    const submitButton = document.getElementById('submitComment');
    const textElement = document.getElementById('commentText');
    
    if (!submitButton || !textElement) {
        debug('Comment form elements not found');
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
    debug(`Showing details for team: ${teamName}`);
    // Implementation for program details view will go here
}

//=============================================================================
// SECTION 9: MAIN INITIALIZATION
//=============================================================================

document.addEventListener('DOMContentLoaded', async function() {
    try {
        debug('Starting application initialization...');
        
        // Check for auth errors
        const urlParams = new URLSearchParams(window.location.search);
        const error = urlParams.get('error');
        if (error) {
            debug('Auth error detected:', error);
            showAuthError(error === 'auth_failed' 
                ? 'Authentication failed. Please try again.'
                : 'An error occurred. Please try again.');
        }

        // Initialize components in sequence
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

        debug('Application initialization complete');
    } catch (error) {
        console.error('Initialization error:', error);
        showAuthError('Failed to initialize application. Please refresh the page.');
    }
});