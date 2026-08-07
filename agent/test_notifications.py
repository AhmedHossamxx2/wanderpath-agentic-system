import asyncio
import pathlib
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_notifications():
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

            # STEP 1: Inspect initial tool set (Junior Agent)
            print("--- Step 1: Initial Tools (Junior Agent Role) ---")
            initial_tools = await session.list_tools()
            initial_names = [t.name for t in initial_tools.tools]
            print(f"Available Tools: {initial_names}")
            assert "override_cancellation_fee" not in initial_names, "Privileged tool should NOT be visible yet!"

            # STEP 2: Authenticate as Senior Manager
            print("\n--- Step 2: Authenticating as Senior Manager ---")
            auth_result = await session.call_tool(
                "authenticate_manager",
                arguments={"passcode": "admin123"}
            )
            print(f"Auth Response: {auth_result.content[0].text}")

            # STEP 3: Wait for notification signal over stdio
            print("\nWaiting for tools/list_changed push notification...")
            await asyncio.sleep(1.0) # Yield control so the background read task receives the push

            print("\n--- Step 3: Re-fetching Tools Post-Notification ---")
            updated_tools = await session.list_tools()
            updated_names = [t.name for t in updated_tools.tools]
            print(f"Updated Available Tools: {updated_names}")

            # STEP 4: Call privileged tool
            assert "override_cancellation_fee" in updated_names, "Privileged tool should now be unlocked!"
            override_result = await session.call_tool(
                "override_cancellation_fee",
                arguments={"booking_id": 3, "waived_amount": 250.0}
            )
            print(f"\nPrivileged Tool Execution Result:\n{override_result.content[0].text}")
            print("\n✅ Notifications test passed successfully!")

if __name__ == "__main__":
    asyncio.run(test_notifications())