// Constants
const WEBV2_IMAGE_BASE = '/images';
const ITEMS_PER_PAGE = 100;
const DEFAULT_PLACEHOLDER_IMAGE = '/images/placeholder-image.jpg';
const API_BASE_URL = 'https://static-football-rankings.vercel.app';

// State management
let currentPage = 1;
let programsData = [];

// Main initialization
document.addEventListener('DOMContentLoaded', async function() {
    console.log('Initializing app...');
    try {
        // Load programs data first
        await initializeRankings();
        
        // Then set up comments if needed
        if (document.getElementById('commentsList')) {
            await initializeComments();
        }
    } catch (error) {
        console.error('Error initializing app:', error);
    }
});

// Rankings Initialization
async function initializeRankings() {
    try {
        updateLoadingState(true);
        
        const response = await fetch('data/all-time-programs-fifty.json');
        if (!response.ok) {
            throw new Error(`Failed to load rankings: ${response.status}`);
        }
        
        programsData = await response.json();
        
        if (programsData && programsData.length > 0) {
            await updateTeamHeader(programsData[0]);
            setupPagination();
            displayCurrentPage();
            
            const searchInput = document.getElementById('searchInput');
            if (searchInput) {
                searchInput.addEventListener('input', handleSearch);
            }
        } else {
            throw new Error('No program data available');
        }
        
        updateLoadingState(false);
    } catch (error) {
        console.error('Error initializing rankings:', error);
        updateLoadingState(false, error.message);
    }
}

// Comments Initialization
async function initializeComments() {
    console.log('Setting up comments functionality...');
    const submitButton = document.getElementById('submitComment');
    if (submitButton) {
        submitButton.addEventListener('click', handleCommentSubmit);
    }
    await loadComments();
}

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
            </div>
        `;
    } else if (errorMessage) {
        header.innerHTML = `
            <div class="container">
                <div class="alert alert-danger">
                    <p>${errorMessage}</p>
                </div>
            </div>
        `;
    }
}

async function updateTeamHeader(program) {
    const header = document.querySelector('.team-header');
    if (!header) return;
    
    const getImagePath = (relativePath) => {
        if (!relativePath) return DEFAULT_PLACEHOLDER_IMAGE;
        return relativePath;
    };

    header.innerHTML = `
        <div class="container">
            <div class="row align-items-center">
                <div class="col-md-3">
                    <img src="${getImagePath(program.LogoURL)}" 
                         alt="${program.Team} Logo" 
                         class="img-fluid team-logo" 
                         style="max-height: 100px;" 
                         onerror="this.onerror=null; this.src='${DEFAULT_PLACEHOLDER_IMAGE}';" />
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
                         onerror="this.onerror=null; this.src='${DEFAULT_PLACEHOLDER_IMAGE}';" />
                </div>
            </div>
        </div>
    `;
    
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
    const paginationElement = document.getElementById('pagination');
    if (!paginationElement) return;

    const totalPages = Math.ceil(data.length / ITEMS_PER_PAGE);
    paginationElement.innerHTML = '';
    
    if (totalPages <= 1) return;

    // Previous button
    paginationElement.appendChild(createPaginationItem('Previous', () => {
        if (currentPage > 1) {
            currentPage--;
            displayCurrentPage(data);
            setupPagination(data);
        }
    }, currentPage === 1));

    // Page numbers
    for (let i = 1; i <= totalPages; i++) {
        if (shouldShowPageNumber(i, currentPage, totalPages)) {
            paginationElement.appendChild(createPaginationItem(i, () => {
                currentPage = i;
                displayCurrentPage(data);
                setupPagination(data);
            }, false, currentPage === i));
        } else if (shouldShowEllipsis(i, currentPage, totalPages)) {
            paginationElement.appendChild(createEllipsisItem());
        }
    }

    // Next button
    paginationElement.appendChild(createPaginationItem('Next', () => {
        if (currentPage < totalPages) {
            currentPage++;
            displayCurrentPage(data);
            setupPagination(data);
        }
    }, currentPage === totalPages));
}

function shouldShowPageNumber(pageNum, currentPage, totalPages) {
    return pageNum === 1 || 
           pageNum === totalPages || 
           (pageNum >= currentPage - 1 && pageNum <= currentPage + 1);
}

function shouldShowEllipsis(pageNum, currentPage, totalPages) {
    return (pageNum === currentPage - 2 && pageNum > 2) ||
           (pageNum === currentPage + 2 && pageNum < totalPages - 1);
}

function createPaginationItem(text, onClick, disabled = false, active = false) {
    const li = document.createElement('li');
    li.className = `page-item ${disabled ? 'disabled' : ''} ${active ? 'active' : ''}`;
    const button = document.createElement('button');
    button.className = 'page-link';
    button.textContent = text;
    if (!disabled) button.addEventListener('click', onClick);
    li.appendChild(button);
    return li;
}

function createEllipsisItem() {
    const li = document.createElement('li');
    li.className = 'page-item disabled';
    li.innerHTML = '<span class="page-link">...</span>';
    return li;
}

function displayCurrentPage(data = programsData) {
    const tableBody = document.getElementById('programsTableBody');
    if (!tableBody) return;

    const start = (currentPage - 1) * ITEMS_PER_PAGE;
    const end = start + ITEMS_PER_PAGE;
    const currentData = data.slice(start, end);
    
    tableBody.innerHTML = currentData.map(program => `
        <tr>
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
        </tr>
    `).join('');
}

// Comments Functions
async function loadComments() {
    console.log('Loading comments...');
    try {
        const response = await fetch(`${API_BASE_URL}/api/comments`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const comments = await response.json();
        displayComments(comments);
    } catch (error) {
        console.error('Error loading comments:', error);
        const commentsListElement = document.getElementById('commentsList');
        if (commentsListElement) {
            commentsListElement.innerHTML = `
                <div class="alert alert-warning">
                    Unable to load comments at this time.
                </div>
            `;
        }
    }
}

function displayComments(comments) {
    const commentsListElement = document.getElementById('commentsList');
    if (!commentsListElement) return;

    if (!Array.isArray(comments) || comments.length === 0) {
        commentsListElement.innerHTML = '<p>No comments yet. Be the first to comment!</p>';
        return;
    }

    commentsListElement.innerHTML = comments.map(comment => `
        <div class="comment mb-3 p-3 border rounded">
            <div class="comment-header d-flex justify-content-between">
                <strong>${comment.author || 'Anonymous'}</strong>
                <small class="text-muted">
                    ${new Date(comment.timestamp).toLocaleDateString()}
                </small>
            </div>
            <div class="comment-body mt-2">
                ${comment.text}
            </div>
        </div>
    `).join('');
}

async function handleCommentSubmit() {
    const textElement = document.getElementById('commentText');
    const emailElement = document.getElementById('commentEmail');
    
    if (!textElement || !emailElement) {
        console.error('Comment form elements not found');
        return;
    }

    const text = textElement.value.trim();
    const email = emailElement.value.trim();
    
    if (!text || !email) {
        alert('Please provide both a comment and email address.');
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/api/comments`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                text,
                email,
                author: email.split('@')[0],
                programName: document.querySelector('.team-name')?.textContent || 'General'
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        textElement.value = '';
        emailElement.value = '';
        await loadComments();
    } catch (error) {
        console.error('Error submitting comment:', error);
        alert('Unable to submit comment. Please try again later.');
    }
}

function showProgramDetails(teamName) {
    console.log(`Showing details for team: ${teamName}`);
    // Implement program details view
}