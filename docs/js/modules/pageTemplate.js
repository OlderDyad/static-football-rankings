// docs/js/modules/pageTemplate.js

import { DEBUG_LEVELS, log } from './logger.js';
import { createTeamHeader } from './teamHeader.js';

export function initializePage(pageConfig) {
    log(DEBUG_LEVELS.INFO, 'Starting', pageConfig.pageTitle, 'initialization');

    let programsData =;
    let currentPage = 1;
    const ITEMS_PER_PAGE = 100;

    async function initialize() {
        try {
            updateLoadingState(true); // Show loading state

            programsData = await loadProgramData(pageConfig.dataFile);
            if (programsData.length === 0) {
                throw new Error('Failed to load program data');
            }

            // Update page title and breadcrumb
            document.title = pageConfig.pageTitle;
            const breadcrumbItem = document.querySelector('.breadcrumb-item.active');
            if (breadcrumbItem) {
                breadcrumbItem.textContent = pageConfig.pageTitle;
            }

            // Display initial data and setup pagination
            displayCurrentPage();
            setupPagination();

            // Add event listeners
            const searchInput = document.getElementById('searchInput');
            if (searchInput) {
                searchInput.addEventListener('input', handleSearch);
            }

            updateLoadingState(false); // Hide loading state
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

            if (!data || !data.programs) {
                throw new Error('Invalid data format: Missing "programs" array');
            }

            // Handle top program separately
            if (data.topProgram) {
                createTeamHeader(data.topProgram);
            }

            return data.programs;
        } catch (error) {
            log(DEBUG_LEVELS.ERROR, 'Error loading program data:', error);
            return;
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
        } else {
            header.innerHTML = ''; // Clear loading state on success
        }
    }

    function setupPagination(data = programsData) {
        const totalPages = Math.ceil(data.length / ITEMS_PER_PAGE);
        log(DEBUG_LEVELS.DEBUG, `Setting up pagination: Total Pages = ${totalPages}`);
        const paginationElement = document.getElementById('pagination');
        if (!paginationElement) {
            log(DEBUG_LEVELS.ERROR, 'Pagination element not found');
            return;
        }

        paginationElement.innerHTML = ''; // Clear existing pagination

        if (totalPages <= 1) {
            return; // No need for pagination if only one page
        }

        for (let i = 1; i <= totalPages; i++) {
            const li = document.createElement('li');
            li.className = `page-item ${currentPage === i ? 'active' : ''}`;
            log(DEBUG_LEVELS.DEBUG, `Creating pagination button for page ${i}`);

            const button = document.createElement('button');
            button.className = 'page-link';
            button.textContent = i;
            button.addEventListener('click', () => {
                currentPage = i;
                log(DEBUG_LEVELS.DEBUG, `Page ${i} clicked`);
                displayCurrentPage(data);
                setupPagination(data); // Update pagination after filtering
            });

            li.appendChild(button);
            paginationElement.appendChild(li);
        }
    }

    function displayCurrentPage(data = programsData) {
        const tableBody = document.getElementById('programsTableBody');
        if (!tableBody) {
            log(DEBUG_LEVELS.ERROR, 'Programs table body element not found');
            return;
        }

        const start = (currentPage - 1) * ITEMS_PER_PAGE;
        const end = start + ITEMS_PER_PAGE;
        const currentData = data.slice(start, end);
        log(DEBUG_LEVELS.DEBUG, `Displaying page ${currentPage}: Items ${start + 1} to ${end}`);

        tableBody.innerHTML = ''; // Clear existing table data

        currentData.forEach(program => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${escapeHTML(program.rank.toString())}</td>
                <td>${escapeHTML(program.team)}</td>
                <td>${typeof program.avgCombined === 'number' ? program.avgCombined.toFixed(3) : escapeHTML(program.avgCombined)}</td>
                <td>${typeof program.avgMargin === 'number' ? program.avgMargin.toFixed(3) : escapeHTML(program.avgMargin)}</td>
                <td>${typeof program.avgWinLoss === 'number' ? program.avgWinLoss.toFixed(3) : escapeHTML(program.avgWinLoss)}</td>
                <td>${typeof program.avgOffense === 'number' ? program.avgOffense.toFixed(3) : escapeHTML(program.avgOffense)}</td>
                <td>${typeof program.avgDefense === 'number' ? program.avgDefense.toFixed(3) : escapeHTML(program.avgDefense)}</td>
                <td>${escapeHTML(program.state)}</td>
                <td>${escapeHTML(program.seasons.toString())}</td>
                <td>
                    <a href="/program/${encodeURIComponent(program.team)}" 
                       class="btn btn-primary btn-sm">View Details</a>
                </td>
            `;
            tableBody.appendChild(row);
        });
    }

    function handleSearch(event) {
        const searchTerm = event.target.value.toLowerCase();
        const filteredPrograms = programsData.filter(program => 
            program.team.toLowerCase().includes(searchTerm) ||
            program.state.toLowerCase().includes(searchTerm)
        );

        currentPage = 1; // Reset to first page when filtering
        displayCurrentPage(filteredPrograms);
        setupPagination(filteredPrograms); // Update pagination after filtering
    }

    function escapeHTML(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    return {
        initialize
    };
}