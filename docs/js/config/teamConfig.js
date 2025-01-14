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

        // Remove any leading slash
        const cleanPath = imageFile.replace(/^\//, '');

        // If path starts with 'images/Teams/', prepend our base path
        if (cleanPath.startsWith('images/Teams/')) {
            const finalPath = `/static-football-rankings/${cleanPath}`;
            console.log('Processed path:', finalPath);
            console.groupEnd();
            return finalPath;
        }

        // Handle paths that don't start with images/Teams/
        // This ensures we still try to find the image in our structure
        const constructedPath = `/static-football-rankings/images/Teams/${cleanPath}`;
        console.log('Constructed path:', constructedPath);
        console.groupEnd();
        return constructedPath;
    }
};