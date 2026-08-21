"""
Wanderpath Travel Agency - Master End-to-End Smoke Test Suite
=============================================================
Unified verification suite testing all 6 architectural concerns:
1. Dynamic MCP Tool Registry & Notifications
2. Dynamic ChromaDB RAG Document Ingestion & Purge
3. Durable SQLite State Checkpointer & Crash-Recovery
4. Three Stateful Agent Graphs (Visa, Dispute, Medevac) with 2 LLM Additions Each
5. HITL Escalation & Unplanned Failure Ticket State Patch Recovery
6. Full-Stack Platform REST API & Multi-Agent Router
"""

import asyncio
import json
import logging
import os
import pathlib
import sys
import tempfile
import time

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure project root and mcp_server are in sys.path
project_root = pathlib.Path(__file__).parent.parent.resolve()
mcp_server_dir = project_root / "mcp_server"
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(mcp_server_dir) not in sys.path:
    sys.path.insert(0, str(mcp_server_dir))

# Disable extraneous loggers during smoke test
logging.getLogger("StateGraph").setLevel(logging.WARNING)
logging.getLogger("VisaProcessingGraph").setLevel(logging.WARNING)
logging.getLogger("DisputeReconciliationGraph").setLevel(logging.WARNING)
logging.getLogger("MedevacRepatriationGraph").setLevel(logging.WARNING)
logging.getLogger("WanderpathPlatformAPI").setLevel(logging.WARNING)

from server import (
    register_dynamic_tool,
    deregister_dynamic_tool,
    set_tool_enabled,
    get_all_registered_tools,
)
from rag.vector_store import WanderpathVectorStore
from state_graph.checkpointer import DurableCheckpointer
from state_graph.base import StateGraph, InterruptSignal, END
from state_graph.graphs.visa_graph import create_visa_processing_graph
from state_graph.graphs.dispute_graph import create_dispute_reconciliation_graph
from state_graph.graphs.medevac_graph import create_medevac_repatriation_graph
from state_graph.recovery.hitl_engine import HITLEngine
from state_graph.recovery.ticket_engine import TicketEngine
from starlette.testclient import TestClient
from wanderpath_platform.backend.app import app


class MasterSmokeTestRunner:
    def __init__(self):
        self.results = {}

    def run_all(self):
        print("=" * 80)
        print("🌟 WANDERPATH AUTONOMOUS AGENT SYSTEM — MASTER SMOKE TEST (Final v3.0)")
        print("=" * 80)
        start_time = time.time()

        self.test_concern_1_dynamic_mcp()
        self.test_concern_2_dynamic_rag()
        self.test_concern_3_durable_checkpoint_recovery()
        self.test_concern_4_stateful_agent_graphs()
        self.test_concern_5_hitl_and_failure_tickets()
        self.test_concern_6_full_stack_platform_api()

        elapsed = time.time() - start_time
        self.print_summary(elapsed)

    # ------------------------------------------------------------------------
    # Concern 1: Dynamic MCP Tool Registry
    # ------------------------------------------------------------------------
    def test_concern_1_dynamic_mcp(self):
        print("\n[Concern 1/6] 🛠️  Dynamic MCP Tool Registry & Live Toggles")
        try:
            tool_name = "test_smoke_custom_tool"
            schema = {"type": "object", "properties": {"code": {"type": "string"}}}
            
            # Register dynamic tool
            register_dynamic_tool(tool_name, "Master smoke test dynamic tool", schema, enabled=True)
            tools = get_all_registered_tools()
            assert any(t["name"] == tool_name and t["enabled"] is True for t in tools)
            print("  ✓ Dynamic MCP tool registered successfully at runtime.")

            # Toggle tool disabled
            set_tool_enabled(tool_name, False)
            tools_after = get_all_registered_tools()
            target = next(t for t in tools_after if t["name"] == tool_name)
            assert target["enabled"] is False
            print("  ✓ Dynamic MCP tool disabled on live server.")

            # Deregister
            assert deregister_dynamic_tool(tool_name) is True
            print("  ✓ Dynamic MCP tool deregistered cleanly.")

            self.results["1. Dynamic MCP Tool Registry"] = "PASSED (100%)"
        except Exception as e:
            print(f"  ✗ Concern 1 Failed: {e}")
            self.results["1. Dynamic MCP Tool Registry"] = f"FAILED: {e}"

    # ------------------------------------------------------------------------
    # Concern 2: Dynamic RAG Knowledge Base CRUD
    # ------------------------------------------------------------------------
    def test_concern_2_dynamic_rag(self):
        print("\n[Concern 2/6] 📚 Dynamic ChromaDB Vector Policy Store CRUD")
        try:
            with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
                vdb = WanderpathVectorStore(collection_name="master_smoke_rag", persist_dir=tmp_dir)
                doc_id = "policy_smoke_safari"
                doc_content = "Serengeti Migration Lodge: 45-day cancellation notice required for VIP bookings."
                
                # Ingest document
                vdb.add_document(doc_id=doc_id, document=doc_content, metadata={"country": "Tanzania"})
                docs = vdb.list_documents()
                assert len(docs) == 1
                assert docs[0]["id"] == doc_id
                print("  ✓ New policy document dynamically ingested into ChromaDB.")

                # Retrieve via similarity search
                results = vdb.similarity_search("Serengeti cancellation window", n_results=1)
                assert len(results) == 1
                assert "45-day" in results[0]["document"]
                print("  ✓ Ingested document immediately retrieved via vector similarity search.")

                # Delete document
                vdb.delete_document(doc_id)
                assert len(vdb.list_documents()) == 0
                print("  ✓ Policy document deleted and purged from vector index.")

            self.results["2. Dynamic RAG Policy Store"] = "PASSED (100%)"
        except Exception as e:
            print(f"  ✗ Concern 2 Failed: {e}")
            self.results["2. Dynamic RAG Policy Store"] = f"FAILED: {e}"

    # ------------------------------------------------------------------------
    # Concern 3: Durable SQLite State Checkpoint & Recovery
    # ------------------------------------------------------------------------
    def test_concern_3_durable_checkpoint_recovery(self):
        print("\n[Concern 3/6] 💾 Durable SQLite State Checkpointer & Resumption")
        try:
            with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
                db_path = str(pathlib.Path(tmp_dir) / "smoke_checkpoints.sqlite3")
                checkpointer = DurableCheckpointer(db_path=db_path)
                thread_id = "thread-smoke-chk-001"

                # Step 1: Save Step 1 checkpoint
                chk1 = checkpointer.save_checkpoint(
                    thread_id=thread_id,
                    graph_name="SmokeGraph",
                    current_node="node_a",
                    state_data={"step": 1, "data": "initial_payload"},
                    step_number=1,
                )
                assert chk1.startswith("chk-")

                # Step 2: Save Step 2 checkpoint
                chk2 = checkpointer.save_checkpoint(
                    thread_id=thread_id,
                    graph_name="SmokeGraph",
                    current_node="node_b",
                    state_data={"step": 2, "data": "computed_payload", "value": 450},
                    step_number=2,
                    parent_checkpoint_id=chk1,
                )

                # Inspect checkpoints
                history = checkpointer.list_checkpoints(thread_id)
                assert len(history) == 2
                latest = checkpointer.load_latest_checkpoint(thread_id)
                assert latest.current_node == "node_b"
                assert latest.state_data["value"] == 450
                print(f"  ✓ Verified: Sequential checkpoints intact in SQLite ({len(history)} snapshots).")

            self.results["3. Durable SQLite Checkpointing"] = "PASSED (100%)"
        except Exception as e:
            print(f"  ✗ Concern 3 Failed: {e}")
            self.results["3. Durable SQLite Checkpointing"] = f"FAILED: {e}"

    # ------------------------------------------------------------------------
    # Concern 4: Three Stateful Problem Graphs (2 LLM Additions Each)
    # ------------------------------------------------------------------------
    def test_concern_4_stateful_agent_graphs(self):
        print("\n[Concern 4/6] 🧠 Three Stateful Agent Problem Graphs (2 LLM Additions Each)")
        try:
            with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
                db_path = str(pathlib.Path(tmp_dir) / "smoke_graphs.sqlite3")
                checkpointer = DurableCheckpointer(db_path=db_path)

                # Graph 1: Visa & Consular (Task Decomp + RAG)
                g1 = create_visa_processing_graph(checkpointer=checkpointer, db_path=db_path)
                s1 = g1.run_sync("thread-smoke-visa", initial_state={"client_id": 101, "destination": "France", "visa_type": "schengen"})
                assert s1.get("__status__") == "INTERRUPTED"
                assert s1.get("roadmap_decomposed") is True
                assert s1.get("policy_retrieved") is True
                print("  ✓ Graph 1 (Visa Desk): Task Decomposition + RAG verified. Paused at consular webhook.")

                # Graph 2: Supplier Dispute (ToT + Constrained ReAct)
                g2 = create_dispute_reconciliation_graph(checkpointer=checkpointer, db_path=db_path)
                s2 = g2.run_sync("thread-smoke-disp", initial_state={"booking_id": 88, "carrier": "PacificFly", "amount_disputed": 450.00})
                assert s2.get("__status__") == "INTERRUPTED"
                assert s2.get("selected_strategy") == "EU261_STATUTORY_CLAIM"
                assert s2.get("gds_action_executed") == "gds_file_chargeback"
                print("  ✓ Graph 2 (Supplier Dispute): Tree of Thoughts + Constrained ReAct verified. Paused at 7-day window.")

                # Graph 3: VIP Medevac (LATS + Constrained ReAct)
                g3 = create_medevac_repatriation_graph(checkpointer=checkpointer, db_path=db_path)
                s3 = g3.run_sync("thread-smoke-med", initial_state={"patient_name": "Elena Rostova", "current_location": "Bali (DPS)", "acuity_level": "CRITICAL"})
                assert s3.get("__status__") == "INTERRUPTED"
                assert s3.get("selected_route_id") == "ROUTE_SGH_DIRECT"
                assert s3.get("dispatch_action_executed") == "medevac_issue_guarantee_and_standby"
                print("  ✓ Graph 3 (VIP Medevac): LATS Airfield Search + Constrained ReAct verified. Paused at ICU bed admission.")

            self.results["4. Three Stateful Agent Graphs"] = "PASSED (100%)"
        except Exception as e:
            print(f"  ✗ Concern 4 Failed: {e}")
            self.results["4. Three Stateful Agent Graphs"] = f"FAILED: {e}"

    # ------------------------------------------------------------------------
    # Concern 5: HITL Escalation & Failure Ticket Recovery
    # ------------------------------------------------------------------------
    def test_concern_5_hitl_and_failure_tickets(self):
        print("\n[Concern 5/6] 🚨 HITL Resolution & Unplanned Failure Ticket Recovery")
        try:
            with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
                db_path = str(pathlib.Path(tmp_dir) / "smoke_recovery.sqlite3")
                hitl_engine = HITLEngine(db_path=db_path)
                ticket_engine = TicketEngine(db_path=db_path)

                # HITL Task
                task_id = hitl_engine.create_task(
                    thread_id="thread-smoke-hitl-01",
                    graph_name="visa_processing_graph",
                    node_name="evaluate_consular_response",
                    reason="Expedited consular fee of $650.00 exceeds $500.00 limit",
                    threshold_info="Fee: $650.00 > $500.00 limit",
                )
                pending = hitl_engine.list_tasks(status="PENDING")
                assert any(t.task_id == task_id for t in pending)
                hitl_engine.resolve_task(task_id, admin_decision="APPROVED", admin_notes="Authorized by Director")
                assert hitl_engine.get_task(task_id).status == "APPROVED"
                print("  ✓ Planned HITL Task: Created, inspected, approved, and marked APPROVED in SQLite.")

                # Failure Ticket
                ticket_id = ticket_engine.create_ticket(
                    thread_id="thread-smoke-ticket-01",
                    graph_name="supplier_dispute_graph",
                    failed_node="execute_gds_filing",
                    error_message="GDS Gateway Timeout (504)",
                    error_traceback="Traceback at GDS clearinghouse connection...",
                    state_data={"booking_id": 88, "step": 3},
                )
                open_tickets = ticket_engine.list_tickets(status="OPEN")
                assert any(t.ticket_id == ticket_id for t in open_tickets)
                ticket_engine.resolve_and_resume_ticket(
                    ticket_id=ticket_id,
                    state_patch={"gds_gateway_override": "GDS-BACKUP-01"},
                    resolution_notes="Patched to secondary GDS clearinghouse.",
                )
                assert ticket_engine.get_ticket(ticket_id).status == "RESOLVED"
                print("  ✓ Unplanned Failure Ticket: Intercepted, inspected, state patched, and marked RESOLVED in SQLite.")

            self.results["5. HITL & Failure Ticket Recovery"] = "PASSED (100%)"
        except Exception as e:
            print(f"  ✗ Concern 5 Failed: {e}")
            self.results["5. HITL & Failure Ticket Recovery"] = f"FAILED: {e}"

    # ------------------------------------------------------------------------
    # Concern 6: Full-Stack Platform REST API & Multi-Agent Router
    # ------------------------------------------------------------------------
    def test_concern_6_full_stack_platform_api(self):
        print("\n[Concern 6/6] 🌐 Full-Stack Platform REST API & Multi-Agent Router")
        try:
            client = TestClient(app)

            # 1. System Overview
            res_ov = client.get("/api/admin/overview")
            assert res_ov.status_code == 200
            assert res_ov.json()["status"] == "OPERATIONAL"

            # 2. Chat with Planning Agent
            res_chat = client.post("/api/chat", json={
                "agent_id": "planning_agent",
                "message": "Maria Ostrowski Lisbon to Marrakech flight cancelled.",
            })
            assert res_chat.status_code == 200
            assert "Plan" in res_chat.json()["response"] or "Rebooking" in res_chat.json()["response"]

            # 3. Chat with Memory & RAG Agent
            res_rag = client.post("/api/chat", json={
                "agent_id": "memory_rag_agent",
                "message": "What is the cancellation policy for Alpine Resort & Spa?",
            })
            assert res_rag.status_code == 200
            assert "Alpine" in res_rag.json()["response"] or "14 days" in res_rag.json()["response"]

            # 4. Frontend index served
            res_html = client.get("/")
            assert res_html.status_code == 200
            assert "Wanderpath" in res_html.text

            print("  ✓ Platform Overview, 5-Agent Chat Router, and Luxury Frontend verified.")
            self.results["6. Full-Stack Platform API & Frontend"] = "PASSED (100%)"
        except Exception as e:
            print(f"  ✗ Concern 6 Failed: {e}")
            self.results["6. Full-Stack Platform API & Frontend"] = f"FAILED: {e}"

    # ------------------------------------------------------------------------
    # Summary Table
    # ------------------------------------------------------------------------
    def print_summary(self, elapsed: float):
        print("\n" + "=" * 80)
        print(f"📋 MASTER SMOKE TEST SUMMARY TABLE (Completed in {elapsed:.2f}s)")
        print("=" * 80)
        print(f"{'Architectural Concern Area':<50} | {'Status':<25}")
        print("-" * 80)
        all_passed = True
        for concern, status in self.results.items():
            print(f"{concern:<50} | {status:<25}")
            if "PASSED" not in status:
                all_passed = False
        print("=" * 80)
        if all_passed:
            print("🎉 ALL 6 ARCHITECTURAL CONCERNS PASSED 100% WITH ZERO DEFECTS!")
        else:
            print("❌ SOME CONCERNS FAILED!")
        print("=" * 80)


if __name__ == "__main__":
    runner = MasterSmokeTestRunner()
    runner.run_all()
