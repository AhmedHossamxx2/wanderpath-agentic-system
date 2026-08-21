# Wanderpath Travel Agency — Live Demo Transcript
## Scenario 5: Unplanned Failure Ticket Intercept, State Patching & Resumption
**Graph**: `supplier_dispute_graph.py` | **Subsystem**: `TicketEngine` & `StateGraph` Checkpointer  
**Incident**: Unplanned External GDS Gateway 502 Bad Gateway / Network Timeout  
**Outcome**: Zero loss of completed state, failure logged with full stack trace, state patched via Admin UI, resumed from exact node without restart  

---

### Step 1: Normal Execution Up to Node 2
```json
{
  "timestamp": "2026-08-22T02:25:01.000Z",
  "thread_id": "thread-demo-crash-005",
  "node": "intake_dispute_claim",
  "status": "COMPLETED",
  "state_data": {
    "booking_id": 99,
    "carrier": "PacificFly",
    "amount_disputed": 450.00,
    "payload_ready": true
  },
  "checkpoint_id": "chk-crash-01"
}
```

```json
{
  "timestamp": "2026-08-22T02:25:01.250Z",
  "thread_id": "thread-demo-crash-005",
  "node": "evaluate_appeal_strategies",
  "status": "COMPLETED",
  "state_data": {
    "selected_strategy": "EU261_STATUTORY_CLAIM",
    "selected_argument": "Involuntary cancellation under 14 days without extraordinary circumstances..."
  },
  "checkpoint_id": "chk-crash-02"
}
```

---

### Step 2: Unhandled Runtime Exception Caught at Node 3
```json
{
  "timestamp": "2026-08-22T02:25:01.500Z",
  "thread_id": "thread-demo-crash-005",
  "node": "execute_gds_filing",
  "event": "UNHANDLED_NODE_EXCEPTION",
  "error_type": "ConnectionError",
  "error_message": "GDS Gateway 502 Bad Gateway: Primary API endpoint https://gds-clearinghouse.wanderpath.internal/v1/dispute unreachable.",
  "action_taken": "StateGraph Interceptor snapshot state and serialized Failure Ticket to SQLite"
}
```

```json
{
  "timestamp": "2026-08-22T02:25:01.550Z",
  "persisted_table": "failure_tickets",
  "ticket_id": "ticket-7ecc9163",
  "thread_id": "thread-demo-crash-005",
  "graph_name": "supplier_dispute_graph",
  "failed_node": "execute_gds_filing",
  "status": "OPEN",
  "error_traceback": "Traceback (most recent call last):\n  File \".../state_graph/base.py\", line 258, in execute\n    updated_state = await self._execute_node_fn(node_fn, state)\n  File \".../state_graph/graphs/dispute_graph.py\", line 88, in execute_gds_filing\n    raise ConnectionError(\"GDS Gateway 502 Bad Gateway: Primary API endpoint unreachable.\")\nConnectionError: GDS Gateway 502 Bad Gateway: Primary API endpoint unreachable.",
  "state_snapshot": {
    "booking_id": 99,
    "carrier": "PacificFly",
    "amount_disputed": 450.00,
    "payload_ready": true,
    "selected_strategy": "EU261_STATUTORY_CLAIM",
    "__current_node__": "execute_gds_filing",
    "__step__": 3,
    "__status__": "FAILED"
  }
}
```

---

### Step 3: Admin Discovers Open Ticket on Platform UI & Sets Investigating
```http
GET /api/admin/tickets?status=OPEN HTTP/1.1
Host: localhost:8500
```

```json
{
  "status": "success",
  "count": 1,
  "tickets": [
    {
      "ticket_id": "ticket-7ecc9163",
      "thread_id": "thread-demo-crash-005",
      "graph_name": "supplier_dispute_graph",
      "failed_node": "execute_gds_filing",
      "status": "OPEN",
      "error_message": "GDS Gateway 502 Bad Gateway: Primary API endpoint unreachable."
    }
  ]
}
```

```http
POST /api/admin/tickets/ticket-7ecc9163/status?status=INVESTIGATING HTTP/1.1
Host: localhost:8500
```

---

### Step 4: Admin Applies State Patch & Resumes from Failure Checkpoint
```http
POST /api/admin/tickets/ticket-7ecc9163/resolve HTTP/1.1
Host: localhost:8500
Content-Type: application/json

{
  "state_patch": {
    "gds_gateway_override": "GDS-BACKUP-01",
    "carrier_settlement": {
      "decision": "OFFER_PARTIAL",
      "amount": 200.00,
      "fee_waiver": 200.00
    }
  },
  "resolution_notes": "Patched to secondary GDS clearinghouse endpoint GDS-BACKUP-01."
}
```

---

### Step 5: Execution Resumes from Step 3 without Re-running Steps 1 & 2
```json
{
  "timestamp": "2026-08-22T02:25:20.100Z",
  "event": "STATE_GRAPH_RESUMED",
  "thread_id": "thread-demo-crash-005",
  "resumed_from_node": "execute_gds_filing",
  "execution_log": [
    "Step 3 -> Re-executing 'execute_gds_filing' with state patch: gds_gateway_override='GDS-BACKUP-01'",
    "Step 3 -> [Ticket Node 2] ✅ Backup GDS Gateway active! Transaction succeeded.",
    "Step 4 -> Executing node: 'awaiting_carrier_adjudication' (Carrier settlement applied)",
    "Step 5 -> Executing node: 'evaluate_settlement_offer' (Settlement authorized)",
    "Step 6 -> Executing node: 'finalize_dispute' (Ledger credited with $200.00)",
    "Step 6 -> 🏁 Graph execution reached END successfully."
  ],
  "final_status": "COMPLETED",
  "ticket_status_in_db": "RESOLVED"
}
```
