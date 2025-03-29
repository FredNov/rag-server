# RAG Server

A Retrieval-Augmented Generation (RAG) server that uses Supabase for vector storage and OpenAI for embeddings.

## Prerequisites

- Python 3.8 or higher
- Supabase account and project
- OpenAI API key
- PostgreSQL database with vector extension enabled

## Setup

1. Clone the repository:
```bash
git clone https://github.com/FredNov/rag-server.git
cd rag-server
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your credentials:
```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
OPENAI_API_KEY=your_openai_api_key
```

5. Set up the database:
   - Go to your Supabase project dashboard
   - Navigate to the SQL Editor
   - Copy and paste the contents of `setup.sql`
   - Run the SQL commands

## Running the Server

Start the RAG server:
```bash
python rag_server.py
```

The server will start on port 3000 by default.

## API Endpoints

- `POST /messages/` - Send messages to the server
- `GET /sse` - Server-Sent Events endpoint for real-time communication

## Available Tools

1. `search_note`: Search for notes using semantic similarity
   - Parameters:
     - `query`: The search query
     - `limit`: Maximum number of results (default: 5)

2. `add_note`: Add a new note to the database
   - Parameters:
     - `content`: The note content
     - `metadata`: Optional JSON metadata

3. `delete_note`: Delete a note by ID
   - Parameters:
     - `note_id`: The ID of the note to delete

## Database Schema

The `notes` table has the following structure:
- `id`: Serial primary key
- `content`: Text content of the note
- `embedding`: Vector(1536) for semantic search
- `metadata`: JSONB field for additional data
- `created_at`: Timestamp of creation

## License

MIT License 