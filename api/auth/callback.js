// api/auth/callback.js
export default async function handler(req, res) {
    try {
        const { code } = req.query;
        
        if (!code) {
            console.error('No authorization code received');
            return res.redirect('https://olderdyad.github.io/static-football-rankings/?error=no_code');
        }

        // Set CORS headers
        res.setHeader('Access-Control-Allow-Origin', 'https://olderdyad.github.io');
        res.setHeader('Access-Control-Allow-Credentials', 'true');

        // Exchange code for tokens
        const tokenResponse = await fetch('https://oauth2.googleapis.com/token', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                code,
                client_id: process.env.GOOGLE_CLIENT_ID,
                client_secret: process.env.GOOGLE_CLIENT_SECRET,
                redirect_uri: 'https://static-football-rankings.vercel.app/api/auth/callback',
                grant_type: 'authorization_code'
            })
        });

        const tokens = await tokenResponse.json();
        
        if (!tokenResponse.ok) {
            console.error('Token exchange failed:', tokens);
            return res.redirect('https://olderdyad.github.io/static-football-rankings/?error=token_exchange_failed');
        }

        // Get user info
        const userResponse = await fetch('https://www.googleapis.com/oauth2/v2/userinfo', {
            headers: {
                'Authorization': `Bearer ${tokens.access_token}`
            }
        });

        const userData = await userResponse.json();
        
        if (!userResponse.ok) {
            console.error('Failed to get user info:', userData);
            return res.redirect('https://olderdyad.github.io/static-football-rankings/?error=user_info_failed');
        }

        // Set session cookies
        res.setHeader('Set-Cookie', [
            `auth_token=${tokens.access_token}; Path=/; HttpOnly; Secure; SameSite=None`,
            `user_name=${userData.name}; Path=/; Secure; SameSite=None`,
            `user_email=${userData.email}; Path=/; HttpOnly; Secure; SameSite=None`
        ]);

        // Log successful authentication
        console.log('Successfully authenticated user:', userData.email);

        // Redirect back to the application
        res.redirect('https://olderdyad.github.io/static-football-rankings/');
    } catch (error) {
        console.error('Auth callback error:', error);
        res.redirect('https://olderdyad.github.io/static-football-rankings/?error=auth_failed');
    }
}
