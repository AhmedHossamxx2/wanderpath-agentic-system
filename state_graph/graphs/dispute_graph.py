"""
Wanderpath Travel Agency - Problem 2: Supplier Dispute & Chargeback Appeal Graph
==============================================================================
Stateful problem managing airline/hotel contract disputes, 7-day carrier response windows,
and arbitration appeals.

Embedded LLM Additions:
1. Tree of Thoughts (ToT) (Exploring and scoring legal appeal strategies)
2. Constrained ReAct (Executing strictly whitelisted GDS write tools)
"""

import json
import logging
from typing import Any, Dict, List, Optional

from state_graph.base import END, InterruptSignal, StateGraph
from state_graph.checkpointer import DurableCheckpointer

logger = logging.getLogger("DisputeReconciliationGraph")


def create_dispute_reconciliation_graph(
    checkpointer: Optional[DurableCheckpointer] = None, db_path: Optional[str] = None
) -> StateGraph:
    graph = StateGraph("supplier_dispute_graph", checkpointer=checkpointer, db_path=db_path)

    # ========================================================================
    # NODE 1: Intake Dispute Claim
    # ========================================================================
    def intake_dispute_claim(state: Dict[str, Any]) -> Dict[str, Any]:
        booking_id = state.get("booking_id", 3)
        carrier = state.get("carrier", "PacificFly")
        amount_disputed = state.get("amount_disputed", 450.00)
        dispute_reason = state.get("dispute_reason", "Carrier canceled flight due to strike with < 24h notice.")

        logger.info(f"[DisputeGraph] Intake claim for Booking #{booking_id} | Carrier: {carrier} | Amount: ${amount_disputed}")
        return {
            "booking_id": booking_id,
            "carrier": carrier,
            "amount_disputed": amount_disputed,
            "dispute_reason": dispute_reason,
            "claim_status": "INTAKE_LOGGED",
            "cycle_count": state.get("cycle_count", 0),
        }

    # ========================================================================
    # NODE 2: LLM ADDITION 1 — Tree of Thoughts (ToT Appeal Strategy Selection)
    # ========================================================================
    def evaluate_appeal_strategies(state: Dict[str, Any]) -> Dict[str, Any]:
        dispute_reason = state.get("dispute_reason", "")
        amount = state.get("amount_disputed", 450.00)
        
        logger.info(f"[DisputeGraph] 🧠 LLM ADDITION 1 (Tree of Thoughts): Generating candidate legal appeal branches...")
        
        # Branch 1: EU261 Statutory Compensation
        branch_1 = {
            "strategy": "EU261_STATUTORY_CLAIM",
            "argument": "Involuntary cancellation under 14 days without extraordinary circumstances; demanding full refund + €400 statutory penalty.",
            "estimated_recovery": amount + 400.0,
            "confidence_score": 0.92,
        }

        # Branch 2: Force Majeure Strike Breach
        branch_2 = {
            "strategy": "CONTRACT_BREACH_FORCE_MAJEURE",
            "argument": "Airline internal labor strike does not constitute third-party force majeure per IATA Regulation 204.",
            "estimated_recovery": amount,
            "confidence_score": 0.85,
        }

        # Branch 3: Commercial Goodwill Dispute
        branch_3 = {
            "strategy": "COMMERCIAL_GOODWILL_ESCALATION",
            "argument": "Key agency partner tier escalation requesting commercial fee waiver.",
            "estimated_recovery": amount * 0.75,
            "confidence_score": 0.60,
        }

        candidates = [branch_1, branch_2, branch_3]
        
        # Select best thought branch
        best_branch = max(candidates, key=lambda b: b["confidence_score"] * b["estimated_recovery"])
        logger.info(f"[DisputeGraph] 🏆 ToT Selected Strategy: {best_branch['strategy']} (Score: {best_branch['confidence_score']})")

        return {
            "tot_candidates": candidates,
            "selected_strategy": best_branch["strategy"],
            "selected_argument": best_branch["argument"],
            "expected_payout": best_branch["estimated_recovery"],
        }

    # ========================================================================
    # NODE 3: LLM ADDITION 2 — Constrained ReAct (Whitelisted GDS Tool Execution)
    # ========================================================================
    def execute_gds_filing(state: Dict[str, Any]) -> Dict[str, Any]:
        booking_id = state.get("booking_id")
        strategy = state.get("selected_strategy")
        argument = state.get("selected_argument")

        logger.info(f"[DisputeGraph] ⚡ LLM ADDITION 2 (Constrained ReAct): Calling whitelisted GDS filing tool for Booking #{booking_id}...")

        # Constrained action execution
        whitelisted_action = "gds_file_chargeback"
        tool_payload = {
            "booking_id": booking_id,
            "claim_type": strategy,
            "legal_basis": argument,
            "requested_settlement": state.get("expected_payout"),
        }

        # Simulated tool observation
        observation = f"GDS Case #{booking_id}-DISP successfully submitted to carrier adjudication clearinghouse."
        logger.info(f"[DisputeGraph] 📥 GDS Tool Observation: {observation}")

        return {
            "gds_action_executed": whitelisted_action,
            "gds_filing_ref": f"GDS-DISP-{booking_id}",
            "filing_observation": observation,
            "awaiting_settlement": True,
        }

    # ========================================================================
    # NODE 4: Awaiting Carrier Adjudication (Asynchronous Wait State)
    # ========================================================================
    def awaiting_carrier_adjudication(state: Dict[str, Any]) -> Dict[str, Any]:
        settlement_data = (
            state.get("carrier_settlement")
            or state.get("__resume_payload__", {}).get("carrier_settlement")
            or state.get("__resume_payload__")
        )
        
        if not settlement_data:
            logger.info("[DisputeGraph] ⏸️ State: Pausing graph — Awaiting carrier dispute settlement response (7-day window)...")
            raise InterruptSignal(
                reason="Awaiting airline dispute settlement response or clearinghouse rebuttal",
                interrupt_type="AWAITING_EXTERNAL",
                payload={"gds_filing_ref": state.get("gds_filing_ref"), "carrier": state.get("carrier")},
            )

        logger.info(f"[DisputeGraph] 📥 Carrier settlement response received: {settlement_data}")
        return {
            "carrier_decision": settlement_data.get("decision", "OFFER_PARTIAL"),
            "offered_amount": settlement_data.get("amount", 200.00),
            "waived_fee_requested": settlement_data.get("fee_waiver", 350.00),
            "requires_indemnity": settlement_data.get("requires_indemnity", False),
            "carrier_rebuttal": settlement_data.get("rebuttal_notes"),
        }

    # ========================================================================
    # NODE 5: Evaluate Settlement & Check HITL Trigger
    # ========================================================================
    def evaluate_settlement_offer(state: Dict[str, Any]) -> Dict[str, Any]:
        decision = state.get("carrier_decision")
        waived_fee = state.get("waived_fee_requested", 0.0)
        requires_indemnity = state.get("requires_indemnity", False)
        admin_approval = state.get("admin_approval") or state.get("__resume_payload__", {}).get("admin_approval")

        # HITL Condition: Carrier requires fee waiver > $300 or demands legal indemnification
        if (waived_fee > 300.0 or requires_indemnity) and not admin_approval:
            logger.info(f"[DisputeGraph] 🚨 HITL TRIGGER: Fee waiver ${waived_fee} > $300 or indemnity required!")
            raise InterruptSignal(
                reason=f"Carrier settlement requires absorbing a fee waiver of ${waived_fee:.2f} (Threshold > $300.00) or legal indemnification",
                interrupt_type="HITL",
                threshold_info=f"Fee Waiver: ${waived_fee:.2f} > $300 limit | Indemnity: {requires_indemnity}",
                payload={
                    "booking_id": state.get("booking_id"),
                    "carrier": state.get("carrier"),
                    "offered_amount": state.get("offered_amount"),
                    "waived_fee": waived_fee,
                    "requires_indemnity": requires_indemnity,
                },
            )

        if admin_approval == "REJECTED":
            return {"claim_status": "REJECTED_BY_ADMIN", "final_settlement": 0.0}

        return {
            "settlement_authorized": True,
            "final_settlement": state.get("offered_amount", state.get("amount_disputed")),
            "claim_status": "ACCEPTED" if decision != "REJECTED" else "REJECTED_BY_CARRIER",
        }

    # ========================================================================
    # NODE 6: Finalize Ledger & Refund Disbursement
    # ========================================================================
    def finalize_dispute(state: Dict[str, Any]) -> Dict[str, Any]:
        settlement = state.get("final_settlement", 0.0)
        logger.info(f"[DisputeGraph] ✅ Dispute resolved. Ledger credited with ${settlement:.2f} for Booking #{state.get('booking_id')}")
        return {
            "ledger_adjusted": True,
            "refund_credited": settlement,
            "claim_status": "SETTLED_COMPLETED",
            "is_completed": True,
        }

    # Conditional Routing (Branching & Cycles)
    def route_dispute_transition(state: Dict[str, Any]) -> str:
        if state.get("carrier_rebuttal") and state.get("claim_status") == "REJECTED_BY_CARRIER":
            cycle = state.get("cycle_count", 0) + 1
            if cycle <= 2:
                state["cycle_count"] = cycle
                logger.info(f"[DisputeGraph] 🔁 Cycle Triggered: Carrier rejected initial claim. Re-evaluating ToT appeal strategies (Cycle #{cycle}).")
                return "evaluate_appeal_strategies"

        if state.get("claim_status") == "REJECTED_BY_ADMIN":
            return END

        return "finalize_dispute"

    # Register Nodes
    graph.add_node("intake_dispute_claim", intake_dispute_claim)
    graph.add_node("evaluate_appeal_strategies", evaluate_appeal_strategies)
    graph.add_node("execute_gds_filing", execute_gds_filing)
    graph.add_node("awaiting_carrier_adjudication", awaiting_carrier_adjudication)
    graph.add_node("evaluate_settlement_offer", evaluate_settlement_offer)
    graph.add_node("finalize_dispute", finalize_dispute)

    # Register Edges
    graph.add_edge("intake_dispute_claim", "evaluate_appeal_strategies")
    graph.add_edge("evaluate_appeal_strategies", "execute_gds_filing")
    graph.add_edge("execute_gds_filing", "awaiting_carrier_adjudication")
    graph.add_edge("awaiting_carrier_adjudication", "evaluate_settlement_offer")
    
    graph.add_conditional_edge(
        "evaluate_settlement_offer",
        route_dispute_transition,
        {
            "evaluate_appeal_strategies": "evaluate_appeal_strategies",
            "finalize_dispute": "finalize_dispute",
            END: END,
        }
    )
    graph.add_edge("finalize_dispute", END)

    graph.set_entry_point("intake_dispute_claim")
    return graph
