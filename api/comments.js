// api/comments.js
let comments = []; // Initialize at module scope

export default async function handler(req, res) {
    // Set CORS headers
    res.setHeader('Access-Control-Allow-Origin', 'https://olderdyad.github.io');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Accept, Authorization');   
    res.setHeader('Access-Control-Allow-Credentials', 'true');

    // Handle preflight
    if (req.method === 'OPTIONS') {
        return res.status(200).end();
    }

    try {
        if (req.method === 'GET') {
            console.log('[DEBUG API] GET request received');
            return res.status(200).json({
                success: true,
                comments: comments
            });
        }

        if (req.method === 'POST') {
            console.log('[DEBUG API] POST request received');
            const { text, author, programName } = req.body;

            if (!text?.trim()) {
                return res.status(400).json({
                    success: false,
                    error: 'Comment text is required'
                });
            }

            const newComment = {
                id: Date.now().toString(),
                text: text.trim(),
                author: author?.trim() || 'Anonymous',
                programName: programName?.trim() || 'General',
                timestamp: new Date().toISOString()
            };

            comments.unshift(newComment);
            console.log('[DEBUG API] New comment added:', newComment);

            return res.status(201).json({
                success: true,
                comment: newComment
            });
        }

        return res.status(405).json({
            success: false,
            error: `Method ${req.method} Not Allowed`
        });
    } catch (error) {
        console.error('[ERROR API]:', error);
        return res.status(500).json({
            success: false,
            error: 'Internal Server Error'
        });
    }
}



