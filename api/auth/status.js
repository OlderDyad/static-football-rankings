import fetch from 'node-fetch';

export default async function handler(req, res) {
  // CORS
  res.setHeader('Access-Control-Allow-Origin', 'https://olderdyad.github.io');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  res.setHeader('Access-Control-Allow-Credentials', 'true');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  try {
    const authToken = req.cookies?.auth_token;
    const userName = req.cookies?.user_name;

    // If no auth_token, user is not logged in
    if (!authToken) {
      return res.status(200).json({
        success: true,
        loggedIn: false,
        user: null
      });
    }

    // Verify token with Google
    const userResponse = await fetch('https://www.googleapis.com/oauth2/v2/userinfo', {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });

    if (!userResponse.ok) {
      // token is invalid, clear cookies
      res.setHeader('Set-Cookie', [
        'auth_token=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT; HttpOnly; Secure; SameSite=None',
        'user_name=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT; Secure; SameSite=None',
        'user_email=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT; HttpOnly; Secure; SameSite=None'
      ]);

      return res.status(200).json({
        success: true,
        loggedIn: false,
        user: null
      });
    }

    const userData = await userResponse.json();

    // Return user info
    return res.status(200).json({
      success: true,
      loggedIn: true,
      user: {
        name: userName || userData.name,
        email: userData.email
      }
    });
  } catch (error) {
    console.error('Auth status error:', error);
    return res.status(500).json({
      success: false,
      error: 'Internal server error'
    });
  }
}
