// docs/js/modules/auth.js

export const auth = {
    apiBase: '/static-football-rankings/api',

    async checkStatus() {
        try {
            const response = await fetch(`${this.apiBase}/auth/status`, {
                method: 'GET',
                credentials: 'include'
            });
            const data = await response.json();

            if (data.success && data.loggedIn) {
                return {
                    loggedIn: true,
                    user: data.user
                };
            } else {
                return {
                    loggedIn: false,
                    user: null
                };
            }
        } catch (error) {
            console.error('Auth status check failed:', error);
            return {
                loggedIn: false,
                user: null,
                error: error.message
            };
        }
    },

    login() {
        window.location.href = `${this.apiBase}/auth/google`;
    },

    logout() {
        const options = 'Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT; Secure; SameSite=None;';
        document.cookie = `auth_token=; ${options}`;
        document.cookie = `user_name=; ${options}`;
        document.cookie = `user_email=; ${options}`;
        window.location.reload();
    }
};

export default auth;