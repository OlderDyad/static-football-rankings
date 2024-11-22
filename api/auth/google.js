// api/auth/google.js
export default async function handler(req, res) {
  const clientId = process.env.GOOGLE_CLIENT_ID;
  // Update callback URL to point to the Vercel API endpoint
  const redirectUri = 'https://static-football-rankings.vercel.app/api/auth/callback';
  
  const googleAuthUrl = new URL('https://accounts.google.com/o/oauth2/v2/auth');
  googleAuthUrl.searchParams.append('client_id', clientId);
  googleAuthUrl.searchParams.append('redirect_uri', redirectUri);
  googleAuthUrl.searchParams.append('response_type', 'code');
  googleAuthUrl.searchParams.append('scope', 'email profile');
  googleAuthUrl.searchParams.append('prompt', 'select_account');
  
  // Add state parameter for security
  const state = Buffer.from(Date.now().toString()).toString('base64');
  googleAuthUrl.searchParams.append('state', state);
  
  res.setHeader('Access-Control-Allow-Origin', 'https://olderdyad.github.io');
  res.setHeader('Access-Control-Allow-Credentials', 'true');
  
  res.redirect(googleAuthUrl.toString());
}
