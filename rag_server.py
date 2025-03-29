import os
from typing import List, Optional, Union, Dict
from dotenv import load_dotenv, find_dotenv
from mcp.server.fastmcp import FastMCP
from supabase import create_client, Client
from openai import OpenAI
from pydantic import BaseModel
import logging
from pathlib import Path
import httpx
import uuid
import hashlib
from datetime import datetime

# Configure logging with both file and console handlers
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('rag_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_env_file() -> None:
    """
    Load environment variables from .env file.
    Raises an error if .env file is not found or cannot be loaded.
    """
    env_path = find_dotenv(usecwd=True)
    if not env_path:
        error_msg = "No .env file found. Please create a .env file with required configuration."
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)
    
    logger.info(f"Loading .env file from: {env_path}")
    if not load_dotenv(env_path, override=True):
        error_msg = "Failed to load .env file"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

# Load environment variables from .env file
load_env_file()

def get_env_var(key: str, default: Optional[str] = None) -> str:
    """
    Get an environment variable from .env file.
    If the variable is required (no default) and not found, raises an error.
    
    Args:
        key: The environment variable name
        default: Optional default value if the variable is not found
        
    Returns:
        The environment variable value
        
    Raises:
        ValueError: If the variable is required and not found
    """
    value = os.getenv(key)
    if value is None:
        if default is not None:
            logger.warning(f"Environment variable {key} not found in .env file, using default value")
            return default
        else:
            error_msg = f"Required environment variable {key} not found in .env file"
            logger.error(error_msg)
            raise ValueError(error_msg)
    return value

# Script configuration variables from environment
try:
    SUPABASE_URL = get_env_var("SUPABASE_URL")
    SUPABASE_ANON_KEY = get_env_var("SUPABASE_ANON_KEY")
    OPENAI_API_KEY = get_env_var("OPENAI_API_KEY")
    OPENAI_MODEL = get_env_var("OPENAI_MODEL", "text-embedding-3-small")
    DOCUMENTS_TABLE = get_env_var("DOCUMENTS_TABLE")
    DEFAULT_SEARCH_LIMIT = int(get_env_var("DEFAULT_SEARCH_LIMIT", "7"))
    PORT = int(get_env_var("PORT", "8000"))
except ValueError as e:
    logger.error("Failed to load required environment variables")
    raise

# Log startup configuration (with sensitive data masked)
logger.info("Starting RAG Server with configuration:")
logger.info(f"Supabase URL: {SUPABASE_URL}")
logger.info(f"Supabase Key: {'*' * len(SUPABASE_ANON_KEY)}")
logger.info(f"OpenAI Model: {OPENAI_MODEL}")
logger.info(f"Documents Table: {DOCUMENTS_TABLE}")
logger.info(f"Default Search Limit: {DEFAULT_SEARCH_LIMIT}")
logger.info(f"Server Port: {PORT}")

# Initialize Supabase client
logger.info("Initializing Supabase client...")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Initialize OpenAI client
logger.info("Initializing OpenAI client...")
http_client = httpx.Client(
    base_url="https://api.openai.com/v1",
    headers={"Authorization": f"Bearer {OPENAI_API_KEY}"}
)

openai_client = OpenAI(
    api_key=OPENAI_API_KEY,
    http_client=http_client
)

# Create MCP server
logger.info("Creating MCP server...")
mcp = FastMCP("RAG Server")

class Document(BaseModel):
    id: int
    content: str
    embedding: Optional[List[float]] = None
    metadata: Optional[dict] = None

    @classmethod
    def from_supabase(cls, data: dict) -> 'Document':
        # Convert string embedding to list of floats if it exists
        if 'embedding' in data and isinstance(data['embedding'], str):
            try:
                # Remove brackets and split by comma
                embedding_str = data['embedding'].strip('[]')
                data['embedding'] = [float(x) for x in embedding_str.split(',')]
            except (ValueError, AttributeError):
                data['embedding'] = None
        return cls(**data)

class DocumentMetadata(BaseModel):
    loc: Optional[dict] = None
    source: Optional[str] = None
    file_id: Optional[str] = None
    blobType: Optional[str] = None

@mcp.tool("search_note")
async def search_documents(query: str, limit: int = DEFAULT_SEARCH_LIMIT) -> List[Document]:
    """
    Search for user knowledge database (notes) using semantic similarity with the given query.
    
    Args:
        query (str): The search query text
        limit (int): Maximum number of notes to return (defaults to DEFAULT_SEARCH_LIMIT from environment)
        
    Returns:
        List of relevant notes
    """
    logger.info(f"Starting document search with query: '{query}' (limit: {limit})")
    
    try:
        # Generate embedding for the query
        logger.debug("Generating query embedding...")
        query_embedding = openai_client.embeddings.create(
            model=OPENAI_MODEL,
            input=query
        ).data[0].embedding
        
        logger.info(f"Generated query embedding of length: {len(query_embedding)}")
        
        # Query Supabase for similar documents
        logger.debug("Querying Supabase for similar documents...")
        response = supabase.rpc(
            'match_documents',
            {
                'query_embedding': query_embedding,
                'match_count': limit,
                'filter': {}
            }
        ).execute()
        
        # Process and sort results by similarity
        results = []
        for doc in response.data:
            # Convert the distance-based similarity to a proper similarity score
            distance = 1 - doc.get('similarity', 0)
            similarity = 1 - (distance / 2)
            
            # Create a new document with the corrected similarity
            doc_copy = doc.copy()
            doc_copy['similarity'] = similarity
            results.append(doc_copy)
        
        # Sort by similarity in descending order
        results.sort(key=lambda x: x['similarity'], reverse=True)
        
        # Log the results
        logger.info(f"Found {len(results)} matching documents")
        for doc in results:
            logger.debug(f"Document ID={doc['id']}, Similarity={doc['similarity']:.3f}")
            logger.debug(f"Content preview: {doc['content'][:100]}...")
        
        return [Document.from_supabase(doc) for doc in results]
    except Exception as e:
        logger.error(f"Error during document search: {str(e)}")
        raise

@mcp.tool("add_note")
async def add_note(content: str, metadata: Optional[Dict] = None) -> Dict:
    """Add a new note to the user knowledge database."""
    try:
        # Generate embedding for the content
        response = await openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=content
        )
        embedding = response.data[0].embedding

        # Prepare metadata with default values and chat source
        default_metadata = {
            "loc": None,
            "source": "from_chat",
            "file_id": str(uuid.uuid4()),  # Generate unique ID for chat messages
            "blobType": "text",
            "filename": None,
            "path": None,
            "directory": None,
            "file_extension": None,
            "file_size": len(content),
            "file_hash": hashlib.sha256(content.encode()).hexdigest(),
            "content_length": len(content),
            "is_truncated": False,
            "last_modified": datetime.now().isoformat(),
            "created_at": datetime.now().isoformat(),
            "processing_info": {
                "model": "text-embedding-3-small",
                "processed_at": datetime.now().isoformat(),
                "embedding_dimension": 1536
            }
        }

        # Merge with provided metadata if any
        if metadata:
            default_metadata.update(metadata)

        # Insert into Supabase
        result = supabase.table("notes").insert({
            "content": content,
            "embedding": embedding,
            "metadata": default_metadata
        }).execute()

        if result.data:
            return {"id": result.data[0]["id"], "content": content, "metadata": default_metadata}
        else:
            raise Exception("Failed to add note: No data returned from insert")

    except Exception as e:
        logging.error(f"Error adding note: {str(e)}")
        raise

@mcp.tool("delete_note")
async def delete_note(note_id: Union[str, int]) -> bool:
    """
    Delete a note from user knowledge database.
    
    Args:
        note_id (Union[str, int]): The ID of the note to delete
        
    Returns:
        True if the note was successfully deleted
    """
    logger.info(f"Attempting to delete note with ID: {note_id}")
    
    try:
        # Convert note_id to string if it's an integer
        note_id_str = str(note_id)
        response = supabase.table(DOCUMENTS_TABLE).delete().eq('id', note_id_str).execute()
        
        success = len(response.data) > 0
        if success:
            logger.info(f"Successfully deleted note with ID: {note_id}")
        else:
            logger.warning(f"No note found with ID: {note_id}")
        
        return success
    except Exception as e:
        logger.error(f"Error deleting note {note_id}: {str(e)}")
        raise

if __name__ == "__main__":
    import uvicorn
    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.routing import Mount, Route
    
    logger.info(f"Starting RAG Server on port {PORT}")
    
    # Create SSE transport
    sse = SseServerTransport("/messages/")
    
    async def handle_sse(request):
        async with sse.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await mcp._mcp_server.run(
                streams[0],
                streams[1],
                mcp._mcp_server.create_initialization_options()
            )
    
    # Create Starlette app with routes
    starlette_app = Starlette(
        debug=True,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )
    
    # Run the server
    uvicorn.run(starlette_app, host="0.0.0.0", port=PORT) 