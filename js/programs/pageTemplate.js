//=============================================================================
// SECTION 1: IMPORTS AND CONFIG
//=============================================================================
import { DEBUG_LEVELS, log, checkLoginStatus, loadComments, submitComment } from '../main.js';
import { teamConfig } from '../config/teamConfig.js';

export function initializePage(pageConfig) {
    const ITEMS_PER_PAGE = 100;
    let programsData = [];
    let currentPage = 1;

    //=============================================================================
    // SECTION 2: DATA LOADING AND STATE MANAGEMENT
    //=============================================================================
    async function initializeRankings() {
        log(DEBUG_LEVELS.INFO, `Starting ${pageConfig.pageTitle} initialization`);
        try {
            updateLoadingState(true);
            const response = await fetch(pageConfig.dataFile);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            programsData = data.programs;
            
            if (programsData.length > 0) {
                // Update timestamp from metadata
                const lastUpdated = document.getElementById('lastUpdated');
                if (lastUpdated && data.metadata?.timestamp) {
                    const date = new Date(data.metadata.timestamp);
                    lastUpdated.textContent = date.toLocaleDateString('en-US');
                }

                await updateTeamHeader(data.topProgram);
                setupPagination();
                displayCurrentPage();
                log(DEBUG_LEVELS.INFO, 'Rankings display complete');
            }
            
            updateLoadingState(false);
        } catch (error) {
            log(DEBUG_LEVELS.ERROR, 'Rankings initialization failed', error);
            updateLoadingState(false, error.message);
        }
    }

    function updateLoadingState(isLoading, errorMessage = '') {
        const header = document.querySelector('.team-header');
        if (!header) return;

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

    //=============================================================================
    // SECTION 3: UI UPDATES AND DISPLAY
    //=============================================================================
    function updateTeamHeader(program) {
        log(DEBUG_LEVELS.DEBUG, 'Updating team header', { team: program.team });
        const header = document.querySelector('.team-header');
        if (!header) {
            log(DEBUG_LEVELS.ERROR, 'Team header element not found');
            return;
        }

        const logoUrl = teamConfig.getTeamImagePath(program.LogoURL);
        const schoolLogoUrl = teamConfig.getTeamImagePath(program.School_Logo_URL);

        header.innerHTML = `
            <div class="container">
                <div class="row align-items-center">
                    <div class="col-md-3">
                        <img src="${logoUrl}"
                             alt="${program.team} Logo"
                             class="img-fluid"
                             style="max-height: 100px;"
                             onerror="this.onerror=null; this.src='${teamConfig.defaultLogo}';" />
                    </div>
                    <div class="col-md-6 text-center">
                        <h2>${program.team}</h2>
                        <p>${program.mascot || ''}</p>
                    </div>
                    <div class="col-md-3 text-right">
                        <img src="${schoolLogoUrl}"
                             alt="${program.mascot}"
                             class="img-fluid"
                             style="max-height: 100px;"
                             onerror="this.onerror=null; this.src='${teamConfig.defaultLogo}';" />
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
        currentData.forEach((program, index) => {
            const displayRank = start + index + 1;  // Calculate display rank
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${displayRank}</td>
                <td>${program.team}</td>
                <td>${program.avgCombined}</td>
                <td>${program.avgMargin}</td>
                <td>${program.avgWinLoss}</td>
                <td>${program.avgOffense}</td>
                <td>${program.avgDefense}</td>
                <td>${program.state}</td>
                <td>${program.seasons}</td>
                <td>
                    <button class="btn btn-primary btn-sm" data-team="${program.team}">View Details</button>
                </td>
            `;
            tableBody.appendChild(row);
        });
    }

    //=============================================================================
    // SECTION 4: EVENT HANDLERS
    //=============================================================================
    function handleSearch(event) {
        const searchTerm = event.target.value.toLowerCase();
        log(DEBUG_LEVELS.DEBUG, 'Processing search', { term: searchTerm });

        const filteredPrograms = programsData.filter(program =>
            program.team.toLowerCase().includes(searchTerm) ||
            program.state.toLowerCase().includes(searchTerm)
        );

        currentPage = 1;
        setupPagination(filteredPrograms);
        displayCurrentPage(filteredPrograms);
    }

    function setupPagination(data = programsData) {
        const paginationElement = document.getElementById('pagination');
        if (!paginationElement) return;

        const totalPages = Math.ceil(data.length / ITEMS_PER_PAGE);
        paginationElement.innerHTML = '';

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

    //=============================================================================
    // SECTION 5: INITIALIZATION
    //=============================================================================
    async function initialize() {
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.addEventListener('input', handleSearch);
        }

        // Set up comment submit button listener
        const submitButton = document.getElementById('submitComment');
        if (submitButton) {
            submitButton.addEventListener('click', submitComment);
            log(DEBUG_LEVELS.DEBUG, 'Comment submit button listener added');
        }

        // Auth and Comments after data load
        await checkLoginStatus();
        await initializeRankings();
        await loadComments();

        log(DEBUG_LEVELS.INFO, 'Page initialization complete');
    }

    return {
        initialize,
        handleSearch,
        updateTeamHeader,
        displayCurrentPage
    };
}
