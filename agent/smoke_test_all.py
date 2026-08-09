import asyncio
import pathlib
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def run_master_smoke_test():
    root_dir = pathlib.Path(__file__).parent.parent.resolve()
    python_venv = root_dir / "mcp_server" / ".venv" / "Scripts" / "python.exe"
    server_script = root_dir / "mcp_server" / "server.py"

    server_params = StdioServerParameters(
        command=str(python_venv),
        args=[str(server_script), "--transport", "stdio"], # Explicitly set stdio mode
    )

    print("==================================================================")
    print("🚀 STARTING MASTER MCP PROTOCOL SMOKE TEST (ALL 7 CONCERNS)")
    print("==================================================================\n")

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # ------------------------------------------------------------
            # CONCERN 1: Handshake & Capability Negotiation
            # ------------------------------------------------------------
            print("1️⃣ Testing Handshake & Capability Negotiation...")
            await session.initialize()
            caps = session.get_server_capabilities()
            assert caps is not None
            print("   ✅ Handshake initialized. Server Capabilities Negotiated.\n")

            # ------------------------------------------------------------
            # CONCERN 2: Read-Only Policy Resources
            # ------------------------------------------------------------
            print("2️⃣ Testing Policy Resource (`policy://passport-rules`)...")
            res = await session.read_resource("policy://passport-rules")
            assert len(res.contents[0].text) > 0
            print("   ✅ Successfully fetched static policy resource text.\n")

            # ------------------------------------------------------------
            # CONCERN 3: Parameterized Prompt Templates
            # ------------------------------------------------------------
            print("3️⃣ Testing Parameterized Prompt Template (`draft_refund_explanation`)...")
            prompt = await session.get_prompt(
                "draft_refund_explanation",
                arguments={"booking_id": "3", "client_name": "Sophia", "refund_amount": "250.0"}
            )
            assert "Sophia" in prompt.messages[0].content.text
            print("   ✅ Successfully rendered prompt template with arguments.\n")

            # ------------------------------------------------------------
            # CONCERN 4: Dynamic Tool Notifications (RBAC Role Change)
            # ------------------------------------------------------------
            print("4️⃣ Testing Dynamic Notifications & RBAC Role Elevation...")
            initial_tools = [t.name for t in (await session.list_tools()).tools]
            print(f"   Initial tools (Junior): {initial_tools}")
            
            # Auth as Manager
            await session.call_tool("authenticate_manager", arguments={"passcode": "admin123"})
            await asyncio.sleep(0.5)
            
            updated_tools = [t.name for t in (await session.list_tools()).tools]
            print(f"   Updated tools (Manager): {updated_tools}")
            assert "override_cancellation_fee" in updated_tools
            print("   ✅ Role elevation triggered dynamic tool list expansion.\n")

            # ------------------------------------------------------------
            # CONCERN 5: Elicitation / Human-in-the-loop Pause
            # ------------------------------------------------------------
            print("5️⃣ Testing Elicitation Mid-Call Pause (`cancel_booking`)...")
            # Step A: Trigger Elicitation
            el_res = await session.call_tool("cancel_booking", arguments={"booking_id": 3, "reason": "Emergency"})
            assert "ELICITATION_REQUIRED" in el_res.content[0].text
            print("   ✅ Server correctly paused mid-call to demand human sign-off.")
            
            # Step B: Provide Sign-off
            el_ok = await session.call_tool("cancel_booking", arguments={"booking_id": 3, "reason": "Emergency", "human_confirmation": "APPROVED"})
            assert "SUCCESS (ELICITED)" in el_ok.content[0].text
            print("   ✅ Completed cancellation after receiving human confirmation.\n")

            # ------------------------------------------------------------
            # CONCERN 6: Progress Tracking
            # ------------------------------------------------------------
            print("6️⃣ Testing Progress Tracking (`generate_itinerary_report`)...")
            prog_res = await session.call_tool(
                "generate_itinerary_report",
                arguments={"destination": "Tokyo", "duration_days": 7},
                meta={"progressToken": "tokyo-progress"},
            )
            assert "COMPLETED" in prog_res.content[0].text
            print("   ✅ Completed multi-stage progress tracking operation.\n")

            # ------------------------------------------------------------
            # CONCERN 7: Defensive Tool Validation & Auth Check
            # ------------------------------------------------------------
            print("7️⃣ Testing Defensive Validation & Auth (`modify_booking_dates`)...")
            val_res = await session.call_tool(
                "modify_booking_dates",
                arguments={"booking_id": 1, "start_date": "2026-09-10", "end_date": "2026-09-01"}
            )
            assert "VALIDATION_ERROR" in val_res.content[0].text
            print("   ✅ Caught invalid date order validation error.")

            def_ok = await session.call_tool(
                "modify_booking_dates",
                arguments={"booking_id": 1, "start_date": "2026-09-01", "end_date": "2026-09-10"}
            )
            assert "SUCCESS" in def_ok.content[0].text
            print("   ✅ Defensive write tool mutated state successfully.\n")

    print("==================================================================")
    print("🎉 ALL 7 MCP CONCERNS VERIFIED SUCCESSFULLY! READY FOR SUBMISSION!")
    print("==================================================================")

if __name__ == "__main__":
    asyncio.run(run_master_smoke_test())