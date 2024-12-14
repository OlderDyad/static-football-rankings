// js/config/teamConfig.js

const GITHUB_PAGES_BASE = 'https://olderdyad.github.io';
const REPO_BASE = '/static-football-rankings';
const IMAGES_REPO = 'hsfootball-images';

export const teamConfig = {
    // Base paths
    repoBase: REPO_BASE,
    imageRepoBase: `${GITHUB_PAGES_BASE}/${IMAGES_REPO}`,
    
    // Default image path
    defaultLogo: `${REPO_BASE}/docs/images/placeholder-image.jpg`,
    
    /**
     * Returns the provided image URL or falls back to default logo
     * @param {string} state - Not used but kept for compatibility
     * @param {string} teamName - Not used but kept for compatibility
     * @param {string} imageFile - Full image URL from JSON
     * @returns {string} Image URL or default logo
     */
    getTeamImagePath: (state, teamName, imageFile) => {
        if (!imageFile) {
            console.log('No image file provided');
            return teamConfig.defaultLogo;
        }
        return imageFile;
    }
};

export default teamConfig;