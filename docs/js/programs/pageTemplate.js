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

   // Function to be used in both main.js and pageTemplate.js
function updateTeamHeader(program) {
    log(DEBUG_LEVELS.DEBUG, 'Updating team header', { 
        team: program.team,
        logoUrl: program.LogoURL,
        schoolLogoUrl: program.School_Logo_URL
    });

    const header = document.querySelector('.team-header');
    if (!header) {
        log(DEBUG_LEVELS.ERROR, 'Team header element not found');
        return;
    }

    const headerContent = `
        <div class="container">
            <div class="row align-items-center">
                <div class="col-md-3">
                    <img src="${program.LogoURL || '/static-football-rankings/docs/images/placeholder-image.jpg'}"
                         alt="${program.team} Logo"
                         class="img-fluid team-logo"
                         style="max-height: 100px;"
                         onerror="this.src='/static-football-rankings/docs/images/placeholder-image.jpg'"
                         onload="console.log('Logo loaded successfully:', this.src)"
                         onerror="console.log('Logo failed to load:', this.src)" />
                </div>
                <div class="col-md-6 text-center">
                    <h2 class="team-name">${program.team}</h2>
                    <p class="team-mascot">${program.mascot || ''}</p>
                    <div class="team-stats">
                        <small>Seasons: ${program.seasons} | Combined Rating: ${typeof program.avgCombined === 'number' ? program.avgCombined.toFixed(3) : program.avgCombined}</small>
                    </div>
                </div>
                <div class="col-md-3 text-right">
                    <img src="${program.School_Logo_URL || '/static-football-rankings/docs/images/placeholder-image.jpg'}"
                         alt="${program.team} School Logo"
                         class="img-fluid school-logo"
                         style="max-height: 100px;"
                         onerror="this.src='/static-football-rankings/docs/images/placeholder-image.jpg'"
                         onload="console.log('School logo loaded successfully:', this.src)"
                         onerror="console.log('School logo failed to load:', this.src)" />
                </div>
            </div>
        </div>
    `;

    header.innerHTML = headerContent;
    header.style.backgroundColor = program.backgroundColor || '#000000';
    header.style.color = program.textColor || '#FFFFFF';

    log(DEBUG_LEVELS.DEBUG, 'Header update complete');
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