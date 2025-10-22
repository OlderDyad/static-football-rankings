// docs/js/modules/utils.js

export function formatDate(timestamp) {
    try {
        return new Date(timestamp).toLocaleDateString();
    } catch (error) {
        console.error('Error formatting date:', error);
        return 'Unknown';
    }
}

// This is a very basic implementation.
// You'll likely need a more robust escaping function for production.
export function escapeHTML(str) {
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}