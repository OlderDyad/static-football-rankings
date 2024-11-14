export default async function handler(req, res) {
    // Set CORS headers
    res.setHeader("Access-Control-Allow-Origin", "https://olderdyad.github.io");
    res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
    res.setHeader("Access-Control-Allow-Headers", "Content-Type");
    res.setHeader("Access-Control-Allow-Credentials", "true");
  
    // Handle preflight OPTIONS request
    if (req.method === "OPTIONS") {
      res.status(200).end();
      return;
    }
  
    if (req.method === "POST") {
      return res.status(200).json({ message: "Email verification placeholder" });
    } else {
      return res.status(405).json({ error: "Method not allowed" });
    }
  }
  