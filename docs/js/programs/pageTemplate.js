// js/programs/pageTemplate.js
import { DEBUG_LEVELS, log } from '../main.js';
import { teamConfig } from '../config/teamConfig.js';

export function initializePage(pageConfig) {
   // Program specific constants
   const ITEMS_PER_PAGE = 100;
   let programsData = [];
   let currentPage = 1;

   function getImagePath(imageFile) {
       if (!imageFile) return teamConfig.defaultLogo;
       try {
           const program = programsData[0]; // Use first program for state/team
           return teamConfig.getTeamImagePath(program.State, program.Team, imageFile);
       } catch (error) {
           log(DEBUG_LEVELS.ERROR, 'Error generating image path', { imageFile, error });
           return teamConfig.defaultLogo;
       }
   }

   async function initializeRankings() {
       log(DEBUG_LEVELS.INFO, `Starting ${pageConfig.pageTitle} initialization`);
       try {
           updateLoadingState(true);
           const response = await fetch(pageConfig.dataFile);
           if (!response.ok) {
               throw new Error(`HTTP error! status: ${response.status}`);
           }
           programsData = await response.json();
           
           if (programsData.length > 0) {
               await updateTeamHeader(programsData[0]);
               setupPagination();
               displayCurrentPage();
               log(DEBUG_LEVELS.INFO, 'Rankings display complete');
           }
           
           updateLoadingState(false);
       } catch (error) {
           log(DEBUG_LEVELS.ERROR, 'Rankings initialization failed', error);
           updateLoadingState(false, error.message);
       }
   }

   function updateTeamHeader(program) {
    log(DEBUG_LEVELS.DEBUG, 'Updating team header', { team: program.team });
    const header = document.querySelector('.team-header');
    if (!header) {
        log(DEBUG_LEVELS.ERROR, 'Team header element not found');
        return;
    }

    // Use the actual image paths from the program data
    const logoUrl = program.LogoURL;  // This would come from WebV2
    const schoolLogoUrl = program.School_Logo_URL;  // This would come from WebV2

    header.innerHTML = `
        <div class="container">
            <div class="row align-items-center">
                <div class="col-md-3">
                    <img src="${logoUrl}"
                         alt="${program.Team} Logo"
                         class="img-fluid"
                         style="max-height: 100px;"
                         onerror="this.onerror=null; this.src='${teamConfig.defaultLogo}';" />
                </div>
                <div class="col-md-6 text-center">
                    <h2>${program.Team}</h2>
                    <p>${program.Mascot || ''}</p>
                </div>
                <div class="col-md-3 text-right">
                    <img src="${schoolLogoUrl}"
                         alt="${program.Mascot}"
                         class="img-fluid"
                         style="max-height: 100px;"
                         onerror="this.onerror=null; this.src='${teamConfig.defaultLogo}';" />
                </div>
            </div>
        </div>
    `;

    header.style.backgroundColor = program.PrimaryColor || '#000000';
    header.style.color = program.SecondaryColor || '#FFFFFF';
}

   // ... rest of the functions (displayCurrentPage, handleSearch, etc.) ...

   async function initialize() {
       try {
           const searchInput = document.getElementById('searchInput');
           if (searchInput) {
               searchInput.addEventListener('input', handleSearch);
           }

           await checkLoginStatus();  // Initialize auth
           await initializeRankings();
           await loadComments();      // Load comments after auth check
           
           log(DEBUG_LEVELS.INFO, 'Page initialization complete');
       } catch (error) {
           log(DEBUG_LEVELS.ERROR, 'Page initialization failed', error);
       }
   }

   return {
       initialize,
       handleSearch,
       updateTeamHeader,
       displayCurrentPage
   };
}