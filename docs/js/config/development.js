// docs/js/config/development.js
export const isDevelopment = window.location.hostname === 'localhost';

export const mockAuth = {
    isAuthenticated: false,
    user: null,
};

export const endpoints = {
    // Change this to always use the Vercel URL since we're using GitHub Pages
    api: 'https://static-football-rankings.vercel.app',
    auth: {
        status: '/api/auth/status',
        login: '/api/auth/google',
        logout: '/api/auth/logout'
    }
};