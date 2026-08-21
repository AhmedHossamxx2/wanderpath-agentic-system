"""
Wanderpath Travel Agency - Human-in-the-Loop (HITL) Dispatcher & Resolution Engine
==================================================================================
Manages planned human approval workflows when agents encounter financial thresholds,
policy ambiguities, or irreversible action checkpoints.
"""

import json
import logging
import os
import pathlib
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("HITLEngine")


@dataclass
class HITLTaskRecord:
    task_id: str
    thread_id: str
    graph_name: str
    node_name: str
    status: str
    reason: str
    threshold_info: Optional[str]
    payload: Dict[str, Any]
    admin_decision: Optional[str]
    admin_notes: Optional[str]
    resolved_at: Optional[str]
    created_at: str


class HITLEngine:
    """
    Manages planned Human-in-the-Loop tasks across all state graphs.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            project_root = pathlib.Path(__file__).parent.parent.parent.resolve()
            db_dir = project_root / "db"
            os.makedirs(db_dir, exist_ok=True)
            self.db_path = str(db_dir / "wanderpath.sqlite3")
        else:
            self.db_path = db_path

        self._ensure_table()

    def _ensure_table(self) -> None:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS hitl_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id VARCHAR UNIQUE NOT NULL,
                    thread_id VARCHAR NOT NULL,
                    graph_name VARCHAR NOT NULL,
                    node_name VARCHAR NOT NULL,
                    status VARCHAR NOT NULL DEFAULT 'PENDING',
                    reason VARCHAR NOT NULL,
                    threshold_info VARCHAR,
                    payload TEXT,
                    admin_decision VARCHAR,
                    admin_notes TEXT,
                    resolved_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED', 'CANCELLED'))
                );
            """)
            conn.commit()
        finally:
            conn.close()

    def list_tasks(self, status: Optional[str] = None) -> List[HITLTaskRecord]:
        """Lists HITL tasks, optionally filtered by status ('PENDING', 'APPROVED', 'REJECTED')."""
        records = []
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            if status:
                cursor = conn.execute("SELECT * FROM hitl_tasks WHERE status = ? ORDER BY id DESC", (status,))
            else:
                cursor = conn.execute("SELECT * FROM hitl_tasks ORDER BY id DESC")
            
            for row in cursor.fetchall():
                records.append(
                    HITLTaskRecord(
                        task_id=row["task_id"],
                        thread_id=row["thread_id"],
                        graph_name=row["graph_name"],
                        node_name=row["node_name"],
                        status=row["status"],
                        reason=row["reason"],
                        threshold_info=row["threshold_info"],
                        payload=json.loads(row["payload"]) if row["payload"] else {},
                        admin_decision=row["admin_decision"],
                        admin_notes=row["admin_notes"],
                        resolved_at=row["resolved_at"],
                        created_at=row["created_at"],
                    )
                )
        finally:
            conn.close()
        return records

    def get_task(self, task_id: str) -> Optional[HITLTaskRecord]:
        """Fetches a specific HITL task by task_id."""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute("SELECT * FROM hitl_tasks WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()
            if row:
                return HITLTaskRecord(
                    task_id=row["task_id"],
                    thread_id=row["thread_id"],
                    graph_name=row["graph_name"],
                    node_name=row["node_name"],
                    status=row["status"],
                    reason=row["reason"],
                    threshold_info=row["threshold_info"],
                    payload=json.loads(row["payload"]) if row["payload"] else {},
                    admin_decision=row["admin_decision"],
                    admin_notes=row["admin_notes"],
                    resolved_at=row["resolved_at"],
                    created_at=row["created_at"],
                )
        finally:
            conn.close()
        return None

    def create_task(
        self,
        thread_id: str,
        graph_name: str,
        node_name: str,
        reason: str,
        threshold_info: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Registers a new pending HITL task in SQLite."""
        task_id = f"hitl-{uuid.uuid4().hex[:8]}"
        created_at = datetime.utcnow().isoformat()

        conn = sqlite3.connect(self.db_path, timeout=10.0)
        try:
            conn.execute(
                """
                INSERT INTO hitl_tasks (
                    task_id, thread_id, graph_name, node_name,
                    status, reason, threshold_info, payload, created_at
                ) VALUES (?, ?, ?, ?, 'PENDING', ?, ?, ?, ?)
                """,
                (
                    task_id,
                    thread_id,
                    graph_name,
                    node_name,
                    reason,
                    threshold_info,
                    json.dumps(payload or {}, default=str),
                    created_at,
                ),
            )
            conn.commit()
        finally:
            conn.close()

        logger.info(f"[HITLEngine] 📋 Created HITL Task '{task_id}' for thread '{thread_id}' ({node_name})")
        return task_id

    def resolve_task(
        self,
        task_id: str,
        admin_decision: str,
        admin_notes: str = "",
        graph: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Resolves a pending HITL task with the admin's decision ('APPROVED' or 'REJECTED')
        and automatically resumes the underlying state graph.
        """
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"HITL Task '{task_id}' not found.")

        if task.status != "PENDING":
            raise ValueError(f"HITL Task '{task_id}' is already {task.status}.")

        decision_clean = admin_decision.strip().upper()
        if decision_clean not in ["APPROVED", "REJECTED"]:
            raise ValueError("admin_decision must be 'APPROVED' or 'REJECTED'")

        resolved_at = datetime.utcnow().isoformat()

        # 1. Update task in database
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        try:
            conn.execute(
                """
                UPDATE hitl_tasks
                SET status = ?, admin_decision = ?, admin_notes = ?, resolved_at = ?
                WHERE task_id = ?
                """,
                (decision_clean, decision_clean, admin_notes, resolved_at, task_id),
            )
            conn.commit()
        finally:
            conn.close()

        logger.info(f"[HITLEngine] ✅ Resolved HITL Task '{task_id}' -> Decision: {decision_clean}")

        # 2. Resume graph if instance provided
        if graph is not None:
            resume_payload = {
                "admin_approval": decision_clean,
                "admin_notes": admin_notes,
                "hitl_resolved_task_id": task_id,
            }
            logger.info(f"[HITLEngine] 🚀 Resuming StateGraph thread '{task.thread_id}' with admin decision...")
            return graph.run_sync(task.thread_id, resume_payload=resume_payload)

        return {"task_id": task_id, "status": decision_clean, "resolved": True}
