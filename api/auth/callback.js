// api/auth/callback.js
export default async function handler(req, res) {
    try {
        const { code } = req.query;
        
        if (!code) {
            throw new Error('No authorization code received');
        }

        // Use permanent domain for redirect
        const redirectUri = 'https://static-football-rankings.vercel.app/api/auth/callback';

        const tokenResponse = await fetch('https://oauth2.googleapis.com/token', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                code,
                client_id: process.env.GOOGLE_CLIENT_ID,
                client_secret: process.env.GOOGLE_CLIENT_SECRET,
                redirect_uri: redirectUri,
                grant_type: 'authorization_code'
            })
        });

        const tokens = await tokenResponse.json();

        if (!tokenResponse.ok) {
            console.error('Token response error:', tokens);
            throw new Error(tokens.error || 'Failed to exchange code for tokens');
        }

        // Get user info
        const userInfoResponse = await fetch('https://www.googleapis.com/oauth2/v2/userinfo', {
            headers: {
                'Authorization': `Bearer ${tokens.access_token}`
            }
        });

        const userInfo = await userInfoResponse.json();

        if (!userInfoResponse.ok) {
            console.error('User info error:', userInfo);
            throw new Error('Failed to get user info');
        }

        // Set cookies
        res.setHeader('Set-Cookie', [
            `auth_token=${tokens.access_token}; Path=/; HttpOnly; Secure; SameSite=None`,
            `user_name=${userInfo.name}; Path=/; Secure; SameSite=None`
        ]);

        // Redirect back to main site
        res.redirect('https://olderdyad.github.io/static-football-rankings/');
    } catch (error) {
        console.error('Callback error:', error);
        res.redirect(`https://olderdyad.github.io/static-football-rankings/?error=${encodeURIComponent(error.message)}`);
    }
}
