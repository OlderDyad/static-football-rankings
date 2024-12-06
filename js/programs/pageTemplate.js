// js/programs/pageTemplate.js
import { DEBUG_LEVELS, log, REPO_BASE } from '../main.js';

export function initializePage(pageConfig) {
    // Program specific constants
    const ITEMS_PER_PAGE = 100;
    let programsData = [];
    let currentPage = 1;

    // Validate required config
    if (!pageConfig.dataFile || !pageConfig.pageId) {
        log(DEBUG_LEVELS.ERROR, 'Invalid page configuration', pageConfig);
        throw new Error('Missing required page configuration');
    }

    async function initializeRankings() {
        log(DEBUG_LEVELS.INFO, `Starting ${pageConfig.pageTitle} initialization`);
        try {
            updateLoadingState(true);
            const response = await fetch(`${REPO_BASE}${pageConfig.dataFile}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            programsData = await response.json();
            
            if (programsData.length > 0) {
                await updateTeamHeader(programsData[0]);
                setupPagination(programsData);
                displayCurrentPage(programsData);
                log(DEBUG_LEVELS.INFO, 'Rankings display complete');
            } else {
                // Handle no data scenario
                updateLoadingState(false, 'No data available for this page.');
            }
            
            updateLoadingState(false);
        } catch (error) {
            log(DEBUG_LEVELS.ERROR, 'Rankings initialization failed', error);
            updateLoadingState(false, error.message);
        }
    }

    function updateTeamHeader(program) {
        log(DEBUG_LEVELS.DEBUG, 'Updating team header', { team: program.Team });
        const header = document.querySelector('.team-header');
        if (!header) {
            log(DEBUG_LEVELS.ERROR, 'Team header element not found');
            return;
        }

        header.innerHTML = `
            <div class="container">
                <div class="row align-items-center">
                    <div class="col-md-3">
                        <img src="${getImagePath(program.State, program.Team, program.LogoURL)}"
                             alt="${program.Team} Logo"
                             class="img-fluid"
                             style="max-height: 100px;"
                             onerror="this.src='${pageConfig.defaultLogo}'" />
                    </div>
                    <div class="col-md-6 text-center">
                        <h2>${program.Team}</h2>
                        <p>${program.Mascot || ''}</p>
                    </div>
                    <div class="col-md-3 text-right">
                        <img src="${getImagePath(program.State, program.Team, program.School_Logo_URL)}"
                             alt="${program.Mascot}"
                             class="img-fluid"
                             style="max-height: 100px;"
                             onerror="this.src='${pageConfig.defaultLogo}'" />
                    </div>
                </div>
            </div>
        `;

        header.style.backgroundColor = program.PrimaryColor || '#000000';
        header.style.color = program.SecondaryColor || '#FFFFFF';
    }

    function displayCurrentPage(data = programsData) {
        log(DEBUG_LEVELS.DEBUG, 'Displaying page', { 
            page: currentPage,
            totalItems: data?.length 
        });

        const tableBody = document.getElementById('programsTableBody');
        if (!tableBody) {
            log(DEBUG_LEVELS.ERROR, 'Table body element not found');
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
                    <button class="btn btn-primary btn-sm" 
                            data-team="${program.Team}">View Details</button>
                </td>
            `;
            tableBody.appendChild(row);
        });

        // Add event listeners for detail buttons
        tableBody.querySelectorAll('button[data-team]').forEach(btn => {
            btn.addEventListener('click', () => showProgramDetails(btn.dataset.team));
        });
    }

    // Search functionality
    function handleSearch(event) {
        const searchTerm = event.target.value.toLowerCase();
        log(DEBUG_LEVELS.DEBUG, 'Processing search', { term: searchTerm });

        const filteredPrograms = programsData.filter(program =>
            program.Team.toLowerCase().includes(searchTerm) ||
            program.State.toLowerCase().includes(searchTerm)
        );

        log(DEBUG_LEVELS.DEBUG, 'Search results', { 
            total: programsData.length,
            filtered: filteredPrograms.length 
        });

        currentPage = 1;
        setupPagination(filteredPrograms);
        displayCurrentPage(filteredPrograms);
    }

    function setupPagination(data = programsData) {
        log(DEBUG_LEVELS.DEBUG, 'Setting up pagination', { totalItems: data.length });
        const paginationElement = document.getElementById('pagination');
        if (!paginationElement) {
            log(DEBUG_LEVELS.DEBUG, 'Creating pagination element');
            const nav = document.createElement('nav');
            nav.innerHTML = '<ul class="pagination" id="pagination"></ul>';
            const tableContainer = document.querySelector('.table-responsive');
            if (tableContainer) {
                tableContainer.after(nav);
                return setupPagination(data);
            }
        }

        paginationElement.innerHTML = '';
        const totalPages = Math.ceil(data.length / ITEMS_PER_PAGE);

        // Previous button
        const prevLi = document.createElement('li');
        prevLi.className = `page-item ${currentPage === 1 ? 'disabled' : ''}`;
        prevLi.innerHTML = `<button class="page-link" ${currentPage === 1 ? 'disabled' : ''}>Previous</button>`;
        prevLi.addEventListener('click', () => {
            if (currentPage > 1) {
                currentPage--;
                displayCurrentPage(data);
                setupPagination(data);
            }
        });
        paginationElement.appendChild(prevLi);

        // Page numbers
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

        // Next button
        const nextLi = document.createElement('li');
        nextLi.className = `page-item ${currentPage === totalPages ? 'disabled' : ''}`;
        nextLi.innerHTML = `<button class="page-link" ${currentPage === totalPages ? 'disabled' : ''}>Next</button>`;
        nextLi.addEventListener('click', () => {
            if (currentPage < totalPages) {
                currentPage++;
                displayCurrentPage(data);
                setupPagination(data);
            }
        });
        paginationElement.appendChild(nextLi);
    }

    function showProgramDetails(teamName) {
        log(DEBUG_LEVELS.DEBUG, 'Showing details for team', { teamName });
        // Implement the logic to display program details.
        // This might open a modal or navigate to another page.
    }

    function updateLoadingState(isLoading, errorMessage = '') {
        const header = document.querySelector('.team-header');
        if (!header) {
            log(DEBUG_LEVELS.ERROR, 'Team header element not found while updating loading state');
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

    function getImagePath(state, teamName, imageFile) {
        if (!imageFile) {
            return pageConfig.defaultLogo;
        }
        // Adjust as needed to match your directory structure.
        return `${REPO_BASE}/docs/images/teams/${state}/${encodeURIComponent(teamName)}/${encodeURIComponent(imageFile)}`;
    }

    function initialize() {
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.addEventListener('input', handleSearch);
        }

        return initializeRankings();
    }

    return {
        initialize,
        handleSearch,
        updateTeamHeader,
        displayCurrentPage
    };
}
