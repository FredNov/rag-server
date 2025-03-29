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
            
            # Try to add a test document
            result = await session.call_tool("add_document", {
                "content": "This is a test document",
                "metadata": {"source": "test"}
            })
            print("Add document result:", result)

if __name__ == "__main__":
    asyncio.run(test_connection()) 