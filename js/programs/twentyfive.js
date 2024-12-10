// js/programs/twentyfive.js
import { DEBUG_LEVELS, log, REPO_BASE } from '../main.js';
import { initializePage } from './pageTemplate.js';
import { teamConfig } from '../config/teamConfig.js';

const CONFIG = {
    pageId: 'all-time-programs-twentyfive',
    pageTitle: 'Top High School Football Programs (25+ seasons)',
    dataFile: `${REPO_BASE}/data/all-time-programs-twentyfive.json`,
    defaultLogo: teamConfig.defaultLogo,
    imagePath: teamConfig.imagePath
};

document.addEventListener('DOMContentLoaded', async function() {
    try {
        log(DEBUG_LEVELS.INFO, 'Initializing 25+ seasons page');
        const page = initializePage(CONFIG);
        await page.initialize();
    } catch (error) {
        log(DEBUG_LEVELS.ERROR, 'Page initialization failed', error);
    }
});

export { CONFIG };