export default async function handler(req, res) {
    res.setHeader('Access-Control-Allow-Origin', 'https://olderdyad.github.io');
    res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    res.setHeader('Access-Control-Allow-Credentials', 'true');
  
    if (req.method === 'OPTIONS') {
      return res.status(200).end();
    }
  
    const config = {
      hasClientId: Boolean(process.env.GOOGLE_CLIENT_ID),
      hasClientSecret: Boolean(process.env.GOOGLE_CLIENT_SECRET),
      clientIdStart: process.env.GOOGLE_CLIENT_ID
        ? `${process.env.GOOGLE_CLIENT_ID.substring(0, 8)}...`
        : 'not set',
      timestamp: new Date().toISOString()
    };
  
    return res.status(200).json({
      success: true,
      config,
      message: 'OAuth Configuration Status'
    });
  }
  