// Constants
const WEBV2_IMAGE_BASE = '/McKnightFootballRankings.WebV2/wwwroot/images';
const ITEMS_PER_PAGE = 100;

// State management
let currentPage = 1;
let programsData = [];

// Core Functions
function updateLoadingState(isLoading, errorMessage = '') {
    const header = document.querySelector('.team-header');
    if (!header) {
        console.error('Team header element not found');
        return;
    }

    if (isLoading) {
        header.classList.add('loading');
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

function getImagePath(relativePath) {
    if (!relativePath) {
        console.log('No image path provided, using placeholder');
        return 'images/placeholder-image.jpg';
    }
    const fullPath = `${WEBV2_IMAGE_BASE}/${relativePath.replace('images/', '')}`;
    console.log('Constructed image path:', fullPath);
    return fullPath;
}

// Main initialization
document.addEventListener('DOMContentLoaded', async function() {
    console.log('DOM Content Loaded');
    try {
        console.log('Starting initialization...');
        await initializeRankings();
        console.log('Rankings initialized');
        initializeComments();
        console.log('Comments initialized');
    } catch (error) {
        console.error('Initialization error:', error);
    }
});

// Rankings Initialization
async function initializeRankings() {
    try {
        console.log('Initializing rankings...');
        updateLoadingState(true);
        
        const response = await fetch('data/all-time-programs-fifty.json');
        if (!response.ok) {
            throw new Error(`Failed to fetch data: ${response.status}`);
        }
        
        programsData = await response.json();
        console.log('Data loaded, first program:', programsData[0]);
        
        if (programsData.length > 0) {
            await updateTeamHeader(programsData[0]);
            console.log('Team header updated');
        }
        
        setupPagination();
        displayCurrentPage();
        
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.addEventListener('input', handleSearch);
        }
        
        updateLoadingState(false);
        console.log('Rankings initialization complete');
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
                         onerror="console.error('Logo load failed:', this.src); this.src='images/placeholder-image.jpg'" />
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
                         onerror="console.error('School logo load failed:', this.src); this.src='images/placeholder-image.jpg'" />
                </div>
            </div>
        </div>
    `;
    
    header.style.backgroundColor = program.PrimaryColor || '#000000';
    header.style.color = program.SecondaryColor || '#FFFFFF';
}

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
    const paginationElement = document.getElementById('pagination');
    if (!paginationElement) {
        console.error('Pagination element not found');
        return;
    }

    const totalPages = Math.ceil(data.length / ITEMS_PER_PAGE);
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
                <a href="/program/${encodeURIComponent(program.Team)}" 
                   class="btn btn-primary btn-sm">View Details</a>
            </td>
        `;
        tableBody.appendChild(row);
    });
}

// Comments Initialization and Functions
function initializeComments() {
    console.log('Initializing comments...');
    const submitButton = document.getElementById('submitComment');
    if (submitButton) {
        submitButton.addEventListener('click', submitComment);
        console.log('Comment submit button initialized');
    } else {
        console.warn('Comment submit button not found');
    }
    loadComments();
}

async function loadComments() {
    try {
        console.log('Loading comments...');
        const response = await fetch('/api/comments');
        if (!response.ok) {
            throw new Error(`Failed to load comments: ${response.status}`);
        }
        const comments = await response.json();
        displayComments(comments);
        console.log('Comments loaded successfully');
    } catch (error) {
        console.error('Error loading comments:', error);
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

async function submitComment() {
    const textElement = document.getElementById('commentText');
    const text = textElement?.value?.trim();
    
    if (!text) {
        console.warn('No comment text provided');
        return;
    }
    
    try {
        const response = await fetch('/api/comments', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                text,
                author: 'Anonymous',
                programName: document.querySelector('.team-name')?.textContent || 'General'
            })
        });
        
        if (response.ok) {
            textElement.value = '';
            await loadComments();
            console.log('Comment submitted successfully');
        } else {
            throw new Error(`Failed to submit comment: ${response.status}`);
        }
    } catch (error) {
        console.error('Error posting comment:', error);
    }
}