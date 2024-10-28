// api/verify-email.js
import { createClient } from '@vercel/postgres';
import { createTransport } from 'nodemailer';
import { sign } from 'jsonwebtoken';
import { rateLimit } from '../utils/rateLimit';

const EMAIL_SECRET = process.env.EMAIL_SECRET;
const SMTP_CONFIG = {
  host: process.env.SMTP_HOST,
  port: process.env.SMTP_PORT,
  auth: {
    user: process.env.SMTP_USER,
    pass: process.env.SMTP_PASS
  }
};

export default async function handler(req, res) {
  // Enable CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // Apply rate limiting for email verification
  try {
    await rateLimit(req, res, {
      windowSize: 3600 * 1000, // 1 hour
      maxRequests: 5 // 5 verification emails per hour
    });
  } catch (error) {
    return res.status(429).json({ 
      error: 'Too many verification attempts. Please try again later.' 
    });
  }
  
  try {
    const { email, pendingCommentData } = JSON.parse(req.body);
    
    // Validate email format
    if (!email || !email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) {
      return res.status(400).json({ error: 'Invalid email format' });
    }

    // Generate verification token with pending comment data
    const token = sign(
      { 
        email,
        pendingComment: pendingCommentData // Store the comment data in token
      }, 
      EMAIL_SECRET, 
      { expiresIn: '1h' }
    );
    
    // Create email transporter
    const transporter = createTransport(SMTP_CONFIG);
    
    // Send verification email
    await transporter.sendMail({
      from: process.env.SMTP_FROM,
      to: email,
      subject: 'Verify your email to comment',
      html: `
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
          <h2>Verify your email</h2>
          <p>Click the link below to verify your email and post your comment:</p>
          <div style="margin: 20px 0;">
            <a href="${process.env.VERCEL_URL}/api/confirm-email?token=${token}"
               style="background: #0070f3; color: white; padding: 12px 24px; 
                      text-decoration: none; border-radius: 5px; display: inline-block;">
              Verify Email
            </a>
          </div>
          <p>This link will expire in 1 hour.</p>
          <p style="color: #666; font-size: 0.9em;">
            If you didn't request this verification, please ignore this email.
          </p>
        </div>
      `
    });
    
    res.status(200).json({ 
      message: 'Verification email sent',
      email: email 
    });
  } catch (error) {
    console.error('Error sending verification:', error);
    res.status(500).json({ error: 'Error sending verification email' });
  }
}