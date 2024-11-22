// api/comments.js
const comments = [];

export default async function handler(req, res) {
    // Set CORS headers immediately
    res.setHeader('Access-Control-Allow-Origin', 'https://olderdyad.github.io');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Accept, Authorization');
    res.setHeader('Access-Control-Allow-Credentials', 'true');

    // Handle preflight request
    if (req.method === 'OPTIONS') {
        return res.status(200).end();
    }

    try {
        if (req.method === 'GET') {
            return res.status(200).json({
                success: true,
                comments: comments
            });
        }

        if (req.method === 'POST') {
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
        console.error('API Error:', error);
        return res.status(500).json({
            success: false,
            error: 'Internal Server Error'
        });
    }
}

// Optional: Add type definitions for better code organization
/**
 * @typedef {Object} Comment
 * @property {string} id - Unique identifier
 * @property {string} text - Comment content
 * @property {string} author - Comment author
 * @property {string} programName - Associated program
 * @property {string} timestamp - ISO timestamp
 */

/**
 * @typedef {Object} ApiResponse
 * @property {boolean} success - Operation success status
 * @property {Comment[] | Comment} [comments] - Array of comments or single comment
 * @property {string} [error] - Error message if success is false
 */




