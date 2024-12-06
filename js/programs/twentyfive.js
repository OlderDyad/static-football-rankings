// js/programs/twentyfive.js
import { DEBUG_LEVELS, log, REPO_BASE } from '../main.js';

// Program specific constants
const ITEMS_PER_PAGE = 100;
let programsData = [];
let currentPage = 1;

// Program specific configuration
const CONFIG = {
   dataFile: '/static-football-rankings/data/all-time-programs-twentyfive.json',
   pageId: 'all-time-programs-twentyfive'
};

// Core ranking functions
async function initializeRankings() {
   log(DEBUG_LEVELS.INFO, 'Starting 25+ programs initialization');
   try {
       updateLoadingState(true);
       const response = await fetch(CONFIG.dataFile);
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
   log(DEBUG_LEVELS.DEBUG, 'Updating team header', { team: program.Team });
   const header = document.querySelector('.team-header');
   if (!header) {
       log(DEBUG_LEVELS.ERROR, 'Team header element not found');
       return;
   }

   header.innerHTML = `
       <div class="container">
           <div class="row align-items-center">
               <div class="col-md-3">
                   <img src="${getImagePath(program.LogoURL)}"
                        alt="${program.Team} Logo"
                        class="img-fluid team-logo"
                        style="max-height: 100px;"
                        onerror="this.src='${DEFAULT_PLACEHOLDER}'" />
               </div>
               <div class="col-md-6 text-center">
                   <h2 class="team-name">${program.Team}</h2>
                   <p class="team-mascot">${program.Mascot || ''}</p>
                   <div class="team-stats">
                       <small>Seasons: ${program.Seasons} | Combined Rating: ${program.AvgCombined.toFixed(3)}</small>
                   </div>
               </div>
               <div class="col-md-3 text-right">
                   <img src="${getImagePath(program.School_Logo_URL)}"
                        alt="${program.Team} School Logo"
                        class="img-fluid school-logo"
                        style="max-height: 100px;"
                        onerror="this.src='${DEFAULT_PLACEHOLDER}'" />
               </div>
           </div>
       </div>
   `;

   header.style.backgroundColor = program.PrimaryColor || '#000000';
   header.style.color = program.SecondaryColor || '#FFFFFF';
}

// Display and pagination functions
function displayCurrentPage(data = programsData) {
   log(DEBUG_LEVELS.DEBUG, 'Displaying page', { 
       page: currentPage,
       totalItems: data?.length 
   });

   const tableBody = document.getElementById('programsTableBody');
   if (!tableBody) {
       log(DEBUG_LEVELS.ERROR, 'Table body element not found');
       return;
   }

   const start = (currentPage - 1) * ITEMS_PER_PAGE;
   const end = start + ITEMS_PER_PAGE;
   const currentData = data.slice(start, end);

   tableBody.innerHTML = '';
   currentData.forEach(program => {
       const row = document.createElement('tr');
       row.innerHTML = `
           <td>${program.Rank}</td>
           <td>${program.Team}</td>
           <td>${program.AvgCombined.toFixed(3)}</td>
           <td>${program.AvgMargin.toFixed(3)}</td>
           <td>${program.AvgWinLoss.toFixed(3)}</td>
           <td>${program.AvgOffense.toFixed(3)}</td>
           <td>${program.AvgDefense.toFixed(3)}</td>
           <td>${program.State}</td>
           <td>${program.Seasons}</td>
           <td>
               <button onclick="showProgramDetails('${program.Team}')"
                       class="btn btn-primary btn-sm">View Details</button>
           </td>
       `;
       tableBody.appendChild(row);
   });
}

// Search functionality
function handleSearch(event) {
   const searchTerm = event.target.value.toLowerCase();
   log(DEBUG_LEVELS.DEBUG, 'Processing search', { term: searchTerm });

   const filteredPrograms = programsData.filter(program =>
       program.Team.toLowerCase().includes(searchTerm) ||
       program.State.toLowerCase().includes(searchTerm)
   );

   log(DEBUG_LEVELS.DEBUG, 'Search results', { 
       total: programsData.length,
       filtered: filteredPrograms.length 
   });

   currentPage = 1;
   setupPagination(filteredPrograms);
   displayCurrentPage(filteredPrograms);
}

// Initialize the page
document.addEventListener('DOMContentLoaded', async function() {
   try {
       await initializeRankings();
       
       // Set up event listeners
       const searchInput = document.getElementById('searchInput');
       if (searchInput) {
           searchInput.addEventListener('input', handleSearch);
       }
   } catch (error) {
       log(DEBUG_LEVELS.ERROR, 'Page initialization failed', error);
   }
});

export { initializeRankings };