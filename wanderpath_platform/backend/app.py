"""
Wanderpath Travel Agency - Full-Stack Platform API
==================================================
Starlette ASGI server serving:
1. Multi-Agent Chat Router (3 State Graph Agents + Planning Agent + Memory/RAG Agent)
2. Live MCP Dynamic Tool Management & RBAC Controls
3. Live RAG Document Ingestion & Deletion
4. Admin Human-in-the-Loop (HITL) Resolution
5. Admin Failure Ticket Inspection & Mid-Node Recovery
"""

import asyncio
import json
import logging
import os
import pathlib
import sys
import uuid
from typing import Any, Dict, List, Optional

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route

# Ensure project root is in sys.path
project_root = pathlib.Path(__file__).parent.parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

mcp_server_dir = project_root / "mcp_server"
if str(mcp_server_dir) not in sys.path:
    sys.path.insert(0, str(mcp_server_dir))

from server import (
    register_dynamic_tool,
    deregister_dynamic_tool,
    set_tool_enabled,
    get_all_registered_tools,
    broadcast_tool_list_changed,
)
from rag.vector_store import WanderpathVectorStore
from state_graph.checkpointer import DurableCheckpointer
from state_graph.recovery.hitl_engine import HITLEngine
from state_graph.recovery.ticket_engine import TicketEngine
from state_graph.graphs.visa_graph import create_visa_processing_graph
from state_graph.graphs.dispute_graph import create_dispute_reconciliation_graph
from state_graph.graphs.medevac_graph import create_medevac_repatriation_graph
from planning.routing.route_subtask import route_subtask
from planning.algorithms_glue.plan_and_solve import run_plan_and_solve
from planning.adapters.model_provider import WanderpathModelProvider

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WanderpathPlatformAPI")

# Persistent Shared Subsystems
DB_PATH = str(project_root / "db" / "wanderpath.sqlite3")
checkpointer = DurableCheckpointer(db_path=DB_PATH)
hitl_engine = HITLEngine(db_path=DB_PATH)
ticket_engine = TicketEngine(db_path=DB_PATH)
vector_db = WanderpathVectorStore(collection_name="wanderpath_knowledge", persist_dir=str(project_root / "rag" / "chroma_db"))

# Seed baseline policies if empty
if len(vector_db.list_documents()) == 0:
    vector_db.add_document(
        doc_id="policy_hotel_alpine",
        document="Alpine Resort & Spa Policy: Cancellations must be made at least 14 days prior to check-in for a 100% full refund.",
        metadata={"property": "Alpine Resort & Spa", "category": "cancellation"}
    )
    vector_db.add_document(
        doc_id="policy_airline_pacificfly",
        document="PacificFly Delay Policy: Delays exceeding 3 hours qualify for EU261 statutory compensation.",
        metadata={"carrier": "PacificFly", "category": "delay"}
    )

# Graph Instances Registry
visa_graph = create_visa_processing_graph(checkpointer=checkpointer, db_path=DB_PATH)
dispute_graph = create_dispute_reconciliation_graph(checkpointer=checkpointer, db_path=DB_PATH)
medevac_graph = create_medevac_repatriation_graph(checkpointer=checkpointer, db_path=DB_PATH)

GRAPH_REGISTRY = {
    "visa_processing_graph": visa_graph,
    "supplier_dispute_graph": dispute_graph,
    "medevac_repatriation_graph": medevac_graph,
}


# ============================================================================
# 1. USER CHAT API & MULTI-AGENT ROUTER
# ============================================================================
async def handle_agent_chat(request: Request) -> JSONResponse:
    body = await request.json()
    thread_id = body.get("thread_id") or f"thread-{uuid.uuid4().hex[:8]}"
    agent_id = body.get("agent_id", "").lower()
    user_msg = body.get("message", "")
    params = body.get("parameters") or {}

    logger.info(f"[ChatAPI] Route to agent '{agent_id}' on thread '{thread_id}': '{user_msg}'")

    if agent_id == "visa_agent":
        init_state = {
            "client_id": params.get("client_id", 1),
            "destination": params.get("destination", "Japan" if "japan" in user_msg.lower() else "France"),
            "visa_type": params.get("visa_type", "tourist" if "tourist" in user_msg.lower() else "schengen"),
            "user_prompt": user_msg,
        }
        res = await visa_graph.execute(thread_id, initial_state=init_state)
        return JSONResponse({
            "agent_id": agent_id,
            "thread_id": thread_id,
            "status": res.get("__status__"),
            "current_node": res.get("__current_node__"),
            "response": f"Visa Application processed to step: {res.get('__current_node__')}. Status: {res.get('__status__')}",
            "state": res,
        })

    elif agent_id == "dispute_agent":
        init_state = {
            "booking_id": params.get("booking_id", 3),
            "carrier": params.get("carrier", "PacificFly"),
            "amount_disputed": params.get("amount", 450.00),
            "dispute_reason": user_msg,
        }
        res = await dispute_graph.execute(thread_id, initial_state=init_state)
        return JSONResponse({
            "agent_id": agent_id,
            "thread_id": thread_id,
            "status": res.get("__status__"),
            "current_node": res.get("__current_node__"),
            "response": f"Dispute Claim processed to step: {res.get('__current_node__')}. Strategy: {res.get('selected_strategy')}",
            "state": res,
        })

    elif agent_id == "medevac_agent":
        init_state = {
            "patient_name": params.get("patient_name", "Elena Rostova"),
            "current_location": params.get("location", "Bali (DPS)"),
            "medical_condition": user_msg,
            "acuity_level": params.get("acuity", "CRITICAL"),
        }
        res = await medevac_graph.execute(thread_id, initial_state=init_state)
        return JSONResponse({
            "agent_id": agent_id,
            "thread_id": thread_id,
            "status": res.get("__status__"),
            "current_node": res.get("__current_node__"),
            "response": f"Medevac Mission processed to step: {res.get('__current_node__')}. Selected Route: {res.get('selected_route_id')}",
            "state": res,
        })

    elif agent_id == "planning_agent":
        provider = WanderpathModelProvider()
        routed_algo = route_subtask(user_msg, risk_level="medium", requires_branching=True)
        plan_res = run_plan_and_solve(user_msg, provider)
        return JSONResponse({
            "agent_id": agent_id,
            "thread_id": thread_id,
            "status": "COMPLETED",
            "routed_algorithm": routed_algo,
            "response": f"Planning Strategy ({routed_algo}): {plan_res}",
            "state": {"plan_output": plan_res, "algorithm": routed_algo},
        })

    elif agent_id == "memory_rag_agent":
        retrieved = vector_db.similarity_search(user_msg, n_results=1)
        rag_context = retrieved[0]["document"] if retrieved else "No direct policy match found in knowledge base."
        return JSONResponse({
            "agent_id": agent_id,
            "thread_id": thread_id,
            "status": "COMPLETED",
            "response": f"Verified Travel Policy Response:\n\n{rag_context}",
            "state": {"retrieved_context": rag_context},
        })

    return JSONResponse({"error": f"Unknown agent_id: {agent_id}"}, status_code=400)


# ============================================================================
# 2. ADMIN MCP TOOL MANAGEMENT
# ============================================================================
async def list_admin_tools(request: Request) -> JSONResponse:
    tools = get_all_registered_tools()
    return JSONResponse({"status": "success", "tools": tools})

async def toggle_admin_tool(request: Request) -> JSONResponse:
    body = await request.json()
    tool_name = body.get("tool_name")
    enabled = body.get("enabled", True)
    set_tool_enabled(tool_name, enabled)
    await broadcast_tool_list_changed()
    return JSONResponse({"status": "success", "tool_name": tool_name, "enabled": enabled})

async def register_new_admin_tool(request: Request) -> JSONResponse:
    body = await request.json()
    name = body.get("name")
    desc = body.get("description", "")
    schema = body.get("input_schema", {})
    register_dynamic_tool(name, desc, schema, enabled=True)
    await broadcast_tool_list_changed()
    return JSONResponse({"status": "success", "registered_tool": name})

async def deregister_admin_tool(request: Request) -> JSONResponse:
    name = request.path_params.get("name")
    success = deregister_dynamic_tool(name)
    if not success:
        return JSONResponse({"error": "Tool not found or is protected"}, status_code=404)
    await broadcast_tool_list_changed()
    return JSONResponse({"status": "success", "deregistered": name})


# ============================================================================
# 3. ADMIN RAG KNOWLEDGE BASE MANAGEMENT
# ============================================================================
async def list_rag_documents(request: Request) -> JSONResponse:
    docs = vector_db.list_documents()
    return JSONResponse({"status": "success", "count": len(docs), "documents": docs})

async def add_rag_document(request: Request) -> JSONResponse:
    body = await request.json()
    doc_id = body.get("doc_id")
    content = body.get("content")
    meta = body.get("metadata")
    vector_db.add_document(doc_id=doc_id, document=content, metadata=meta)
    return JSONResponse({"status": "success", "added_doc_id": doc_id})

async def delete_rag_document(request: Request) -> JSONResponse:
    doc_id = request.path_params.get("doc_id")
    vector_db.delete_document(doc_id)
    return JSONResponse({"status": "success", "deleted_doc_id": doc_id})


# ============================================================================
# 4. ADMIN HUMAN-IN-THE-LOOP (HITL) RESOLUTION
# ============================================================================
async def list_hitl_tasks(request: Request) -> JSONResponse:
    status = request.query_params.get("status")
    tasks = hitl_engine.list_tasks(status=status)
    return JSONResponse({"status": "success", "count": len(tasks), "tasks": [t.__dict__ for t in tasks]})

async def resolve_hitl_task(request: Request) -> JSONResponse:
    task_id = request.path_params.get("task_id")
    body = await request.json()
    decision = body.get("decision", "APPROVED")
    notes = body.get("admin_notes", "")

    task = hitl_engine.get_task(task_id)
    if not task:
        return JSONResponse({"error": "HITL task not found"}, status_code=404)

    target_graph = GRAPH_REGISTRY.get(task.graph_name)
    result = hitl_engine.resolve_task(
        task_id=task_id,
        admin_decision=decision,
        admin_notes=notes,
        graph=target_graph,
    )
    return JSONResponse({"status": "success", "task_id": task_id, "decision": decision, "resumed_state": result})


# ============================================================================
# 5. ADMIN FAILURE TICKET CENTER
# ============================================================================
async def list_failure_tickets(request: Request) -> JSONResponse:
    status = request.query_params.get("status")
    tickets = ticket_engine.list_tickets(status=status)
    return JSONResponse({"status": "success", "count": len(tickets), "tickets": [t.__dict__ for t in tickets]})

async def update_ticket_status(request: Request) -> JSONResponse:
    ticket_id = request.path_params.get("ticket_id")
    status = request.query_params.get("status", "INVESTIGATING")
    ticket_engine.update_status(ticket_id, status=status)
    return JSONResponse({"status": "success", "ticket_id": ticket_id, "new_status": status})

async def resolve_and_resume_ticket(request: Request) -> JSONResponse:
    ticket_id = request.path_params.get("ticket_id")
    body = await request.json()
    patch = body.get("state_patch")
    notes = body.get("resolution_notes", "")

    ticket = ticket_engine.get_ticket(ticket_id)
    if not ticket:
        return JSONResponse({"error": "Failure ticket not found"}, status_code=404)

    target_graph = GRAPH_REGISTRY.get(ticket.graph_name)
    result = ticket_engine.resolve_and_resume_ticket(
        ticket_id=ticket_id,
        state_patch=patch,
        resolution_notes=notes,
        graph=target_graph,
    )
    return JSONResponse({"status": "success", "ticket_id": ticket_id, "resumed_state": result})


# ============================================================================
# 6. SYSTEM OVERVIEW
# ============================================================================
async def get_system_overview(request: Request) -> JSONResponse:
    hitl_pending = len(hitl_engine.list_tasks(status="PENDING"))
    tickets_open = len(ticket_engine.list_tickets(status="OPEN"))
    rag_count = len(vector_db.list_documents())
    tools = get_all_registered_tools()
    
    return JSONResponse({
        "status": "OPERATIONAL",
        "active_mcp_tools": len([t for t in tools if t.get("enabled")]),
        "total_mcp_tools": len(tools),
        "pending_hitl_tasks": hitl_pending,
        "open_failure_tickets": tickets_open,
        "rag_documents_count": rag_count,
        "supported_agents": ["visa_agent", "dispute_agent", "medevac_agent", "planning_agent", "memory_rag_agent"],
    })


# ============================================================================
# 7. STATIC FRONTEND
# ============================================================================
FRONTEND_DIR = pathlib.Path(__file__).parent.parent / "frontend"

async def serve_frontend_index(request: Request) -> HTMLResponse:
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Wanderpath Platform Active</h1>")


# Route Declarations
routes = [
    Route("/", endpoint=serve_frontend_index, methods=["GET"]),
    Route("/api/chat", endpoint=handle_agent_chat, methods=["POST"]),
    Route("/api/admin/overview", endpoint=get_system_overview, methods=["GET"]),
    Route("/api/admin/tools", endpoint=list_admin_tools, methods=["GET"]),
    Route("/api/admin/tools/toggle", endpoint=toggle_admin_tool, methods=["POST"]),
    Route("/api/admin/tools/register", endpoint=register_new_admin_tool, methods=["POST"]),
    Route("/api/admin/tools/{name}", endpoint=deregister_admin_tool, methods=["DELETE"]),
    Route("/api/admin/rag/documents", endpoint=list_rag_documents, methods=["GET"]),
    Route("/api/admin/rag/documents", endpoint=add_rag_document, methods=["POST"]),
    Route("/api/admin/rag/documents/{doc_id}", endpoint=delete_rag_document, methods=["DELETE"]),
    Route("/api/admin/hitl/tasks", endpoint=list_hitl_tasks, methods=["GET"]),
    Route("/api/admin/hitl/tasks/{task_id}/resolve", endpoint=resolve_hitl_task, methods=["POST"]),
    Route("/api/admin/tickets", endpoint=list_failure_tickets, methods=["GET"]),
    Route("/api/admin/tickets/{ticket_id}/status", endpoint=update_ticket_status, methods=["POST"]),
    Route("/api/admin/tickets/{ticket_id}/resolve", endpoint=resolve_and_resume_ticket, methods=["POST"]),
]

middleware = [
    Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
]

app = Starlette(debug=True, routes=routes, middleware=middleware)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8500)
