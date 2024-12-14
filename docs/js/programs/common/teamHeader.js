// C:\Users\demck\OneDrive\Football_2024\static-football-rankings\docs\js\programs\common\teamHeader.js

import teamConfig from '../config/teamConfig.js'; // Ensure the correct relative path

export function createTeamHeader(program) {
    const teamDetails = {
        teamName: program.team, // Changed from program.Team to program.team
        city: program.city || '',
        state: program.state, // Changed from program.State to program.state
        mascot: program.mascot, // Changed from program.Mascot to program.mascot
        primaryColor: program.backgroundColor, // Changed from program.PrimaryColor to program.backgroundColor
        secondaryColor: program.textColor, // Changed from program.SecondaryColor to program.textColor
        tertiaryColor: program.tertiaryColor, // Ensure this exists in your JSON or handle accordingly
        logoPath: program.LogoURL, // Assuming LogoURL is correct
        schoolLogoPath: program.School_Logo_URL, // Assuming School_Logo_URL is correct
        yearFounded: program.yearFounded, // Changed from program.YearFounded to program.yearFounded
        conference: program.conference, // Changed from program.Conference to program.conference
        division: program.division // Changed from program.Division to program.division
    };

    // Debugging: Log teamDetails to verify property values
    console.log('Rendering team header for:', teamDetails.teamName);
    console.log('LogoURL:', teamDetails.logoPath);
    console.log('SchoolLogoURL:', teamDetails.schoolLogoPath);

    const headerHtml = `
        <div class="team-header" style="background-color: ${teamDetails.primaryColor}; color: ${teamDetails.secondaryColor};">
            <div class="container">
                <div class="row align-items-center">
                    <div class="col-md-3">
                        <img src="${teamConfig.getTeamImagePath(teamDetails.state, teamDetails.teamName, teamDetails.logoPath)}"
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
                        <img src="${teamConfig.getTeamImagePath(teamDetails.state, teamDetails.teamName, teamDetails.schoolLogoPath)}"
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
