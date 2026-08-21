# Wanderpath Travel Agency — Live Demo Transcript
## Scenario 4: Dynamic MCP Tool Mutation & ChromaDB Vector Store CRUD
**Platform UI / REST API**: `wanderpath_platform/backend/app.py`  
**Concerns Verified**: Live MCP Tool Registration/Toggling & Live RAG Policy Document CRUD  

---

### Step 1: Querying Registered MCP Tools via Platform API
```http
GET /api/admin/tools HTTP/1.1
Host: localhost:8500
```

```json
{
  "status": "success",
  "tools": [
    {"name": "check_flight_status", "enabled": true, "is_dynamic": false},
    {"name": "search_flight_alternatives", "enabled": true, "is_dynamic": false},
    {"name": "get_booking_details", "enabled": true, "is_dynamic": false},
    {"name": "cancel_flight_booking", "enabled": true, "is_dynamic": false},
    {"name": "rebook_flight", "enabled": true, "is_dynamic": false},
    {"name": "get_itinerary_details", "enabled": true, "is_dynamic": false},
    {"name": "admin_register_tool", "enabled": true, "is_dynamic": false},
    {"name": "admin_toggle_tool", "enabled": true, "is_dynamic": false},
    {"name": "admin_list_all_tools", "enabled": true, "is_dynamic": false}
  ]
}
```

---

### Step 2: Dynamically Registering a New Tool at Runtime
```http
POST /api/admin/tools/register HTTP/1.1
Host: localhost:8500
Content-Type: application/json

{
  "name": "dispatch_embassy_courier",
  "description": "Dispatches a bonded diplomatic courier for physical biometric passport collection.",
  "input_schema": {
    "type": "object",
    "properties": {
      "dossier_id": {"type": "string"},
      "destination_embassy": {"type": "string"}
    },
    "required": ["dossier_id", "destination_embassy"]
  }
}
```

```json
{
  "status": "success",
  "registered_tool": "dispatch_embassy_courier",
  "notification": "broadcast_tool_list_changed() dispatched to all connected clients"
}
```

---

### Step 3: Toggling Tool Enabled/Disabled Status on the Live Server
```http
POST /api/admin/tools/toggle HTTP/1.1
Host: localhost:8500
Content-Type: application/json

{
  "tool_name": "dispatch_embassy_courier",
  "enabled": false
}
```

```json
{
  "status": "success",
  "tool_name": "dispatch_embassy_courier",
  "enabled": false
}
```

---

### Step 4: Live Ingestion of a New Policy Document into ChromaDB
```http
POST /api/admin/rag/documents HTTP/1.1
Host: localhost:8500
Content-Type: application/json

{
  "doc_id": "policy_morocco_fasttrack",
  "content": "Morocco Consular Fast-Track: Travelers arriving via Casablanca (CMN) with VIP charter clearances are exempt from paper boarding cards if electronic health declaration is submitted 24h prior.",
  "metadata": {"country": "Morocco", "category": "customs_exemptions"}
}
```

```json
{
  "status": "success",
  "added_doc_id": "policy_morocco_fasttrack"
}
```

---

### Step 5: Immediate Agent Retrieval Verification
```http
POST /api/chat HTTP/1.1
Host: localhost:8500
Content-Type: application/json

{
  "agent_id": "memory_rag_agent",
  "message": "What is the policy for VIP charter arrivals in Morocco?"
}
```

```json
{
  "agent_id": "memory_rag_agent",
  "thread_id": "thread-demo-rag-query",
  "status": "COMPLETED",
  "response": "Verified Travel Policy Response:\n\nMorocco Consular Fast-Track: Travelers arriving via Casablanca (CMN) with VIP charter clearances are exempt from paper boarding cards if electronic health declaration is submitted 24h prior.",
  "state": {
    "retrieved_context": "Morocco Consular Fast-Track: Travelers arriving via Casablanca (CMN)..."
  }
}
```
