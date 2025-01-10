// api/comments.js
let comments = []; // Ephemeral in-memory store; resets on serverless cold starts

export default async function handler(req, res) {
  console.log('[comments] Received request:', req.method);

  // CORS (adjust domain if needed)
  res.setHeader('Access-Control-Allow-Origin', 'https://olderdyad.github.io'); // Update if using a different domain
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  res.setHeader('Access-Control-Allow-Credentials', 'true');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  try {
    if (req.method === 'GET') {
      const { pageId } = req.query; // e.g., ?pageId=1920s
      let resultComments = comments;

      if (pageId) {
        // Filter by pageId
        resultComments = comments.filter(c => c.pageId === pageId);
      }

      return res.status(200).json({
        success: true,
        comments: resultComments
      });
    }

    if (req.method === 'POST') {
      const { text, pageId } = req.body || {};
      if (!text) {
        return res.status(400).json({ success: false, error: 'text is required' });
      }

      // Tag comment with pageId (or 'unknown' if not provided)
      const newComment = {
        id: Date.now().toString(),
        text: text.trim(),
        author: 'Anonymous',   // or retrieve from user session/cookie if desired
        pageId: pageId || 'unknown',
        timestamp: new Date().toISOString()
      };

      // Insert at front
      comments.unshift(newComment);
      console.log('[comments] New comment:', newComment);

      return res.status(201).json({ success: true, comment: newComment });
    }

    // If not GET/POST:
    return res.status(405).json({ success: false, error: `Method ${req.method} Not Allowed` });
  } catch (error) {
    console.error('[comments] Error:', error);
    return res.status(500).json({ success: false, error: 'Internal Server Error' });
  }
}


