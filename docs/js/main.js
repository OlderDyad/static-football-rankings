// ============= 1. CORE FUNCTIONALITY ============= 
const ITEMS_PER_PAGE = 100;
let currentPage = 1;
let programsData = [];

// Add this to keep track of failed image loads
const failedImages = new Set();

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

// Update the team header function to use better image handling
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

// ============= 3. INITIALIZATION =============
// Update the initializeApp function
async function initializeApp() {
    try {
        // Initialize rankings
        updateLoadingState(true);
        console.log('Fetching data...');
        const response = await fetch('data/all-time-programs-fifty.json');
        console.log('Response status:', response.status);
        
        programsData = await response.json();
        console.log('Data loaded:', programsData.length, 'programs');
        console.log('First program:', programsData[0]);
        
        if (programsData.length > 0) {
            console.log('Updating header with program:', programsData[0].Team);
            await updateTeamHeader(programsData[0]);
        } else {
            console.error('No programs found in data');
        }
        
        setupPagination();
        displayCurrentPage();
        updateLoadingState(false);
        updateTimestamp();

        // Set up event listeners
        document.getElementById('searchInput').addEventListener('input', handleSearch);
        
        /* Comment out comments functionality for now
        // Initialize comments
        const submitButton = document.getElementById('submitComment');
        if (submitButton) {
            submitButton.addEventListener('click', submitComment);
        }
        loadComments();
        */
    } catch (error) {
        console.error('Error initializing app:', error);
        console.error('Full error details:', {
            message: error.message,
            stack: error.stack
        });
        updateLoadingState(false, error.message);
    }
}

// Start the application
document.addEventListener('DOMContentLoaded', initializeApp);
