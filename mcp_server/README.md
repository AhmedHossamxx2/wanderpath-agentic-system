### Folder 2: `mcp_server/README.md` — MCP Server Infrastructure

```markdown
# Model Context Protocol Server (`mcp_server/`)

## Overview
The `mcp_server/` directory contains the Model Context Protocol server implementation for Wanderpath Travel B. The server acts as a defensive middleware layer between LLM agents and the underlying relational database, wrapping data operations in typed, authorized tool handlers.

---

## File Manifest
* `server.py`: Dual-transport MCP server code implementing capabilities initialization, tools, resources, prompts, dynamic notifications, elicitation, progress tracking, and defensive validation.
* `resources/passport_policy.md`: Static markdown document containing international passport validity rules, visa exemption guidelines, and entry regulations exposed via `resources/read`.

---

## Implemented MCP Protocol Concerns

| Protocol Concern | Code Location | Behavioral Description |
|---|---|---|
| **Capability Negotiation** | `run_stdio()`, `run_sse()` | Explicitly declares tool, resource, and prompt support during the `initialize` handshake exchange. |
| **Resources** | `list_resources()`, `read_resource()` | Exposes `policy://passport-rules` read from `resources/passport_policy.md`. |
| **Prompts** | `list_prompts()`, `get_prompt()` | Exposes `draft_refund_explanation` with parameterized arguments (`booking_id`, `client_name`, `refund_amount`). |
| **Dynamic Notifications** | `call_tool("authenticate_manager")` | Emits `send_tool_list_changed()` push notification upon role elevation to dynamically expose privileged write tools. |
| **Elicitation** | `call_tool("cancel_booking")` | Halts execution mid-call for non-refundable flight bookings (`is_refundable = 0`), demanding explicit human `APPROVED` sign-off. |
| **Progress Tracking** | `call_tool("generate_itinerary_report")` | Streams `send_progress_notification()` tokens (`progress` / `total`) across multi-stage processing steps. |
| **Defensive Tool Specs** | `call_tool("modify_booking_dates")` | Enforces strict JSON Schema typing (`additionalProperties: false`), handler-level RBAC (`PERMISSION_DENIED`), and date sequence validation. |

---

## Transport Support
The server natively supports two transport options via CLI flags:

### Standard I/O Transport (`stdio`)
Used for local agent subprocess execution:

powershell
python mcp_server/server.py --transport stdio
Streamable HTTP / Server-Sent Events (sse)
Used for networked deployment over Starlette and Uvicorn:

PowerShell
python mcp_server/server.py --transport sse --port 8000
SSE Stream Endpoint: GET http://localhost:8000/sse

JSON-RPC Message Endpoint: POST http://localhost:8000/messages