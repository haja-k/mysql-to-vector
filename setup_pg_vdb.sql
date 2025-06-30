-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create genie_documents table
CREATE TABLE genie_documents (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT,
    link TEXT,
    date TIMESTAMP,
    question_embedding VECTOR(1024),  -- Adjust dimension if needed
    answer_embedding VECTOR(1024)
);

-- Create indexes for vector search
CREATE INDEX ON genie_documents USING ivfflat (question_embedding vector_cosine_ops);
CREATE INDEX ON genie_documents USING ivfflat (answer_embedding vector_cosine_ops);