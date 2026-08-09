import argparse
import asyncio
import pathlib
import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Route, Mount
import uvicorn

# Initialize MCP Server
app = Server("WanderpathTravelAgent")

# ============================================================================
# SESSION STATE & RBAC
# ============================================================================
CURRENT_ROLE = "junior_agent"  # junior_agent | senior_manager

# ============================================================================
# 1. RESOURCES
# ============================================================================
RESOURCES_DIR = pathlib.Path(__file__).parent / "resources"

@app.list_resources()
async def list_resources() -> list[types.Resource]:
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
    if str(uri) == "policy://passport-rules":
        policy_file = RESOURCES_DIR / "passport_policy.md"
        return policy_file.read_text(encoding="utf-8")
    raise ValueError(f"Unknown resource URI: {uri}")

# ============================================================================
# 2. PROMPTS
# ============================================================================
@app.list_prompts()
async def list_prompts() -> list[types.Prompt]:
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
            messages=[types.PromptMessage(role="user", content=types.TextContent(type="text", text=rendered_text))]
        )
    raise ValueError(f"Unknown prompt: {name}")

# ============================================================================
# 3. DEFENSIVE TOOLS
# ============================================================================
@app.list_tools()
async def list_tools() -> list[types.Tool]:
    tools = [
        types.Tool(
            name="get_itinerary_details",
            description="Fetch travel itinerary details by ID.",
            inputSchema={
                "type": "object",
                "properties": {"itinerary_id": {"type": "integer"}},
                "required": ["itinerary_id"],
                "additionalProperties": False,
            },
        ),
        types.Tool(
            name="authenticate_manager",
            description="Authenticate as a Senior Manager to unlock administrative write tools.",
            inputSchema={
                "type": "object",
                "properties": {"passcode": {"type": "string"}},
                "required": ["passcode"],
                "additionalProperties": False,
            },
        ),
        types.Tool(
            name="cancel_booking",
            description="Cancel a flight or hotel booking by ID. Triggers human elicitation if non-refundable.",
            inputSchema={
                "type": "object",
                "properties": {
                    "booking_id": {"type": "integer"},
                    "reason": {"type": "string"},
                    "human_confirmation": {
                        "type": "string",
                        "description": "Optional human sign-off response ('APPROVED' or 'REJECTED').",
                    },
                },
                "required": ["booking_id", "reason"],
                "additionalProperties": False,
            },
        ),
        types.Tool(
            name="generate_itinerary_report",
            description="Long-running operation: Compile a comprehensive multi-city travel itinerary with progress updates.",
            inputSchema={
                "type": "object",
                "properties": {
                    "destination": {"type": "string"},
                    "duration_days": {"type": "integer"},
                },
                "required": ["destination", "duration_days"],
                "additionalProperties": False,
            },
        ),
        types.Tool(
            name="modify_booking_dates",
            description="[DEFENSIVE WRITE TOOL] Modify start and end dates for an existing travel booking.",
            inputSchema={
                "type": "object",
                "properties": {
                    "booking_id": {"type": "integer", "minimum": 1},
                    "start_date": {"type": "string", "description": "YYYY-MM-DD format"},
                    "end_date": {"type": "string", "description": "YYYY-MM-DD format"},
                },
                "required": ["booking_id", "start_date", "end_date"],
                "additionalProperties": False,
            },
        ),
    ]

    if CURRENT_ROLE == "senior_manager":
        tools.append(
            types.Tool(
                name="override_cancellation_fee",
                description="[PRIVILEGED] Override and waive cancellation fees on non-refundable bookings.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "booking_id": {"type": "integer"},
                        "waived_amount": {"type": "number"},
                    },
                    "required": ["booking_id", "waived_amount"],
                    "additionalProperties": False,
                },
            )
        )

    return tools

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    global CURRENT_ROLE

    if name == "get_itinerary_details":
        it_id = arguments.get("itinerary_id")
        return [types.TextContent(type="text", text=f"Itinerary #{it_id}: Active (London Autumn Break)")]

    elif name == "authenticate_manager":
        passcode = arguments.get("passcode")
        if passcode == "admin123":
            CURRENT_ROLE = "senior_manager"
            try:
                ctx = app.request_context
                if ctx and ctx.session:
                    await ctx.session.send_tool_list_changed()
            except Exception:
                pass
            return [types.TextContent(type="text", text="Authentication successful! Senior Manager role activated.")]
        else:
            return [types.TextContent(type="text", text="Authentication failed: Invalid passcode.")]

    elif name == "cancel_booking":
        b_id = arguments.get("booking_id")
        reason = arguments.get("reason", "Customer request")
        confirmation = arguments.get("human_confirmation")
        is_refundable = False if b_id == 3 else True

        if not is_refundable:
            if not confirmation:
                return [
                    types.TextContent(
                        type="text",
                        text=(
                            f"ELICITATION_REQUIRED: Booking #{b_id} is NON-REFUNDABLE! "
                            f"Canceling will incur a $250.00 cancellation fee. "
                            f"Please respond with 'human_confirmation': 'APPROVED' or 'REJECTED' to proceed."
                        ),
                    )
                ]
            if confirmation.upper() != "APPROVED":
                return [types.TextContent(type="text", text=f"ABORTED: Cancellation for non-refundable Booking #{b_id} was rejected.")]
            return [types.TextContent(type="text", text=f"SUCCESS (ELICITED): Non-refundable Booking #{b_id} cancelled with human sign-off. Reason: {reason}")]

        return [types.TextContent(type="text", text=f"SUCCESS: Refundable Booking #{b_id} cancelled successfully. Full refund issued.")]

    elif name == "generate_itinerary_report":
        dest = arguments.get("destination")
        days = arguments.get("duration_days")
        try:
            session = app.request_context.session
            steps = 4
            for idx in range(1, steps + 1):
                if session:
                    await session.send_progress_notification(
                        progress_token=f"itinerary-{dest}",
                        progress=float(idx),
                        total=float(steps),
                    )
                await asyncio.sleep(0.2)
        except Exception:
            pass

        return [types.TextContent(type="text", text=f"COMPLETED: Generated {days}-day itinerary report for {dest}. All 4 processing stages finished successfully.")]

    elif name == "modify_booking_dates":
        if CURRENT_ROLE != "senior_manager":
            return [types.TextContent(type="text", text="PERMISSION_DENIED: Senior Manager authorization required to modify booking dates.")]

        b_id = arguments.get("booking_id")
        s_date = arguments.get("start_date")
        e_date = arguments.get("end_date")

        if e_date <= s_date:
            return [types.TextContent(type="text", text=f"VALIDATION_ERROR: End date ({e_date}) must be strictly after start date ({s_date}).")]

        return [types.TextContent(type="text", text=f"SUCCESS: Booking #{b_id} dates updated to {s_date} -> {e_date}.")]

    elif name == "override_cancellation_fee":
        if CURRENT_ROLE != "senior_manager":
            raise PermissionError("Handler Auth Failed: Senior Manager role required.")
        b_id = arguments.get("booking_id")
        amt = arguments.get("waived_amount")
        return [types.TextContent(type="text", text=f"SUCCESS: Waived ${amt} cancellation fee for Booking #{b_id}.")]

    raise ValueError(f"Unknown tool: {name}")

# [Keep all your existing code down to the run_stdio block]
# Ensure these imports are at the top of your file:
# from starlette.requests import Request
# from starlette.routing import Route, Mount

# ============================================================================
# DUAL TRANSPORT RUNNER (SSE / HTTP vs STDIO)
# ============================================================================
async def run_stdio():
    print("Starting MCP Server over stdio transport...")
    async with stdio_server() as (read_stream, write_stream):
        init_options = app.create_initialization_options()
        await app.run(read_stream, write_stream, init_options)

def run_sse(host: str = "0.0.0.0", port: int = 8000):
    import uvicorn
    from mcp.server.sse import SseServerTransport

    print(f"🌐 Starting MCP Server over Streamable HTTP / SSE transport on http://{host}:{port}/sse")
    
    # Initialize the SSE transport pointing to /messages
    sse_transport = SseServerTransport("/messages")

    # A pure, lightweight ASGI application (Bypasses Starlette entirely to prevent crashes)
    async def asgi_app(scope, receive, send):
        if scope["type"] == "lifespan":
            while True:
                message = await receive()
                if message["type"] == "lifespan.startup":
                    await send({"type": "lifespan.startup.complete"})
                elif message["type"] == "lifespan.shutdown":
                    await send({"type": "lifespan.shutdown.complete"})
                    break
        elif scope["type"] == "http":
            path = scope.get("path", "")
            if path == "/sse":
                # Safely bind the read/write streams
                async with sse_transport.connect_sse(scope, receive, send) as (read_stream, write_stream):
                    init_options = app.create_initialization_options()
                    await app.run(read_stream, write_stream, init_options)
            elif path == "/messages":
                # Safely handle the POST JSON-RPC payload
                await sse_transport.handle_post_message(scope, receive, send)
            else:
                # 404 for unmatched routes
                await send({"type": "http.response.start", "status": 404, "headers": []})
                await send({"type": "http.response.body", "body": b""})

    # Run the raw ASGI app via Uvicorn
    uvicorn.run(asgi_app, host=host, port=port, log_level="info")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Wanderpath Travel Agent MCP Server")
    # Change default from "sse" to "stdio"
    parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio", help="Transport mechanism (default: stdio)")
    parser.add_argument("--port", type=int, default=8000, help="Port for SSE transport")
    args = parser.parse_args()

    if args.transport == "stdio":
        asyncio.run(run_stdio())
    else:
        run_sse(port=args.port)