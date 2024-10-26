// Configuration
const ITEMS_PER_PAGE = 100;
let currentPage = 1;
let programsData = [];

// Initialize the page
document.addEventListener('DOMContentLoaded', async function() {
    try {
        // Fetch the programs data
        const response = await fetch('data/all-time-programs-fifty.json');
        programsData = await response.json();
        
        // Initialize the page with the first program's header
        if (programsData.length > 0) {
            updateTeamHeader(programsData[0]);
        }
        
        // Set up the initial view
        setupPagination();
        displayCurrentPage();
        
        // Set up search functionality
        document.getElementById('searchInput').addEventListener('input', handleSearch);
    } catch (error) {
        console.error('Error initializing page:', error);
    }
});

// Update team header with program data
function updateTeamHeader(program) {
    const header = document.querySelector('.team-header');
    const teamName = document.querySelector('.team-name');
    const teamMascot = document.querySelector('.team-mascot');
    const teamLogo = document.querySelector('.team-logo');
    const schoolLogo = document.querySelector('.school-logo');
    
    teamName.textContent = program.Team;
    teamMascot.textContent = program.Mascot || '';
    teamLogo.src = program.LogoURL || 'images/placeholder-image.jpg';
    schoolLogo.src = program.School_Logo_URL || 'images/placeholder-image.jpg';
    
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
