import asyncio
import os
from dotenv import load_dotenv
from mcp.client import Client
from mcp.transport.sse import SSETransport

# Load environment variables
load_dotenv()

async def main():
    # Initialize the client with SSE transport
    transport = SSETransport("http://localhost:3000/sse")
    client = Client(transport)
    
    # List available tools
    print("\nAvailable tools:")
    for tool in client.tools:
        print(f"- {tool.name}: {tool.description}")
    
    # Delete existing test documents
    print("\nDeleting existing test documents...")
    try:
        await client.execute_tool("delete_note", {"note_id": 638})
        print("Successfully deleted test document")
    except Exception as e:
        print(f"Error deleting document: {str(e)}")
    
    # Add a test document with new metadata structure
    print("\nAdding test document...")
    test_content = "I need to visit the dentist next week for a checkup. The appointment is scheduled for Monday at 2 PM."
    test_metadata = {
        "source": "from_chat",
        "file_id": "test_chat_1",
        "blobType": "text",
        "content_length": len(test_content),
        "is_truncated": False,
        "processing_info": {
            "model": "text-embedding-3-small",
            "processed_at": "2025-03-29T04:04:20.377298",
            "embedding_dimension": 1536
        }
    }
    
    try:
        result = await client.execute_tool("add_note", {
            "content": test_content,
            "metadata": test_metadata
        })
        print(f"Successfully added document with ID: {result['id']}")
        print(f"Metadata: {result['metadata']}")
    except Exception as e:
        print(f"Error adding document: {str(e)}")
    
    # Search for notes about dentist
    print("\nSearching for notes about dentist...")
    try:
        results = await client.execute_tool("search_note", {
            "query": "dentist",
            "limit": 5
        })
        print("\nSearch results:")
        for result in results:
            print(f"\nID: {result['id']}")
            print(f"Content: {result['content']}")
            print(f"Metadata: {result['metadata']}")
            print(f"Similarity: {result['similarity']}")
    except Exception as e:
        print(f"Error searching notes: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 