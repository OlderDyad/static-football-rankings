// api/auth/callback.js
export default async function handler(req, res) {
    try {
        const { code, state } = req.query;
        
        if (!code) {
            throw new Error('No authorization code received');
        }

        // Exchange code for tokens
        const tokenResponse = await fetch('https://oauth2.googleapis.com/token', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                code,
                client_id: process.env.GOOGLE_CLIENT_ID,
                client_secret: process.env.GOOGLE_CLIENT_SECRET,
                redirect_uri: 'https://static-football-rankings.vercel.app/api/auth/callback',
                grant_type: 'authorization_code',
            }),
        });

        const tokens = await tokenResponse.json();

        if (!tokenResponse.ok) {
            throw new Error(tokens.error || 'Failed to exchange code for tokens');
        }

        // Get user info
        const userResponse = await fetch('https://www.googleapis.com/oauth2/v2/userinfo', {
            headers: {
                'Authorization': `Bearer ${tokens.access_token}`,
            },
        });

        const userData = await userResponse.json();

        if (!userResponse.ok) {
            throw new Error('Failed to get user info');
        }

        // Set session cookie
        res.setHeader('Set-Cookie', `session=${tokens.access_token}; Path=/; HttpOnly; Secure; SameSite=None`);

        // Redirect back to the main site
        res.redirect('https://olderdyad.github.io/static-football-rankings/');
    } catch (error) {
        console.error('Auth callback error:', error);
        res.redirect('https://olderdyad.github.io/static-football-rankings/?error=auth_failed');
    }
}
