// js/programs/fifty.js
import { DEBUG_LEVELS, log } from '../main.js';
import { initializePage } from './pageTemplate.js';

const CONFIG = {
   pageId: 'all-time-programs-fifty',
   pageTitle: 'Top High School Football Programs (50+ seasons)',
   dataFile: '/data/all-time-programs-fifty.json',
   defaultLogo: '/static-football-rankings/docs/images/placeholder-image.jpg',
   imagePath: '/static-football-rankings/docs/images/teams'
};

// Initialize page with config
document.addEventListener('DOMContentLoaded', async function() {
   try {
       log(DEBUG_LEVELS.INFO, 'Initializing 50+ seasons page');
       const page = initializePage(CONFIG);
       await page.initialize();
       log(DEBUG_LEVELS.INFO, 'Page initialization complete');
   } catch (error) {
       log(DEBUG_LEVELS.ERROR, 'Page initialization failed', error);
   }
});

export { CONFIG };