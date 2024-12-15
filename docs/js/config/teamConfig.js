// teamConfig.js
export const teamConfig = {
    defaultLogo: '/static-football-rankings/docs/images/default-logo.png',
    baseImagePath: 'https://olderdyad.github.io/hsfootball-images/images/Teams/',
    
    getTeamImagePath(relativePath) {
        if (!relativePath) return this.defaultLogo;
        if (relativePath.startsWith('http')) return relativePath;
        return `${this.baseImagePath}${relativePath}`;
    },

    getStateAbbreviation(state) {
        const stateMap = {
            'Texas': 'TX',
            'Ohio': 'OH',
            // Add more states as needed
        };
        return stateMap[state] || state;
    },

    defaultColors: {
        primary: '#000000',
        secondary: '#FFFFFF',
        tertiary: '#808080'
    }
};