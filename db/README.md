# Database Architecture (`db/`)

## Overview
The `db/` directory contains the normalized relational database schemas, seed data, and ERD architectural definitions for **Wanderpath Travel B.** The database enforces strict ANSI-SQL data integrity constraints, Role-Based Access Control (RBAC) linking, sensitive PII isolation, and state graph persistence tables for durable checkpoints, Human-in-the-Loop (HITL) tasks, and runtime failure tickets.

---

## File Manifest
* `schema.sql`: ANSI-SQL creation script establishing all tables, primary keys, foreign keys, polymorphic integrity checks, checkpoint tables, HITL escalation tables, and failure recovery ticket tables.
* `seed.sql`: Seed data script populating normal operational records and targeted edge cases (non-refundable flight bookings, expired passports, pending cancellations, pending HITL tasks, and open failure tickets).
* `schema.dbml`: DBML source file used to generate visual Entity-Relationship Diagrams (ERDs).

---

## Relational Entity Structure

```
[clients] ──┬──< [passports] (PII Isolation)
            └──< [itineraries] >── [agents] (RBAC Assigned)
                     │
                     ├──< [bookings] ──┬──> [flights]
                     │                 └──> [hotels]
                     └──< [payments]

[state_checkpoints] (Durable crash-and-resume state serialized per node)
[hitl_tasks]        (Expected admin escalation queues: approvals/rejections)
[failure_tickets]   (Unplanned runtime failure tickets: stack traces & state patches)
```

### Table Specifications
1. `clients`: Root customer profile information (`id`, `first_name`, `last_name`, `email`, `phone`).
2. `passports`: Sensitive customer identification records (`passport_number`, `country_code`, `expiration_date`). Isolated from `clients` to prevent accidental PII exposure during routine queries.
3. `agents`: Role-based system users (`role`: `'junior_agent'` | `'senior_manager'`).
4. `itineraries`: Aggregates multi-segment travel plans under an assigned agent (`assigned_agent_id`).
5. `flights` & `hotels`: Read-only catalog inventory.
6. `bookings`: Polymorphic active reservation table linked to itineraries. Enforces refundability status (`is_refundable`) and cancellation fees.
7. `payments`: Tracks completed, pending, and refunded transactions.
8. `state_checkpoints`: Durable state persistence records (`thread_id`, `checkpoint_id`, `parent_checkpoint_id`, `graph_name`, `current_node`, `state_data`, `step_number`).
9. `hitl_tasks`: Queued Human-in-the-Loop escalation records (`task_id`, `thread_id`, `graph_name`, `node_name`, `status`, `reason`, `threshold_info`, `payload`, `admin_decision`).
10. `failure_tickets`: Unplanned runtime failure recovery tickets (`ticket_id`, `thread_id`, `graph_name`, `failed_node`, `status`, `error_message`, `error_traceback`, `checkpoint_id`, `state_data`).

---

## Key Safety & Design Decisions
* **PII Data Isolation**: Passport numbers and expiration dates are stored in a dedicated `passports` table rather than directly in `clients`. General itinerary retrieval tools query `clients` and `itineraries`, preventing PII from leaking into the LLM context window unless international entry validation is explicitly invoked.
* **Polymorphic Integrity Constraint**: The `bookings` table enforces a database-level `CHECK` constraint:
  ```sql
  CHECK (
      (booking_type = 'flight' AND flight_id IS NOT NULL AND hotel_id IS NULL) OR 
      (booking_type = 'hotel' AND hotel_id IS NOT NULL AND flight_id IS NULL)
  )
  ```
* **State Graph Durability & Crash Recovery**: `state_checkpoints` enables restarting interrupted workflows after process failure without re-executing already completed nodes.
* **Separation of Concerns for Interventions**: Expected approval workflows use `hitl_tasks`, whereas unexpected software/API failures create `failure_tickets`.

---

## Verification
Run the database and MCP test suite:
```bash
python agent/test_dynamic_mcp_rag.py
```