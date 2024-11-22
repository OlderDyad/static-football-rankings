// api/auth/google.js
export default async function handler(req, res) {
  try {
      // Set CORS headers
      res.setHeader('Access-Control-Allow-Origin', 'https://olderdyad.github.io');
      res.setHeader('Access-Control-Allow-Credentials', 'true');

      // Handle preflight
      if (req.method === 'OPTIONS') {
          res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
          res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
          return res.status(200).end();
      }

      const clientId = process.env.GOOGLE_CLIENT_ID;
      if (!clientId) {
          throw new Error('Google Client ID not configured');
      }

      // Explicitly set the redirect URI
      const redirectUri = 'https://static-football-rankings.vercel.app/api/auth/callback';
      
      // Construct the Google OAuth URL
      const params = new URLSearchParams({
          client_id: clientId,
          redirect_uri: redirectUri,
          response_type: 'code',
          scope: 'email profile openid',
          access_type: 'offline',
          state: Buffer.from(Date.now().toString()).toString('base64'),
          prompt: 'consent'
      });

      const googleAuthUrl = `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`;
      console.log('Redirecting to:', googleAuthUrl);
      
      // Redirect to Google's OAuth page
      res.redirect(googleAuthUrl);
  } catch (error) {
      console.error('Google auth error:', error);
      res.redirect('https://olderdyad.github.io/static-football-rankings/?error=auth_configuration');
  }
}
