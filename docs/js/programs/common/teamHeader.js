// js/programs/common/teamHeader.js
export function createTeamHeader(program) {
    const teamDetails = {
        teamName: program.Team,
        city: program.City || '',
        state: program.State,
        mascot: program.Mascot,
        primaryColor: program.PrimaryColor,
        secondaryColor: program.SecondaryColor,
        tertiaryColor: program.TertiaryColor,
        logoPath: program.LogoURL,
        schoolLogoPath: program.School_Logo_URL,
        yearFounded: program.YearFounded,
        conference: program.Conference,
        division: program.Division
    };

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