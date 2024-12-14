// C:\Users\demck\OneDrive\Football_2024\static-football-rankings\docs\js\programs\common\teamHeader.js

import teamConfig from '../config/teamConfig.js';

export function createTeamHeader(program) {
    // Debug incoming data
    console.log('Creating header for program:', program);

    const teamDetails = {
        teamName: program.team || 'Unknown Team',
        city: program.city || '',
        state: program.state || '',
        mascot: program.mascot || '',
        primaryColor: program.backgroundColor || '#000000',
        secondaryColor: program.textColor || '#FFFFFF',
        tertiaryColor: program.tertiaryColor || '',
        logoPath: program.LogoURL || '',
        schoolLogoPath: program.School_Logo_URL || '',
        yearFounded: program.yearFounded || '',
        conference: program.conference || '',
        division: program.division || ''
    };

    // Debug processed details
    console.log('Team details:', {
        name: teamDetails.teamName,
        logoPath: teamDetails.logoPath,
        schoolLogoPath: teamDetails.schoolLogoPath
    });

    const headerHtml = `
        <div class="team-header" style="background-color: ${teamDetails.primaryColor}; color: ${teamDetails.secondaryColor};">
            <div class="container">
                <div class="row align-items-center">
                    <div class="col-md-3">
                        <img src="${teamConfig.getTeamImagePath(null, null, teamDetails.logoPath)}"
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
                        <img src="${teamConfig.getTeamImagePath(null, null, teamDetails.schoolLogoPath)}"
                             alt="${teamDetails.mascot}"
                             class="img-fluid"
                             style="max-height: 100px;"
                             onerror="this.src='${teamConfig.defaultLogo}'" />
                    </div>
                </div>
            </div>
        </div>
    `;

    // Debug generated HTML
    console.log('Generated header HTML for', teamDetails.teamName);

    return headerHtml;
}
