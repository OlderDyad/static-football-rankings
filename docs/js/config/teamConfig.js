// teamConfig.js - improved version with more robust path handling
export const teamConfig = {
    // Default values - use absolute path
    defaultLogo: '/static-football-rankings/images/default-logo.png',
    
    // Get the correct path for team images with better handling
    getTeamImagePath: function(path) {
        if (!path) return this.defaultLogo;
        
        try {
            console.debug("Original path:", path);
            
            // Remove any leading/trailing whitespace
            let cleanPath = path.trim();
            
            // If it already has the full prefix, return as is
            if (cleanPath.startsWith('/static-football-rankings/')) {
                return cleanPath;
            }
            
            // Build the absolute path
            let fullPath;
            if (cleanPath.startsWith('/')) {
                fullPath = '/static-football-rankings' + cleanPath;
            } 
            else {
                fullPath = '/static-football-rankings/' + cleanPath;
            }
            
            console.debug(`Processed image path: ${path} → ${fullPath}`);
            return fullPath;
        } catch (error) {
            console.error("Error processing image path:", error);
            return this.defaultLogo;
        }
    },
    
    normalizeTeamName: function(name) {
        if (!name) return '';
        return name.trim();
    }
};