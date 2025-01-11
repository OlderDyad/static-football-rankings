//C:\Users\demck\OneDrive\Football_2024\static-football-rankings\docs\js\modules\teamHeader.js

import teamConfig from '../config/teamConfig.js'; // Ensure the correct relative path

export function createTeamHeader(program) {
    const teamDetails = {
        teamName: program.team || 'Unknown Team',
        city: program.city || '',
        state: program.state || '',
        mascot: program.mascot || '',
        primaryColor: program.backgroundColor || '#FFFFFF', // Default to white if not specified
        secondaryColor: program.textColor || '#000000', // Default to black if not specified
        tertiaryColor: program.tertiaryColor || '',
        logoPath: program.LogoURL || '', // Will use defaultLogo if empty
        schoolLogoPath: program.School_Logo_URL || '', // Will use defaultLogo if empty
        yearFounded: program.yearFounded || '',
        conference: program.conference || '',
        division: program.division || ''
    };

    // Debugging: Log teamDetails to verify property values
    console.log('Rendering team header for:', teamDetails.teamName);
    console.log('LogoURL:', teamDetails.logoPath);
    console.log('SchoolLogoURL:', teamDetails.schoolLogoPath);

    // Determine image sources using teamConfig
    const logoImgSrc = teamDetails.logoPath 
        ? teamConfig.getTeamImagePath(teamDetails.logoPath)
        : teamConfig.defaultLogo;

    const schoolLogoImgSrc = teamDetails.schoolLogoPath 
        ? teamConfig.getTeamImagePath(teamDetails.schoolLogoPath)
        : teamConfig.defaultLogo;

    const headerHtml = `
        <div class="team-header" style="background-color: ${teamDetails.primaryColor}; color: ${teamDetails.secondaryColor};">
            <div class="container">
                <div class="row align-items-center">
                    <div class="col-md-3">
                        <img src="${logoImgSrc}"
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
                        <img src="${schoolLogoImgSrc}"
                             alt="${teamDetails.mascot}"
                             class="img-fluid"
                             style="max-height: 100px;"
                             onerror="this.src='${teamConfig.defaultLogo}'" />
                    </div>
                </div>
            </div>
        </div>
    `;

    return headerHtml;
}
