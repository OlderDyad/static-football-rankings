// config.js
const config = {
    development: {
        webv2BasePath: '/webv2',  // Changed to relative path
        imagesPath: '/images',
        useLocalImages: false
    },
    production: {
        webv2BasePath: '', 
        imagesPath: '/images',
        useLocalImages: true
    }
};

// Export the development configuration
const currentConfig = config.development;
