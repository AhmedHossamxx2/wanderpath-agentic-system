# Human-in-the-Loop & Failure Ticket Recovery Subsystem (`state_graph/recovery/`)

## Overview
The `state_graph/recovery/` module enforces a strict architectural separation between **Planned Human-in-the-Loop (HITL) Escalations** and **Unplanned Failure Ticket Recovery**. Both paths leverage durable checkpoints to pause and resume execution without starting from the beginning, but they serve completely distinct operational concerns.

---

## Architectural Comparison: HITL vs. Failure Tickets

| Concern | Human-in-the-Loop (HITL) | Failure Ticket System |
|---|---|---|
| **Nature** | Planned, expected business decision gate. | Unplanned runtime crash / exception. |
| **Trigger Examples** | Fee > \$500, fee waiver > \$300, irreversible air charter dispatch > \$5,000. | External API 502 error, network timeout, schema validation bug, unparseable LLM output. |
| **Mechanism** | Node raises `InterruptSignal` gracefully. | Node execution interceptor catches unhandled `Exception`. |
| **Database Table** | `hitl_tasks` (`PENDING`, `APPROVED`, `REJECTED`). | `failure_tickets` (`OPEN`, `INVESTIGATING`, `RESOLVED`, `ABORTED`). |
| **Admin Action in Platform** | Reviews context snapshot and clicks **Approve** or **Reject**. | Inspects stack trace, applies state patch (e.g. backup gateway), clicks **Resolve & Resume**. |
| **Resumption Behavior** | Graph advances with admin decision payload (`APPROVED`/`REJECTED`). | Graph retries the failed node using the patched state and proceeds. |

---

## File Manifest
* `hitl_engine.py`: Implements `HITLEngine` for creating, querying, and resolving `hitl_tasks` and resuming paused graph threads.
* `ticket_engine.py`: Implements `TicketEngine` for logging stack traces into `failure_tickets`, updating ticket status, patching state, and triggering mid-node resumption.
* `../tests/test_hitl_and_tickets.py`: Automated test suite proving that both paths operate independently, update SQLite records correctly, and resume execution without loss of prior node state.

---

## Data Schemas

### 1. `hitl_tasks`
```sql
CREATE TABLE hitl_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id VARCHAR UNIQUE NOT NULL,
    thread_id VARCHAR NOT NULL,
    graph_name VARCHAR NOT NULL,
    node_name VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'PENDING',
    reason VARCHAR NOT NULL,
    threshold_info VARCHAR,
    payload TEXT, -- JSON contextual snapshot
    admin_decision VARCHAR, -- 'APPROVED' | 'REJECTED'
    admin_notes TEXT,
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2. `failure_tickets`
```sql
CREATE TABLE failure_tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id VARCHAR UNIQUE NOT NULL,
    thread_id VARCHAR NOT NULL,
    graph_name VARCHAR NOT NULL,
    failed_node VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'OPEN', -- 'OPEN' | 'INVESTIGATING' | 'RESOLVED' | 'ABORTED'
    error_message TEXT NOT NULL,
    error_traceback TEXT,
    checkpoint_id VARCHAR,
    state_data TEXT, -- JSON state snapshot at crash
    resolution_notes TEXT,
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Verification
Run the recovery verification test suite:
```bash
mcp_server\.venv\Scripts\python.exe state_graph\tests\test_hitl_and_tickets.py
```
