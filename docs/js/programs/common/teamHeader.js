// js/programs/common/teamHeader.js
import { teamConfig } from '../config/teamConfig.js';

export function createTeamHeader(program) {
    const teamDetails = {
        teamName: program.team,  // Changed from Team to team
        city: program.city || '',
        state: program.state,    // Changed from State to state
        mascot: program.mascot,  // Changed from Mascot to mascot
        primaryColor: program.backgroundColor, // Changed to match JSON
        secondaryColor: program.textColor,     // Changed to match JSON
        tertiaryColor: program.tertiaryColor,
        logoPath: program.LogoURL,            // This matches JSON
        schoolLogoPath: program.School_Logo_URL, // This matches JSON
        yearFounded: program.yearFounded,
        conference: program.conference,
        division: program.division
    };

    console.log('Team Details:', teamDetails); // Add debugging

    const headerHtml = `
        <div class="team-header" style="background-color: ${teamDetails.primaryColor}; color: ${teamDetails.secondaryColor};">
            <div class="container">
                <div class="row align-items-center">
                    <div class="col-md-3">
                        <img src="${teamDetails.logoPath}"
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
                        <img src="${teamDetails.schoolLogoPath}"
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