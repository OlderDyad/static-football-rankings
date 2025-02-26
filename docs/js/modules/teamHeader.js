// topBanner.js
import { teamConfig } from '../config/teamConfig.js';
import { log, DEBUG_LEVELS } from './logger.js';

// Function to fix image paths with spaces and special characters
function fixImagePath(path) {
    if (!path) return '';
    
    // Handle URL encoding for spaces and special characters
    const parts = path.split('/');
    const filename = parts.pop();
    const encodedFilename = encodeURIComponent(filename);
    parts.push(encodedFilename);
    
    return parts.join('/');
}

export class TopBanner {
    constructor() {
        this.container = document.getElementById('teamHeaderContainer');
        this.imageRetryCount = {}; // Track retry counts for images
    }

    async initialize() {
        try {
            // Remove any existing duplicate banners
            const duplicateBanners = document.querySelectorAll('.header-banner');
            if (duplicateBanners.length > 1) {
                // Keep only the first banner
                for (let i = 1; i < duplicateBanners.length; i++) {
                    duplicateBanners[i].remove();
                }
            }

            const data = await this.loadTopItemData();
            if (data && data.topItem) {
                log(DEBUG_LEVELS.DEBUG, 'Loaded topItem data:', JSON.stringify(data.topItem));
                this.renderBanner(data.topItem);
            }
        } catch (error) {
            log(DEBUG_LEVELS.ERROR, 'TopBanner initialization failed:', error);
            this.renderError('Failed to load banner data');
        }
    }

    async loadTopItemData() {
        const dataFileMeta = document.querySelector('meta[name="data-file"]');
        if (!dataFileMeta) {
            log(DEBUG_LEVELS.ERROR, 'No data file meta tag found');
            return null;
        }
    
        try {
            const dataPath = dataFileMeta.content;
            log(DEBUG_LEVELS.INFO, `Loading data from: ${dataPath}`);
            
            const response = await fetch(dataPath);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            return data;
        } catch (error) {
            log(DEBUG_LEVELS.ERROR, 'Failed to load top item data:', error);
            throw error;
        }
    }

    renderBanner(topItem) {
        if (!this.container) {
            log(DEBUG_LEVELS.ERROR, 'Banner container not found');
            return;
        }
    
        // Detailed logging of the topItem object
        log(DEBUG_LEVELS.DEBUG, 'Full topItem data:', topItem);
        log(DEBUG_LEVELS.DEBUG, 'LogoURL (uppercase):', topItem.LogoURL);
        log(DEBUG_LEVELS.DEBUG, 'logoURL (lowercase):', topItem.logoURL);
        log(DEBUG_LEVELS.DEBUG, 'School_Logo_URL:', topItem.School_Logo_URL);
        log(DEBUG_LEVELS.DEBUG, 'schoolLogoURL:', topItem.schoolLogoURL);
    
        // Support both property naming conventions
        const logoURL = topItem.logoURL || topItem.LogoURL;
        const schoolLogoURL = topItem.schoolLogoURL || topItem.School_Logo_URL;
    
        // More logging for the resolved URLs
        log(DEBUG_LEVELS.DEBUG, 'Resolved logoURL:', logoURL);
        log(DEBUG_LEVELS.DEBUG, 'Resolved schoolLogoURL:', schoolLogoURL);
    
        // Fix #1: Better team/program name handling with explicit null checking
        const teamName = topItem.team || topItem.program || 'Unknown Team';
        const mascot = topItem.mascot || '';
    
        // Fix #2: Handle image paths better - stop endless loops
        const logoPath = logoURL ? 
            teamConfig.getTeamImagePath(fixImagePath(logoURL)) : 
            teamConfig.defaultLogo;
            
        const schoolLogoPath = schoolLogoURL ? 
            teamConfig.getTeamImagePath(fixImagePath(schoolLogoURL)) : 
            teamConfig.defaultLogo;
    
        // Handle styling with fallbacks
        const backgroundColor = topItem.backgroundColor || '#FFFFFF';
        const textColor = topItem.textColor || '#000000';
    
        // Fix #3: Better stats display with proper null handling
        const seasonsText = topItem.seasons ? `Seasons: ${topItem.seasons}` : '';
        const marginText = topItem.margin ? `Margin: ${parseFloat(topItem.margin).toFixed(1)}` : '';
        const seasonText = topItem.season ? `Season: ${topItem.season}` : '';
        const statsText = [seasonsText, marginText, seasonText].filter(Boolean).join(' | ');
    
        // The rest of your method remains unchanged...

        const bannerHTML = `
            <div class="team-header" style="background-color: ${backgroundColor}; color: ${textColor};">
                <div class="container">
                    <div class="row align-items-center">
                        <!-- Team Logo -->
                        <div class="col-md-3 text-center">
                            <img src="${logoPath}"
                                 alt="${teamName} Logo"
                                 class="img-fluid team-logo"
                                 data-default-shown="false"
                                 onerror="if(!this.dataset.defaultShown){this.src='${teamConfig.defaultLogo}'; this.dataset.defaultShown='true';}" />
                        </div>
                        <!-- Team/Program Info -->
                        <div class="col-md-6 text-center">
                            <h2>${teamName}</h2>
                            ${mascot ? `<p class="mascot-name">${mascot}</p>` : ''}
                            <div class="team-stats">
                                <small>${statsText}</small>
                            </div>
                        </div>
                        <!-- School Logo -->
                        <div class="col-md-3 text-center">
                            <img src="${schoolLogoPath}"
                                 alt="${teamName} School Logo"
                                 class="img-fluid school-logo"
                                 data-default-shown="false"
                                 onerror="if(!this.dataset.defaultShown){this.src='${teamConfig.defaultLogo}'; this.dataset.defaultShown='true';}" />
                        </div>
                    </div>
                </div>
            </div>
        `;

        this.container.innerHTML = bannerHTML;
        log(DEBUG_LEVELS.INFO, 'Banner rendered successfully');
    }

    renderError(message) {
        if (!this.container) return;
        
        this.container.innerHTML = `
            <div class="alert alert-warning m-3" role="alert">
                ${message}
            </div>
        `;
        log(DEBUG_LEVELS.ERROR, 'Banner error rendered:', message);
    }
}