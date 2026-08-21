"""
Wanderpath Travel Agency - Problem 1: International Visa & Consular Application Graph
=====================================================================================
Stateful problem spanning weeks across diplomatic milestones, waiting for embassy webhooks,
and handling document requests and fee approvals.

Embedded LLM Additions:
1. Task Decomposition (Milestone breakdown of consular requirements)
2. RAG Architecture (Querying vector store for real-time embassy visa rules)
"""

import json
import logging
from typing import Any, Dict, Optional

from rag.vector_store import WanderpathVectorStore
from state_graph.base import END, InterruptSignal, StateGraph
from state_graph.checkpointer import DurableCheckpointer

logger = logging.getLogger("VisaProcessingGraph")


def create_visa_processing_graph(checkpointer: Optional[DurableCheckpointer] = None, db_path: Optional[str] = None) -> StateGraph:
    graph = StateGraph("visa_processing_graph", checkpointer=checkpointer, db_path=db_path)

    # Initialize RAG Vector Store for Consular Knowledge
    vector_db = WanderpathVectorStore(collection_name="consular_knowledge_db")
    # Ingest baseline embassy rules if empty
    if len(vector_db.list_documents()) == 0:
        vector_db.add_document(
            doc_id="embassy_japan_policy",
            document="Japan Consular Policy: Tourist e-Visa processing takes 5-7 business days. Passport must be valid for intended stay. Expedited processing incurs $150 fee.",
            metadata={"country": "Japan", "visa_type": "tourist"}
        )
        vector_db.add_document(
            doc_id="embassy_schengen_policy",
            document="Schengen Visa Policy: Requires 3 months passport validity beyond departure date, proof of accommodation, and biometrics. Expedited emergency processing fee is $650.",
            metadata={"country": "France", "visa_type": "schengen"}
        )
        vector_db.add_document(
            doc_id="embassy_indonesia_policy",
            document="Indonesia Policy: Visa on Arrival (VoA) valid for 30 days. Passport must have at least 6 months validity from entry date.",
            metadata={"country": "Indonesia", "visa_type": "voa"}
        )

    # ========================================================================
    # NODE 1: Intake Visa Request
    # ========================================================================
    def intake_visa_request(state: Dict[str, Any]) -> Dict[str, Any]:
        client_id = state.get("client_id", 1)
        destination = state.get("destination", "Japan")
        visa_type = state.get("visa_type", "tourist")
        
        logger.info(f"[VisaGraph] Intake request for Client #{client_id} -> {destination} ({visa_type})")
        return {
            "client_id": client_id,
            "destination": destination,
            "visa_type": visa_type,
            "application_status": "INTAKE_COMPLETED",
            "cycle_count": state.get("cycle_count", 0),
        }

    # ========================================================================
    # NODE 2: LLM ADDITION 1 — Task Decomposition (Milestone Roadmap)
    # ========================================================================
    def decompose_consular_roadmap(state: Dict[str, Any]) -> Dict[str, Any]:
        destination = state.get("destination", "Japan")
        visa_type = state.get("visa_type", "tourist")
        
        logger.info(f"[VisaGraph] 🧠 LLM ADDITION 1 (Task Decomposition): Breaking down milestones for {destination}")
        
        # Decomposed sub-milestones
        milestones = [
            f"1. Validate passport validity and photo specifications for {destination}",
            f"2. Query embassy consular knowledge base for {visa_type} requirements",
            f"3. Prepare certified application dossier and financial sponsorship records",
            f"4. Submit electronic visa application to {destination} consular portal",
            f"5. Await consular status webhook / appointment slot confirmation",
            f"6. Process visa fee payment and verify final visa issuance",
        ]

        if state.get("additional_docs_requested"):
            milestones.insert(3, f"3b. [RE-DECOMPOSED] Gather requested supplementary documentation: {state['additional_docs_requested']}")

        return {
            "consular_milestones": milestones,
            "current_milestone_index": 1,
            "roadmap_decomposed": True,
        }

    # ========================================================================
    # NODE 3: LLM ADDITION 2 — RAG Architecture (Embassy Rules Retrieval)
    # ========================================================================
    def retrieve_embassy_policy(state: Dict[str, Any]) -> Dict[str, Any]:
        destination = state.get("destination", "Japan")
        visa_type = state.get("visa_type", "tourist")
        
        logger.info(f"[VisaGraph] 🔍 LLM ADDITION 2 (RAG): Retrieving consular rules for {destination}...")
        
        retrieved = vector_db.similarity_search(f"{destination} {visa_type} embassy requirements", n_results=1)
        policy_text = retrieved[0]["document"] if retrieved else "Standard consular processing guidelines apply."
        
        # Parse expedited fee from policy if present
        expedited_fee = 0.0
        if "$650" in policy_text:
            expedited_fee = 650.0
        elif "$150" in policy_text:
            expedited_fee = 150.0

        return {
            "retrieved_consular_policy": policy_text,
            "expedited_fee": expedited_fee,
            "policy_retrieved": True,
        }

    # ========================================================================
    # NODE 4: Submit Application to Consular Portal
    # ========================================================================
    def submit_to_consulate(state: Dict[str, Any]) -> Dict[str, Any]:
        destination = state.get("destination")
        logger.info(f"[VisaGraph] Submitting digital dossier to {destination} consulate portal...")
        
        # Simulated external submission reference
        consular_ref = f"CONS-{destination.upper()[:3]}-2026-991"
        return {
            "consular_reference": consular_ref,
            "submitted_at": "2026-08-22T02:00:00Z",
            "awaiting_webhook": True,
        }

    # ========================================================================
    # NODE 5: Awaiting Consular Webhook (Asynchronous Wait State)
    # ========================================================================
    def awaiting_consular_webhook(state: Dict[str, Any]) -> Dict[str, Any]:
        # If webhook payload has arrived in resume_payload, process it
        webhook_data = state.get("webhook_payload") or state.get("__resume_payload__", {}).get("webhook_payload")
        
        if not webhook_data:
            logger.info("[VisaGraph] ⏸️ State: Pausing graph — Awaiting external consular webhook...")
            raise InterruptSignal(
                reason="Awaiting asynchronous embassy status webhook or biometrics slot confirmation",
                interrupt_type="AWAITING_EXTERNAL",
                payload={"consular_reference": state.get("consular_reference")},
            )
        
        logger.info(f"[VisaGraph] 📥 Consular webhook received: {webhook_data}")
        return {
            "webhook_received": True,
            "consular_decision": webhook_data.get("decision", "APPROVED"),
            "consular_fee_charged": webhook_data.get("fee", state.get("expedited_fee", 0.0)),
            "consular_notes": webhook_data.get("notes", "All requirements verified."),
            "additional_docs_requested": webhook_data.get("additional_docs"),
        }

    # ========================================================================
    # NODE 6: Evaluate Response & Check HITL Trigger
    # ========================================================================
    def evaluate_consular_response(state: Dict[str, Any]) -> Dict[str, Any]:
        fee = state.get("consular_fee_charged", 0.0)
        decision = state.get("consular_decision", "APPROVED")
        admin_approval = state.get("admin_approval") or state.get("__resume_payload__", {}).get("admin_approval")

        # HITL Condition: Expedited fees exceeding $500 threshold or ambiguous flag
        if fee > 500.0 and not admin_approval:
            logger.info(f"[VisaGraph] 🚨 HITL TRIGGER: Expedited consular fee ${fee} exceeds $500 threshold!")
            raise InterruptSignal(
                reason=f"Expedited consular fee of ${fee:.2f} exceeds standard agency authorization threshold ($500.00)",
                interrupt_type="HITL",
                threshold_info=f"Fee: ${fee:.2f} > $500.00 limit",
                payload={
                    "client_id": state.get("client_id"),
                    "destination": state.get("destination"),
                    "fee": fee,
                    "reason": "Expedited Emergency Consular Processing",
                },
            )

        if admin_approval == "REJECTED":
            return {"application_status": "CANCELLED_BY_ADMIN", "final_decision": "REJECTED"}

        return {
            "fee_authorized": True,
            "consular_decision": decision,
            "application_status": "APPROVED" if decision == "APPROVED" else "NEEDS_REVISION",
        }

    # ========================================================================
    # NODE 7: Finalize Visa Record
    # ========================================================================
    def finalize_visa(state: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"[VisaGraph] ✅ Visa issued successfully for Client #{state.get('client_id')} ({state.get('destination')})")
        return {
            "visa_number": f"VISA-JP-2026-OK-{state.get('client_id')}",
            "application_status": "COMPLETED_ISSUED",
            "is_completed": True,
        }

    # Conditional Routing Function (Branching & Cycles)
    def route_after_evaluation(state: Dict[str, Any]) -> str:
        if state.get("additional_docs_requested"):
            # CYCLE: Loop back to decomposition to handle supplementary docs
            cycle = state.get("cycle_count", 0) + 1
            state["cycle_count"] = cycle
            logger.info(f"[VisaGraph] 🔁 Cycle Triggered: Supplementary docs requested (Cycle #{cycle}). Returning to decompose_consular_roadmap.")
            return "decompose_consular_roadmap"

        if state.get("application_status") == "CANCELLED_BY_ADMIN":
            return END

        return "finalize_visa"

    # Register Nodes
    graph.add_node("intake_visa_request", intake_visa_request)
    graph.add_node("decompose_consular_roadmap", decompose_consular_roadmap)
    graph.add_node("retrieve_embassy_policy", retrieve_embassy_policy)
    graph.add_node("submit_to_consulate", submit_to_consulate)
    graph.add_node("awaiting_consular_webhook", awaiting_consular_webhook)
    graph.add_node("evaluate_consular_response", evaluate_consular_response)
    graph.add_node("finalize_visa", finalize_visa)

    # Register Edges
    graph.add_edge("intake_visa_request", "decompose_consular_roadmap")
    graph.add_edge("decompose_consular_roadmap", "retrieve_embassy_policy")
    graph.add_edge("retrieve_embassy_policy", "submit_to_consulate")
    graph.add_edge("submit_to_consulate", "awaiting_consular_webhook")
    graph.add_edge("awaiting_consular_webhook", "evaluate_consular_response")
    
    # Conditional edge with potential cycle back to decomposition
    graph.add_conditional_edge(
        "evaluate_consular_response",
        route_after_evaluation,
        {
            "decompose_consular_roadmap": "decompose_consular_roadmap",
            "finalize_visa": "finalize_visa",
            END: END,
        }
    )
    graph.add_edge("finalize_visa", END)

    graph.set_entry_point("intake_visa_request")
    return graph
