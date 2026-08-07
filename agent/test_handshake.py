import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_handshake():
    # Define how to run your server
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server/server.py"],
    )

    # Connect via stdio
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Executes the initialize request and processes initialized response
            await session.initialize()
            
            # ACCEPTANCE CRITERIA: Check the capabilities explicitly
            print("Handshake successful!")
            # Call get_server_capabilities() as a method
            print("Server Capabilities:", session.get_server_capabilities())

if __name__ == "__main__":
    asyncio.run(test_handshake())