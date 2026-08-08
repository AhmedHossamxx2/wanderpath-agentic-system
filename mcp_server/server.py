import asyncio
import pathlib
import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

app = Server("WanderpathTravelAgent")

# ============================================================================
# SESSION STATE & RBAC
# Tracks runtime role state for the active stdio session
# ============================================================================
CURRENT_ROLE = "junior_agent"  # Default role: junior_agent | senior_manager

# ============================================================================
# RESOURCES & PROMPTS (Preserved from Step 3)
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
# DYNAMIC TOOLS & NOTIFICATIONS
# ============================================================================
@app.list_tools()
async def list_tools() -> list[types.Tool]:
    """Dynamically return tools based on CURRENT_ROLE session state."""
    # Base tools available to all roles
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
                        "description": "Optional human sign-off response for non-refundable cancellation elicitation.",
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
    ]

    # Manager-only privileged tool
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
            # FIX: Properly extract the active session from the ContextVar
            await app.request_context.session.send_tool_list_changed()
            
            return [types.TextContent(type="text", text="Authentication successful! Senior Manager role activated. Tools list updated.")]
        else:
            return [types.TextContent(type="text", text="Authentication failed: Invalid passcode.")]

    elif name == "override_cancellation_fee":
        if CURRENT_ROLE != "senior_manager":
            raise PermissionError("Handler Auth Failed: Senior Manager role required.")
        b_id = arguments.get("booking_id")
        amt = arguments.get("waived_amount")
        return [types.TextContent(type="text", text=f"SUCCESS: Waived ${amt} cancellation fee for Booking #{b_id}.")]

    elif name == "cancel_booking":
        b_id = arguments.get("booking_id")
        reason = arguments.get("reason", "Customer request")
        confirmation = arguments.get("human_confirmation")

        # Mock database lookup: Booking #3 is non-refundable! (Sophia Chen's flight)
        # Booking #1 is refundable.
        is_refundable = False if b_id == 3 else True

        if not is_refundable:
            # Check if human sign-off was provided via elicitation
            if not confirmation:
                # PROTOCOL REQUIREMENT: Pause mid-call and issue elicitation request
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
                return [types.TextContent(type="text", text=f"ABORTED: Cancellation for non-refundable Booking #{b_id} was rejected by human operator.")]

            return [
                types.TextContent(
                    type="text",
                    text=f"SUCCESS (ELICITED): Non-refundable Booking #{b_id} cancelled with human sign-off. Fee charged: $250.00. Reason: {reason}",
                )
            ]

        # Standard refundable cancellation
        return [types.TextContent(type="text", text=f"SUCCESS: Refundable Booking #{b_id} cancelled successfully. Full refund issued.")]

    elif name == "generate_itinerary_report":
        dest = arguments.get("destination")
        days = arguments.get("duration_days")
        session = app.request_context.session

        steps = [
            f"Searching flight matrix for {dest}...",
            f"Checking hotel availability for {days} nights...",
            "Validating passport and visa entry policies...",
            "Rendering final itinerary document...",
        ]
        total_steps = len(steps)

        for idx, step_msg in enumerate(steps, start=1):
            if session:
                # Send progress notification over active stdio session
                await session.send_progress_notification(
                    progress_token=f"itinerary-{dest}",
                    progress=float(idx),
                    total=float(total_steps),
                )
            await asyncio.sleep(0.4)  # Simulate workload

        return [
            types.TextContent(
                type="text",
                text=f"COMPLETED: Generated {days}-day itinerary report for {dest}. All 4 processing stages finished successfully.",
            )
        ]
        dest = arguments.get("destination")
        days = arguments.get("duration_days")
        ctx = app.request_context

        steps = [
            f"Searching flight matrix for {dest}...",
            f"Checking hotel availability for {days} nights...",
            "Validating passport and visa entry policies...",
            "Rendering final itinerary document...",
        ]
        total_steps = len(steps)

        for idx, step_msg in enumerate(steps, start=1):
            # PROTOCOL REQUIREMENT: Stream progress notifications over stdio session
            if ctx and ctx.session:
                await ctx.session.send_progress_notification(
                    progress_token=f"itinerary-{dest}",
                    progress=float(idx),
                    total=float(total_steps),
                )
            await asyncio.sleep(0.5)  # Simulate multi-step processing workload

        return [
            types.TextContent(
                type="text",
                text=f"COMPLETED: Generated {days}-day itinerary report for {dest}. All 4 processing stages finished successfully.",
            )
        ]

    raise ValueError(f"Unknown tool: {name}")

# ============================================================================
# SERVER EXECUTION
# ============================================================================
async def main():
    async with stdio_server() as (read_stream, write_stream):
        init_options = app.create_initialization_options()
        await app.run(read_stream, write_stream, init_options)

if __name__ == "__main__":
    asyncio.run(main())