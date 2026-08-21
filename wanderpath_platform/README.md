# Wanderpath Full-Stack Platform (`wanderpath_platform/`)

## Overview
The `wanderpath_platform/` package provides the unified, full-stack web application and REST backend connecting all five Wanderpath agents (the 3 state-graph agents, the trip disruption planning agent, and the memory & hybrid RAG agent) to a live Model Context Protocol (MCP) server, SQLite durable checkpointer, ChromaDB vector store, Human-in-the-Loop (HITL) resolution engine, and Failure Ticket recovery center.

---

## System Architecture

```mermaid
graph TD
    User([End User / Travel Agent]) <-->|Browser UI: Port 8500| Platform[Wanderpath Platform: Starlette ASGI]
    Admin([Operations Admin / Medical Director]) <-->|Admin Control Center| Platform
    
    subgraph "Backend API Layer (wanderpath_platform/backend/app.py)"
        Platform --> ChatRouter["Multi-Agent Router (/api/chat)"]
        Platform --> MCPAdmin["MCP Tool Dynamic Registry (/api/admin/tools)"]
        Platform --> RAGAdmin["RAG Knowledge Base CRUD (/api/admin/rag)"]
        Platform --> HITLAdmin["HITL Task Resolution (/api/admin/hitl)"]
        Platform --> TicketAdmin["Failure Ticket Recovery (/api/admin/tickets)"]
    end
    
    subgraph "Core Agent & State Subsystems"
        ChatRouter --> VisaGraph["Visa Processing Graph (Decomp + RAG)"]
        ChatRouter --> DisputeGraph["Dispute Reconciliation Graph (ToT + ReAct)"]
        ChatRouter --> MedevacGraph["VIP Medevac Graph (LATS + ReAct)"]
        ChatRouter --> PlanningAgent["Trip Disruption Planner (DAG)"]
        ChatRouter --> MemoryAgent["Memory & Hybrid RAG Agent"]
        
        MCPAdmin -->|Runtime Mutate| MCPServer["MCP Server (Streamable HTTP: Port 8000)"]
        RAGAdmin -->|Live Sync| ChromaDB["ChromaDB Vector Store"]
        HITLAdmin -->|Resume Run| Checkpointer["Durable SQLite Checkpointer"]
        TicketAdmin -->|State Patch & Resume| Checkpointer
    end
```

---

## File Manifest
* `backend/app.py`: Starlette ASGI backend providing REST endpoints for chat routing, live MCP tool toggles, RAG document management, HITL resolution, and Failure Ticket recovery.
* `frontend/index.html`: Responsive single-page web app built with TailwindCSS and Lucide icons containing:
  - **User Chat Portal**: Sidebar agent switcher across all 5 agents, thread sessions, preset quick-prompts, and live execution status badges.
  - **Admin Operations Center**:
    - *Tab 1 (MCP Tools)*: Real-time toggles enabling/disabling tools on the running server and dynamic tool registration.
    - *Tab 2 (RAG Knowledge)*: Document browser, upload form, and deletion actions syncing with ChromaDB.
    - *Tab 3 (HITL Tasks)*: Pending task queue with contextual state inspection and 1-click Approve / Reject buttons that resume state graphs.
    - *Tab 4 (Failure Tickets)*: Open tickets with stack traces, JSON state patch editor, and "Resolve & Resume Run" action.
    - *Tab 5 (State Checkpoints)*: Live SQLite state checkpoint history.
* `tests/test_platform_e2e.py`: Automated end-to-end integration test validating all API endpoints.

---

## Launching the Platform

### 1. Start the Platform Web Server
```powershell
mcp_server\.venv\Scripts\python.exe -m uvicorn wanderpath_platform.backend.app:app --host 0.0.0.0 --port 8500
```
Open your browser to: **`http://localhost:8500`**

### 2. Run Automated Platform End-to-End Tests
```powershell
mcp_server\.venv\Scripts\python.exe wanderpath_platform\tests\test_platform_e2e.py
```
