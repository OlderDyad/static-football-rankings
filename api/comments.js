// api/comments.js

// Simple in-memory storage for comments (will reset on server restart)
let comments = [];

export default async function handler(req, res) {
    // Set CORS headers
    res.setHeader('Access-Control-Allow-Origin', 'https://olderdyad.github.io');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    // Handle preflight requests
    if (req.method === 'OPTIONS') {
        res.status(200).end();
        return;
    }

    if (req.method === 'GET') {
        // Return all comments
        return res.status(200).json(comments);
    }

    if (req.method === 'POST') {
        try {
            const { text, author, programName } = req.body;
            
            // Validate required fields
            if (!text) {
                return res.status(400).json({ error: 'Comment text is required' });
            }

            // Create new comment
            const newComment = {
                id: Date.now(), // Simple unique ID
                text,
                author: author || 'Anonymous',
                programName: programName || 'General',
                timestamp: new Date().toISOString()
            };

            // Add to storage
            comments.push(newComment);

            // Return success
            return res.status(201).json(newComment);
        } catch (error) {
            console.error('Error creating comment:', error);
            return res.status(500).json({ error: 'Error creating comment' });
        }
    }

    // Handle unsupported methods
    res.setHeader('Allow', ['GET', 'POST', 'OPTIONS']);
    res.status(405).json({ error: `Method ${req.method} Not Allowed` });
}

