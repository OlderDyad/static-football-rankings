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
            return await response.json();
        } catch (error) {
            log(DEBUG_LEVELS.ERROR, 'Failed to load top item data:', error);
            return null;
        }
    }

    renderBanner(topItem) {
        if (!this.container) {
            log(DEBUG_LEVELS.ERROR, 'Banner container not found');
            return;
        }

        const logoPath = teamConfig.getTeamImagePath(topItem.LogoURL);
        const schoolLogoPath = teamConfig.getTeamImagePath(topItem.School_Logo_URL);

        const bannerHTML = `
            <div class="team-header" style="background-color: ${topItem.backgroundColor || '#FFFFFF'}; color: ${topItem.textColor || '#000000'};">
                <div class="container">
                    <div class="row align-items-center">
                        <div class="col-md-3 text-center">
                            <img src="${logoPath}"
                                 alt="${topItem.program || 'Team'} Logo"
                                 class="img-fluid team-logo"
                                 onerror="this.src='${teamConfig.defaultLogo}'; this.classList.add('default-logo');" />
                        </div>
                        <div class="col-md-6 text-center">
                            <h2>${topItem.program || 'Unknown Team'}</h2>
                            ${topItem.mascot ? `<p class="mascot-name">${topItem.mascot}</p>` : ''}
                        </div>
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
    }
}