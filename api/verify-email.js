// api/verify-email.js

require('dotenv').config();

export default async function handler(req, res) {
    // Set CORS headers
    res.setHeader("Access-Control-Allow-Origin", "https://olderdyad.github.io");
    res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
    res.setHeader("Access-Control-Allow-Headers", "Content-Type");
    res.setHeader("Access-Control-Allow-Credentials", "true");

    // Handle preflight
    if (req.method === 'OPTIONS') {
        res.status(200).end();
        return;
    }

    if (req.method === 'POST') {
        try {
            const { email, commentText } = req.body;

            // Validate email and comment text
            if (!email) {
                return res.status(400).json({ error: 'Email is required for verification' });
            }

            if (!commentText) {
                return res.status(400).json({ error: 'Comment text is required' });
            }

            // Mock email sending logic
            console.log(`Sending verification email to ${email} for comment: "${commentText}"`);

            // Replace this console log with actual email-sending logic.
            // For example:
            // await sendEmail({
            //   to: email,
            //   subject: "Comment Verification",
            //   text: `Please verify your comment: "${commentText}"`,
            // });

            res.status(200).json({ message: 'Verification email sent' });
        } catch (error) {
            console.error('Error in email verification:', error);
            res.status(500).json({ error: 'Failed to send verification email' });
        }
    } else {
        res.setHeader('Allow', ['POST', 'OPTIONS']);
        res.status(405).json({ error: `Method ${req.method} not allowed` });
    }
}




  