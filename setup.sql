-- Enable the vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Drop existing tables and functions if they exist
DROP FUNCTION IF EXISTS match_documents(vector, integer, jsonb);
DROP TABLE IF EXISTS notes CASCADE;

-- Create the notes table with proper column types
CREATE TABLE notes (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding vector(1536) NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create an index for faster similarity searches
CREATE INDEX ON notes USING hnsw (embedding vector_cosine_ops);

-- Create the match_documents function with proper column references
CREATE OR REPLACE FUNCTION match_documents(
    query_embedding vector(1536),
    match_count int DEFAULT 5,
    filter jsonb DEFAULT '{}'::jsonb
)
RETURNS TABLE (
    id int,
    content text,
    metadata jsonb,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        n.id,
        n.content,
        n.metadata,
        1 - (n.embedding <=> query_embedding) as similarity
    FROM notes n
    WHERE
        CASE
            WHEN filter::text = '{}'::text THEN true
            ELSE n.metadata @> filter
        END
    ORDER BY n.embedding <=> query_embedding
    LIMIT match_count;
END;
$$; 