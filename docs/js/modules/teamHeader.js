import { teamConfig } from '../config/teamConfig.js';

function verifyImagePath(src, type = 'logo') {
    const img = new Image();
    img.onload = () => console.log(`✅ ${type} loaded successfully:`, src);
    img.onerror = () => console.error(`❌ ${type} failed to load:`, src);
    img.src = src;
}

export function createTeamHeader(topItem) {
    if (!topItem) {
        console.warn('No top item data provided');
        return;
    }

    console.group('Team Header Creation');
    console.log('Top item data:', topItem);

    const logoPath = teamConfig.getTeamImagePath(topItem.LogoURL);
    const schoolLogoPath = teamConfig.getTeamImagePath(topItem.School_Logo_URL);

    // Verify both image paths
    verifyImagePath(logoPath, 'Team logo');
    verifyImagePath(schoolLogoPath, 'School logo');

    console.log('Creating header with top item:', topItem);

    const headerContainer = document.getElementById('teamHeaderContainer');
    if (!headerContainer) {
        console.warn('Team header container not found');
        return;
    }

    const headerHtml = `
        <div class="team-header" style="background-color: ${topItem.backgroundColor || '#FFFFFF'}; color: ${topItem.textColor || '#000000'};">
            <div class="container">
                <div class="row align-items-center">
                    <div class="col-md-3 text-center">
                        <img src="${teamConfig.getTeamImagePath(topItem.LogoURL)}"
                             alt="${topItem.program || topItem.team || 'Team'} Logo"
                             class="img-fluid team-logo"
                             onerror="this.src='${teamConfig.defaultLogo}'; this.classList.add('default-logo');" />
                    </div>
                    <div class="col-md-6 text-center">
                        <h2>${topItem.program || topItem.team || 'Unknown Team'}</h2>
                        ${topItem.mascot ? `<p class="mascot-name">${topItem.mascot}</p>` : ''}
                    </div>
                    <div class="col-md-3 text-center">
                        <img src="${teamConfig.getTeamImagePath(topItem.School_Logo_URL)}"
                             alt="${topItem.program || topItem.team || 'School'} School Logo"
                             class="img-fluid school-logo"
                             onerror="this.src='${teamConfig.defaultLogo}'; this.classList.add('default-logo');" />
                    </div>
                </div>
            </div>
        </div>
    `;

    headerContainer.innerHTML = headerHtml;
    console.log('Header created and inserted');
}
