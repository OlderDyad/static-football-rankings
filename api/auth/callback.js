import jwt from 'jsonwebtoken';
import axios from 'axios';

export default async function handler(req, res) {
    const { code } = req.query;

    if (!code) {
        return res.status(400).json({ error: 'Authorization code is required' });
    }

    try {
        // Exchange authorization code for tokens
        const tokenResponse = await axios.post('https://oauth2.googleapis.com/token', {
            code,
            client_id: process.env.GOOGLE_CLIENT_ID,
            client_secret: process.env.GOOGLE_CLIENT_SECRET,
            redirect_uri: process.env.REDIRECT_URI,
            grant_type: 'authorization_code',
        });

        const { id_token } = tokenResponse.data;

        // Decode ID token to get user info
        const decodedToken = jwt.decode(id_token);
        const user = {
            email: decodedToken.email,
            name: decodedToken.name,
            picture: decodedToken.picture,
        };

        // Generate JWT for session management
        const jwtToken = jwt.sign(user, process.env.JWT_SECRET, { expiresIn: '1h' });

        // Send JWT to the frontend
        res.redirect(`${process.env.REDIRECT_URI}?token=${jwtToken}`);
    } catch (error) {
        console.error('Error during Google OAuth callback:', error);
        res.status(500).json({ error: 'Failed to exchange authorization code' });
    }
}
