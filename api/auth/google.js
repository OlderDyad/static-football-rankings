// api/auth/google.js
export default async function handler(req, res) {
    try {
        res.setHeader('Access-Control-Allow-Origin', 'https://olderdyad.github.io');
        res.setHeader('Access-Control-Allow-Credentials', 'true');

        if (req.method === 'OPTIONS') {
            res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
            res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
            return res.status(200).end();
        }

        const redirectUri = 'https://static-football-rankings.vercel.app/api/auth/callback';
        
        const params = new URLSearchParams({
            client_id: process.env.GOOGLE_CLIENT_ID,
            redirect_uri: redirectUri,
            response_type: 'code',
            scope: 'email profile openid',
            access_type: 'offline',
            state: Buffer.from(Date.now().toString()).toString('base64'),
            prompt: 'consent'
        });

        const googleAuthUrl = `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`;
        console.log('Redirecting to Google OAuth:', googleAuthUrl);
        
        res.redirect(googleAuthUrl);
    } catch (error) {
        console.error('Google auth error:', error);
        res.redirect('https://olderdyad.github.io/static-football-rankings/?error=auth_configuration');
    }
}

        const googleAuthUrl = `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`;
        console.log('Redirecting to Google OAuth:', googleAuthUrl);
        
        res.redirect(googleAuthUrl);
    } catch (error) {
        console.error('Google auth error:', error);
        res.redirect('https://olderdyad.github.io/static-football-rankings/?error=auth_configuration');
    }
}
