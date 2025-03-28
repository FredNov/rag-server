import os
from typing import List, Optional, Union
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from supabase import create_client, Client
from openai import OpenAI
from pydantic import BaseModel
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def find_env_file() -> Optional[Path]:
    """
    Find the .env file by checking multiple locations:
    1. Current working directory
    2. Script directory
    3. Parent directory of script
    """
    # Get the script's directory
    script_dir = Path(__file__).resolve().parent
    current_dir = Path.cwd()
    
    # List of possible .env file locations
    possible_locations = [
        current_dir / '.env',
        script_dir / '.env',
        script_dir.parent / '.env'
    ]
    
    # Log all locations we're checking
    logger.info(f"Checking for .env file in locations: {[str(p) for p in possible_locations]}")
    
    # Find the first existing .env file
    for env_path in possible_locations:
        if env_path.exists():
            logger.info(f"Found .env file at: {env_path}")
            return env_path
    
    logger.info("No .env file found in any of the checked locations")
    return None

# Try to load .env file if it exists
env_path = find_env_file()
if env_path:
    load_dotenv(env_path)
else:
    logger.info("Using system environment variables")

# Get environment variables with fallback to system environment
def get_env_var(key: str, default: Optional[str] = None) -> str:
    value = os.getenv(key, default)
    if value is None:
        raise ValueError(f"Required environment variable {key} not found in .env file or system environment")
    return value

# Initialize Supabase client
supabase: Client = create_client(
    get_env_var("SUPABASE_URL"),
    get_env_var("SUPABASE_ANON_KEY")
)

# Initialize OpenAI client
openai_client = OpenAI(api_key=get_env_var("OPENAI_API_KEY"))

# Create MCP server
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

@mcp.tool()
async def search_documents(query: str, limit: int = int(os.getenv("DEFAULT_SEARCH_LIMIT", "5"))) -> List[Document]:
    """
    Search for documents using semantic similarity with the given query.
    
    Args:
        query: The search query
        limit: Maximum number of documents to return (defaults to DEFAULT_SEARCH_LIMIT from environment)
        
    Returns:
        List of relevant documents
    """
    logger.info(f"Searching for query: {query}")
    
    # Generate embedding for the query
    query_embedding = openai_client.embeddings.create(
        model=os.getenv("OPENAI_MODEL"),
        input=query
    ).data[0].embedding
    
    logger.info(f"Generated query embedding of length: {len(query_embedding)}")
    
    # Query Supabase for similar documents
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
        # The database returns 1 - (cosine distance), where cosine distance is 0 to 2
        # We want to convert this to a proper similarity score between -1 and 1
        distance = 1 - doc.get('similarity', 0)  # Convert back to distance
        similarity = 1 - (distance / 2)  # Convert distance to similarity
        
        # Create a new document with the corrected similarity
        doc_copy = doc.copy()
        doc_copy['similarity'] = similarity
        results.append(doc_copy)
    
    # Sort by similarity in descending order
    results.sort(key=lambda x: x['similarity'], reverse=True)
    
    # Log the results
    for doc in results:
        logger.info(f"Found document: ID={doc['id']}, Similarity={doc['similarity']:.3f}")
        logger.info(f"Content preview: {doc['content'][:100]}...")
    
    return [Document.from_supabase(doc) for doc in results]

@mcp.tool()
async def add_document(content: str, metadata: Optional[DocumentMetadata] = None) -> Document:
    """
    Add a new document to the database with its embedding.
    
    Args:
        content: The document content
        metadata: Optional metadata for the document with structure:
            {
                "loc": {
                    "lines": {
                        "to": int,
                        "from": int
                    }
                },
                "source": str,
                "file_id": str,
                "blobType": str
            }
        
    Returns:
        The created document
    """
    # Generate embedding for the document
    embedding = openai_client.embeddings.create(
        model=os.getenv("OPENAI_MODEL"),
        input=content
    ).data[0].embedding
    
    # Convert metadata to dict if provided
    metadata_dict = metadata.dict() if metadata else None
    
    # Insert document into Supabase
    response = supabase.table(os.getenv("DOCUMENTS_TABLE")).insert({
        'content': content,
        'embedding': embedding,
        'metadata': metadata_dict
    }).execute()
    
    return Document.from_supabase(response.data[0])

@mcp.tool()
async def delete_document(document_id: Union[str, int]) -> bool:
    """
    Delete a document from the database.
    
    Args:
        document_id: The ID of the document to delete (can be string or integer)
        
    Returns:
        True if deletion was successful
    """
    # Convert document_id to string if it's an integer
    document_id_str = str(document_id)
    response = supabase.table(os.getenv("DOCUMENTS_TABLE")).delete().eq('id', document_id_str).execute()
    return len(response.data) > 0

if __name__ == "__main__":
    import uvicorn
    # Run with SSE transport
    mcp.run(transport='sse') 