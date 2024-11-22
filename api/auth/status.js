// api/auth/status.js

export default async function handler(req, res) {
    // Set CORS headers first
    const corsHeaders = {
        'Access-Control-Allow-Origin': 'https://olderdyad.github.io',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Accept, Authorization',
        'Access-Control-Allow-Credentials': 'true'
    };

    // Apply CORS headers to all responses
    Object.entries(corsHeaders).forEach(([key, value]) => {
        res.setHeader(key, value);
    });

    // Handle preflight request
    if (req.method === 'OPTIONS') {
        return res.status(200).end();
    }

    // Handle the actual request
    if (req.method === 'GET') {
        try {
            // TODO: Add your session verification logic here
            return res.status(200).json({
                success: true,
                loggedIn: false,
                user: null
            });
        } catch (error) {
            console.error('Auth status error:', error);
            return res.status(500).json({
                success: false,
                error: 'Internal server error'
            });
        }
    }

    // Handle invalid methods
    res.setHeader('Allow', ['GET', 'OPTIONS']);
    return res.status(405).json({
        success: false,
        error: `Method ${req.method} Not Allowed`
    });
}