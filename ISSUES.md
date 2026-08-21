# Wanderpath Final Project — GitHub Issues & Modular Work Tracker

This document tracks all modular engineering issues, rationales, operational constraints, acceptance criteria, and resolution traceability for the Wanderpath Final Project.

---

## Issue #58: `feat(mcp-db-rag): runtime dynamic tool management, schema migrations, and live vector CRUD`
- **Owner**: Ahmed Hossam (`ahmedhossam7800@gmail.com`)
- **Status**: RESOLVED (Closed via Sub-Module 1 implementation)
- **Problem Statement**:
  Currently, the MCP server (`mcp_server/server.py`) defines tools statically in code, and role elevation is limited to a hardcoded toggle. Administrators cannot dynamically register or de-register tools at runtime from a web platform without restarting the process. Furthermore, the RAG vector store (`rag/vector_store.py`) lacks dynamic document addition and deletion endpoints with instant index updates, and the relational database (`db/schema.sql`) lacks schemas for durable checkpoints, HITL tasks, and failure tickets.
- **Operational Constraint**:
  The running MCP server must allow registering and deregistering tools over JSON-RPC or HTTP API and emit `notifications/tools/list_changed` without dropping active agent client sessions. Dynamic document additions and deletions in ChromaDB must immediately alter subsequent retrieval results.
- **Acceptance Criteria**:
  1. `mcp_server/server.py` implements dynamic `register_tool(tool_def, handler)` and `deregister_tool(tool_name)` APIs and broadcasts `list_changed` notifications to connected MCP clients. (PASSED)
  2. `rag/vector_store.py` implements `add_document(doc_id, text, metadata)` and `delete_document(doc_id)` with verified real-time retrieval reflection. (PASSED)
  3. `db/schema.sql` and `db/seed.sql` include tables: `state_checkpoints`, `hitl_tasks`, and `failure_tickets` with relational constraints. (PASSED)
  4. Unit test suite `agent/test_dynamic_mcp_rag.py` passes 100%. (PASSED)
- **Resolution Summary**:
  Added `register_dynamic_tool`, `deregister_dynamic_tool`, and `set_tool_enabled` in `mcp_server/server.py` with REST endpoints (`/api/tools`). Added dynamic CRUD in `rag/vector_store.py`. Added checkpoint, HITL, and failure ticket persistence tables in SQLite schema. Verified 100% via `agent/test_dynamic_mcp_rag.py`.

---

## Issue #59: `feat(state-graph): durable sqlite state checkpointer & crash-recovery engine`
- **Owner**: Ahmed Hossam (`ahmedhossam7800@gmail.com`)
- **Status**: PLANNED
- **Problem Statement**:
  Previous planning agents ran acyclic DAGs in transient memory. If a process dies or encounters a network partition, all intermediate state is lost and the agent must restart from scratch. A production travel management system requires durable state persistence after every meaningful node transition.
- **Operational Constraint**:
  State serialization must support complex Python structures, timestamps, node execution history, and interrupted states. If the Python process is abruptly terminated (`SIGKILL` / `os._exit`), restarting with the same `thread_id` must resume from the exact checkpoint without re-executing completed nodes.
- **Acceptance Criteria**:
  1. `state_graph/checkpointer.py` implements SQLite-backed atomic state persistence and retrieval by `thread_id` and checkpoint timestamp.
  2. `state_graph/base.py` provides cyclic state graph routing, node execution interceptors, and interrupt signaling.
  3. Unit test `state_graph/tests/test_checkpoint_recovery.py` simulates mid-node process termination and verifies idempotent recovery.
  4. `state_graph/README.md` documents the checkpointer architecture and recovery invariants.

---

## Issue #60: `feat(agents): three stateful agent problem graphs with 2 LLM additions per graph`
- **Owner**: Ahmed Hossam (`ahmedhossam7800@gmail.com`)
- **Status**: PLANNED
- **Problem Statement**:
  Wanderpath requires 3 genuinely stateful, long-running problem domains that cannot be executed as a single linear pass:
  1. Complex International Visa & Consular Application (weeks-long, multi-stage, awaiting consular webhooks).
  2. Supplier Contract Dispute & Chargeback Reconciliation (7-day airline windows, branching appeals, awaiting settlement).
  3. VIP Emergency Medical Evacuation & Repatriation (high-stakes air charter coordination, hospital admission waits, physician sign-offs).
- **Operational Constraint**:
  Each graph must embed exactly two distinct LLM-call additions (Task Decomposition, Tree of Thoughts/LATS, Constrained ReAct, RAG) tied directly to node responsibilities, with cyclic transitions and asynchronous wait states.
- **Acceptance Criteria**:
  1. `state_graph/graphs/visa_graph.py` implements Task Decomposition + RAG with `awaiting_embassy_webhook` state.
  2. `state_graph/graphs/dispute_graph.py` implements Tree of Thoughts + Constrained ReAct with `awaiting_carrier_adjudication` state.
  3. `state_graph/graphs/medevac_graph.py` implements LATS + Constrained ReAct with `awaiting_hospital_admission` state.
  4. Each graph has automated execution tests in `state_graph/tests/` verifying graph cycles and LLM addition execution.
  5. `state_graph/graphs/README.md` details the architectural justification for each LLM pairing.

---

## Issue #61: `feat(recovery): platform-routed HITL escalation & failure ticket recovery system`
- **Owner**: Ahmed Hossam (`ahmedhossam7800@gmail.com`)
- **Status**: PLANNED
- **Problem Statement**:
  The system must clearly distinguish between planned Human-in-the-Loop (HITL) pauses (expected business decisions like fees exceeding thresholds or medical authorizations) and unplanned Failure Tickets (tool crashes, schema validation errors, network drops). Both must persist state and resume without restarting from the beginning.
- **Operational Constraint**:
  HITL pauses must not auto-approve or print to console; they must create a durable record and await explicit admin resolution via API/UI. Failure Tickets must capture stack traces and failed node context, allowing admin state inspection, state patching, and resume.
- **Acceptance Criteria**:
  1. `state_graph/recovery/hitl_engine.py` implements pause-on-condition, state persistence, and resume-with-decision.
  2. `state_graph/recovery/ticket_engine.py` intercepts node exceptions, registers `FailureTicket` (`OPEN`), and provides a resume endpoint.
  3. Unit test `state_graph/tests/test_hitl_and_tickets.py` validates the two distinct code paths and verifies no state loss upon resumption.
  4. `state_graph/recovery/README.md` documents HITL trigger conditions and ticket resolution workflows.

---

## Issue #62: `feat(platform): full-stack admin control surface & multi-agent user chat portal`
- **Owner**: Ahmed Hossam (`ahmedhossam7800@gmail.com`)
- **Status**: PLANNED
- **Problem Statement**:
  End users and agency administrators currently have no interface to interact with the agents, manage MCP tools, update knowledge base documents, or resolve HITL tasks and failure tickets.
- **Operational Constraint**:
  The platform must be a real, fully operational full-stack application (FastAPI backend + responsive web frontend). Tool additions/removals in the UI must immediately reach the live MCP server. RAG document additions/deletions must immediately reflect in retrieval.
- **Acceptance Criteria**:
  1. `platform/backend/` provides REST & WebSocket endpoints for agent chat, tool toggling, RAG CRUD, HITL resolution, and ticket resumption.
  2. `platform/frontend/` provides:
     - User Chat with multi-agent switcher (3 stateful agents + Planning Agent + Memory/RAG Agent).
     - Admin MCP Tool Manager with live toggle switches.
     - Admin RAG Document Manager with upload and delete controls.
     - Admin HITL Resolution Center with approval/rejection actions.
     - Admin Failure Ticket Center with stack trace inspection and resume trigger.
  3. End-to-end integration tests verify live platform actions mutating backend agent behavior.
  4. `platform/README.md` provides complete launch instructions.

---

## Issue #63: `test(smoke): master end-to-end verification, demo evidence transcripts & documentation`
- **Owner**: Ahmed Hossam (`ahmedhossam7800@gmail.com`)
- **Status**: PLANNED
- **Problem Statement**:
  Grading requires rigorous proof that the entire system functions seamlessly end-to-end, with reproducible test evidence for crash-and-resume, HITL resolution via UI, failure ticket recovery, and dynamic tool updates.
- **Operational Constraint**:
  All evidence must be executable, reproducible, and verifiable via automated smoke test scripts and recorded transcripts without mock compromises.
- **Acceptance Criteria**:
  1. `agent/smoke_test_final_project.py` executes all final project concerns and asserts 100% pass rate.
  2. `demo_transcript_final.txt` documents live runs of crash recovery, HITL resolution, and ticket recovery.
  3. `README.md` updated with comprehensive documentation, architecture diagrams, benchmark tables, and setup instructions.
