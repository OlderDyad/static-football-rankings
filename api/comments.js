export default async function handler(req, res) {
    // Set CORS headers
    res.setHeader("Access-Control-Allow-Origin", "*");
    res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
    res.setHeader("Access-Control-Allow-Headers", "Content-Type");

    if (req.method === "OPTIONS") {
        return res.status(200).end();
    }

    if (req.method === "GET") {
        return res.status(200).json({ message: "GET request to comments" });
    } else if (req.method === "POST") {
        return res.status(200).json({ message: "POST request to comments" });
    } else {
        return res.status(405).json({ error: "Method not allowed" });
    }
}