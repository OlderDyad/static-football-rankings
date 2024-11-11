// Constants
const WEBV2_IMAGE_BASE = '/McKnightFootballRankings.WebV2/wwwroot';
const ITEMS_PER_PAGE = 100;

// State management
let currentPage = 1;
let programsData = [];

// Main initialization
document.addEventListener('DOMContentLoaded', async function() {
    console.log('Initializing app...');
    try {
        // Initialize both rankings and comments
        await initializeRankings();
        initializeComments();
    } catch (error) {
        console.error('Error initializing app:', error);
    }
});

// Rankings Initialization
async function initializeRankings() {
    try {
        updateLoadingState(true);
        
        const response = await fetch('data/all-time-programs-fifty.json');
        programsData = await response.json();
        
        // Log first program data to verify structure
        if (programsData.length > 0) {
            console.log('First program data:', programsData[0]);
            console.log('Constructed image paths:', {
                logo: getImagePath(programsData[0].LogoURL),
                schoolLogo: getImagePath(programsData[0].School_Logo_URL)
            });
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

// Image Path Handling
function getImagePath(relativePath) {
    if (!relativePath) {
        console.log('No image path provided, using placeholder');
        return `${WEBV2_IMAGE_BASE}/images/placeholder-image.jpg`;
    }
    
    // Remove leading 'images/' if present as it's included in WEBV2_IMAGE_BASE
    const cleanPath = relativePath.startsWith('images/') 
        ? relativePath.substring(7) 
        : relativePath;
        
    const fullPath = `${WEBV2_IMAGE_BASE}/images/${cleanPath}`;
    console.log(`Constructed image path: ${fullPath} from relative path: ${relativePath}`);
    return fullPath;
}

// Team Header Update
async function updateTeamHeader(program) {
    const header = document.querySelector('.team-header');
    
    console.log('Updating team header for:', program.Team);
    console.log('Using image paths:', {
        logo: getImagePath(program.LogoURL),
        schoolLogo: getImagePath(program.School_Logo_URL)
    });

    header.innerHTML = `
        <div class="container">
            <div class="row align-items-center">
                <div class="col-md-3">
                    <img src="${getImagePath(program.LogoURL)}" 
                         alt="${program.Team} Logo" 
                         class="img-fluid team-logo" 
                         style="max-height: 100px;" 
                         onerror="console.error('Failed to load logo:', this.src); this.src='${WEBV2_IMAGE_BASE}/images/placeholder-image.jpg';" />
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
                         onerror="console.error('Failed to load school logo:', this.src); this.src='${WEBV2_IMAGE_BASE}/images/placeholder-image.jpg';" />
                </div>
            </div>
        </div>
    `;
    
    header.style.backgroundColor = program.PrimaryColor || '#000000';
    header.style.color = program.SecondaryColor || '#FFFFFF';
}

// Search and Pagination
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
    if (!paginationElement) {
        console.warn('Pagination element not found');
        return;
    }
    
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
function initializeComments() {
    const submitButton = document.getElementById('submitComment');
    if (submitButton) {
        submitButton.addEventListener('click', submitComment);
    }
    loadComments();
}

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
                author: 'Anonymous',
                programName: document.querySelector('.team-name')?.textContent || 'General'
            })
        });
        
        if (response.ok) {
            textElement.value = '';
            await loadComments();
        }
    } catch (error) {
        console.error('Error posting comment:', error);
    }
}

// Program Details View
function showProgramDetails(teamName) {
    console.log(`Showing details for team: ${teamName}`);
    // Implement program details view
}