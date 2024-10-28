// ============= 1. CORE FUNCTIONALITY =============
const ITEMS_PER_PAGE = 100;
let currentPage = 1;
let programsData = [];

// Add this function at the top level
function updateTimestamp() {
    const today = new Date();
    const formattedDate = today.toLocaleDateString('en-US', {
        month: '2-digit',
        day: '2-digit',
        year: 'numeric'
    });
    document.getElementById('lastUpdated').textContent = formattedDate;
}

// Helper function to get image path
function getImagePath(relativePath) {
    if (!relativePath) return 'images/placeholder-image.jpg';
    
    if (currentConfig.useLocalImages) {
        return `${currentConfig.imagesPath}/${relativePath.replace('images/', '')}`;
    } else {
        return `${currentConfig.webv2BasePath}/${relativePath}`;
    }
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

// ============= 2. COMMENTS FUNCTIONALITY =============
async function loadComments() {
    try {
        console.log('Loading comments...');
        const response = await fetch('/api/comments');  // Add leading slash
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const comments = await response.json();
        console.log('Comments loaded:', comments);
        displayComments(comments);
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

// In the submitComment function (around line 178)
async function submitComment() {
    const textElement = document.getElementById('commentText');
    const text = textElement.value.trim();
    
    if (!text) {
        alert('Please enter a comment');
        return;
    }
    
    try {
        console.log('Submitting comment...');
        const response = await fetch('/api/comments', {  // Add leading slash
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                text,
                programName: document.querySelector('.team-name').textContent,
                author: {
                    email: 'anonymous@example.com'
                }
            })
        });
        
        console.log('Response status:', response.status);
        
        if (response.ok) {
            textElement.value = '';
            loadComments();
            console.log('Comment submitted successfully');
        } else {
            const error = await response.json();
            alert(`Error posting comment: ${error.message}`);
        }
    } catch (error) {
        console.error('Error posting comment:', error);
        alert('Error posting comment. Please try again.');
    }
}

// ============= 3. INITIALIZATION =============
// Update the initializeApp function
async function initializeApp() {
    try {
        // Initialize rankings
        updateLoadingState(true);
        const response = await fetch('data/all-time-programs-fifty.json');
        programsData = await response.json();
        
        if (programsData.length > 0) {
            await updateTeamHeader(programsData[0]);
        }
        
        setupPagination();
        displayCurrentPage();
        updateLoadingState(false);
        updateTimestamp();  // Add this line

        // Set up event listeners
        document.getElementById('searchInput').addEventListener('input', handleSearch);
        
        // Initialize comments
        const submitButton = document.getElementById('submitComment');
        if (submitButton) {
            submitButton.addEventListener('click', submitComment);
        }
        loadComments();
    } catch (error) {
        console.error('Error initializing app:', error);
        updateLoadingState(false, error.message);
    }
}

// Start the application
document.addEventListener('DOMContentLoaded', initializeApp);