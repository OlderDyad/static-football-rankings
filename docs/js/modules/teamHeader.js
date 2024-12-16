// C:\Users\demck\OneDrive\Football_2024\static-football-rankings\docs\js\programs\common\teamHeader.js

// docs/js/modules/teamHeader.js
import { teamConfig } from '../config/teamConfig.js';
import { DEBUG_LEVELS, log } from './logger.js';

// Image load tracking
const imageLoadScript = `
<script>
    window.imageLoadStats = {
        attempts: 0,
        successes: 0,
        failures: 0
    };

    function trackImageLoad(success, src) {
        window.imageLoadStats.attempts++;
        if (success) {
            window.imageLoadStats.successes++;
        } else {
            window.imageLoadStats.failures++;
            console.warn('Image load failed:', src);
        }
        console.debug('Image load stats:', window.imageLoadStats);
    }
</script>
`;

export function createTeamHeader(program) {
    log(DEBUG_LEVELS.DEBUG, 'Creating team header with data:', program);

    // Default values for missing data
    const defaultDetails = {
        teamName: 'Unknown Team',
        mascot: '',
        backgroundColor: '#000000',
        textColor: '#FFFFFF'
    };

    // If no program data, return minimal header
    if (!program) {
        log(DEBUG_LEVELS.WARN, 'No program data provided for header');
        return createMinimalHeader(defaultDetails);
    }

    const teamDetails = {
        teamName: program.team || defaultDetails.teamName,
        mascot: program.mascot || defaultDetails.mascot,
        primaryColor: program.backgroundColor || defaultDetails.backgroundColor,
        secondaryColor: program.textColor || defaultDetails.textColor,
        logoPath: program.LogoURL || null,
        schoolLogoPath: program.School_Logo_URL || null
    };

    log(DEBUG_LEVELS.DEBUG, 'Processed team details:', teamDetails);

    // Return header HTML with conditionally rendered images
    return `
        <div class="container">
            <div class="row align-items-center">
                <div class="col-md-3">
                    ${teamDetails.logoPath ? 
                        `<img src="${teamDetails.logoPath}"
                             alt="${teamDetails.teamName} Logo"
                             class="img-fluid"
                             style="max-height: 100px;"
                             onerror="this.style.display='none'"/>` : ''}
                </div>
                <div class="col-md-6 text-center">
                    <h2>${teamDetails.teamName}</h2>
                    <p>${teamDetails.mascot}</p>
                </div>
                <div class="col-md-3 text-right">
                    ${teamDetails.schoolLogoPath ? 
                        `<img src="${teamDetails.schoolLogoPath}"
                             alt="${teamDetails.mascot}"
                             class="img-fluid"
                             style="max-height: 100px;"
                             onerror="this.style.display='none'"/>` : ''}
                </div>
            </div>
        </div>
    `;
}

function createMinimalHeader(details) {
    return `
        <div class="container">
            <div class="row align-items-center">
                <div class="col-md-12 text-center">
                    <h2>${details.teamName}</h2>
                    <p>${details.mascot}</p>
                </div>
            </div>
        </div>
    `;
}