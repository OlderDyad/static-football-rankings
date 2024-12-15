// comments.js
export class CommentManager {
    constructor(pageId) {
        this.pageId = pageId;
        this.commentsContainer = document.getElementById('commentsList');
        this.commentForm = document.getElementById('commentForm');
    }

    async loadComments() {
        try {
            const response = await fetch(`/api/comments?pageId=${this.pageId}`);
            if (!response.ok) throw new Error('Failed to load comments');
            const comments = await response.json();
            this.displayComments(comments);
        } catch (error) {
            console.error('Error loading comments:', error);
            this.showError('Unable to load comments');
        }
    }

    displayComments(comments) {
        if (!this.commentsContainer) return;
        
        this.commentsContainer.innerHTML = comments.length 
            ? comments.map(comment => this.createCommentHTML(comment)).join('')
            : '<p class="text-muted">No comments yet. Be the first to comment!</p>';
    }

    createCommentHTML(comment) {
        return `
            <div class="comment mb-3 p-3 border rounded">
                <div class="d-flex justify-content-between">
                    <strong>${this.escapeHTML(comment.author)}</strong>
                    <small class="text-muted">
                        ${new Date(comment.createdAt).toLocaleDateString()}
                    </small>
                </div>
                <div class="mt-2">${this.escapeHTML(comment.content)}</div>
            </div>
        `;
    }

    escapeHTML(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    showError(message) {
        if (this.commentsContainer) {
            this.commentsContainer.innerHTML = `
                <div class="alert alert-danger" role="alert">
                    ${this.escapeHTML(message)}
                </div>
            `;
        }
    }

    async submitComment(content) {
        try {
            const response = await fetch('/api/comments', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    pageId: this.pageId,
                    content
                }),
                credentials: 'include'
            });

            if (!response.ok) throw new Error('Failed to submit comment');
            await this.loadComments(); // Reload comments after successful submission
            return true;
        } catch (error) {
            console.error('Error submitting comment:', error);
            this.showError('Unable to submit comment');
            return false;
        }
    }
}