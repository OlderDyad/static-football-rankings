// topBanner.js
import { teamConfig } from '../config/teamConfig.js';
import { log, DEBUG_LEVELS } from './logger.js';

export class TopBanner {
    constructor() {
        this.container = document.getElementById('teamHeaderContainer');
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
            const response = await fetch(dataFileMeta.content);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            log(DEBUG_LEVELS.INFO, 'Top item data loaded:', data);
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

        // Get image paths with fallback to default
        const logoPath = topItem.LogoURL ? teamConfig.getTeamImagePath(topItem.LogoURL) : teamConfig.defaultLogo;
        const schoolLogoPath = topItem.School_Logo_URL ? teamConfig.getTeamImagePath(topItem.School_Logo_URL) : teamConfig.defaultLogo;

        // Handle styling with fallbacks
        const backgroundColor = topItem.backgroundColor || '#FFFFFF';
        const textColor = topItem.textColor || '#000000';

        const bannerHTML = `
            <div class="team-header" style="background-color: ${backgroundColor}; color: ${textColor};">
                <div class="container">
                    <div class="row align-items-center">
                        <!-- Team Logo -->
                        <div class="col-md-3 text-center">
                            <img src="${logoPath}"
                                 alt="${topItem.program || 'Team'} Logo"
                                 class="img-fluid team-logo"
                                 onerror="this.src='${teamConfig.defaultLogo}'; this.classList.add('default-logo');" />
                        </div>
                        <!-- Team/Program Info -->
                        <div class="col-md-6 text-center">
                            <h2>${topItem.program || 'Unknown Team'}</h2>
                            ${topItem.mascot ? `<p class="mascot-name">${topItem.mascot}</p>` : ''}
                            <div class="team-stats">
                                <small>
                                    ${topItem.seasons ? `Seasons: ${topItem.seasons}` : ''}
                                    ${topItem.margin ? `| Margin: ${parseFloat(topItem.margin).toFixed(1)}` : ''}
                                </small>
                            </div>
                        </div>
                        <!-- School Logo -->
                        <div class="col-md-3 text-center">
                            <img src="${schoolLogoPath}"
                                 alt="${topItem.program || 'School'} School Logo"
                                 class="img-fluid school-logo"
                                 onerror="this.src='${teamConfig.defaultLogo}'; this.classList.add('default-logo');" />
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

    // Helper method to validate image paths
    validateImagePath(path) {
        if (!path) return false;
        const img = new Image();
        img.src = path;
        return new Promise((resolve) => {
            img.onload = () => resolve(true);
            img.onerror = () => resolve(false);
        });
    }
}