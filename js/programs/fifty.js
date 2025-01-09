// js/programs/fifty.js
import { DEBUG_LEVELS, log } from '../main.js';
import { initializePage } from './pageTemplate.js';
import { teamConfig } from '../config/teamConfig.js';

const CONFIG = {
   pageId: 'all-time-programs-fifty',
   pageTitle: 'Top High School Football Programs (50+ seasons)',
   dataFile: '/static-football-rankings/data/all-time-programs-fifty.json',
   defaultLogo: teamConfig.defaultLogo,
   imagePath: teamConfig.imagePath
};

document.addEventListener('DOMContentLoaded', async function() {
   try {
       log(DEBUG_LEVELS.INFO, 'Initializing 50+ seasons page');
       const page = initializePage(CONFIG);
       await page.initialize();
   } catch (error) {
       log(DEBUG_LEVELS.ERROR, 'Page initialization failed', { 
           error,
           pageId: CONFIG.pageId 
       });
   }
});

export { CONFIG };
