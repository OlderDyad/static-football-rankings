// js/config/teamConfig.js

// Define base URLs for different environments
const GITHUB_PAGES_BASE = 'https://olderdyad.github.io';
const REPO_BASE = '/static-football-rankings';
const IMAGES_REPO = 'hsfootball-images';

export const teamConfig = {
    // Base paths
    repoBase: REPO_BASE,
    imageRepoBase: `${GITHUB_PAGES_BASE}/${IMAGES_REPO}`,
    
    // Image paths
    imagePath: `${GITHUB_PAGES_BASE}/${IMAGES_REPO}/images/teams`,
    defaultLogo: `${REPO_BASE}/docs/images/placeholder-image.jpg`,
    
    /**
     * Constructs the full image path for team assets
     * @param {string} state - Team's state (with or without parentheses)
     * @param {string} teamName - Full team name
     * @param {string} imageFile - Image filename or path
     * @returns {string} Complete URL to the image
     */
    getTeamImagePath: (state, teamName, imageFile) => {
        if (!imageFile) return teamConfig.defaultLogo;
        
        // Clean up state (remove parentheses)
        const cleanState = state.replace(/[()]/g, '');
        
        // Clean up team name (remove state suffix if present)
        const cleanTeamName = teamName.replace(/\s+\([A-Z]{2}\)$/, '');
        
        // Clean up image file path (remove any existing path prefixes)
        const cleanImageFile = imageFile
            .replace(/^.*images\/Teams\//i, '') // Remove any path prefix up to images/Teams/
            .replace(/^.*Teams\//i, '')         // Remove any path prefix up to Teams/
            .replace(/^\//, '');                // Remove leading slash if present
        
        // Construct the full URL
        return `${teamConfig.imagePath}/${cleanState}/${cleanTeamName}/${cleanImageFile}`;
    },
    
    /**
     * Validates if an image URL matches the expected pattern
     * @param {string} url - Image URL to validate
     * @returns {boolean} True if URL matches expected pattern
     */
    isValidImageUrl: (url) => {
        if (!url) return false;
        
        // Check if URL matches either the GitHub Pages pattern or the local pattern
        const githubPagesPattern = new RegExp(`^${GITHUB_PAGES_BASE}/${IMAGES_REPO}/images/teams/[A-Z]{2}/[^/]+/[^/]+$`);
        const localPattern = new RegExp(`^${REPO_BASE}/docs/images/teams/[A-Z]{2}/[^/]+/[^/]+$`);
        
        return githubPagesPattern.test(url) || localPattern.test(url);
    },
    
    /**
     * Extracts team information from an image path
     * @param {string} url - Image URL to parse
     * @returns {Object} Object containing state and teamName, or null if invalid
     */
    parseImagePath: (url) => {
        if (!url) return null;
        
        // Try to match either GitHub Pages or local pattern
        const githubPattern = new RegExp(`${GITHUB_PAGES_BASE}/${IMAGES_REPO}/images/teams/([A-Z]{2})/([^/]+)/`);
        const localPattern = new RegExp(`${REPO_BASE}/docs/images/teams/([A-Z]{2})/([^/]+)/`);
        
        const match = url.match(githubPattern) || url.match(localPattern);
        
        if (match) {
            return {
                state: match[1],
                teamName: match[2]
            };
        }
        
        return null;
    }
};

// Export additional constants that might be useful
export const CONSTANTS = {
    GITHUB_PAGES_BASE,
    REPO_BASE,
    IMAGES_REPO
};

export default teamConfig;