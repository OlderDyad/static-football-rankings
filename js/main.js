// Add this at the top of main.js
const WEBV2_IMAGE_BASE = '/McKnightFootballRankings.WebV2/wwwroot/images';

// Configuration
const ITEMS_PER_PAGE = 100;
let currentPage = 1;
let programsData = [];

// Initialize the page
document.addEventListener('DOMContentLoaded', async function() {
    try {
        // Show loading state in header
        updateLoadingState(true);
        
        // Fetch the programs data
        const response = await fetch('data/all-time-programs-fifty.json');
        programsData = await response.json();
        
        // Initialize the page with the first program's header
        if (programsData.length > 0) {
            const topProgram = programsData[0];
            await updateTeamHeader(topProgram);
        }
        
        // Set up the initial view
        setupPagination();
        displayCurrentPage();
        
        // Set up search functionality
        document.getElementById('searchInput').addEventListener('input', handleSearch);
        
        // Remove loading state
        updateLoadingState(false);
    } catch (error) {
        console.error('Error initializing page:', error);
        updateLoadingState(false, error.message);
    }
});

// Update loading state
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

// Update the image URL handling in updateTeamHeader function
async function updateTeamHeader(program) {
    const header = document.querySelector('.team-header');
    
    // Function to get full image path
    const getImagePath = (relativePath) => {
        if (!relativePath) return 'images/placeholder-image.jpg';
        // Convert relative path to WebV2 path
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
    
    // Set header colors
    header.style.backgroundColor = program.PrimaryColor || '#000000';
    header.style.color = program.SecondaryColor || '#FFFFFF';
}



// Handle search functionality
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

// Set up pagination
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

// Display current page of data
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
                <a href="/program/${encodeURIComponent(program.Team)}" class="btn btn-primary btn-sm">View Details</a>
            </td>
        `;
        
        tableBody.appendChild(row);
    });
}
