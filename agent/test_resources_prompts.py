import asyncio
import pathlib
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_resources_and_prompts():
    # Resolve absolute paths to python interpreter inside virtual environment
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

            # ----------------------------------------------------------------
            # TEST 1: Resources (List & Read)
            # ----------------------------------------------------------------
            print("--- Testing Resources ---")
            resources = await session.list_resources()
            print(f"Discovered Resources: {[r.uri for r in resources.resources]}")
            
            # Read the passport policy resource
            policy_resource = await session.read_resource("policy://passport-rules")
            print("\nSuccessfully fetched 'policy://passport-rules':")
            print("=" * 50)
            print(policy_resource.contents[0].text.strip()[:250] + "...\n[Truncated]")
            print("=" * 50)

            # ----------------------------------------------------------------
            # TEST 2: Prompts (List & Get)
            # ----------------------------------------------------------------
            print("\n--- Testing Prompts ---")
            prompts = await session.list_prompts()
            print(f"Discovered Prompts: {[p.name for p in prompts.prompts]}")

            # Fetch the parameterized prompt
            prompt_result = await session.get_prompt(
                "draft_refund_explanation",
                arguments={
                    "booking_id": "3",
                    "client_name": "Sophia Chen",
                    "refund_amount": "1000.00"
                }
            )
            print("\nSuccessfully rendered 'draft_refund_explanation' prompt template:")
            print("-" * 50)
            print(prompt_result.messages[0].content.text)
            print("-" * 50)

if __name__ == "__main__":
    asyncio.run(test_resources_and_prompts())