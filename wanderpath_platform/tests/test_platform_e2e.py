"""
Wanderpath Travel Agency - Platform End-to-End Verification Suite
==================================================================
Verifies all REST API endpoints for:
1. Multi-Agent Chat Router (5 Agents)
2. Live MCP Dynamic Tool Management & Toggles
3. RAG Knowledge Base Live CRUD
4. HITL Task Resolution & State Graph Resumption
5. Failure Ticket Investigation, State Patching & Recovery
"""

import json
import os
import pathlib
import sys
from starlette.testclient import TestClient

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure project root is in sys.path
project_root = pathlib.Path(__file__).parent.parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from wanderpath_platform.backend.app import app

client = TestClient(app)


def test_platform_overview():
    print("\n--- 1. Testing System Overview API ---")
    res = client.get("/api/admin/overview")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "OPERATIONAL"
    assert "visa_agent" in data["supported_agents"]
    print(f"  ✅ Overview verified: {data['active_mcp_tools']} active MCP tools, {data['rag_documents_count']} RAG documents.")


def test_multi_agent_chat_router():
    print("\n--- 2. Testing Multi-Agent Chat Router ---")
    
    # 1. Visa Agent Chat
    print("  -> Chatting with Visa Agent...")
    res_visa = client.post("/api/chat", json={
        "agent_id": "visa_agent",
        "message": "Liam Neeson requesting expedited tourist visa for Japan.",
        "thread_id": "thread-e2e-visa-01"
    })
    assert res_visa.status_code == 200
    data_visa = res_visa.json()
    assert data_visa["agent_id"] == "visa_agent"
    print(f"  ✅ Visa Agent responded: Status = {data_visa['status']} (Current Node = {data_visa['current_node']})")

    # 2. Planning Agent Chat
    print("  -> Chatting with Trip Disruption Planning Agent...")
    res_plan = client.post("/api/chat", json={
        "agent_id": "planning_agent",
        "message": "Maria Ostrowski Lisbon to Marrakech flight cancelled.",
        "thread_id": "thread-e2e-plan-01"
    })
    assert res_plan.status_code == 200
    data_plan = res_plan.json()
    assert "Planning Strategy" in data_plan["response"]
    print("  ✅ Planning Agent responded with routed strategy.")

    # 3. Memory & RAG Agent Chat
    print("  -> Chatting with Memory & Hybrid RAG Agent...")
    res_rag = client.post("/api/chat", json={
        "agent_id": "memory_rag_agent",
        "message": "What is the cancellation policy for Alpine Resort & Spa?",
        "thread_id": "thread-e2e-rag-01"
    })
    assert res_rag.status_code == 200
    data_rag = res_rag.json()
    assert "14 days" in data_rag["response"] or "Alpine" in data_rag["response"]
    print("  ✅ Memory & RAG Agent responded from ChromaDB knowledge base.")


def test_admin_mcp_tool_management():
    print("\n--- 3. Testing Admin Live MCP Tool Management ---")
    
    # 1. List tools
    res_list = client.get("/api/admin/tools")
    assert res_list.status_code == 200
    tools = res_list.json()["tools"]
    assert len(tools) > 0
    print(f"  ✅ Listed {len(tools)} registered MCP tools.")

    # 2. Toggle tool disabled
    tool_to_toggle = "get_itinerary_details"
    res_toggle = client.post("/api/admin/tools/toggle", json={"tool_name": tool_to_toggle, "enabled": False})
    assert res_toggle.status_code == 200
    assert res_toggle.json()["enabled"] is False

    # Check that tool status updated
    res_check = client.get("/api/admin/tools")
    updated = next(t for t in res_check.json()["tools"] if t["name"] == tool_to_toggle)
    assert updated["enabled"] is False
    print(f"  ✅ Successfully disabled '{tool_to_toggle}' on live MCP server.")

    # Re-enable tool
    client.post("/api/admin/tools/toggle", json={"tool_name": tool_to_toggle, "enabled": True})
    print(f"  ✅ Re-enabled '{tool_to_toggle}'.")


def test_admin_rag_knowledge_base_crud():
    print("\n--- 4. Testing Admin Live RAG Document CRUD ---")
    
    doc_id = "policy_e2e_safari"
    doc_text = "Kenya Safari Lodge: 30-day cancellation window. Yellow fever certificate mandatory for entry."
    
    # 1. Ingest document via API
    res_add = client.post("/api/admin/rag/documents", json={
        "doc_id": doc_id,
        "content": doc_text,
        "metadata": {"country": "Kenya", "category": "health_rules"}
    })
    assert res_add.status_code == 200
    assert res_add.json()["added_doc_id"] == doc_id
    print("  ✅ Ingested new policy document into ChromaDB via admin API.")

    # 2. List documents
    res_list = client.get("/api/admin/rag/documents")
    docs = res_list.json()["documents"]
    assert any(d["id"] == doc_id for d in docs)

    # 3. Verify RAG Agent immediately retrieves it
    res_query = client.post("/api/chat", json={
        "agent_id": "memory_rag_agent",
        "message": "What certificates are required for Kenya Safari Lodge?",
        "thread_id": "thread-e2e-rag-safari"
    })
    assert "Yellow fever" in res_query.json()["response"]
    print("  ✅ Verified: Agent immediately retrieved newly ingested document!")

    # 4. Delete document
    res_del = client.delete(f"/api/admin/rag/documents/{doc_id}")
    assert res_del.status_code == 200
    print("  ✅ Deleted policy document from ChromaDB via admin API.")


def test_admin_hitl_resolution_api():
    print("\n--- 5. Testing Admin HITL Resolution API ---")
    
    # Run Visa graph with France (Schengen fee $650 > $500 limit -> triggers HITL)
    thread_id = "thread-e2e-hitl-01"
    client.post("/api/chat", json={
        "agent_id": "visa_agent",
        "message": "Urgent visa application for France.",
        "thread_id": thread_id,
        "parameters": {"destination": "France", "visa_type": "schengen"}
    })
    
    # Deliver webhook to trigger HITL
    from wanderpath_platform.backend.app import visa_graph
    visa_graph.run_sync(thread_id, resume_payload={"webhook_payload": {"decision": "APPROVED", "fee": 650.0}})

    # Fetch pending tasks via API
    res_tasks = client.get("/api/admin/hitl/tasks?status=PENDING")
    assert res_tasks.status_code == 200
    pending = res_tasks.json()["tasks"]
    assert len(pending) > 0
    target_task = next(t for t in pending if t["thread_id"] == thread_id)
    print(f"  ✅ Pending HITL task discovered via API: Task ID {target_task['task_id']}")

    # Resolve via API
    res_resolve = client.post(f"/api/admin/hitl/tasks/{target_task['task_id']}/resolve", json={
        "decision": "APPROVED",
        "admin_notes": "Authorized via E2E test suite"
    })
    assert res_resolve.status_code == 200
    data_res = res_resolve.json()
    assert data_res["decision"] == "APPROVED"
    assert data_res["resumed_state"]["__status__"] == "COMPLETED"
    print("  ✅ HITL task resolved via API -> StateGraph resumed and completed successfully.")


def test_admin_failure_ticket_resolution_api():
    print("\n--- 6. Testing Admin Failure Ticket Recovery API ---")
    
    from state_graph.recovery.ticket_engine import TicketEngine
    from wanderpath_platform.backend.app import DB_PATH
    ticket_engine = TicketEngine(db_path=DB_PATH)
    
    ticket_id = ticket_engine.create_ticket(
        thread_id="thread-e2e-ticket-01",
        graph_name="supplier_dispute_graph",
        failed_node="execute_gds_filing",
        error_message="GDS Gateway Timeout (504)",
        error_traceback="Traceback in execute_gds_filing...",
        state_data={"booking_id": 3, "carrier": "PacificFly", "amount_disputed": 450.00, "__step__": 2}
    )

    # 1. List open tickets via API
    res_tickets = client.get("/api/admin/tickets?status=OPEN")
    assert res_tickets.status_code == 200
    open_tickets = res_tickets.json()["tickets"]
    assert any(t["ticket_id"] == ticket_id for t in open_tickets)
    print(f"  ✅ Open Failure Ticket discovered via API: {ticket_id}")

    # 2. Update status to INVESTIGATING
    client.post(f"/api/admin/tickets/{ticket_id}/status?status=INVESTIGATING")

    # 3. Resolve and patch state via API
    res_resolve = client.post(f"/api/admin/tickets/{ticket_id}/resolve", json={
        "state_patch": {"gds_gateway_override": "GDS-BACKUP-01", "carrier_settlement": {"decision": "OFFER_PARTIAL", "amount": 200.0, "fee_waiver": 200.0}},
        "resolution_notes": "Switched to secondary GDS clearinghouse."
    })
    assert res_resolve.status_code == 200
    assert res_resolve.json()["ticket_id"] == ticket_id
    
    # Check ticket is marked RESOLVED
    t_check = ticket_engine.get_ticket(ticket_id)
    assert t_check.status == "RESOLVED"
    print("  ✅ Failure Ticket resolved and state patched via API.")


if __name__ == "__main__":
    print("==================================================================")
    print("🧪 RUNNING SUB-MODULE 5 PLATFORM E2E TESTS (Issue #68)")
    print("==================================================================")

    test_platform_overview()
    test_multi_agent_chat_router()
    test_admin_mcp_tool_management()
    test_admin_rag_knowledge_base_crud()
    test_admin_hitl_resolution_api()
    test_admin_failure_ticket_resolution_api()

    print("\n==================================================================")
    print("🎉 FULL-STACK PLATFORM E2E VERIFICATION PASSED 100%!")
    print("==================================================================")
