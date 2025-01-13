// docs/js/modules/teamHeader.js
import { teamConfig } from '../config/teamConfig.js';

export function createTeamHeader(program) {
    if (!program) {
        console.log('No program data provided for header');
        return '';
    }

    const teamDetails = {
        teamName: program.team || program.program || 'Unknown Team',
        mascot: program.mascot || '',
        primaryColor: program.backgroundColor || '#FFFFFF',
        secondaryColor: program.textColor || '#000000',
        logoPath: program.LogoURL || '',
        schoolLogoPath: program.School_Logo_URL || ''
    };

    console.log('Creating header for:', teamDetails.teamName);

    // Process image paths using teamConfig
    const logoImgSrc = teamConfig.getTeamImagePath(teamDetails.logoPath);
    const schoolLogoImgSrc = teamConfig.getTeamImagePath(teamDetails.schoolLogoPath);

    console.log('Logo path:', logoImgSrc);
    console.log('School logo path:', schoolLogoImgSrc);

    const headerHtml = `
        <div class="team-header" style="background-color: ${teamDetails.primaryColor}; color: ${teamDetails.secondaryColor};">
            <div class="container">
                <div class="row align-items-center">
                    <div class="col-md-3 text-center">
                        <img src="${logoImgSrc}"
                             alt="${teamDetails.teamName} Logo"
                             class="img-fluid team-logo"
                             onerror="this.src='${teamConfig.defaultLogo}'; this.classList.add('default-logo');" />
                    </div>
                    <div class="col-md-6 text-center">
                        <h2>${teamDetails.teamName}</h2>
                        ${teamDetails.mascot ? `<p class="mascot-name">${teamDetails.mascot}</p>` : ''}
                    </div>
                    <div class="col-md-3 text-center">
                        <img src="${schoolLogoImgSrc}"
                             alt="${teamDetails.teamName} School Logo"
                             class="img-fluid school-logo"
                             onerror="this.src='${teamConfig.defaultLogo}'; this.classList.add('default-logo');" />
                    </div>
                </div>
            </div>
        </div>
    `;

    // Find the container and insert the header
    const headerContainer = document.getElementById('teamHeaderContainer');
    if (headerContainer) {
        headerContainer.innerHTML = headerHtml;
    } else {
        console.warn('Team header container not found');
    }
}
