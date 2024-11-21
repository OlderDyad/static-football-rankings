// 1. Constants
const REPO_BASE = '/static-football-rankings';
const IMAGE_BASE = `${REPO_BASE}/docs/images`;
const DEFAULT_PLACEHOLDER = `${IMAGE_BASE}/placeholder-image.jpg`;
const ITEMS_PER_PAGE = 100;
const API_BASE = 'https://static-football-rankings.vercel.app/api';
const LOGIN_API_BASE = `${API_BASE}/auth`;
let isLoggedIn = false;
let userName = '';


// 2. State management
let currentPage = 1;
let programsData = [];

// 3. Utility Functions
function getImagePath(relativePath, isPlaceholder = false) {
    if (!relativePath || isPlaceholder) {
        const placeholderPath = `${IMAGE_BASE}/placeholder-image.jpg`;
        console.log('Using placeholder:', placeholderPath);
        return placeholderPath;
    }

    // Remove any 'images/' prefix from the path
    const cleanPath = relativePath.replace(/^images\//, '');

    // Convert 'Teams' to lowercase 'teams' in the path
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

// 4. Core Data Loading and Display
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

// 5. Search and Pagination Functions
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
        return setupPagination(data); // Retry now that element exists
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

// 6. Comments System

//Google Login:
async function checkLoginStatus() {
    try {
        const response = await fetch(`${LOGIN_API_BASE}/status`, {
            method: 'GET',
            credentials: 'include'
        });

        if (response.ok) {
            const data = await response.json();
            isLoggedIn = true;
            userName = data.name || 'User';
            showLoggedInState();
        } else {
            isLoggedIn = false;
            showLoggedOutState();
        }
    } catch (error) {
        console.error('Error checking login status:', error);
        isLoggedIn = false;
        showLoggedOutState();
    }
}

function showLoggedInState() {
    const loginArea = document.getElementById('loginArea');
    if (loginArea) {
        loginArea.innerHTML = `
            <span class="text-muted">Logged in as ${userName}</span>
            <button id="logoutButton" class="btn btn-outline-secondary ms-2">Logout</button>
        `;
        const logoutButton = document.getElementById('logoutButton');
        logoutButton.addEventListener('click', handleLogout);
    }

    const commentForm = document.getElementById('commentForm');
    if (commentForm) commentForm.style.display = 'block';
}

function showLoggedOutState() {
    const loginArea = document.getElementById('loginArea');
    if (loginArea) {
        loginArea.innerHTML = `
            <button id="loginButton" class="btn btn-outline-primary">Login with Google</button>
        `;
        const loginButton = document.getElementById('loginButton');
        loginButton.addEventListener('click', handleLogin);
    }

    const commentForm = document.getElementById('commentForm');
    if (commentForm) commentForm.style.display = 'none';
}

function handleLogin() {
    window.location.href = `${LOGIN_API_BASE}/google`;
}

async function handleLogout() {
    try {
        await fetch(`${LOGIN_API_BASE}/logout`, {
            method: 'POST',
            credentials: 'include'
        });
        isLoggedIn = false;
        userName = '';
        showLoggedOutState();
    } catch (error) {
        console.error('Error logging out:', error);
    }
}


//updateCommentFormStat

function updateCommentFormState(isSubmitting) {
    const submitButton = document.getElementById('submitComment');
    const textElement = document.getElementById('commentText');
    
    if (!submitButton || !textElement) {
        console.warn('Comment form elements not found');
        return;
    }
    
    if (isSubmitting) {
        submitButton.disabled = true;
        submitButton.innerHTML = `
            <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
            Posting...
        `;
        textElement.disabled = true;
    } else {
        submitButton.disabled = false;
        submitButton.textContent = 'Post Comment';
        textElement.disabled = false;
    }
}

//Load Comments

async function loadComments() {
    console.log('Starting comments load...');
    const commentsListElement = document.getElementById('commentsList');
    
    if (!commentsListElement) {
        console.warn('Comments list element not found');
        return;
    }
 
    commentsListElement.innerHTML = `
        <div class="text-center">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading comments...</span>
            </div>
        </div>
    `;
 
    try {
        const response = await fetch(`${API_BASE}/comments`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Raw API response:', data);
        
        const comments = data.comments || (Array.isArray(data) ? data : []);
        comments.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
        console.log('Processed and sorted comments:', comments);
        displayComments(comments);
    } catch (error) {
        console.error('Error loading comments:', error);
        commentsListElement.innerHTML = `
            <div class="alert alert-warning">
                Comments temporarily unavailable. Please try again later.
            </div>
        `;
    }
 }

function displayComments(comments) {
    console.log('Displaying comments:', comments);
    const commentsListElement = document.getElementById('commentsList');
    if (!commentsListElement) {
        console.warn('Comments list element not found');
        return;
    }
 
    if (comments.length === 0) {
        commentsListElement.innerHTML = '<p class="text-muted">No comments yet. Be the first to comment!</p>';
        return;
    }
 
    commentsListElement.innerHTML = comments.map(comment => {
        const timestamp = new Date(comment.timestamp);
        const timeAgo = getTimeAgo(timestamp);
        
        return `
            <div class="comment mb-3 p-3 border rounded">
                <div class="comment-header d-flex justify-content-between">
                    <div>
                        <strong class="me-2">${comment.author || 'Anonymous'}</strong>
                        <small class="text-muted">• ${timeAgo}</small>
                    </div>
                    ${comment.programName ? `
                        <small class="text-muted">
                            Re: ${comment.programName}
                        </small>
                    ` : ''}
                </div>
                <div class="comment-body mt-2">
                    ${comment.text}
                </div>
            </div>
        `;
    }).join('');
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
 
 async function submitComment() {
    console.log('Comment submission started');
    const textElement = document.getElementById('commentText');
    const text = textElement?.value?.trim();
    
    if (!text) {
        console.log('No comment text provided');
        return;
    }
    
    updateCommentFormState(true);
    
    // Get page identifier
    const pageIdentifier = document.querySelector('h1')?.dataset.pageName || 'unknown-page';
    console.log('Submitting comment for page:', pageIdentifier);
    
    try {
        console.log('Sending comment:', text);
        const response = await fetch(`${API_BASE}/comments`, {
            method: 'POST',
            mode: 'cors',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                text,
                author: 'Anonymous',
                programName: pageIdentifier,
                timestamp: new Date().toISOString()
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        console.log('Submit response:', result);
        
        // More flexible response check
        if (result) {
            console.log('Comment submitted successfully');
            textElement.value = '';
            
            // Show success message
            const successDiv = document.createElement('div');
            successDiv.className = 'alert alert-success mt-2';
            successDiv.textContent = 'Comment posted successfully!';
            textElement.parentNode.insertBefore(successDiv, textElement.nextSibling);
            
            // Remove success message after 3 seconds
            setTimeout(() => {
                successDiv.remove();
            }, 3000);
            
            // Reload comments
            await loadComments();
        } else {
            throw new Error('No response from server');
        }
    } catch (error) {
        console.error('Error submitting comment:', error);
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger mt-2';
        errorDiv.textContent = 'Unable to submit comment. Please try again later.';
        textElement.parentNode.insertBefore(errorDiv, textElement.nextSibling);
        
        setTimeout(() => {
            errorDiv.remove();
        }, 3000);
    } finally {
        updateCommentFormState(false);
    }
 }

// Program Details
function showProgramDetails(teamName) {
    console.log(`Showing details for team: ${teamName}`);
    // Implementation for program details view will go here
}

// Main initialization
document.addEventListener('DOMContentLoaded', async function() {
    try {
        await checkLoginStatus();
        await initializeRankings();
        await loadComments();

        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.addEventListener('input', handleSearch);
        }

        const submitButton = document.getElementById('submitComment');
        if (submitButton) {
            submitButton.addEventListener('click', submitComment);
        }
    } catch (error) {
        console.error('Initialization error:', error);
    }
});
