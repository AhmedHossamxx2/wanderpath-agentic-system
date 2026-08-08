import asyncio
import pathlib
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_defensive_design():
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

            # STEP 1: Test Unprivileged Call
            print("--- Step 1: Testing Auth Check Failure (As Junior Agent) ---")
            auth_fail_res = await session.call_tool(
                "modify_booking_dates",
                arguments={"booking_id": 1, "start_date": "2026-09-01", "end_date": "2026-09-10"}
            )
            print(f"Result: {auth_fail_res.content[0].text}")
            assert "PERMISSION_DENIED" in auth_fail_res.content[0].text, "Should reject unprivileged call!"
            print("✅ Handler correctly rejected unprivileged call!\n")

            # Authenticate as Senior Manager
            await session.call_tool("authenticate_manager", arguments={"passcode": "admin123"})
            await asyncio.sleep(0.5)

            # STEP 2: Test Validation Error (Invalid Date Order)
            print("--- Step 2: Testing Server-Side Validation Failure (Invalid Date Range) ---")
            val_res = await session.call_tool(
                "modify_booking_dates",
                arguments={"booking_id": 1, "start_date": "2026-09-10", "end_date": "2026-09-01"}
            )
            print(f"Result: {val_res.content[0].text}")
            assert "VALIDATION_ERROR" in val_res.content[0].text, "Should reject end_date <= start_date!"
            print("✅ Server correctly caught invalid business logic!\n")

            # STEP 3: Test Valid Tool Execution
            print("--- Step 3: Testing Valid Defensive Write Execution ---")
            valid_res = await session.call_tool(
                "modify_booking_dates",
                arguments={"booking_id": 1, "start_date": "2026-09-01", "end_date": "2026-09-10"}
            )
            print(f"Result: {valid_res.content[0].text}")
            assert "SUCCESS" in valid_res.content[0].text, "Should successfully update dates!"

            print("\n✅ Defensive tool design test passed successfully!")

if __name__ == "__main__":
    asyncio.run(test_defensive_design())