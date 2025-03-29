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
    metadata JSONB NOT NULL DEFAULT '{
        "loc": null,
        "source": "file_system",
        "file_id": null,
        "blobType": "markdown",
        "filename": null,
        "path": null,
        "directory": null,
        "file_extension": null,
        "file_size": null,
        "file_hash": null,
        "content_length": null,
        "is_truncated": false,
        "last_modified": null,
        "created_at": null,
        "processing_info": {
            "model": "text-embedding-3-small",
            "processed_at": null,
            "embedding_dimension": 1536
        }
    }'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for commonly queried metadata fields
CREATE INDEX idx_notes_file_id ON notes USING gin ((metadata->>'file_id'));
CREATE INDEX idx_notes_source ON notes USING gin ((metadata->>'source'));
CREATE INDEX idx_notes_blob_type ON notes USING gin ((metadata->>'blobType'));
CREATE INDEX idx_notes_directory ON notes USING gin ((metadata->>'directory'));
CREATE INDEX idx_notes_created_at ON notes USING gin ((metadata->>'created_at'));

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

-- Add a function to validate metadata structure
CREATE OR REPLACE FUNCTION validate_note_metadata()
RETURNS TRIGGER AS $$
BEGIN
    -- Check required fields
    IF NEW.metadata->>'source' IS NULL THEN
        RAISE EXCEPTION 'source field is required in metadata';
    END IF;
    
    IF NEW.metadata->>'file_id' IS NULL THEN
        RAISE EXCEPTION 'file_id field is required in metadata';
    END IF;
    
    IF NEW.metadata->>'blobType' IS NULL THEN
        RAISE EXCEPTION 'blobType field is required in metadata';
    END IF;
    
    -- Validate processing_info structure
    IF NEW.metadata->'processing_info' IS NULL THEN
        RAISE EXCEPTION 'processing_info object is required in metadata';
    END IF;
    
    IF NEW.metadata->'processing_info'->>'model' IS NULL THEN
        RAISE EXCEPTION 'model field is required in processing_info';
    END IF;
    
    IF NEW.metadata->'processing_info'->>'embedding_dimension' IS NULL THEN
        RAISE EXCEPTION 'embedding_dimension field is required in processing_info';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to validate metadata on insert/update
CREATE TRIGGER validate_note_metadata_trigger
    BEFORE INSERT OR UPDATE ON notes
    FOR EACH ROW
    EXECUTE FUNCTION validate_note_metadata(); 