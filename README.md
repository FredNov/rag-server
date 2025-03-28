# RAG Server

A server implementation for a Retrieval-Augmented Generation (RAG) system using FastMCP, Supabase, and OpenAI.

## Features

- Semantic document search using embeddings
- Document management (add/delete)
- Integration with Supabase for vector storage
- OpenAI embeddings for semantic search

## Setup

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file with the following variables:
   ```
   SUPABASE_URL=your_supabase_url
   SUPABASE_ANON_KEY=your_supabase_anon_key
   OPENAI_API_KEY=your_openai_api_key
   OPENAI_MODEL=your_openai_model
   DOCUMENTS_TABLE=your_documents_table_name
   DEFAULT_SEARCH_LIMIT=5
   ```

## Usage

Run the server:
```bash
python rag_server.py
```

The server will start with SSE transport enabled.

## API Endpoints

- `search_documents`: Search for documents using semantic similarity
- `add_document`: Add a new document with its embedding
- `delete_document`: Delete a document by ID

## License

MIT 