// api/comments.js
import { createClient } from '@vercel/postgres';
import { rateLimit } from '../utils/rateLimit';

    // At the top of docs/api/comments.js
    export default async function handler(req, res) {
        const allowedOrigin = process.env.CORS_ORIGIN || 'https://olderdyad.github.io';
        
        // Set CORS headers
        res.setHeader('Access-Control-Allow-Origin', allowedOrigin);
        res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
        res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
        res.setHeader('Access-Control-Max-Age', '86400'); // 24 hours
    
        // Handle preflight requests
        if (req.method === 'OPTIONS') {
            res.status(200).end();
            return;
        }

    // Apply rate limiting
    try {
        await rateLimit(req, res);
    } catch (error) {
        return res.status(429).json({ error: 'Too many requests' });
    }

    if (req.method === 'POST') {
        return handlePostComment(req, res);
    } else if (req.method === 'GET') {
        return handleGetComments(req, res);
    }
  
    res.status(405).json({ error: 'Method not allowed' });
}

async function handlePostComment(req, res) {
    const client = createClient();
  
    try {
        await client.connect();
    
        const { text, programName, parentId, author } = JSON.parse(req.body);
    
        // Verify email token if provided
        if (author.emailToken) {
            const verified = await verifyEmailToken(author.emailToken);
            if (!verified) {
                return res.status(401).json({ error: 'Invalid email token' });
            }
        }
    
        // Add spam prevention check
        if (await isSpam(text)) {
            return res.status(400).json({ error: 'Comment detected as spam' });
        }
    
        // Insert comment
        const result = await client.sql`
            INSERT INTO comments (
                text, 
                program_name, 
                parent_id, 
                author_email, 
                created_at,
                status
            )
            VALUES (
                ${text}, 
                ${programName}, 
                ${parentId}, 
                ${author.email}, 
                NOW(),
                'pending'
            )
            RETURNING id;
        `;
    
        res.status(200).json({ 
            id: result.rows[0].id,
            message: 'Comment submitted and pending review'
        });
    } catch (error) {
        console.error('Error posting comment:', error);
        res.status(500).json({ error: 'Error posting comment' });
    } finally {
        await client.end();
    }
}

async function handleGetComments(req, res) {
    const client = createClient();
  
    try {
        await client.connect();
    
        const { programName } = req.query;
    
        // Fetch comments with replies using recursive CTE
        const result = await client.sql`
            WITH RECURSIVE comment_tree AS (
                SELECT 
                    id, text, program_name, parent_id, author_email, created_at,
                    status, 1 as level
                FROM comments
                WHERE parent_id IS NULL 
                    AND program_name = ${programName}
                    AND status = 'approved'
        
                UNION ALL
        
                SELECT 
                    c.id, c.text, c.program_name, c.parent_id, c.author_email, 
                    c.created_at, c.status, ct.level + 1
                FROM comments c
                JOIN comment_tree ct ON c.parent_id = ct.id
                WHERE c.status = 'approved'
            )
            SELECT * FROM comment_tree
            ORDER BY level, created_at DESC;
        `;
    
        // Organize into threaded structure
        const threads = organizeThreads(result.rows);
    
        res.status(200).json(threads);
    } catch (error) {
        console.error('Error fetching comments:', error);
        res.status(500).json({ error: 'Error fetching comments' });
    } finally {
        await client.end();
    }
}

function organizeThreads(comments) {
    const threadMap = new Map();
    const rootThreads = [];
  
    comments.forEach(comment => {
        comment.replies = [];
        threadMap.set(comment.id, comment);
    
        if (comment.parent_id === null) {
            rootThreads.push(comment);
        } else {
            const parent = threadMap.get(comment.parent_id);
            if (parent) {
                parent.replies.push(comment);
            }
        }
    });
  
    return rootThreads;
}

async function isSpam(text) {
    // Basic spam word check
    const spamWords = ['casino', 'viagra', 'buy now', 'click here'];
    const containsSpam = spamWords.some(word => 
        text.toLowerCase().includes(word)
    );
  
    if (containsSpam) return true;
  
    // Add more sophisticated checks
    const hasExcessiveLinks = (text.match(/http/g) || []).length > 3;
    const hasRepeatedCharacters = /(.)\1{4,}/.test(text);
    const isExcessivelyLong = text.length > 2000;
  
    return hasExcessiveLinks || hasRepeatedCharacters || isExcessivelyLong;
}

async function verifyEmailToken(token) {
    // Implement email token verification logic here
    // This could involve checking against a database or verifying a JWT
    return true; // Placeholder
}