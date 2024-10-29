// api/confirm-email.js
import { createClient } from '@vercel/postgres';
import { verify } from 'jsonwebtoken';

const EMAIL_SECRET = process.env.EMAIL_SECRET;

export default async function handler(req, res) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }
  
  const client = createClient();
  
  try {
    const { token } = req.query;
    
    // Verify token and extract data
    const { email, pendingComment } = verify(token, EMAIL_SECRET);
    
    await client.connect();
    
    // Begin transaction
    await client.sql`BEGIN`;
    
    // Store verified email
    await client.sql`
      INSERT INTO verified_emails (email, verified_at)
      VALUES (${email}, NOW())
      ON CONFLICT (email) DO UPDATE
      SET verified_at = NOW();
    `;

    // If there's pending comment data, post it
    if (pendingComment) {
      await client.sql`
        INSERT INTO comments (
          text,
          program_name,
          parent_id,
          author_email,
          created_at,
          status
        )
        VALUES (
          ${pendingComment.text},
          ${pendingComment.programName},
          ${pendingComment.parentId},
          ${email},
          NOW(),
          'pending'
        );
      `;
    }

    // Commit transaction
    await client.sql`COMMIT`;
    
    // Redirect back with success
    const successUrl = new URL('/', process.env.VERCEL_URL);
    successUrl.searchParams.set('verified', 'true');
    successUrl.searchParams.set('email', email);
    res.redirect(302, successUrl.toString());
    
  } catch (error) {
    // Rollback transaction if error
    await client.sql`ROLLBACK`;
    console.error('Error confirming email:', error);
    
    // Redirect back with error
    const errorUrl = new URL('/', process.env.VERCEL_URL);
    errorUrl.searchParams.set('verified', 'false');
    errorUrl.searchParams.set('error', 'Invalid or expired verification link');
    res.redirect(302, errorUrl.toString());
  } finally {
    await client.end();
  }
}