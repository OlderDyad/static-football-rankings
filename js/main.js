// Constants
const WEBV2_IMAGE_BASE = '/images';
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
        return `${relativePath}`;
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
    if (!paginationElement) return;
    
    paginationElement.innerHTML = '';
    
    // Add Previous button
    const prevLi = document.createElement('li');
    prevLi.className = `page-item ${currentPage === 1 ? 'disabled' : ''}`;
    prevLi.innerHTML = `
        <button class="page-link" ${currentPage === 1 ? 'disabled' : ''}>
            Previous
        </button>
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
        if (i === 1 || i === totalPages || (i >= currentPage - 2 && i <= currentPage + 2)) {
            const li = document.createElement('li');
            li.className = `page-item ${currentPage === i ? 'active' : ''}`;
            li.innerHTML = `
                <button class="page-link">${i}</button>
            `;
            li.addEventListener('click', () => {
                currentPage = i;
                displayCurrentPage(data);
                setupPagination(data);
            });
            paginationElement.appendChild(li);
        } else if (i === currentPage - 3 || i === currentPage + 3) {
            const li = document.createElement('li');
            li.className = 'page-item disabled';
            li.innerHTML = '<button class="page-link">...</button>';
            paginationElement.appendChild(li);
        }
    }

    // Add Next button
    const nextLi = document.createElement('li');
    nextLi.className = `page-item ${currentPage === totalPages ? 'disabled' : ''}`;
    nextLi.innerHTML = `
        <button class="page-link" ${currentPage === totalPages ? 'disabled' : ''}>
            Next
        </button>
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

// Comments Functions
// Replace the loadComments function
async function loadComments() {
    try {
        console.log('Loading comments...');
        const response = await fetch('https://static-football-rankings.vercel.app/api/comments', {
            method: 'GET',
            mode: 'cors',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const comments = await response.json();
        displayComments(comments);
    } catch (error) {
        console.error('Error loading comments:', error);
        // Display user-friendly error message
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

// Replace the submitComment function
async function submitComment() {
    console.log('Submitting comment...');
    const textElement = document.getElementById('commentText');
    const emailElement = document.getElementById('commentEmail');
    const text = textElement?.value?.trim();
    const email = emailElement?.value?.trim();
    
    if (!text || !email) {
        alert('Please provide both comment and email');
        return;
    }
    
    try {
        // First verify email
        const verifyResponse = await fetch('https://static-football-rankings.vercel.app/api/verify-email', {
            method: 'POST',
            mode: 'cors',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email })
        });

        if (!verifyResponse.ok) {
            throw new Error(`Email verification failed: ${verifyResponse.status}`);
        }

        // Then submit comment
        const response = await fetch('https://static-football-rankings.vercel.app/api/comments', {
            method: 'POST',
            mode: 'cors',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                text,
                email,
                author: email.split('@')[0], // Use part before @ as author name
                programName: document.querySelector('.team-name')?.textContent || 'General'
            })
        });

        if (!response.ok) {
            throw new Error(`Comment submission failed: ${response.status}`);
        }

        // Clear form and reload comments
        textElement.value = '';
        emailElement.value = '';
        await loadComments();
        
    } catch (error) {
        console.error('Error submitting comment:', error);
        alert('Unable to submit comment. Please try again later.');
    }
}

// Add this helper function for API URLs
function getApiUrl(endpoint) {
    const isProd = window.location.hostname === 'olderdyad.github.io';
    const baseUrl = isProd 
        ? 'https://static-football-rankings.vercel.app'
        : 'http://localhost:3000';
    return `${baseUrl}/api/${endpoint}`;
}

// Program Details View
function showProgramDetails(teamName) {
    console.log(`Showing details for team: ${teamName}`);
    // Implement program details view
}