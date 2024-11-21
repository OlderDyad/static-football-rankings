// api/auth/google.js
export default function handler(req, res) {
    const googleAuthUrl = `https://accounts.google.com/o/oauth2/v2/auth?
      client_id=${process.env.GOOGLE_CLIENT_ID}&
      redirect_uri=${process.env.REDIRECT_URI}&
      response_type=code&
      scope=profile email`;
    
    res.redirect(googleAuthUrl);
  }