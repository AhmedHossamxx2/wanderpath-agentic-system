# Wanderpath Travel Agency — Live Demo Transcript
## Scenario 3: VIP Emergency Medical Evacuation & Dynamic Repatriation
**Graph**: `medevac_repatriation_graph.py` | **Architecture**: Cyclic State Graph with SQLite Durable Checkpoints  
**Embedded LLM Additions**: 1. LATS (Language Agent Tree Search) Airfield Routing • 2. Constrained ReAct Tool Execution  
**Asynchronous Wait State**: `awaiting_hospital_admission` | **HITL Gate**: Physician Sign-Off & Charter Launch > $5,000  

---

### Step 1: Emergency Triage Alert Intake
```json
{
  "timestamp": "2026-08-22T02:20:01.000Z",
  "event": "CHAT_REQUEST_RECEIVED",
  "agent_id": "medevac_agent",
  "thread_id": "thread-demo-med-003",
  "user_message": "Patient Elena Rostova suffered acute spinal trauma in Bali (DPS). Requesting urgent ICU aeromedical evacuation charter to Singapore General Hospital."
}
```

```json
{
  "timestamp": "2026-08-22T02:20:01.200Z",
  "node": "intake_medical_alert",
  "state_transition": {
    "patient_name": "Elena Rostova",
    "current_location": "Bali (DPS)",
    "medical_condition": "Acute spinal trauma requiring ICU transport",
    "acuity_level": "CRITICAL",
    "evacuation_status": "TRIAGE_COMPLETED"
  },
  "checkpoint_id": "chk-m01-a1b2c3d4"
}
```

---

### Step 2: LLM Addition 1 — LATS (Language Agent Tree Search) Airfield Search
```json
{
  "timestamp": "2026-08-22T02:20:01.500Z",
  "node": "search_evacuation_routes",
  "action": "LATS_TREE_SEARCH",
  "candidate_routes_searched": [
    {
      "route_id": "ROUTE_SGH_DIRECT",
      "aircraft_type": "Learjet 60XR Dedicated Air Ambulance",
      "transit_hub": "Singapore (SIN)",
      "destination_hospital": "Singapore General Hospital (ICU Level 1)",
      "flight_time_hours": 2.5,
      "grounded_score": 0.96,
      "cost_estimate": 14500.00,
      "grounded_validation": "Grounded airfield cleared: 24/7 runway length and trauma team on standby."
    },
    {
      "route_id": "ROUTE_COMMERCIAL_STRETCHER",
      "aircraft_type": "Commercial Carrier with 6-Seat Stretcher Install",
      "transit_hub": "Jakarta (CGK)",
      "destination_hospital": "Jakarta Medika Hospital",
      "flight_time_hours": 5.0,
      "grounded_score": 0.45,
      "grounded_validation": "REJECTED: 5-hour transit exceeds safe window for acute spinal trauma."
    },
    {
      "route_id": "ROUTE_BANGKOK_TERTIARY",
      "aircraft_type": "Challenger 604 Heavy Medevac",
      "transit_hub": "Bangkok (BKK)",
      "destination_hospital": "Bumrungrad International Hospital",
      "flight_time_hours": 3.8,
      "grounded_score": 0.88,
      "cost_estimate": 16000.00,
      "grounded_validation": "Validated secondary backup route if Singapore ICU capacity saturates."
    }
  ],
  "selected_route": "ROUTE_SGH_DIRECT (Score: 0.96)",
  "checkpoint_id": "chk-m02-e5f6g7h8"
}
```

---

### Step 3: LLM Addition 2 — Constrained ReAct (Charter Standby Tool)
```json
{
  "timestamp": "2026-08-22T02:20:01.800Z",
  "node": "dispatch_medical_charter",
  "action": "CONSTRAINED_REACT_TOOL_CALL",
  "tool_called": "medevac_issue_guarantee_and_standby",
  "tool_payload": {
    "route_id": "ROUTE_SGH_DIRECT",
    "aircraft": "Learjet 60XR Dedicated Air Ambulance",
    "guarantee_of_payment": 14500.00
  },
  "tool_observation": "Charter Standby Activated for Learjet 60XR Dedicated Air Ambulance. Flight clearance WP-MED-99 logged.",
  "dispatch_ref": "WP-MED-99",
  "checkpoint_id": "chk-m03-i9j0k1l2"
}
```

---

### Step 4: Receiving Hospital Bed Admission Wait State
```json
{
  "timestamp": "2026-08-22T02:20:02.050Z",
  "node": "awaiting_hospital_admission",
  "status": "INTERRUPTED",
  "interrupt_type": "AWAITING_EXTERNAL",
  "reason": "Awaiting ICU bed availability confirmation from Singapore General Hospital (ICU Level 1)",
  "checkpoint_id": "chk-m04-m3n4o5p6"
}
```

---

### Step 5: Bed Confirmation Arrives & Triggers Medical Director HITL Gate
```json
{
  "timestamp": "2026-08-22T02:20:15.000Z",
  "event": "HOSPITAL_BED_CONFIRMED",
  "payload": {
    "confirmed": true,
    "bed_id": "ICU-BED-04",
    "physician": "Dr. K. Tan",
    "saturated": false
  }
}
```

```json
{
  "timestamp": "2026-08-22T02:20:15.250Z",
  "node": "evaluate_physician_authorization",
  "status": "INTERRUPTED",
  "interrupt_type": "HITL",
  "reason": "Irreversible Medevac Air Charter dispatch requires Senior Medical Director authorization (Guarantee amount: $14,500.00 exceeds $5,000 limit)",
  "threshold_info": "Charter Guarantee: $14,500.00 > $5,000.00 limit | Acuity: CRITICAL",
  "hitl_task_id": "hitl-med-990",
  "persisted_table": "hitl_tasks",
  "checkpoint_id": "chk-m05-q7r8s9t0"
}
```

---

### Step 6: Platform UI Medical Director Approval & Aircraft Launch
```json
{
  "timestamp": "2026-08-22T02:20:30.150Z",
  "platform_endpoint": "POST /api/admin/hitl/tasks/hitl-med-990/resolve",
  "admin_decision": "APPROVED",
  "admin_notes": "Dr. Aris Thorne (Chief Medical Officer) signs off on Learjet 60XR launch to SGH ICU-04."
}
```

```json
{
  "timestamp": "2026-08-22T02:20:30.400Z",
  "action": "RESUME_FROM_CHECKPOINT",
  "resumed_checkpoint_id": "chk-m05-q7r8s9t0",
  "node": "finalize_repatriation",
  "final_state": {
    "mission_id": "MEDEVAC-MISSION-2026-COMPLETE",
    "evacuation_status": "PATIENT_EN_ROUTE_TO_ICU",
    "flight_cleared": true,
    "__status__": "COMPLETED"
  },
  "final_checkpoint_id": "chk-m06-u1v2w3x4"
}
```
