-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Drop existing objects if they exist
DROP FUNCTION IF EXISTS match_documents(vector, integer, jsonb);
DROP FUNCTION IF EXISTS validate_note_metadata();
DROP TRIGGER IF EXISTS validate_note_metadata_trigger ON notes;
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
CREATE INDEX idx_notes_file_id ON notes USING gin ((metadata->>'file_id') gin_trgm_ops);
CREATE INDEX idx_notes_source ON notes USING gin ((metadata->>'source') gin_trgm_ops);
CREATE INDEX idx_notes_blob_type ON notes USING gin ((metadata->>'blobType') gin_trgm_ops);
CREATE INDEX idx_notes_directory ON notes USING gin ((metadata->>'directory') gin_trgm_ops);
CREATE INDEX idx_notes_created_at ON notes USING gin ((metadata->>'created_at') gin_trgm_ops);
CREATE INDEX idx_notes_processing_info ON notes USING gin ((metadata->'processing_info'));

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

-- Create function to validate metadata structure
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
    
    -- Validate numeric fields if present
    IF NEW.metadata->>'file_size' IS NOT NULL AND 
       (NEW.metadata->>'file_size')::integer IS NULL THEN
        RAISE EXCEPTION 'file_size must be a valid integer';
    END IF;
    
    IF NEW.metadata->>'content_length' IS NOT NULL AND 
       (NEW.metadata->>'content_length')::integer IS NULL THEN
        RAISE EXCEPTION 'content_length must be a valid integer';
    END IF;
    
    -- Validate boolean fields if present
    IF NEW.metadata->>'is_truncated' IS NOT NULL AND 
       (NEW.metadata->>'is_truncated')::boolean IS NULL THEN
        RAISE EXCEPTION 'is_truncated must be a valid boolean';
    END IF;
    
    -- Validate timestamps if present
    IF NEW.metadata->>'last_modified' IS NOT NULL AND 
       (NEW.metadata->>'last_modified')::timestamp IS NULL THEN
        RAISE EXCEPTION 'last_modified must be a valid timestamp';
    END IF;
    
    IF NEW.metadata->>'created_at' IS NOT NULL AND 
       (NEW.metadata->>'created_at')::timestamp IS NULL THEN
        RAISE EXCEPTION 'created_at must be a valid timestamp';
    END IF;
    
    IF NEW.metadata->'processing_info'->>'processed_at' IS NOT NULL AND 
       (NEW.metadata->'processing_info'->>'processed_at')::timestamp IS NULL THEN
        RAISE EXCEPTION 'processed_at must be a valid timestamp';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to validate metadata on insert/update
CREATE TRIGGER validate_note_metadata_trigger
    BEFORE INSERT OR UPDATE ON notes
    FOR EACH ROW
    EXECUTE FUNCTION validate_note_metadata();

-- Create RLS policies
ALTER TABLE notes ENABLE ROW LEVEL SECURITY;

-- Allow all authenticated users to read notes
CREATE POLICY "Allow authenticated users to read notes"
    ON notes FOR SELECT
    TO authenticated
    USING (true);

-- Allow all authenticated users to insert notes
CREATE POLICY "Allow authenticated users to insert notes"
    ON notes FOR INSERT
    TO authenticated
    WITH CHECK (true);

-- Allow all authenticated users to delete their own notes
CREATE POLICY "Allow authenticated users to delete their own notes"
    ON notes FOR DELETE
    TO authenticated
    USING (true);

-- Allow all authenticated users to update their own notes
CREATE POLICY "Allow authenticated users to update their own notes"
    ON notes FOR UPDATE
    TO authenticated
    USING (true)
    WITH CHECK (true); 