import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client

async def test_sse_transport():
    server_url = "http://localhost:8000/sse"
    print(f"Connecting to MCP server over HTTP/SSE at {server_url}...")

    async with sse_client(server_url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("✅ Handshake completed over Streamable HTTP / SSE transport!\n")

            # 1. Discover tools over SSE
            tools = await session.list_tools()
            tool_names = [t.name for t in tools.tools]
            print(f"Discovered Tools over SSE: {tool_names}")
            assert "get_itinerary_details" in tool_names

            # 2. Discover resources over SSE
            resources = await session.list_resources()
            print(f"Discovered Resources over SSE: {[r.uri for r in resources.resources]}")

            # 3. Execute tool call over SSE
            res = await session.call_tool("get_itinerary_details", arguments={"itinerary_id": 101})
            print(f"Tool Result over SSE: {res.content[0].text}")

            print("\n✅ Streamable HTTP / SSE Transport Test Passed Successfully!")

if __name__ == "__main__":
    asyncio.run(test_sse_transport())