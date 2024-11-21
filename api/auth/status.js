require('dotenv').config();
const jwt = require('jsonwebtoken');

export default async function handler(req, res) {
    res.setHeader("Access-Control-Allow-Origin", "https://olderdyad.github.io");
    res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
    res.setHeader("Access-Control-Allow-Headers", "Content-Type");
    res.setHeader("Access-Control-Allow-Credentials", "true");

    if (req.method === 'OPTIONS') {
        return res.status(200).end();
    }

    try {
        // Check for JWT token in cookies
        const token = req.cookies?.token;

        if (!token) {
            return res.status(200).json({ loggedIn: false });
        }

        // Verify JWT token
        const decoded = jwt.verify(token, process.env.JWT_SECRET);

        if (decoded) {
            return res.status(200).json({
                loggedIn: true,
                user: decoded, // Include user info like name and email
            });
        } else {
            return res.status(200).json({ loggedIn: false });
        }
    } catch (error) {
        console.error("Error verifying login status:", error);
        return res.status(500).json({ error: 'Error verifying login status' });
    }
}
