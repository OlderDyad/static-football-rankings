// Create this file at: api/auth/verify-config.js

export default async function handler(req, res) {
    // Set CORS headers first
    res.setHeader('Access-Control-Allow-Origin', 'https://olderdyad.github.io');
    res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    res.setHeader('Access-Control-Allow-Credentials', 'true');

    // Handle preflight
    if (req.method === 'OPTIONS') {
        return res.status(200).end();
    }

    // Verify environment variables
    const config = {
        hasClientId: Boolean(process.env.GOOGLE_CLIENT_ID),
        hasClientSecret: Boolean(process.env.GOOGLE_CLIENT_SECRET),
        clientIdStart: process.env.GOOGLE_CLIENT_ID ? 
            `${process.env.GOOGLE_CLIENT_ID.substring(0, 8)}...` : 'not set',
        timestamp: new Date().toISOString()
    };

    // Return configuration status
    return res.status(200).json({
        success: true,
        config,
        message: 'OAuth Configuration Status'
    });
}