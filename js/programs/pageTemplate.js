// js/programs/pageTemplate.js
import { DEBUG_LEVELS, log, checkLoginStatus, loadComments, submitComment } from '../main.js';
import { teamConfig } from '../config/teamConfig.js';

export function initializePage(pageConfig) {
    const ITEMS_PER_PAGE = 100;
    let programsData = [];
    let currentPage = 1;

    function getImagePath(imageFile) {
        if (!imageFile) return teamConfig.defaultLogo;
        const program = programsData[0];
        return teamConfig.getTeamImagePath(program.State, program.Team, imageFile);
    }

    async function initializeRankings() {
        log(DEBUG_LEVELS.INFO, `Starting ${pageConfig.pageTitle} initialization`);
        try {
            updateLoadingState(true);
            const response = await fetch(pageConfig.dataFile);
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
                updateLoadingState(false, 'No data available');
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

        const logoUrl = getImagePath(program.LogoURL);
        const sealUrl = getImagePath(program.School_Logo_URL);

        header.innerHTML = `
            <div class="container">
                <div class="row align-items-center">
                    <div class="col-md-3">
                        <img src="${logoUrl}"
                             alt="${program.Team} Logo"
                             class="img-fluid"
                             style="max-height: 100px;"
                             onerror="this.src='${teamConfig.defaultLogo}'" />
                    </div>
                    <div class="col-md-6 text-center">
                        <h2>${program.Team}</h2>
                        <p>${program.Mascot || ''}</p>
                    </div>
                    <div class="col-md-3 text-right">
                        <img src="${sealUrl}"
                             alt="${program.Mascot}"
                             class="img-fluid"
                             style="max-height: 100px;"
                             onerror="this.src='${teamConfig.defaultLogo}'" />
                    </div>
                </div>
            </div>
        `;

        header.style.backgroundColor = program.PrimaryColor || '#000000';
        header.style.color = program.SecondaryColor || '#FFFFFF';
    }

    function displayCurrentPage(data = programsData) {
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
        const paginationElement = document.getElementById('pagination');
        if (!paginationElement) {
            const nav = document.createElement('nav');
            nav.innerHTML = '<ul class="pagination" id="pagination"></ul>';
            const tableContainer = document.querySelector('.table-responsive');
            if (tableContainer) {
                tableContainer.after(nav);
                return setupPagination(data);
            }
            return;
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

    async function initialize() {
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.addEventListener('input', handleSearch);
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

