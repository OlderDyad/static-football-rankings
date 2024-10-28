// utils/verifyEmailToken.js
import { createClient } from '@vercel/postgres';

export async function verifyEmailToken(email) {
  const client = createClient();
  
  try {
    await client.connect();
    
    // Check if email is verified and verification is still valid (within 30 days)
    const result = await client.sql`
      SELECT verified_at 
      FROM verified_emails 
      WHERE email = ${email}
        AND verified_at > NOW() - INTERVAL '30 days';
    `;
    
    return result.rows.length > 0;
  } finally {
    await client.end();
  }
}