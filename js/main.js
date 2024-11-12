// 1. Constants
const REPO_BASE = '/static-football-rankings';
const WEBV2_IMAGE_BASE = `${REPO_BASE}/docs/images`;
const DEFAULT_PLACEHOLDER = `${REPO_BASE}/docs/images/placeholder-image.jpg`;
const ITEMS_PER_PAGE = 100;
const API_BASE = 'https://static-football-rankings.vercel.app/api';

// 2. State management
let currentPage = 1;
let programsData = [];

// 3. Utility Functions
function getImagePath(relativePath, isPlaceholder = false) {
    if (!relativePath || isPlaceholder) {
        console.log('Using placeholder image');
        return DEFAULT_PLACEHOLDER;
    }
    
    // Handle team-specific images from WebV2
    if (relativePath.includes('Teams/')) {
        return `${WEBV2_IMAGE_BASE}/teams/${relativePath.split('Teams/')[1]}`;
    }
    
    // For other images, use the local docs path
    return `${WEBV2_IMAGE_BASE}/${relativePath}`;
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

// 6. Program Details
function showProgramDetails(teamName) {
    console.log(`Showing details for team: ${teamName}`);
    // Implementation for program details view will go here
}

// 7. Comments System
async function loadComments() {
    console.log('Loading comments...');
    try {
        const response = await fetch(`${API_BASE}/comments`, {
            method: 'GET',
            mode: 'cors',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        });
        
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
                    Comments temporarily unavailable. Please try again later.
                </div>
            `;
        }
    }
}

function displayComments(comments) {
    const commentsListElement = document.getElementById('commentsList');
    if (!commentsListElement) {
        console.warn('Comments list element not found');
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
        const response = await fetch(`${API_BASE}/comments`, {
            method: 'POST',
            mode: 'cors',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({
                text,
                author: 'Anonymous',
                programName: document.querySelector('.team-name')?.textContent || 'General'
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        textElement.value = '';
        await loadComments();
        console.log('Comment submitted successfully');
    } catch (error) {
        console.error('Error submitting comment:', error);
        alert('Unable to submit comment. Please try again later.');
    }
}

// 8. Main initialization
document.addEventListener('DOMContentLoaded', async function() {
    console.log('DOM Content Loaded');
    try {
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