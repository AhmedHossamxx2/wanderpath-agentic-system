# Model Context Protocol Server (`mcp_server/`)

## Overview
The `mcp_server/` directory contains the production Model Context Protocol server implementation for **Wanderpath Travel B.** The server acts as a defensive middleware layer between LLM agents and the underlying relational database, wrapping data operations in typed, authorized tool handlers and supporting live runtime tool registration and deregistration from the platform.

---

## File Manifest
* `server.py`: Dual-transport MCP server code implementing capabilities initialization, tools, resources, prompts, dynamic notifications, elicitation, progress tracking, defensive validation, and the runtime dynamic tool registry with REST API integration.
* `resources/passport_policy.md`: Static markdown document containing international passport validity rules, visa exemption guidelines, and entry regulations exposed via `resources/read`.

---

## Implemented MCP Protocol Concerns

| Protocol Concern | Code Location | Behavioral Description |
|---|---|---|
| **Capability Negotiation** | `run_stdio()`, `run_sse()` | Explicitly declares tool, resource, and prompt support during the `initialize` handshake exchange. |
| **Resources** | `list_resources()`, `read_resource()` | Exposes `policy://passport-rules` read from `resources/passport_policy.md`. |
| **Prompts** | `list_prompts()`, `get_prompt()` | Exposes `draft_refund_explanation` with parameterized arguments (`booking_id`, `client_name`, `refund_amount`). |
| **Dynamic Notifications** | `call_tool("authenticate_manager")`, `register_dynamic_tool()` | Emits `send_tool_list_changed()` push notification upon role elevation and runtime tool mutations to dynamically update agent toolsets without disconnecting. |
| **Runtime Tool Management** | `register_dynamic_tool()`, `set_tool_enabled()` | Allows the platform admin panel to add, remove, enable, or disable tools at runtime via JSON-RPC or REST API (`/api/tools`). |
| **Elicitation** | `call_tool("cancel_booking")` | Halts execution mid-call for non-refundable flight bookings (`is_refundable = 0`), demanding explicit human `APPROVED` sign-off. |
| **Progress Tracking** | `call_tool("generate_itinerary_report")` | Streams `send_progress_notification()` tokens (`progress` / `total`) across multi-stage processing steps. |
| **Defensive Tool Specs** | `call_tool("modify_booking_dates")` | Enforces strict JSON Schema typing (`additionalProperties: false`), handler-level RBAC (`PERMISSION_DENIED`), and date sequence validation. |

---

## Transport & REST Endpoints

### 1. Standard I/O Transport (`stdio`)
Used for local agent subprocess execution:
```bash
python mcp_server/server.py --transport stdio
```

### 2. Streamable HTTP / Server-Sent Events (`sse`)
Used for networked deployment over Starlette and Uvicorn:
```bash
python mcp_server/server.py --transport sse --port 8000
```
- **SSE Stream Endpoint:** `GET http://localhost:8000/sse`
- **JSON-RPC Message Endpoint:** `POST http://localhost:8000/messages`
- **Admin Tool List Endpoint:** `GET http://localhost:8000/api/tools`
- **Admin Tool Toggle Endpoint:** `POST http://localhost:8000/api/tools/toggle`
- **Admin Tool Register Endpoint:** `POST http://localhost:8000/api/tools/register`

---

## Verification
Run the Sub-Module 1 verification test suite to validate all MCP features:
```bash
python agent/test_dynamic_mcp_rag.py
```