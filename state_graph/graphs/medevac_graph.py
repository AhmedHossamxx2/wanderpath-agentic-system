"""
Wanderpath Travel Agency - Problem 3: VIP Emergency Medical Evacuation Graph
============================================================================
Stateful problem handling urgent patient evacuation, flight routing constraints,
receiving hospital bed waits, and physician sign-offs.

Embedded LLM Additions:
1. LATS (Language Agent Tree Search) (Route & airfield search scored against live constraints)
2. Constrained ReAct (Executing whitelisted medical dispatch and guarantee letter tools)
"""

import json
import logging
from typing import Any, Dict, List, Optional

from state_graph.base import END, InterruptSignal, StateGraph
from state_graph.checkpointer import DurableCheckpointer

logger = logging.getLogger("MedevacRepatriationGraph")


def create_medevac_repatriation_graph(
    checkpointer: Optional[DurableCheckpointer] = None, db_path: Optional[str] = None
) -> StateGraph:
    graph = StateGraph("medevac_repatriation_graph", checkpointer=checkpointer, db_path=db_path)

    # ========================================================================
    # NODE 1: Intake Emergency Medical Alert
    # ========================================================================
    def intake_medical_alert(state: Dict[str, Any]) -> Dict[str, Any]:
        patient_name = state.get("patient_name", "Elena Rostova")
        current_location = state.get("current_location", "Bali (DPS)")
        medical_condition = state.get("medical_condition", "Acute spinal trauma requiring ICU transport")
        acuity_level = state.get("acuity_level", "CRITICAL")

        logger.info(f"[MedevacGraph] 🚨 Intake Medical Alert: Patient '{patient_name}' at {current_location} ({acuity_level})")
        return {
            "patient_name": patient_name,
            "current_location": current_location,
            "medical_condition": medical_condition,
            "acuity_level": acuity_level,
            "evacuation_status": "TRIAGE_COMPLETED",
            "cycle_count": state.get("cycle_count", 0),
        }

    # ========================================================================
    # NODE 2: LLM ADDITION 1 — LATS (Language Agent Tree Search Routing)
    # ========================================================================
    def search_evacuation_routes(state: Dict[str, Any]) -> Dict[str, Any]:
        location = state.get("current_location", "Bali (DPS)")
        acuity = state.get("acuity_level", "CRITICAL")
        
        logger.info(f"[MedevacGraph] 🧠 LLM ADDITION 1 (LATS): Tree-searching candidate flight routings for {location}...")

        # Action 1: Learjet 60XR Direct Medevac to Singapore General Hospital (SGH)
        action_1 = {
            "route_id": "ROUTE_SGH_DIRECT",
            "aircraft_type": "Learjet 60XR Dedicated Air Ambulance",
            "transit_hub": "Singapore (SIN)",
            "destination_hospital": "Singapore General Hospital (ICU Level 1)",
            "flight_time_hours": 2.5,
            "grounded_score": 0.96,  # Validated: runway length, 24/7 customs, ICU beds open
            "cost_estimate": 14500.00,
            "validation_notes": "Optimal route. 24h trauma center and nighttime runway cleared.",
        }

        # Action 2: Commercial Stretcher Transfer via Jakarta
        action_2 = {
            "route_id": "ROUTE_COMMERCIAL_STRETCHER",
            "aircraft_type": "Commercial Carrier with 6-Seat Stretcher Install",
            "transit_hub": "Jakarta (CGK)",
            "destination_hospital": "Jakarta Medika Hospital",
            "flight_time_hours": 5.0,
            "grounded_score": 0.45,  # Rejected for CRITICAL acuity (too slow, staging delay)
            "cost_estimate": 4200.00,
            "validation_notes": "Sub-optimal: 5 hour transit delay too risky for acute spinal trauma.",
        }

        # Action 3: Alternative Tertiary Route to Bangkok Bumrungrad Hospital
        action_3 = {
            "route_id": "ROUTE_BANGKOK_TERTIARY",
            "aircraft_type": "Challenger 604 Heavy Medevac",
            "transit_hub": "Bangkok (BKK)",
            "destination_hospital": "Bumrungrad International Hospital",
            "flight_time_hours": 3.8,
            "grounded_score": 0.88,
            "cost_estimate": 16000.00,
            "validation_notes": "Viable secondary backup route if Singapore ICU capacity saturates.",
        }

        candidates = [action_1, action_2, action_3]

        if state.get("hospital_beds_saturated"):
            # LATS selects secondary route on ICU saturation cycle
            selected = action_3
            logger.info("[MedevacGraph] 🔁 LATS re-routing to secondary tertiary facility: Bangkok Bumrungrad Hospital.")
        else:
            selected = max(candidates, key=lambda a: a["grounded_score"])

        logger.info(f"[MedevacGraph] 🏆 LATS Selected Route: {selected['route_id']} (Score: {selected['grounded_score']})")

        return {
            "lats_routes": candidates,
            "selected_route_id": selected["route_id"],
            "aircraft_type": selected["aircraft_type"],
            "destination_hospital": selected["destination_hospital"],
            "estimated_cost": selected["cost_estimate"],
            "flight_duration": selected["flight_time_hours"],
        }

    # ========================================================================
    # NODE 3: LLM ADDITION 2 — Constrained ReAct (Medical Dispatch Tool Execution)
    # ========================================================================
    def dispatch_medical_charter(state: Dict[str, Any]) -> Dict[str, Any]:
        route_id = state.get("selected_route_id")
        aircraft = state.get("aircraft_type")
        cost = state.get("estimated_cost", 14500.00)

        logger.info(f"[MedevacGraph] ⚡ LLM ADDITION 2 (Constrained ReAct): Executing whitelisted medevac dispatch tool...")

        # Constrained action execution
        whitelisted_tool = "medevac_issue_guarantee_and_standby"
        payload = {
            "route_id": route_id,
            "aircraft": aircraft,
            "guarantee_of_payment": cost,
        }

        observation = f"Charter Standby Activated for {aircraft}. Flight clearance WP-MED-99 logged."
        logger.info(f"[MedevacGraph] 📥 Dispatch Tool Observation: {observation}")

        return {
            "dispatch_action_executed": whitelisted_tool,
            "dispatch_ref": "WP-MED-99",
            "dispatch_observation": observation,
            "awaiting_bed": True,
        }

    # ========================================================================
    # NODE 4: Awaiting Hospital Admission (Asynchronous Wait State)
    # ========================================================================
    def awaiting_hospital_admission(state: Dict[str, Any]) -> Dict[str, Any]:
        hospital_data = state.get("hospital_confirmation") or state.get("__resume_payload__", {}).get("hospital_confirmation")

        if not hospital_data:
            logger.info("[MedevacGraph] ⏸️ State: Pausing graph — Awaiting receiving hospital ICU bed confirmation...")
            raise InterruptSignal(
                reason=f"Awaiting ICU bed availability confirmation from {state.get('destination_hospital')}",
                interrupt_type="AWAITING_EXTERNAL",
                payload={"destination_hospital": state.get("destination_hospital"), "patient": state.get("patient_name")},
            )

        logger.info(f"[MedevacGraph] 📥 Hospital admission update received: {hospital_data}")
        return {
            "hospital_confirmed": hospital_data.get("confirmed", True),
            "assigned_bed_id": hospital_data.get("bed_id", "ICU-BED-04"),
            "admitting_physician": hospital_data.get("physician", "Dr. K. Tan"),
            "hospital_beds_saturated": hospital_data.get("saturated", False),
        }

    # ========================================================================
    # NODE 5: Evaluate Authorization & Check HITL Trigger
    # ========================================================================
    def evaluate_physician_authorization(state: Dict[str, Any]) -> Dict[str, Any]:
        cost = state.get("estimated_cost", 14500.00)
        admin_approval = state.get("admin_approval") or state.get("__resume_payload__", {}).get("admin_approval")

        # HITL Condition: Irreversible air ambulance launch and guarantee amount > $5,000
        if cost > 5000.0 and not admin_approval:
            logger.info(f"[MedevacGraph] 🚨 HITL TRIGGER: Medevac charter cost ${cost} > $5,000 and requires Physician Sign-Off!")
            raise InterruptSignal(
                reason=f"Irreversible Medevac Air Charter dispatch requires Senior Medical Director authorization (Guarantee amount: ${cost:.2f} exceeds $5,000 limit)",
                interrupt_type="HITL",
                threshold_info=f"Charter Guarantee: ${cost:.2f} > $5,000.00 limit | Acuity: CRITICAL",
                payload={
                    "patient_name": state.get("patient_name"),
                    "route": state.get("selected_route_id"),
                    "destination_hospital": state.get("destination_hospital"),
                    "aircraft": state.get("aircraft_type"),
                    "cost": cost,
                },
            )

        if admin_approval == "REJECTED":
            return {"evacuation_status": "REJECTED_BY_PHYSICIAN", "final_resolution": "CANCELLED"}

        return {
            "physician_authorized": True,
            "flight_cleared": True,
            "evacuation_status": "AUTHORIZED_AND_DISPATCHED",
        }

    # ========================================================================
    # NODE 6: Finalize Repatriation Mission
    # ========================================================================
    def finalize_repatriation(state: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"[MedevacGraph] ✈️ Medevac airborne! Patient '{state.get('patient_name')}' en route to {state.get('destination_hospital')}")
        return {
            "mission_id": "MEDEVAC-MISSION-2026-COMPLETE",
            "evacuation_status": "PATIENT_EN_ROUTE_TO_ICU",
            "is_completed": True,
        }

    # Conditional Routing (Branching & Cycles)
    def route_medevac_transition(state: Dict[str, Any]) -> str:
        if state.get("hospital_beds_saturated"):
            cycle = state.get("cycle_count", 0) + 1
            if cycle <= 2:
                state["cycle_count"] = cycle
                logger.info(f"[MedevacGraph] 🔁 Cycle Triggered: Primary ICU saturated. LATS re-routing to secondary hospital (Cycle #{cycle}).")
                return "search_evacuation_routes"

        if state.get("evacuation_status") == "REJECTED_BY_PHYSICIAN":
            return END

        return "finalize_repatriation"

    # Register Nodes
    graph.add_node("intake_medical_alert", intake_medical_alert)
    graph.add_node("search_evacuation_routes", search_evacuation_routes)
    graph.add_node("dispatch_medical_charter", dispatch_medical_charter)
    graph.add_node("awaiting_hospital_admission", awaiting_hospital_admission)
    graph.add_node("evaluate_physician_authorization", evaluate_physician_authorization)
    graph.add_node("finalize_repatriation", finalize_repatriation)

    # Register Edges
    graph.add_edge("intake_medical_alert", "search_evacuation_routes")
    graph.add_edge("search_evacuation_routes", "dispatch_medical_charter")
    graph.add_edge("dispatch_medical_charter", "awaiting_hospital_admission")
    graph.add_edge("awaiting_hospital_admission", "evaluate_physician_authorization")
    
    graph.add_conditional_edge(
        "evaluate_physician_authorization",
        route_medevac_transition,
        {
            "search_evacuation_routes": "search_evacuation_routes",
            "finalize_repatriation": "finalize_repatriation",
            END: END,
        }
    )
    graph.add_edge("finalize_repatriation", END)

    graph.set_entry_point("intake_medical_alert")
    return graph
