# Wanderpath Travel Agency — Live Demo Transcript
## Scenario 2: Supplier Contract Dispute & Chargeback Reconciliation
**Graph**: `supplier_dispute_graph.py` | **Architecture**: Cyclic State Graph with SQLite Durable Checkpoints  
**Embedded LLM Additions**: 1. Tree of Thoughts (ToT) Legal Strategy Scoring • 2. Constrained ReAct Tool Execution  
**Asynchronous Wait State**: `awaiting_carrier_adjudication` (7-Day Window) | **HITL Gate**: Carrier Waiver > $300.00  

---

### Step 1: User Dispute Claim Intake
```json
{
  "timestamp": "2026-08-22T02:15:01.050Z",
  "event": "CHAT_REQUEST_RECEIVED",
  "agent_id": "dispute_agent",
  "thread_id": "thread-demo-disp-002",
  "user_message": "PacificFly cancelled flight WP-202 due to an unannounced crew strike with 8 hours notice. Demanding statutory compensation and full refund."
}
```

```json
{
  "timestamp": "2026-08-22T02:15:01.250Z",
  "node": "intake_dispute_claim",
  "state_transition": {
    "booking_id": 3,
    "carrier": "PacificFly",
    "amount_disputed": 450.00,
    "dispute_reason": "Carrier cancelled flight WP-202 due to crew strike < 24h notice.",
    "claim_status": "INTAKE_LOGGED"
  },
  "checkpoint_id": "chk-d01-a1b2c3d4"
}
```

---

### Step 2: LLM Addition 1 — Tree of Thoughts (ToT) Strategy Selection
```json
{
  "timestamp": "2026-08-22T02:15:01.500Z",
  "node": "evaluate_appeal_strategies",
  "action": "TREE_OF_THOUGHTS_EVALUATION",
  "thought_branches_evaluated": [
    {
      "branch_id": "T1",
      "strategy": "EU261_STATUTORY_CLAIM",
      "legal_basis": "Involuntary cancellation under 14 days without extraordinary circumstances; demanding full refund + €400 statutory penalty.",
      "estimated_recovery": 850.00,
      "confidence_score": 0.92
    },
    {
      "branch_id": "T2",
      "strategy": "CONTRACT_BREACH_FORCE_MAJEURE",
      "legal_basis": "Airline internal labor strike does not constitute third-party force majeure per IATA Regulation 204.",
      "estimated_recovery": 450.00,
      "confidence_score": 0.85
    },
    {
      "branch_id": "T3",
      "strategy": "COMMERCIAL_GOODWILL_ESCALATION",
      "legal_basis": "Key agency partner tier escalation requesting commercial fee waiver.",
      "estimated_recovery": 337.50,
      "confidence_score": 0.60
    }
  ],
  "selected_branch": "T1 (EU261_STATUTORY_CLAIM)",
  "checkpoint_id": "chk-d02-e5f6g7h8"
}
```

---

### Step 3: LLM Addition 2 — Constrained ReAct (GDS Filing Tool)
```json
{
  "timestamp": "2026-08-22T02:15:01.800Z",
  "node": "execute_gds_filing",
  "action": "CONSTRAINED_REACT_TOOL_CALL",
  "tool_called": "gds_file_chargeback",
  "tool_payload": {
    "booking_id": 3,
    "claim_type": "EU261_STATUTORY_CLAIM",
    "legal_basis": "Involuntary cancellation under 14 days without extraordinary circumstances...",
    "requested_settlement": 850.00
  },
  "tool_observation": "GDS Case #3-DISP successfully submitted to carrier adjudication clearinghouse.",
  "gds_filing_ref": "GDS-DISP-3",
  "checkpoint_id": "chk-d03-i9j0k1l2"
}
```

---

### Step 4: Asynchronous Carrier Adjudication Wait State
```json
{
  "timestamp": "2026-08-22T02:15:02.050Z",
  "node": "awaiting_carrier_adjudication",
  "status": "INTERRUPTED",
  "interrupt_type": "AWAITING_EXTERNAL",
  "reason": "Awaiting airline dispute settlement response or clearinghouse rebuttal (7-day window)",
  "checkpoint_id": "chk-d04-m3n4o5p6"
}
```

---

### Step 5: Carrier Settlement Arrives & Triggers Fee Waiver HITL Gate
```json
{
  "timestamp": "2026-08-22T02:15:20.000Z",
  "event": "SETTLEMENT_OFFER_RECEIVED",
  "payload": {
    "decision": "OFFER_PARTIAL",
    "amount": 200.00,
    "fee_waiver": 350.00,
    "notes": "Carrier agrees to credit $200.00 but demands Wanderpath absorb $350.00 booking fee waiver."
  }
}
```

```json
{
  "timestamp": "2026-08-22T02:15:20.250Z",
  "node": "evaluate_settlement_offer",
  "status": "INTERRUPTED",
  "interrupt_type": "HITL",
  "reason": "Carrier settlement requires absorbing a fee waiver of $350.00 (Threshold > $300.00)",
  "threshold_info": "Fee Waiver: $350.00 > $300.00 limit",
  "hitl_task_id": "hitl-disp-441",
  "persisted_table": "hitl_tasks",
  "checkpoint_id": "chk-d05-q7r8s9t0"
}
```

---

### Step 6: Platform UI Admin Approval & Ledger Finalization
```json
{
  "timestamp": "2026-08-22T02:15:35.100Z",
  "platform_endpoint": "POST /api/admin/hitl/tasks/hitl-disp-441/resolve",
  "admin_decision": "APPROVED",
  "admin_notes": "Commercial dispute settlement accepted to maintain PacificFly partner tier."
}
```

```json
{
  "timestamp": "2026-08-22T02:15:35.350Z",
  "action": "RESUME_FROM_CHECKPOINT",
  "resumed_checkpoint_id": "chk-d05-q7r8s9t0",
  "node": "finalize_dispute",
  "final_state": {
    "booking_id": 3,
    "refund_credited": 200.00,
    "ledger_adjusted": true,
    "claim_status": "SETTLED_COMPLETED",
    "__status__": "COMPLETED"
  },
  "final_checkpoint_id": "chk-d06-u1v2w3x4"
}
```
