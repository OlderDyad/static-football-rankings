// api/auth/status.js
export default async function handler(req, res) {
    // Set CORS headers with strict origin checking
    const allowedOrigins = ['https://olderdyad.github.io'];
    const origin = req.headers.origin;
    
    if (allowedOrigins.includes(origin)) {
      res.setHeader('Access-Control-Allow-Origin', origin);
      res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
      res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
      res.setHeader('Access-Control-Allow-Credentials', 'true');
    }
  
    // Handle preflight requests
    if (req.method === 'OPTIONS') {
      res.status(200).end();
      return;
    }
  
    try {
      // Add session validation logic here
      const session = await validateSession(req);
      res.status(200).json({ 
        loggedIn: Boolean(session),
        user: session?.user || null
      });
    } catch (error) {
      res.status(401).json({ 
        error: 'Authentication failed',
        details: error.message 
      });
    }
  }
  
  // api/auth/google.js
  export default async function handler(req, res) {
    const allowedOrigins = ['https://olderdyad.github.io'];
    const origin = req.headers.origin;
    
    if (allowedOrigins.includes(origin)) {
      res.setHeader('Access-Control-Allow-Origin', origin);
      res.setHeader('Access-Control-Allow-Credentials', 'true');
    }
  
    try {
      const googleAuthUrl = new URL('https://accounts.google.com/o/oauth2/v2/auth');
      googleAuthUrl.searchParams.append('client_id', process.env.GOOGLE_CLIENT_ID);
      googleAuthUrl.searchParams.append('redirect_uri', process.env.REDIRECT_URI);
      googleAuthUrl.searchParams.append('response_type', 'code');
      googleAuthUrl.searchParams.append('scope', 'profile email');
      // Add state parameter for CSRF protection
      googleAuthUrl.searchParams.append('state', generateSecureState());
  
      res.redirect(googleAuthUrl.toString());
    } catch (error) {
      res.status(500).json({ 
        error: 'Failed to initiate Google OAuth',
        details: error.message 
      });
    }
  }
  
  // api/auth/callback.js
  export default async function handler(req, res) {
    const allowedOrigins = ['https://olderdyad.github.io'];
    const origin = req.headers.origin;
    
    if (allowedOrigins.includes(origin)) {
      res.setHeader('Access-Control-Allow-Origin', origin);
      res.setHeader('Access-Control-Allow-Credentials', 'true');
    }
  
    try {
      // Verify state parameter to prevent CSRF
      if (!verifyState(req.query.state)) {
        throw new Error('Invalid state parameter');
      }
  
      const { code } = req.query;
      if (!code) {
        throw new Error('No authorization code received');
      }
  
      // Exchange code for tokens
      const tokens = await exchangeCodeForTokens(code);
      // Create session
      const session = await createSession(tokens);
      
      res.redirect('/dashboard');
    } catch (error) {
      res.redirect('/login?error=' + encodeURIComponent(error.message));
    }
  }
