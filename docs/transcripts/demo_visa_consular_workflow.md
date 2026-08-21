# Wanderpath Travel Agency — Live Demo Transcript
## Scenario 1: Complex International Visa & Consular Application
**Graph**: `visa_processing_graph.py` | **Architecture**: Cyclic State Graph with SQLite Durable Checkpoints  
**Embedded LLM Additions**: 1. Task Decomposition • 2. RAG Policy Store Retrieval  
**Asynchronous Wait State**: `awaiting_consular_webhook` | **HITL Gate**: Expedited Fee > $500.00  

---

### Step 1: User Request Intake & Initialization
```json
{
  "timestamp": "2026-08-22T02:10:01.120Z",
  "event": "CHAT_REQUEST_RECEIVED",
  "agent_id": "visa_agent",
  "thread_id": "thread-demo-visa-001",
  "user_message": "Client Liam Neeson requires emergency Schengen expedited visa for France departing in 4 days."
}
```

```json
{
  "timestamp": "2026-08-22T02:10:01.340Z",
  "node": "intake_visa_request",
  "state_transition": {
    "client_id": 1,
    "destination": "France",
    "visa_type": "schengen",
    "application_status": "INTAKE_COMPLETED"
  },
  "checkpoint_id": "chk-v01-a1b2c3d4"
}
```

---

### Step 2: LLM Addition 1 — Task Decomposition
```json
{
  "timestamp": "2026-08-22T02:10:01.550Z",
  "node": "decompose_consular_roadmap",
  "action": "LLM_TASK_DECOMPOSITION",
  "decomposed_milestones": [
    "1. Validate passport validity (> 3 months beyond departure) and biometric photos",
    "2. Query embassy consular policy store for France Schengen expedited protocols",
    "3. Compile certified financial sponsorship and hotel accommodation dossier",
    "4. Submit electronic dossier to French consular digital portal",
    "5. Await consular webhook for biometrics appointment slot confirmation",
    "6. Process expedited consular fees and verify digital visa issuance"
  ],
  "checkpoint_id": "chk-v02-e5f6g7h8"
}
```

---

### Step 3: LLM Addition 2 — RAG Policy Store Retrieval
```json
{
  "timestamp": "2026-08-22T02:10:01.810Z",
  "node": "retrieve_embassy_policy",
  "action": "VECTOR_SIMILARITY_SEARCH",
  "collection": "consular_knowledge_db",
  "query": "France schengen embassy requirements",
  "retrieved_document": "Schengen Visa Policy: Requires 3 months passport validity beyond departure date, proof of accommodation, and biometrics. Expedited emergency processing fee is $650.",
  "extracted_parameters": {
    "expedited_fee": 650.00,
    "biometrics_required": true
  },
  "checkpoint_id": "chk-v03-i9j0k1l2"
}
```

---

### Step 4: Submission to Consular Portal & Asynchronous Webhook Wait State
```json
{
  "timestamp": "2026-08-22T02:10:02.100Z",
  "node": "submit_to_consulate",
  "consular_reference": "CONS-FRA-2026-991",
  "submitted_at": "2026-08-22T02:10:02Z"
}
```

```json
{
  "timestamp": "2026-08-22T02:10:02.350Z",
  "node": "awaiting_consular_webhook",
  "status": "INTERRUPTED",
  "interrupt_type": "AWAITING_EXTERNAL",
  "reason": "Awaiting asynchronous embassy status webhook or biometrics slot confirmation",
  "persisted_to_sqlite": true,
  "checkpoint_id": "chk-v04-m3n4o5p6"
}
```

---

### Step 5: External Consular Webhook Arrives & Triggers HITL Gate
```json
{
  "timestamp": "2026-08-22T02:10:15.000Z",
  "event": "WEBHOOK_DELIVERED",
  "payload": {
    "consular_reference": "CONS-FRA-2026-991",
    "decision": "APPROVED",
    "fee": 650.00,
    "notes": "Emergency consular fast-track slot allocated."
  }
}
```

```json
{
  "timestamp": "2026-08-22T02:10:15.220Z",
  "node": "evaluate_consular_response",
  "status": "INTERRUPTED",
  "interrupt_type": "HITL",
  "reason": "Expedited consular fee of $650.00 exceeds standard agency authorization threshold ($500.00)",
  "threshold_info": "Fee: $650.00 > $500.00 limit",
  "hitl_task_id": "hitl-9ae6b48e",
  "persisted_table": "hitl_tasks",
  "checkpoint_id": "chk-v05-q7r8s9t0"
}
```

---

### Step 6: Platform UI Admin Approval & Resumption
```json
{
  "timestamp": "2026-08-22T02:10:25.450Z",
  "platform_endpoint": "POST /api/admin/hitl/tasks/hitl-9ae6b48e/resolve",
  "admin_decision": "APPROVED",
  "admin_notes": "VIP Client Liam Neeson emergency expedited fee approved per policy Section 4B.",
  "hitl_task_status": "APPROVED"
}
```

```json
{
  "timestamp": "2026-08-22T02:10:25.700Z",
  "action": "RESUME_FROM_CHECKPOINT",
  "resumed_checkpoint_id": "chk-v05-q7r8s9t0",
  "node": "finalize_visa",
  "final_state": {
    "visa_number": "VISA-JP-2026-OK-1",
    "application_status": "COMPLETED_ISSUED",
    "fee_paid": 650.00,
    "__status__": "COMPLETED"
  },
  "final_checkpoint_id": "chk-v06-u1v2w3x4"
}
```
