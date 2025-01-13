// js/config/teamConfig.js
export const teamConfig = {
    defaultLogo: '/static-football-rankings/images/default-logo.png',
    imagePath: '/static-football-rankings/images/teams',  // Base path for team images
    
    getTeamImagePath: (imageFile) => {
        if (!imageFile) {
            console.log('No image file provided');
            return teamConfig.defaultLogo;
        }

        // If imageFile already starts with "images/Teams", remove it and lowercase "teams"
        const cleanPath = imageFile.replace(/^images\/Teams\//i, '');
        
        // If path starts with a slash, append it to the base static-football-rankings path
        if (cleanPath.startsWith('/')) {
            const fullPath = `/static-football-rankings${cleanPath}`;
            console.log('Loading absolute path image from:', fullPath);
            return fullPath;
        }
        
        // Otherwise construct the full path using the imagePath
        const fullPath = `${teamConfig.imagePath}/${cleanPath}`;
        console.log('Loading relative path image from:', fullPath);
        return fullPath;
    }
};

