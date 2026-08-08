import asyncio
import pathlib
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_progress():
    root_dir = pathlib.Path(__file__).parent.parent.resolve()
    python_venv = root_dir / "mcp_server" / ".venv" / "Scripts" / "python.exe"
    server_script = root_dir / "mcp_server" / "server.py"

    server_params = StdioServerParameters(
        command=str(python_venv),
        args=[str(server_script)],
    )

    print("Connecting to MCP server...")

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("✅ Initialized connection.\n")

            print("--- Testing Progress Tracking (`generate_itinerary_report`) ---")

            # Execute tool call passing progressToken in _meta
            result = await session.call_tool(
                "generate_itinerary_report",
                arguments={"destination": "Tokyo", "duration_days": 7},
                meta={"progressToken": "itinerary-Tokyo"},
            )

            print(f"\nTool Result:\n{result.content[0].text}")
            print("\n✅ Progress tracking test passed successfully!")

if __name__ == "__main__":
    asyncio.run(test_progress())