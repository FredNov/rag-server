import asyncio
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

async def test_connection():
    async with sse_client(url="http://localhost:3000/sse") as (read, write):
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