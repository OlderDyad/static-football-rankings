-- Save this as setup-db.sql
CREATE TABLE IF NOT EXISTS comments (
    id SERIAL PRIMARY KEY,
    text TEXT NOT NULL,
    program_name VARCHAR(255) NOT NULL,
    parent_id INTEGER REFERENCES comments(id),
    author_email VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending'
);

CREATE INDEX idx_comments_program ON comments(program_name);
CREATE INDEX idx_comments_parent ON comments(parent_id);