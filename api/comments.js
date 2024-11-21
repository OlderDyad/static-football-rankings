// comments.js
import { MongoClient } from 'mongodb';
// or for simplicity, keep using in-memory storage
const comments = [];

export default async function handler(req, res) {
    // Set CORS headers first
    const corsHeaders = {
        'Access-Control-Allow-Origin': 'https://olderdyad.github.io',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Accept, Authorization',
        'Access-Control-Allow-Credentials': 'true'
    };

    // Apply CORS headers to all responses
    Object.entries(corsHeaders).forEach(([key, value]) => {
        res.setHeader(key, value);
    });

    // Handle OPTIONS request
    if (req.method === 'OPTIONS') {
        return res.status(200).end();
    }

    try {
        switch (req.method) {
            case 'GET':
                console.log('GET request - Current comments:', comments);
                return res.status(200).json({ 
                    success: true, 
                    comments: comments 
                });

            case 'POST':
                const { text, author, programName } = req.body;

                // Validate required fields
                if (!text?.trim()) {
                    return res.status(400).json({ 
                        success: false, 
                        error: 'Comment text is required' 
                    });
                }

                // Create new comment
                const newComment = {
                    id: Date.now().toString(),
                    text: text.trim(),
                    author: author?.trim() || 'Anonymous',
                    programName: programName?.trim() || 'General',
                    timestamp: new Date().toISOString()
                };

                // Add to storage
                comments.unshift(newComment); // Add to beginning of array
                
                console.log('POST request - New comment added:', newComment);
                console.log('Current comments count:', comments.length);

                return res.status(201).json({ 
                    success: true, 
                    comment: newComment 
                });

            default:
                res.setHeader('Allow', ['GET', 'POST', 'OPTIONS']);
                return res.status(405).json({ 
                    success: false, 
                    error: `Method ${req.method} Not Allowed` 
                });
        }
    } catch (error) {
        console.error('API Error:', error);
        return res.status(500).json({ 
            success: false, 
            error: 'Internal Server Error',
            details: process.env.NODE_ENV === 'development' ? error.message : undefined
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




