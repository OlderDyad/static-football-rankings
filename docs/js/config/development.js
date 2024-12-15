// docs/js/config/development.js
export const isDevelopment = window.location.hostname === 'localhost';

export const mockAuth = {
    isAuthenticated: false,
    user: null,
    // Optional: Add mock user for testing logged-in state
    // user: {
    //     email: 'test@example.com',
    //     name: 'Test User'
    // }
};

export const endpoints = {
    api: isDevelopment ? 'http://localhost:5001/api' : '/api',
    auth: {
        status: '/auth/status',
        login: '/auth/google',
        logout: '/auth/logout'
    }
};