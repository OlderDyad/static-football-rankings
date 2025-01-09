// main.js

// Main initialization function
async function initializeApp() {
    try {
        console.log('Initializing app...');

        // Get page configuration from HTML
        const h1Element = document.querySelector('h1[data-page-name]');
        if (!h1Element) {
            throw new Error('Page configuration not found');
        }

        const pageName = h1Element.dataset.pageName;
        let pageTitle = h1Element.textContent;

        // Get data file path from meta tag
        const dataFileMeta = document.querySelector('meta[name="data-file"]');
        if (!dataFileMeta) {
            throw new Error('Data file meta tag not found.');
        }
        const dataFile = dataFileMeta.content;
        console.log('Loading decade-specific data from', dataFile);

        const pageConfig = {
            pageTitle: pageTitle,
            pageName: pageName,
            dataFile: dataFile
        };

        console.log('Page config:', pageConfig);

        // Load and process the data
        const data = await loadProgramData(dataFile);
        if (!data) {
            throw new Error('Failed to load program data');
        }

        // Update page timestamp if available
        if (data.metadata?.timestamp) {
            updateTimestamp(data.metadata.timestamp);
        }

        // Initialize the page with the data
        populateTable(data);

        // Set up comment submission
        initializeComments();

    } catch (error) {
        console.error('App initialization failed:', error);
        updateLoadingState(false, error.message);
    }
}

// Load program data with unified structure handling
async function loadProgramData(dataFile) {
    console.log('Loading program data from', dataFile);
    updateLoadingState(true);
    
    try {
        const response = await fetch(dataFile);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const jsonData = await response.json();

        if (!jsonData || !jsonData.items || !Array.isArray(jsonData.items)) {
            throw new Error('Invalid data format: "items" array is missing or not an array.');
        }

        // Use the "items" array for populating the table
        return jsonData;

    } catch (error) {
        console.error('Error loading program data:', error);
        throw error;
    } finally {
        updateLoadingState(false);
    }
}

// Function to populate the table with data
function populateTable(data) {
    const tableBody = document.getElementById("programsTableBody");
    tableBody.innerHTML = ""; // Clear existing table data

    if (Array.isArray(data.items) && data.items.length > 0) {
        data.items.forEach((item) => {
            const row = document.createElement("tr");
            row.innerHTML = `
                <td>${item.rank}</td>
                <td>${item.team}</td>
                <td>${item.state}</td>
                <td>${item.seasons}</td>
                <td>${item.combined}</td>
                <td>${item.margin}</td>
                <td>${item.win_loss}</td>
                <td>${item.offense}</td>
                <td>${item.defense}</td>
                <td>${item.games_played}</td>
            `;
            tableBody.appendChild(row);
        });
    } else {
        const noDataRow = document.createElement("tr");
        noDataRow.innerHTML = `<td colspan="10">No data available</td>`;
        tableBody.appendChild(noDataRow);
    }
}

// Loading state management (simplified for static site)
function updateLoadingState(isLoading, errorMessage = '') {
    const loadingIndicator = document.getElementById('loadingIndicator');
    const errorContainer = document.getElementById('errorContainer');

    if (isLoading) {
        if (loadingIndicator) {
            loadingIndicator.style.display = 'block';
        }
        if (errorContainer) {
            errorContainer.style.display = 'none';
        }
    } else {
        if (loadingIndicator) {
            loadingIndicator.style.display = 'none';
        }
        if (errorMessage && errorContainer) {
            errorContainer.innerHTML = `<div class="alert alert-danger">${escapeHTML(errorMessage)}</div>`;
            errorContainer.style.display = 'block';
        }
    }
}

// Utility function for timestamp
function updateTimestamp(timestamp) {
    const element = document.getElementById('lastUpdated');
    if (element && timestamp) {
        element.textContent = new Date(timestamp).toLocaleDateString();
    }
}

// Function to initialize comments
function initializeComments() {
    var disqus_config = function () {
        this.page.url = window.location.href;
        this.page.identifier = window.location.pathname; // Replace with a unique identifier for each page
    };

    (function() { // DON'T EDIT BELOW THIS LINE
        var d = document, s = d.createElement('script');
        s.src = 'https://mckennafootball-com.disqus.com/embed.js'; // Your Disqus shortname
        s.setAttribute('data-timestamp', +new Date());
        (d.head || d.body).appendChild(s);
    })();
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', initializeApp);
