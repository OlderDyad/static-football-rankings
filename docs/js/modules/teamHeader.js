// C:\Users\demck\OneDrive\Football_2024\static-football-rankings\docs\js\programs\common\teamHeader.js

// docs/js/modules/teamHeader.js
import { teamConfig } from '../config/teamConfig.js';
import { DEBUG_LEVELS, log } from './logger.js';

export function createTeamHeader(program) {
    log(DEBUG_LEVELS.DEBUG, 'createTeamHeader received program:', {
        fullObject: program,
        team: program.team,
        LogoURL: program.LogoURL,
        School_Logo_URL: program.School_Logo_URL,
        backgroundColor: program.backgroundColor,
        textColor: program.textColor
    });

    const teamDetails = {
        teamName: program.team || 'Unknown Team',
        city: program.city || '',
        state: program.state || '',
        mascot: program.mascot || '',
        primaryColor: program.backgroundColor || '#000000',
        secondaryColor: program.textColor || '#FFFFFF',
        tertiaryColor: program.tertiaryColor || '',
        logoPath: program.LogoURL,             // Direct URL from JSON
        schoolLogoPath: program.School_Logo_URL // Direct URL from JSON
    };

    log(DEBUG_LEVELS.DEBUG, 'Processed teamDetails:', teamDetails);

    // Get image URLs
    const logoUrl = teamDetails.logoPath || teamConfig.defaultLogo;
    const schoolLogoUrl = teamDetails.schoolLogoPath || teamConfig.defaultLogo;

    log(DEBUG_LEVELS.DEBUG, 'Final image URLs:', { logoUrl, schoolLogoUrl });

    // Changed to return inner content only, since container exists in HTML
    return `
        <div class="container">
            <div class="row align-items-center">
                <div class="col-md-3">
                    <img src="${logoUrl}"
                         alt="${teamDetails.teamName} Logo"
                         class="img-fluid"
                         style="max-height: 100px;"
                         onerror="this.src='${teamConfig.defaultLogo}'" />
                </div>
                <div class="col-md-6 text-center">
                    <h2>${teamDetails.teamName}</h2>
                    <p>${teamDetails.mascot}</p>
                </div>
                <div class="col-md-3 text-right">
                    <img src="${schoolLogoUrl}"
                         alt="${teamDetails.mascot}"
                         class="img-fluid"
                         style="max-height: 100px;"
                         onerror="this.src='${teamConfig.defaultLogo}'" />
                </div>
            </div>
        </div>
    `;
}
