"""
Wanderpath Travel Agency - Three Stateful Graphs Verification Suite
===================================================================
Tests all 3 stateful problem graphs, verifying:
1. Visa Graph (Task Decomposition + RAG + Webhook Pause + HITL Fee Escalation + Cycles)
2. Dispute Graph (Tree of Thoughts + Constrained ReAct + Adjudication Pause + HITL Waiver + Cycles)
3. Medevac Graph (LATS + Constrained ReAct + Hospital Pause + Physician HITL + Cycles)
"""

import os
import pathlib
import sys
import tempfile

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure project root is in sys.path
project_root = pathlib.Path(__file__).parent.parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from state_graph.checkpointer import DurableCheckpointer
from state_graph.graphs.visa_graph import create_visa_processing_graph
from state_graph.graphs.dispute_graph import create_dispute_reconciliation_graph
from state_graph.graphs.medevac_graph import create_medevac_repatriation_graph


# ============================================================================
# TEST 1: VISA APPLICATION STATE GRAPH
# ============================================================================
def test_visa_processing_graph():
    print("\n--- 1. Testing Visa & Consular Application Graph ---")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        db_path = str(pathlib.Path(tmp_dir) / "test_visa.sqlite3")
        checkpointer = DurableCheckpointer(db_path=db_path)
        graph = create_visa_processing_graph(checkpointer=checkpointer, db_path=db_path)
        thread_id = "thread-test-visa-001"

        # Step 1: Run fresh to webhook pause
        print("  -> Running Visa Graph Phase 1: Intake -> Decomposition -> RAG -> Awaiting Webhook...")
        state1 = graph.run_sync(
            thread_id=thread_id,
            initial_state={"client_id": 1, "destination": "France", "visa_type": "schengen"}
        )
        
        assert state1.get("__status__") == "INTERRUPTED", "Visa graph did not pause on webhook wait state!"
        assert state1.get("__interrupt_type__") == "AWAITING_EXTERNAL"
        assert state1.get("roadmap_decomposed") is True, "Task Decomposition LLM addition failed!"
        assert state1.get("policy_retrieved") is True, "RAG Retrieval LLM addition failed!"
        print("  ✅ Phase 1 Passed: Decomposed roadmap and retrieved Schengen RAG policy ($650 fee).")

        # Step 2: Resume with webhook arrival (Expedited Fee $650 -> Triggers HITL > $500)
        print("  -> Running Visa Graph Phase 2: Webhook Delivered -> Triggers HITL Fee Escalation...")
        state2 = graph.run_sync(
            thread_id=thread_id,
            resume_payload={"webhook_payload": {"decision": "APPROVED", "fee": 650.0, "notes": "Expedited biometrics accepted."}}
        )

        assert state2.get("__status__") == "INTERRUPTED", "Visa graph did not pause on HITL fee escalation!"
        assert state2.get("__interrupt_type__") == "HITL"
        assert "650.00" in state2.get("__interrupt_reason__")
        print("  ✅ Phase 2 Passed: HITL pause triggered gracefully for fee > $500 threshold.")

        # Step 3: Admin approves fee in Platform UI -> Completes to END
        print("  -> Running Visa Graph Phase 3: Admin Approves Fee -> Finalize Visa...")
        state3 = graph.run_sync(
            thread_id=thread_id,
            resume_payload={"admin_approval": "APPROVED"}
        )

        assert state3.get("__status__") == "COMPLETED", "Visa graph failed to reach COMPLETED status!"
        assert "VISA-JP-2026-OK" in state3.get("visa_number")
        print("  ✅ Phase 3 Passed: Visa issued successfully after admin HITL resolution.")


# ============================================================================
# TEST 2: SUPPLIER DISPUTE STATE GRAPH
# ============================================================================
def test_dispute_reconciliation_graph():
    print("\n--- 2. Testing Supplier Contract Dispute Graph ---")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        db_path = str(pathlib.Path(tmp_dir) / "test_dispute.sqlite3")
        checkpointer = DurableCheckpointer(db_path=db_path)
        graph = create_dispute_reconciliation_graph(checkpointer=checkpointer, db_path=db_path)
        thread_id = "thread-test-dispute-001"

        # Step 1: Run fresh to carrier adjudication pause
        print("  -> Running Dispute Graph Phase 1: Intake -> Tree of Thoughts -> Constrained ReAct -> Wait...")
        state1 = graph.run_sync(
            thread_id=thread_id,
            initial_state={"booking_id": 3, "carrier": "PacificFly", "amount_disputed": 450.00}
        )

        assert state1.get("__status__") == "INTERRUPTED"
        assert state1.get("selected_strategy") == "EU261_STATUTORY_CLAIM", "Tree of Thoughts LLM addition failed!"
        assert state1.get("gds_action_executed") == "gds_file_chargeback", "Constrained ReAct LLM addition failed!"
        print("  ✅ Phase 1 Passed: Tree of Thoughts selected EU261 and Constrained ReAct filed GDS claim.")

        # Step 2: Resume with carrier settlement (Waiver $350 > $300 -> Triggers HITL)
        print("  -> Running Dispute Graph Phase 2: Carrier Settlement Arrives -> Triggers HITL Waiver...")
        state2 = graph.run_sync(
            thread_id=thread_id,
            resume_payload={"carrier_settlement": {"decision": "OFFER_PARTIAL", "amount": 200.00, "fee_waiver": 350.00}}
        )

        assert state2.get("__status__") == "INTERRUPTED"
        assert state2.get("__interrupt_type__") == "HITL"
        assert "350.00" in state2.get("__interrupt_reason__")
        print("  ✅ Phase 2 Passed: HITL pause triggered gracefully for fee waiver > $300 threshold.")

        # Step 3: Admin approves settlement -> Finalize Dispute
        print("  -> Running Dispute Graph Phase 3: Admin Approves Settlement -> Ledger Adjusted...")
        state3 = graph.run_sync(
            thread_id=thread_id,
            resume_payload={"admin_approval": "APPROVED"}
        )

        assert state3.get("__status__") == "COMPLETED"
        assert state3.get("refund_credited") == 200.00
        assert state3.get("ledger_adjusted") is True
        print("  ✅ Phase 3 Passed: Ledger credited and dispute resolved.")


# ============================================================================
# TEST 3: VIP MEDICAL EVACUATION STATE GRAPH
# ============================================================================
def test_medevac_repatriation_graph():
    print("\n--- 3. Testing VIP Emergency Medical Evacuation Graph ---")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        db_path = str(pathlib.Path(tmp_dir) / "test_medevac.sqlite3")
        checkpointer = DurableCheckpointer(db_path=db_path)
        graph = create_medevac_repatriation_graph(checkpointer=checkpointer, db_path=db_path)
        thread_id = "thread-test-medevac-001"

        # Step 1: Run fresh to hospital admission pause
        print("  -> Running Medevac Graph Phase 1: Intake -> LATS Search -> Constrained ReAct -> Wait...")
        state1 = graph.run_sync(
            thread_id=thread_id,
            initial_state={"patient_name": "Elena Rostova", "current_location": "Bali (DPS)", "acuity_level": "CRITICAL"}
        )

        assert state1.get("__status__") == "INTERRUPTED"
        assert state1.get("selected_route_id") == "ROUTE_SGH_DIRECT", "LATS Routing LLM addition failed!"
        assert state1.get("dispatch_action_executed") == "medevac_issue_guarantee_and_standby", "Constrained ReAct failed!"
        print("  ✅ Phase 1 Passed: LATS selected direct Singapore ICU route and Constrained ReAct issued standby.")

        # Step 2: Resume with hospital confirmation -> Triggers HITL for physician dispatch sign-off
        print("  -> Running Medevac Graph Phase 2: ICU Bed Confirmed -> Triggers Physician HITL Sign-off...")
        state2 = graph.run_sync(
            thread_id=thread_id,
            resume_payload={"hospital_confirmation": {"confirmed": True, "bed_id": "ICU-BED-04", "physician": "Dr. K. Tan"}}
        )

        assert state2.get("__status__") == "INTERRUPTED"
        assert state2.get("__interrupt_type__") == "HITL"
        assert "14500.00" in state2.get("__interrupt_reason__")
        print("  ✅ Phase 2 Passed: Physician sign-off HITL triggered for charter authorization > $5,000.")

        # Step 3: Medical Director approves dispatch -> Medevac Airborne
        print("  -> Running Medevac Graph Phase 3: Medical Director Signs Off -> Airborne...")
        state3 = graph.run_sync(
            thread_id=thread_id,
            resume_payload={"admin_approval": "APPROVED"}
        )

        assert state3.get("__status__") == "COMPLETED"
        assert state3.get("evacuation_status") == "PATIENT_EN_ROUTE_TO_ICU"
        assert state3.get("flight_cleared") is True
        print("  ✅ Phase 3 Passed: Aircraft launched and patient en route to ICU.")


if __name__ == "__main__":
    print("==================================================================")
    print("🧪 RUNNING SUB-MODULE 3 VERIFICATION TESTS (Issue #64)")
    print("==================================================================")

    test_visa_processing_graph()
    test_dispute_reconciliation_graph()
    test_medevac_repatriation_graph()

    print("\n==================================================================")
    print("🎉 ALL 3 STATEFUL GRAPHS VERIFIED 100% SUCCESSFULLY!")
    print("==================================================================")
