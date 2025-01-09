// js/config/teamConfig.js
export const teamConfig = {
    imagePath: '/static-football-rankings/docs/images/teams',  // Changed 'Teams' to 'teams'
    defaultLogo: '/static-football-rankings/docs/images/placeholder-image.jpg',
    
    getTeamImagePath: (imageFile) => {
        if (!imageFile) {
            console.log('No image file provided');
            return teamConfig.defaultLogo;
        }

        // If imageFile already starts with "images/Teams", remove it and lowercase "teams"
        const cleanPath = imageFile.replace(/^images\/Teams\//i, '');
        
        // Construct the full path
        const fullPath = `${teamConfig.imagePath}/${cleanPath}`;
        console.log('Loading image from:', fullPath);
        
        return fullPath;
    }
};

