// docs/js/config/teamConfig.js
export const teamConfig = {
    defaultLogo: '/static-football-rankings/images/default-logo.png',
    
    getTeamImagePath: (imageFile) => {
        console.group('Team Image Path Processing');
        console.log('Input image path:', imageFile);

        if (!imageFile) {
            console.log('No image file provided, using default');
            console.groupEnd();
            return teamConfig.defaultLogo;
        }

        let finalPath;
        // Handle paths that start with /images/Teams/ or images/Teams/
        if (imageFile.startsWith('/images/Teams/') || imageFile.startsWith('images/Teams/')) {
            finalPath = `/static-football-rankings/${imageFile.replace(/^\//, '')}`;
            console.log('Path with Teams directory:', finalPath);
        } else if (imageFile.startsWith('/static-football-rankings/')) {
            finalPath = imageFile;
            console.log('Already formatted path:', finalPath);
        } else {
            finalPath = `/static-football-rankings/images/Teams/${imageFile}`;
            console.log('Default path construction:', finalPath);
        }

        console.log('Final image path:', finalPath);
        console.groupEnd();
        return finalPath;
    }
};