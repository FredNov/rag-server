import asyncio
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from dotenv import load_dotenv, find_dotenv
import os
from pathlib import Path

# Load environment variables from .env file
env_path = find_dotenv(usecwd=True)
if not env_path:
    raise FileNotFoundError("No .env file found. Please create a .env file with required configuration.")

# Load the .env file
load_dotenv(env_path, override=True)

# Get port from .env file
PORT = os.getenv("PORT")
if not PORT:
    raise ValueError("PORT not found in .env file. Please add PORT to your .env file.")

PORT = int(PORT)

async def test_connection():
    async with sse_client(url=f"http://localhost:{PORT}/sse") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # List available tools
            tools = await session.list_tools()
            print("Available tools:", tools)
            
            # First delete any existing test documents
            print("\nDeleting existing test documents...")
            try:
                result = await session.call_tool("delete_note", {
                    "note_id": 638  # ID from previous run
                })
                print("Delete result:", result)
            except Exception as e:
                print("No existing document to delete")
            
            # Add a test document
            print("\nAdding test document...")
            add_result = await session.call_tool("add_note", {
                "content": "I need to visit the dentist next week for a checkup. The appointment is scheduled for Monday at 2 PM.",
                "metadata": {
                    "source": "test",
                    "file_id": "test1"
                }
            })
            print("Add document result:", add_result)
            
            # Search for notes about dentist
            print("\nSearching for notes about dentist...")
            result = await session.call_tool("search_note", {
                "query": "dentist",
                "limit": 5  # Optional: limit the number of results
            })
            print("\nSearch results for 'dentist':", result)

if __name__ == "__main__":
    asyncio.run(test_connection()) 