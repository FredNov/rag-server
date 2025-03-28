# RAG Server

A Retrieval-Augmented Generation (RAG) server implementation using FastMCP, Supabase, and OpenAI.

## Features

- Semantic document search using embeddings
- Document management (add/delete)
- Flexible environment variable configuration
- SSE transport support

## Setup

1. Clone the repository
2. Create a `.env` file in the project root with the following variables:
   ```
   SUPABASE_URL=your_supabase_url
   SUPABASE_ANON_KEY=your_supabase_anon_key
   OPENAI_API_KEY=your_openai_api_key
   OPENAI_MODEL=your_openai_model
   DOCUMENTS_TABLE=your_documents_table
   DEFAULT_SEARCH_LIMIT=5
   ```

   Alternatively, you can set these as system environment variables.

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the server:
```bash
python rag_server.py
```

The server will start with SSE transport enabled.

## API Endpoints

- `search_documents`: Search for documents using semantic similarity
- `add_document`: Add a new document with embedding
- `delete_document`: Delete a document by ID

## Environment Variables

The server looks for environment variables in the following order:
1. `.env` file in the script directory
2. System environment variables

Required variables:
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_ANON_KEY`: Your Supabase anonymous key
- `OPENAI_API_KEY`: Your OpenAI API key
- `OPENAI_MODEL`: The OpenAI model to use for embeddings
- `DOCUMENTS_TABLE`: The name of your documents table in Supabase

Optional variables:
- `DEFAULT_SEARCH_LIMIT`: Maximum number of documents to return in search (default: 5)

## License

MIT 