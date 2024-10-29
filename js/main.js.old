// Constants
const WEBV2_IMAGE_BASE = '/McKnightFootballRankings.WebV2/wwwroot/images';
const ITEMS_PER_PAGE = 100;

// State management
let currentPage = 1;
let programsData = [];

// Main initialization
document.addEventListener('DOMContentLoaded', async function() {
    try {
        // Initialize both rankings and comments
        await initializeRankings();
        initializeComments();
    } catch (error) {
        console.error('Initialization error:', error);
    }
});

// Rankings Initialization
async function initializeRankings() {
    try {
        updateLoadingState(true);
        
        const response = await fetch('data/all-time-programs-fifty.json');
        programsData = await response.json();
        
        if (programsData.length > 0) {
            await updateTeamHeader(programsData[0]);
        }
        
        setupPagination();
        displayCurrentPage();
        
        document.getElementById('searchInput').addEventListener('input', handleSearch);
        
        updateLoadingState(false);
    } catch (error) {
        console.error('Error initializing rankings:', error);
        updateLoadingState(false, error.message);
    }
}

// Comments Initialization
function initializeComments() {
    const submitButton = document.getElementById('submitComment');
    if (submitButton) {
        submitButton.addEventListener('click', submitComment);
    }
    loadComments();
}

// Rankings Functions
function updateLoadingState(isLoading, errorMessage = '') {
    const header = document.querySelector('.team-header');
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

async function updateTeamHeader(program) {
    const header = document.querySelector('.team-header');
    
    const getImagePath = (relativePath) => {
        if (!relativePath) return 'images/placeholder-image.jpg';
        return `${WEBV2_IMAGE_BASE}/${relativePath.replace('images/', '')}`;
    };

    header.innerHTML = `
        <div class="container">
            <div class="row align-items-center">
                <div class="col-md-3">
                    <img src="${getImagePath(program.LogoURL)}" 
                         alt="${program.Team} Logo" 
                         class="img-fluid team-logo" 
                         style="max-height: 100px;" 
                         onerror="this.src='images/placeholder-image.jpg'" />
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
                         onerror="this.src='images/placeholder-image.jpg'" />
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

// Comments Functions
async function loadComments() {
    try {
        const response = await fetch('/api/comments');
        const comments = await response.json();
        displayComments(comments);
    } catch (error) {
        console.error('Error loading comments:', error);
    }
}

function displayComments(comments) {
    const commentsListElement = document.getElementById('commentsList');
    commentsListElement.innerHTML = comments.map(comment => `
        <div class="comment mb-3 p-3 border rounded">
            <div class="comment-header d-flex justify-content-between">
                <strong>${comment.author}</strong>
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
    const text = textElement.value.trim();
    
    if (!text) return;
    
    try {
        const response = await fetch('/api/comments', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                text,
                author: 'Anonymous', // We'll add authentication later
                programName: document.querySelector('.team-name').textContent
            })
        });
        
        if (response.ok) {
            textElement.value = '';
            loadComments();
        }
    } catch (error) {
        console.error('Error posting comment:', error);
    }
}