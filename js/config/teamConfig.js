// js/config/teamConfig.js
export const teamConfig = {
    imagePath: '/static-football-rankings/docs/images/Teams',  // Note: 'Teams' with capital T to match DB
    defaultLogo: '/static-football-rankings/docs/images/placeholder-image.jpg',
    
    getTeamImagePath: (imageFile) => {
        if (!imageFile) {
            return teamConfig.defaultLogo;
        }

        // If imageFile already starts with "images/Teams", remove it to avoid duplication
        const cleanPath = imageFile.replace(/^images\/Teams\//i, '');
        
        // Construct the full path
        return `${teamConfig.imagePath}/${cleanPath}`;
    }
};

