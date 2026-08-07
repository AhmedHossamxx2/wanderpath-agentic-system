import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

# Initialize the strict, silent low-level server
app = Server("WanderpathTravelAgent")

# ============================================================================
# 1. RESOURCES
# Static policy manuals exposed via resources/list and resources/read
# ============================================================================
PASSPORT_POLICY_TEXT = """
# Wanderpath Travel B. - International Passport & Entry Regulations

1. **Minimum Validity Requirement**:
   - All international flight bookings require a passport valid for at least 6 months beyond the departure date.
   - For European Union (Schengen Area) destinations, passports must have been issued within the last 10 years.

2. **Expired Passports**:
   - Bookings associated with expired passports MUST be flagged immediately.
   - No flight ticket issuance or international hotel check-in can proceed with an expired passport record.
"""

@app.list_resources()
async def list_resources() -> list[types.Resource]:
    """Declare available resources to the client."""
    return [
        types.Resource(
            uri="policy://passport-rules",
            name="Passport & Entry Policy",
            description="Static international passport validity rules.",
            mimeType="text/plain",
        )
    ]

@app.read_resource()
async def read_resource(uri: str | types.AnyUrl) -> str | bytes:
    """Return the actual content of the requested resource."""
    # FIX: Cast uri to a string before comparison!
    if str(uri) == "policy://passport-rules":
        return PASSPORT_POLICY_TEXT
    raise ValueError(f"Unknown resource URI: {uri}")

# ============================================================================
# 2. PROMPTS
# Reusable, parameterized prompt templates exposed via prompts/list and prompts/get
# ============================================================================
@app.list_prompts()
async def list_prompts() -> list[types.Prompt]:
    """Declare available prompt templates and their required parameters."""
    return [
        types.Prompt(
            name="draft_refund_explanation",
            description="Draft a professional refund explanation email.",
            arguments=[
                types.PromptArgument(name="booking_id", description="ID of the booking", required=True),
                types.PromptArgument(name="client_name", description="Name of the client", required=True),
                types.PromptArgument(name="refund_amount", description="Amount refunded", required=True),
            ]
        )
    ]

@app.get_prompt()
async def get_prompt(name: str, arguments: dict[str, str] | None) -> types.GetPromptResult:
    """Render and return the requested prompt template using the provided arguments."""
    if name == "draft_refund_explanation":
        args = arguments or {}
        b_id = args.get("booking_id", "[ID]")
        c_name = args.get("client_name", "[Name]")
        r_amt = args.get("refund_amount", "[Amount]")
        
        rendered_text = (
            f"You are a polite travel assistant for Wanderpath Travel B.\n\n"
            f"Draft a professional customer service email to client '{c_name}' regarding "
            f"their recent refund request for booking ID '{b_id}'.\n\n"
            f"Key details to include:\n"
            f"- Acknowledge their cancellation request for booking ID {b_id}.\n"
            f"- State clearly that a refund of ${r_amt} has been processed according to Wanderpath policy.\n"
            f"- Thank them for choosing Wanderpath Travel B. and offer further assistance if needed."
        )
        
        return types.GetPromptResult(
            description="Draft refund email",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(type="text", text=rendered_text)
                )
            ]
        )
    raise ValueError(f"Unknown prompt: {name}")

# ============================================================================
# REQUIRED: Empty Tool Handlers to satisfy the initialization handshake
# ============================================================================
@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return []

# ============================================================================
# SERVER EXECUTION
# ============================================================================
async def main():
    async with stdio_server() as (read_stream, write_stream):
        # Create initialization options strictly declaring our capabilities
        init_options = app.create_initialization_options()
        await app.run(read_stream, write_stream, init_options)

if __name__ == "__main__":
    asyncio.run(main())