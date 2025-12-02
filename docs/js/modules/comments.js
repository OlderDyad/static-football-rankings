// docs/js/modules/comments.js

export class CommentManager {
    constructor() {
        this.comments = [];
        // Note: This URL needs to point to your actual backend/firebase function
        // Since GitHub Pages is static, this path usually implies a proxy or external API.
        this.baseUrl = '/static-football-rankings/api';
    }

    async fetchComments() {
        try {
            // Check if API is reachable (or mock for static demo)
            // If on GitHub Pages without a backend, this fetch will 404.
            // We wrap it to prevent crashing the whole page.
            const response = await fetch(`${this.baseUrl}/comments`, {
                credentials: 'include'
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            this.comments = data.comments || [];
            return this.comments;
        } catch (error) {
            console.warn('Comment system unavailable (API unreachable):', error);
            return [];
        }
    }

    async addComment(text) {
        try {
            const response = await fetch(`${this.baseUrl}/comments`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({ text })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            if (result.success) {
                await this.fetchComments(); // Refresh comments list
                return result.comment;
            } else {
                throw new Error(result.error || 'Failed to add comment');
            }
        } catch (error) {
            console.error('Error adding comment:', error);
            throw error;
        }
    }

    formatDate(dateString) {
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    escapeHTML(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    renderComments(container) {
        if (!container) return;

        if (!this.comments.length) {
            container.innerHTML = '<p class="text-muted">No comments yet</p>';
            return;
        }

        container.innerHTML = this.comments.map(comment => `
            <div class="comment mb-3 p-3 border rounded">
                <div class="d-flex justify-content-between">
                    <strong>${this.escapeHTML(comment.author)}</strong>
                    <small class="text-muted">${this.formatDate(comment.timestamp)}</small>
                </div>
                <div class="mt-2">${this.escapeHTML(comment.text)}</div>
            </div>
        `).join('');
    }
}



