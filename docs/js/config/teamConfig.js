// js/config/teamConfig.js
export const REPO_BASE = '/static-football-rankings';

export const teamConfig = {
    imagePath: `${REPO_BASE}/docs/images/teams`,
    defaultLogo: `${REPO_BASE}/docs/images/placeholder-image.jpg`,
    
    getTeamImagePath: (state, teamName, imageFile) => {
        // Clean up state (remove parentheses)
        const cleanState = state.replace(/[()]/g, '');
        
        // Clean up image file path (remove any existing path prefixes)
        const cleanImageFile = imageFile.replace(/^images\/Teams\//i, '')
                                      .replace(/^\//, '');
                                      
        return `${teamConfig.imagePath}/${cleanState}/${teamName}/${cleanImageFile}`;
    }
};