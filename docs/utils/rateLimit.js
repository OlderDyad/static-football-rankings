// docs/utils/rateLimit.js
export async function rateLimit(req, res, options = {}) {
    const defaultOptions = {
        windowSize: 60 * 1000, // 1 minute
        maxRequests: 20 // requests per window
    };

    const opts = { ...defaultOptions, ...options };
    
    // Get client IP
    const ip = req.headers['x-forwarded-for'] || 
               req.connection.remoteAddress || 
               'unknown';
    
    const now = Date.now();
    const key = `ratelimit:${ip}`;
    
    try {
        // Simple in-memory rate limiting for development
        // In production, you'd want to use Redis or similar
        if (!global.rateLimitMap) {
            global.rateLimitMap = new Map();
        }
        
        const record = global.rateLimitMap.get(key) || { 
            count: 0, 
            startTime: now 
        };
        
        // Reset if window has passed
        if (now - record.startTime > opts.windowSize) {
            record.count = 0;
            record.startTime = now;
        }
        
        record.count++;
        global.rateLimitMap.set(key, record);
        
        if (record.count > opts.maxRequests) {
            throw new Error('Rate limit exceeded');
        }
        
    } catch (error) {
        throw new Error('Rate limit exceeded');
    }
}