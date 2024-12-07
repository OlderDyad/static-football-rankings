// js/config/teamConfig.js
export const teamConfig = {
    imagePath: '/static-football-rankings/docs/images',
    defaultLogo: '/static-football-rankings/docs/images/placeholder-image.jpg',
    
    getTeamImagePath: (imageFile) => {
        if (!imageFile) {
            return teamConfig.defaultLogo;
        }

        // imageFile should already be the correct path from the database
        // Just prepend the repository base path
        return `${teamConfig.imagePath}${imageFile}`; 
    }
};

