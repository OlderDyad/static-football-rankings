// docs/js/modules/pageTemplate.js
import { DEBUG_LEVELS, log } from './logger.js';
import { createTeamHeader } from './teamHeader.js';

export function initializePage(pageConfig) {
    log(DEBUG_LEVELS.INFO, 'Starting', pageConfig.pageTitle, 'initialization');

    let programsData = [];
    let currentPage = 1;
    const ITEMS_PER_PAGE = 100;

    async function initialize() {
        try {
            updateLoadingState(true);

            programsData = await loadProgramData(pageConfig.dataFile);
            if (!Array.isArray(programsData) || programsData.length === 0) {
                throw new Error('No program data available');
            }

            // Update page title and breadcrumb
            document.title = pageConfig.pageTitle;
            updateBreadcrumb(pageConfig.pageTitle);

            // Display initial data and setup pagination
            displayCurrentPage();
            setupPagination();

            // Add event listeners
            setupEventListeners();

            updateLoadingState(false);
            log(DEBUG_LEVELS.INFO, 'Rankings display complete');

        } catch (error) {
            log(DEBUG_LEVELS.ERROR, 'Page initialization failed:', error);
            updateLoadingState(false, error.message);
        }
    }

    async function loadProgramData(dataFile) {
        log(DEBUG_LEVELS.INFO, 'Loading program data from', dataFile);
        try {
            const response = await fetch(dataFile);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();

            // Validate data structure
            validateDataStructure(data);

            // Update timestamp if available
            updateTimestamp(data.metadata?.timestamp);

            // Handle top program
            if (data.topProgram) {
                const headerHtml = createTeamHeader(data.topProgram);
                const headerContainer = document.querySelector('.team-header');
                if (headerContainer) {
                    headerContainer.innerHTML = headerHtml;
                    log(DEBUG_LEVELS.INFO, 'Team header inserted into DOM');
                } else {
                    log(DEBUG_LEVELS.ERROR, 'Team header container not found');
                }
            }

            return data.programs || [];
        } catch (error) {
            log(DEBUG_LEVELS.ERROR, 'Error loading program data:', error);
            return [];
        }
    }

    function validateDataStructure(data) {
        if (!data) {
            throw new Error('No data received');
        }

        if (!data.metadata) {
            log(DEBUG_LEVELS.WARN, 'Missing metadata in data structure');
        }

        if (!Array.isArray(data.programs)) {
            throw new Error('Invalid data format: programs must be an array');
        }

        // Validate required fields in each program with better error reporting
    data.programs.forEach((program, index) => {
        // Skip validation for null/undefined objects
        if (!program) {
            log(DEBUG_LEVELS.WARN, `Empty program at index ${index}`);
            return;
        }

        const requiredFields = ['team', 'rank', 'state', 'seasons'];
        const missingFields = requiredFields.filter(field => !program[field]);
        if (missingFields.length > 0) {
            // Only log warning for actual data entries
            if (index < data.programs.length - 1) {
                log(DEBUG_LEVELS.WARN, `Program at index ${index} missing required fields:`, missingFields);
            }
        }
    });
}

    function updateTimestamp(timestamp) {
        const element = document.getElementById('lastUpdated');
        if (element && timestamp) {
            try {
                element.textContent = new Date(timestamp).toLocaleDateString();
            } catch (error) {
                log(DEBUG_LEVELS.ERROR, 'Error formatting timestamp:', error);
                element.textContent = 'Unknown';
            }
        }
    }

    function updateBreadcrumb(title) {
        const breadcrumbItem = document.querySelector('.breadcrumb-item.active');
        if (breadcrumbItem) {
            breadcrumbItem.textContent = title;
        }
    }

    function setupEventListeners() {
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.addEventListener('input', handleSearch);
        }
    }

    function handleSearch(event) {
        const searchTerm = event.target.value.toLowerCase();
        const filteredPrograms = programsData.filter(program => 
            program.team.toLowerCase().includes(searchTerm) ||
            program.state.toLowerCase().includes(searchTerm)
        );

        currentPage = 1;
        displayCurrentPage(filteredPrograms);
        setupPagination(filteredPrograms);
    }

    function setupPagination(data = programsData) {
        const paginationElement = document.getElementById('pagination');
        if (!paginationElement) {
            log(DEBUG_LEVELS.ERROR, 'Pagination element not found');
            return;
        }

        const totalPages = Math.ceil(data.length / ITEMS_PER_PAGE);
        paginationElement.innerHTML = '';

        if (totalPages <= 1) return;

        // Add pagination controls
        addPaginationControls(paginationElement, totalPages);
    }

    function addPaginationControls(element, totalPages) {
        // Previous button
        const prevLi = createPaginationButton('Previous', currentPage > 1, () => {
            if (currentPage > 1) {
                currentPage--;
                displayCurrentPage();
                setupPagination();
            }
        });
        element.appendChild(prevLi);

        // Page numbers
        for (let i = 1; i <= totalPages; i++) {
            const li = document.createElement('li');
            li.className = `page-item ${currentPage === i ? 'active' : ''}`;
            li.innerHTML = `<button class="page-link">${i}</button>`;
            li.addEventListener('click', () => {
                currentPage = i;
                displayCurrentPage();
                setupPagination();
            });
            element.appendChild(li);
        }

        // Next button
        const nextLi = createPaginationButton('Next', currentPage < totalPages, () => {
            if (currentPage < totalPages) {
                currentPage++;
                displayCurrentPage();
                setupPagination();
            }
        });
        element.appendChild(nextLi);
    }

    function createPaginationButton(text, enabled, onClick) {
        const li = document.createElement('li');
        li.className = `page-item ${!enabled ? 'disabled' : ''}`;
        const button = document.createElement('button');
        button.className = 'page-link';
        button.textContent = text;
        if (enabled) {
            button.addEventListener('click', onClick);
        }
        li.appendChild(button);
        return li;
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

        tableBody.innerHTML = currentData.map(program => createTableRow(program)).join('');
    }

    function createTableRow(program) {
        return `
            <tr>
                <td>${program.rank}</td>
                <td>${program.team}</td>
                <td>${formatNumber(program.avgCombined)}</td>
                <td>${formatNumber(program.avgMargin)}</td>
                <td>${formatNumber(program.avgWinLoss)}</td>
                <td>${formatNumber(program.avgOffense)}</td>
                <td>${formatNumber(program.avgDefense)}</td>
                <td>${program.state}</td>
                <td>${program.seasons}</td>
                <td>
                    <button class="btn btn-primary btn-sm" onclick="viewDetails('${encodeURIComponent(program.team)}')">
                        View Details
                    </button>
                </td>
            </tr>
        `;
    }

    function formatNumber(value) {
        return typeof value === 'number' ? value.toFixed(3) : value;
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

    // Initialize and return public interface
    return {
        initialize
    };
}

// Add to window for onclick handlers
window.viewDetails = (teamName) => {
    log(DEBUG_LEVELS.INFO, 'Viewing details for:', decodeURIComponent(teamName));
    // Implement details view functionality
};