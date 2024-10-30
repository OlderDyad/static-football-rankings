// ============= 1. CORE FUNCTIONALITY =============
const ITEMS_PER_PAGE = 100;
let currentPage = 1;
let programsData = [];
const API_BASE_URL = 'https://static-football-rankings.vercel.app';

// Add this to keep track of failed image loads
const failedImages = new Set();

// Debug messages
const DEBUG = true;

function debugLog(...args) {
    if (DEBUG) {
        console.log(...args);
    }
}

// Add this function at the top level to update the timestamp
function updateTimestamp() {
    const today = new Date();
    const formattedDate = today.toLocaleDateString('en-US', {
        month: '2-digit',
        day: '2-digit',
        year: 'numeric'
    });
    document.getElementById('lastUpdated').textContent = formattedDate;
}

function cleanPath(path) {
    if (!path) return '';
    // Remove escaped forward slashes and any double slashes
    return path.replace(/\\\//g, '/')
              .replace(/\/\//g, '/');
}

function getImagePath(relativePath) {
    if (!relativePath || failedImages.has(relativePath)) {
        return 'images/placeholder-image.jpg';
    }
    
    try {
        let imagePath;
        const cleanedPath = cleanPath(relativePath);
        
        // Always prefix with webv2 for consistent path structure
        imagePath = `webv2/${cleanedPath}`;
        
        return imagePath;
    } catch (error) {
        console.warn(`Error processing image path: ${relativePath}`, error);
        return 'images/placeholder-image.jpg';
    }
}

// Function to handle image errors
function handleImageError(imgElement, originalSrc) {
    // Add to failed images set
    failedImages.add(originalSrc);

    // Set placeholder and prevent further error callbacks
    imgElement.src = 'images/placeholder-image.jpg';
    imgElement.onerror = null;

    // Optional: Log failed image loads during development
    console.debug(`Image failed to load: ${originalSrc}`);
}

function updateLoadingState(isLoading, errorMessage = '') {
    const header = document.querySelector('.team-header');
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

function updateTeamHeader(program) {
    const header = document.querySelector('.team-header');
    const headerContent = `
        <div class="container">
            <div class="row align-items-center">
                <div class="col-md-3">
                    <img src="${getImagePath(program.LogoURL)}" 
                         alt="${program.Team} Logo" 
                         class="img-fluid team-logo" 
                         style="max-height: 100px;" 
                         onerror="handleImageError(this, '${program.LogoURL}')" />
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
                         onerror="handleImageError(this, '${program.School_Logo_URL}')" />
                </div>
            </div>
        </div>
    `;
    
    header.innerHTML = headerContent;
    header.style.backgroundColor = program.PrimaryColor || '#000000';
    header.style.color = program.SecondaryColor || '#FFFFFF';
}

function handleSearch(event) {
    const searchTerm = event.target.value.toLowerCase();
    const filteredPrograms = programsData.filter(program => 
        program.Team.toLowerCase().includes(searchTerm) ||
        program.State.toLowerCase().includes(searchTerm)
    );
    
    currentPage = 1;
    setupPagination(filteredPrograms);
    displayCurrentPage(filteredPrograms);
}

function setupPagination(data = programsData) {
    const totalPages = Math.ceil(data.length / ITEMS_PER_PAGE);
    const paginationElement = document.getElementById('pagination');
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

function displayCurrentPage(data = programsData) {
    const tableBody = document.getElementById('programsTableBody');
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
                <a href="/program/${encodeURIComponent(program.Team)}" 
                   class="btn btn-primary btn-sm">View Details</a>
            </td>
        `;
        tableBody.appendChild(row);
    });
}

// Comments Handling Functions
async function loadComments() {
    try {
        console.log('Loading comments...');
        const programName = document.querySelector('.team-name').textContent;
        const response = await fetch(`${API_BASE_URL}/api/comments?programName=${encodeURIComponent(programName)}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const comments = await response.json();
        displayComments(comments);
    } catch (error) {
        console.error('Error loading comments:', error);
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
        const verifyResponse = await fetch(`${API_BASE_URL}/api/verify-email`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email,
                pendingCommentData: {
                    text,
                    programName: document.querySelector('.team-name').textContent,
                    parentId: null
                }
            })
        });
        
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

// ============= 3. INITIALIZATION =============
async function initializeApp() {
    try {
        debugLog('Initializing app...');
        updateLoadingState(true);
        const response = await fetch('data/all-time-programs-fifty.json');
        programsData = await response.json();
        
        if (programsData.length > 0) {
            await updateTeamHeader(programsData[0]);
        }
        
        setupPagination();
        displayCurrentPage();
        updateLoadingState(false);
        updateTimestamp();

        // Set up event listeners
        document.getElementById('searchInput').addEventListener('input', handleSearch);
        
        // Add more detailed logging for comments
        debugLog('Setting up comment functionality...');
        const submitButton = document.getElementById('submitComment');
        debugLog('Submit button found:', !!submitButton);
        const commentText = document.getElementById('commentText');
        debugLog('Comment text area found:', !!commentText);
        const commentEmail = document.getElementById('commentEmail');
        debugLog('Comment email input found:', !!commentEmail);

        if (submitButton) {
            submitButton.addEventListener('click', submitComment);
            debugLog('Comment submit listener added');
        }
        loadComments();
    } catch (error) {
        console.error('Error initializing app:', error);
        updateLoadingState(false, error.message);
    }
}

// Start the application
document.addEventListener('DOMContentLoaded', initializeApp);