// api/auth/google.js
import { URL } from 'url';

export default async function handler(req, res) {
    console.log('Google auth handler started');
    
    try {
        // Set CORS headers
        res.setHeader('Access-Control-Allow-Origin', 'https://olderdyad.github.io');
        res.setHeader('Access-Control-Allow-Credentials', 'true');
        res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
        res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

        // Handle preflight
        if (req.method === 'OPTIONS') {
            return res.status(200).end();
        }

        // Verify environment variables
        const clientId = process.env.GOOGLE_CLIENT_ID;
        if (!clientId) {
            console.error('Missing GOOGLE_CLIENT_ID environment variable');
            return res.status(500).json({
                error: 'OAuth configuration error',
                details: 'Missing client configuration'
            });
        }

        // Configure OAuth parameters
        const redirectUri = 'https://static-football-rankings.vercel.app/api/auth/callback';
        const scope = ['email', 'profile', 'openid'].join(' ');
        const state = Buffer.from(Date.now().toString()).toString('base64');

        // Construct auth URL
        const authUrl = new URL('https://accounts.google.com/o/oauth2/v2/auth');
        authUrl.searchParams.append('client_id', clientId);
        authUrl.searchParams.append('redirect_uri', redirectUri);
        authUrl.searchParams.append('response_type', 'code');
        authUrl.searchParams.append('scope', scope);
        authUrl.searchParams.append('access_type', 'offline');
        authUrl.searchParams.append('prompt', 'consent');
        authUrl.searchParams.append('state', state);

        console.log('Redirecting to:', authUrl.toString());
        
        // Redirect to Google
        res.redirect(authUrl.toString());
    } catch (error) {
        console.error('Google auth error:', error);
        return res.status(500).json({
            error: 'Internal server error',
            details: process.env.NODE_ENV === 'development' ? error.message : undefined
        });
    }
}
