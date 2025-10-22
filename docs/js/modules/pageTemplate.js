// ============================================================================
// docs/js/modules/pageTemplate.js - Program Display Template Logic
// ============================================================================

import { DEBUG_LEVELS, log } from './logger.js';
import { createTeamHeader } from './teamHeader.js';

export function initializePage(pageConfig) {
    log(DEBUG_LEVELS.INFO, 'Starting', pageConfig.pageTitle, 'initialization');

    let itemsData = [];
    let currentPage = 1;
    const ITEMS_PER_PAGE = 100;

    // Main initialization function
    async function initialize(data = null) {
        try {
            updateLoadingState(true);

            // Use provided data or load from file
            const validatedData = data || await loadData(pageConfig.dataFile);
            
            // Store validated data
            itemsData = validatedData.items || [];
            
            log(DEBUG_LEVELS.INFO, `Loaded ${itemsData.length} items`);
            
            if (itemsData.length === 0) {
                throw new Error('No items available in data');
            }

            // Update page metadata
            document.title = pageConfig.pageTitle;
            updateBreadcrumb(pageConfig.pageTitle);

            // Create header if top item exists
            if (validatedData.topItem) {
                createTeamHeader(validatedData.topItem);
            }

            // Set up display and controls
            displayCurrentPage();
            setupPagination();
            setupEventListeners();
            
            // Update timestamp if available
            if (validatedData.metadata?.timestamp) {
                updateTimestamp(validatedData.metadata.timestamp);
            }

            updateLoadingState(false);
            log(DEBUG_LEVELS.INFO, 'Page initialization complete');

        } catch (error) {
            log(DEBUG_LEVELS.ERROR, 'Page initialization failed:', error);
            updateLoadingState(false, error.message);
            throw error;
        }
    }

    // Data loading function
    async function loadData(dataFile) {
        log(DEBUG_LEVELS.INFO, 'Loading data from', dataFile);
        try {
            const response = await fetch(dataFile);
            if (!response.ok) {
                throw new Error(`Failed to load data: ${response.status} ${response.statusText}`);
            }
            
            const data = await response.json();
            log(DEBUG_LEVELS.INFO, 'Received data structure:', {
                hasMetadata: !!data.metadata,
                hasItems: !!data.items,
                hasPrograms: !!data.programs,
                hasTeams: !!data.teams,
                dataKeys: Object.keys(data)
            });
            
            // Convert and validate data
            return validateDataStructure(data);
        } catch (error) {
            log(DEBUG_LEVELS.ERROR, 'Error loading data:', error);
            throw error;
        }
    }

    // Data validation function
    function validateDataStructure(data) {
        log(DEBUG_LEVELS.INFO, 'Validating data structure:', {
            hasMetadata: !!data?.metadata,
            hasItems: !!data?.items,
            itemsLength: data?.items?.length || 0,
            dataKeys: Object.keys(data || {})
        });

        if (!data || typeof data !== 'object') {
            throw new Error('Invalid data format: Data must be an object');
        }

        if (!data.items || !Array.isArray(data.items)) {
            // Try to find any available data array
            if (data.programs && Array.isArray(data.programs)) {
                data.items = data.programs;
                delete data.programs;
                log(DEBUG_LEVELS.INFO, 'Converted programs array to items');
            } else if (data.teams && Array.isArray(data.teams)) {
                data.items = data.teams;
                delete data.teams;
                log(DEBUG_LEVELS.INFO, 'Converted teams array to items');
            } else {
                throw new Error('Invalid data format: Missing items array');
            }
        }

        if (data.items.length === 0) {
            throw new Error('No items found in data');
        }

        // Log first item structure for debugging
        const firstItem = data.items[0];
        log(DEBUG_LEVELS.INFO, 'First item structure:', {
            hasProgram: 'program' in firstItem,
            hasTeam: 'team' in firstItem,
            keys: Object.keys(firstItem)
        });

        // Ensure metadata exists
        if (!data.metadata) {
            data.metadata = {
                timestamp: new Date().toISOString(),
                type: 'program' in firstItem ? 'all-time-programs' : 'teams',
                yearRange: 'all-time',
                totalItems: data.items.length,
                description: 'Program rankings'
            };
            log(DEBUG_LEVELS.INFO, 'Created default metadata');
        }

        return data;
    }

    // Display functions
    function displayCurrentPage(data = itemsData) {
        const tableBody = document.getElementById('programsTableBody');
        if (!tableBody) {
            log(DEBUG_LEVELS.ERROR, 'Table body element not found');
            return;
        }

        const start = (currentPage - 1) * ITEMS_PER_PAGE;
        const end = start + ITEMS_PER_PAGE;
        const currentData = data.slice(start, end);

        tableBody.innerHTML = currentData.map(item => createTableRow(item)).join('');
    }

    function createTableRow(item) {
        const isTeam = 'team' in item;

        if (isTeam) {
            return `
                <tr>
                    <td>${item.rank}</td>
                    <td>${item.team}</td>
                    <td>${item.season || ''}</td>
                    <td>${formatNumber(item.combined)}</td>
                    <td>${formatNumber(item.margin)}</td>
                    <td>${formatNumber(item.win_loss)}</td>
                    <td>${formatNumber(item.offense)}</td>
                    <td>${formatNumber(item.defense)}</td>
                    <td>${item.games_played || ''}</td>
                    <td>${item.state}</td>
                    <td>
                        <button class="btn btn-primary btn-sm" onclick="viewDetails('${encodeURIComponent(item.team)}')">
                            Details
                        </button>
                    </td>
                </tr>
            `;
        } else {
            return `
                <tr>
                    <td>${item.rank}</td>
                    <td>${item.program}</td>
                    <td>${item.seasons}</td>
                    <td>${formatNumber(item.combined)}</td>
                    <td>${formatNumber(item.margin)}</td>
                    <td>${formatNumber(item.win_loss)}</td>
                    <td>${formatNumber(item.offense)}</td>
                    <td>${formatNumber(item.defense)}</td>
                    <td>${item.state}</td>
                    <td>
                        <button class="btn btn-primary btn-sm" onclick="viewDetails('${encodeURIComponent(item.program)}')">
                            Details
                        </button>
                    </td>
                </tr>
            `;
        }
    }

    // Utility functions
    function formatNumber(value) {
        if (typeof value === 'number') {
            return value.toFixed(3);
        } else if (typeof value === 'string' && !isNaN(parseFloat(value))) {
            return parseFloat(value).toFixed(3);
        }
        return value;
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

    function updateLoadingState(isLoading, errorMessage = '') {
        const loadingElement = document.querySelector('.loading-state');
        if (!loadingElement) return;

        if (isLoading) {
            loadingElement.innerHTML = `
                <div class="text-center">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p>Loading data...</p>
                </div>`;
            loadingElement.style.display = 'block';
        } else if (errorMessage) {
            loadingElement.innerHTML = `
                <div class="alert alert-danger">${errorMessage}</div>`;
            loadingElement.style.display = 'block';
        } else {
            loadingElement.style.display = 'none';
        }
    }

    // Event handlers
    function setupEventListeners() {
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.addEventListener('input', handleSearch);
        }
    }

    function handleSearch(event) {
        const searchTerm = event.target.value.toLowerCase();
        const filteredItems = itemsData.filter(item => {
            const searchableFields = [
                item.team || item.program,
                item.state
            ].filter(Boolean);
            
            return searchableFields.some(field => 
                field.toLowerCase().includes(searchTerm)
            );
        });

        currentPage = 1;
        displayCurrentPage(filteredItems);
        setupPagination(filteredItems);
    }

    // Pagination functions
    function setupPagination(data = itemsData) {
        const paginationElement = document.getElementById('pagination');
        if (!paginationElement) return;

        const totalPages = Math.ceil(data.length / ITEMS_PER_PAGE);
        if (totalPages <= 1) {
            paginationElement.innerHTML = '';
            return;
        }

        addPaginationControls(paginationElement, totalPages);
    }

    function addPaginationControls(element, totalPages) {
        element.innerHTML = '';

        element.appendChild(
            createPaginationButton('Previous', currentPage > 1, () => {
                if (currentPage > 1) {
                    currentPage--;
                    displayCurrentPage();
                    setupPagination();
                }
            })
        );

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

        element.appendChild(
            createPaginationButton('Next', currentPage < totalPages, () => {
                if (currentPage < totalPages) {
                    currentPage++;
                    displayCurrentPage();
                    setupPagination();
                }
            })
        );
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

    // Return public interface
    return {
        initialize
    };
}