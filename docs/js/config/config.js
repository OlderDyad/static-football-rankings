// docs/js/config/config.js
export const config = {
    isProduction: window.location.hostname !== 'localhost',
    basePath: window.location.hostname === 'localhost' ? '' : '/static-football-rankings',
    
    paths: {
        data: '/data',
        images: '/docs/images',
        scripts: '/docs/js'
    },

    getPath(type, file) {
        const base = this.isProduction ? this.basePath : '';
        const pathPrefix = this.paths[type] || '';
        return `${base}${pathPrefix}/${file}`;
    }
};