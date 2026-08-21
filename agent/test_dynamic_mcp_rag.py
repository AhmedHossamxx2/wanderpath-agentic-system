"""
Wanderpath Travel Agency - Sub-Module 1 Verification Suite
===========================================================
Verifies:
1. MCP Dynamic Tool Registration, Toggling & List Changes
2. Vector Store Dynamic Document Addition, Deletion & Immediate Retrieval
3. Database Schema Integrity for State Checkpoints, HITL Tasks, and Failure Tickets
"""

import asyncio
import json
import os
import pathlib
import sqlite3

# Add project root and mcp_server to sys.path
import sys
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

project_root = pathlib.Path(__file__).parent.parent.resolve()
mcp_server_dir = project_root / "mcp_server"
if str(mcp_server_dir) not in sys.path:
    sys.path.insert(0, str(mcp_server_dir))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from server import (
    register_dynamic_tool,
    deregister_dynamic_tool,
    set_tool_enabled,
    get_all_registered_tools,
    list_tools,
    call_tool,
    CURRENT_ROLE,
)
from rag.vector_store import WanderpathVectorStore


# ============================================================================
# TEST 1: MCP DYNAMIC RUNTIME TOOL MANAGEMENT
# ============================================================================
async def test_mcp_dynamic_tool_registration():
    print("\n--- Testing MCP Dynamic Tool Registration ---")
    
    # 1. Register a new tool dynamically
    custom_schema = {
        "type": "object",
        "properties": {
            "country_code": {"type": "string"},
            "emergency_contact": {"type": "string"}
        },
        "required": ["country_code"],
        "additionalProperties": False
    }
    
    register_dynamic_tool(
        name="dispatch_embassy_liaison",
        description="Dispatch diplomatic liaison for consular emergency.",
        input_schema=custom_schema,
        enabled=True
    )
    
    # Check that tool is returned by list_tools
    active_tools = await list_tools()
    tool_names = [t.name for t in active_tools]
    assert "dispatch_embassy_liaison" in tool_names, "Dynamic tool was not listed in active tools!"
    print("✅ Dynamic tool successfully registered and active in tool list.")

    # 2. Execute the dynamic tool
    result = await call_tool("dispatch_embassy_liaison", {"country_code": "MAR", "emergency_contact": "+2125551234"})
    assert "SUCCESS (DYNAMIC TOOL)" in result[0].text
    print(f"✅ Dynamic tool executed successfully: {result[0].text}")

    # 3. Toggle tool disabled
    set_tool_enabled("dispatch_embassy_liaison", False)
    active_tools_after_disable = await list_tools()
    disabled_tool_names = [t.name for t in active_tools_after_disable]
    assert "dispatch_embassy_liaison" not in disabled_tool_names, "Disabled dynamic tool should not appear in list_tools!"
    
    # Calling disabled tool should return PERMISSION_DENIED
    denied_res = await call_tool("dispatch_embassy_liaison", {"country_code": "MAR"})
    assert "PERMISSION_DENIED" in denied_res[0].text
    print("✅ Tool successfully disabled dynamically and execution properly blocked.")

    # 4. Deregister tool
    dereg_res = deregister_dynamic_tool("dispatch_embassy_liaison")
    assert dereg_res is True
    all_tools = get_all_registered_tools()
    assert not any(t["name"] == "dispatch_embassy_liaison" for t in all_tools)
    print("✅ Tool successfully deregistered from server registry.")


# ============================================================================
# TEST 2: DYNAMIC RAG DOCUMENT ADDITION & DELETION
# ============================================================================
def test_dynamic_rag_crud():
    print("\n--- Testing Dynamic RAG Document Addition & Deletion ---")
    
    test_db_dir = project_root / "rag" / "test_dynamic_rag_db"
    store = WanderpathVectorStore(collection_name="dynamic_rag_test", persist_dir=str(test_db_dir))
    
    # 1. Add dynamic document
    doc_id = "consular_guide_portugal"
    doc_text = "Portugal Emergency Visa: Fast-track processing available at Lisbon consulate for urgent medical repatriations within 24 hours."
    metadata = {"country": "Portugal", "category": "visa_policy"}
    
    store.add_document(doc_id=doc_id, document=doc_text, metadata=metadata)
    
    # 2. Search immediately
    results = store.similarity_search("Lisbon emergency visa medical repatriation", n_results=1)
    assert len(results) > 0, "No search results returned after adding document!"
    assert results[0]["id"] == doc_id, f"Expected {doc_id}, got {results[0]['id']}"
    assert "Portugal Emergency Visa" in results[0]["document"]
    print("✅ Newly added document immediately retrieved in similarity search.")

    # 3. List documents
    docs = store.list_documents()
    assert any(d["id"] == doc_id for d in docs)
    print(f"✅ Document list confirmed {len(docs)} indexed documents.")

    # 4. Delete document
    store.delete_document(doc_id)
    post_delete_docs = store.list_documents()
    assert not any(d["id"] == doc_id for d in post_delete_docs)
    print("✅ Document successfully deleted and purged from vector index.")


# ============================================================================
# TEST 3: DATABASE SCHEMA & SEED INTEGRITY FOR STATE PERSISTENCE
# ============================================================================
def test_database_schema_persistence_tables():
    print("\n--- Testing SQLite Database Persistence Tables ---")
    
    db_file = project_root / "db" / "test_wanderpath.sqlite3"
    if db_file.exists():
        db_file.unlink()

    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()

    # Read and apply schema.sql
    schema_path = project_root / "db" / "schema.sql"
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    cursor.executescript(schema_sql)

    # Read and apply seed.sql
    seed_path = project_root / "db" / "seed.sql"
    with open(seed_path, "r", encoding="utf-8") as f:
        seed_sql = f.read()
    cursor.executescript(seed_sql)

    # 1. Verify state_checkpoints table
    cursor.execute("SELECT COUNT(*) FROM state_checkpoints;")
    chk_count = cursor.fetchone()[0]
    assert chk_count >= 2, f"Expected >= 2 seeded checkpoints, got {chk_count}"
    print(f"✅ state_checkpoints table verified ({chk_count} records).")

    # 2. Verify hitl_tasks table
    cursor.execute("SELECT task_id, status, reason FROM hitl_tasks WHERE status = 'PENDING';")
    hitl_task = cursor.fetchone()
    assert hitl_task is not None
    assert hitl_task[0] == "hitl-task-001"
    print(f"✅ hitl_tasks table verified (Pending task: {hitl_task[0]}).")

    # 3. Verify failure_tickets table
    cursor.execute("SELECT ticket_id, status, error_message FROM failure_tickets WHERE status = 'OPEN';")
    ticket = cursor.fetchone()
    assert ticket is not None
    assert ticket[0] == "ticket-err-001"
    print(f"✅ failure_tickets table verified (Open ticket: {ticket[0]}).")

    conn.close()
    if db_file.exists():
        db_file.unlink()


if __name__ == "__main__":
    print("==================================================================")
    print("🧪 RUNNING SUB-MODULE 1 VERIFICATION TESTS (Issue #58)")
    print("==================================================================")
    
    asyncio.run(test_mcp_dynamic_tool_registration())
    test_dynamic_rag_crud()
    test_database_schema_persistence_tables()
    
    print("\n==================================================================")
    print("🎉 ALL SUB-MODULE 1 VERIFICATION TESTS PASSED 100%!")
    print("==================================================================")
