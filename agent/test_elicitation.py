import asyncio
import pathlib
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_elicitation():
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

            # TEST 1: Refundable Booking (No Elicitation Needed)
            print("--- Test 1: Canceling Refundable Booking #1 ---")
            res1 = await session.call_tool(
                "cancel_booking",
                arguments={"booking_id": 1, "reason": "Schedule change"}
            )
            print(f"Result: {res1.content[0].text}\n")

            # TEST 2: Non-Refundable Booking (Triggers Elicitation Pause)
            print("--- Test 2: Canceling Non-Refundable Booking #3 (First Attempt) ---")
            res2 = await session.call_tool(
                "cancel_booking",
                arguments={"booking_id": 3, "reason": "Emergency"}
            )
            print(f"Result: {res2.content[0].text}\n")
            assert "ELICITATION_REQUIRED" in res2.content[0].text, "Should pause and demand human sign-off!"

            # TEST 3: Responding to Elicitation with Human Approval
            print("--- Test 3: Responding to Elicitation with Human Sign-off ('APPROVED') ---")
            res3 = await session.call_tool(
                "cancel_booking",
                arguments={
                    "booking_id": 3,
                    "reason": "Emergency",
                    "human_confirmation": "APPROVED"
                }
            )
            print(f"Result: {res3.content[0].text}\n")
            assert "SUCCESS (ELICITED)" in res3.content[0].text, "Should finalize state with approval!"

            print("✅ Elicitation test passed successfully!")

if __name__ == "__main__":
    asyncio.run(test_elicitation())