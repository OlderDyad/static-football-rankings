# generate_site.ps1
$ScriptPath = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings"
$OutputDir = $ScriptPath

# Create necessary directories
$directories = @(
    "css",
    "js",
    "images"
)

foreach ($dir in $directories) {
    $path = Join-Path $OutputDir $dir
    if (-not (Test-Path $path)) {
        New-Item -Path $path -ItemType Directory -Force
    }
}

# Create CSS file
$cssContent = @'
/* Custom Styles */
.team-header {
    padding: 20px 0;
    margin-bottom: 20px;
}

.table th, .table td {
    padding: 0.5rem;
}

.table-responsive {
    overflow-x: auto;
}

.pagination {
    display: flex;
    justify-content: center;
    list-style: none;
    padding: 0;
    margin: 20px 0;
}

.page-item {
    margin: 0 2px;
}

.page-link {
    padding: 8px 12px;
    border: 1px solid #dee2e6;
    background-color: #fff;
    color: #007bff;
    cursor: pointer;
}

.page-item.active .page-link {
    background-color: #007bff;
    border-color: #007bff;
    color: #fff;
}

.form-group {
    margin-bottom: 1rem;
}

.form-control {
    display: block;
    width: 100%;
    padding: 0.375rem 0.75rem;
    font-size: 1rem;
    line-height: 1.5;
    border: 1px solid #ced4da;
    border-radius: 0.25rem;
}
'@ | Set-Content -Path (Join-Path $OutputDir "css\styles.css") -Encoding UTF8

# Create JavaScript file
$jsContent = @'
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
'@ | Set-Content -Path (Join-Path $OutputDir "js\main.js") -Encoding UTF8

# Create HTML file
$htmlContent = @'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Top High School Football Programs of All-Time (50+ seasons)</title>
    
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    
    <!-- Custom CSS -->
    <link href="css/styles.css" rel="stylesheet">
</head>
<body>
    <!-- Team Header -->
    <div class="team-header" id="teamHeader">
        <div class="container">
            <div class="row align-items-center">
                <div class="col-md-3">
                    <img src="" alt="Team Logo" class="img-fluid team-logo" style="max-height: 100px;" />
                </div>
                <div class="col-md-6 text-center">
                    <h2 class="team-name">Team Name</h2>
                    <p class="team-mascot">Team Mascot</p>
                </div>
                <div class="col-md-3 text-right">
                    <img src="" alt="School Logo" class="img-fluid school-logo" style="max-height: 100px;" />
                </div>
            </div>
        </div>
    </div>

    <!-- Main Content -->
    <div class="container mt-4">
        <h1>Top High School Football Programs of All-Time (50+ seasons)</h1>
        
        <div class="form-group mb-4">
            <input type="text" class="form-control" id="searchInput" placeholder="Search programs..." />
        </div>

        <!-- Table Content -->
        <div class="table-responsive">
            <table class="table table-striped table-hover">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Program</th>
                        <th>Combined</th>
                        <th>Margin</th>
                        <th>Win-Loss</th>
                        <th>Offense</th>
                        <th>Defense</th>
                        <th>State</th>
                        <th>Seasons</th>
                        <th>Details</th>
                    </tr>
                </thead>
                <tbody id="programsTableBody">
                    <!-- Data will be populated by JavaScript -->
                </tbody>
            </table>
        </div>

        <!-- Pagination -->
        <nav>
            <ul class="pagination justify-content-center" id="pagination">
                <!-- Will be populated by JavaScript -->
            </ul>
        </nav>
    </div>

    <!-- Bootstrap Bundle with Popper -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    
    <!-- Custom JavaScript -->
    <script src="js/main.js"></script>
</body>
</html>
'@ | Set-Content -Path (Join-Path $OutputDir "index.html") -Encoding UTF8

Write-Host "Static site files generated successfully!"
Write-Host "You can now open index.html in a web browser to view the site."