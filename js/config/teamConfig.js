// js/config/teamConfig.js
export const REPO_BASE = '/static-football-rankings';

export const teamConfig = {
    imagePath: `${REPO_BASE}/docs/images/teams`,
    defaultLogo: `${REPO_BASE}/docs/images/placeholder-image.jpg`,

    getTeamImagePath: (state, teamName, imageFile) => {
        if (!imageFile) {
            return teamConfig.defaultLogo;
        }

        // Remove parentheses from state
        const cleanState = state.replace(/[()]/g, '');

        // Remove parenthetical parts and spaces from team name if needed:
        // For example: "Cincinnati Archbishop Moeller (OH)" -> "CincinnatiArchbishopMoeller"
        let cleanTeam = teamName.replace(/\(.*?\)/g, '').trim();
        cleanTeam = cleanTeam.replace(/\s+/g, '');

        // Remove "images/Teams/" prefix from imageFile if present
        const cleanImageFile = imageFile
            .replace(/^images\/Teams\//i, '')
            .replace(/^\//, '');

        return `${teamConfig.imagePath}/${cleanState}/${cleanTeam}/${cleanImageFile}`;
    }
};
