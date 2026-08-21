"""
Wanderpath Travel Agency - Failure Ticket Interceptor & Recovery Engine
========================================================================
Captures unplanned mid-node runtime crashes (tool errors, network drops, schema bugs),
records structured tickets with state snapshots, and enables mid-node resumption
after administrator inspection or state patching.
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

logger = logging.getLogger("TicketEngine")


@dataclass
class FailureTicketRecord:
    ticket_id: str
    thread_id: str
    graph_name: str
    failed_node: str
    status: str  # 'OPEN' | 'INVESTIGATING' | 'RESOLVED' | 'ABORTED'
    error_message: str
    error_traceback: Optional[str]
    checkpoint_id: Optional[str]
    state_data: Dict[str, Any]
    resolution_notes: Optional[str]
    resolved_at: Optional[str]
    created_at: str


class TicketEngine:
    """
    Manages unplanned runtime failure tickets, state inspection, and mid-node recovery.
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
                CREATE TABLE IF NOT EXISTS failure_tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id VARCHAR UNIQUE NOT NULL,
                    thread_id VARCHAR NOT NULL,
                    graph_name VARCHAR NOT NULL,
                    failed_node VARCHAR NOT NULL,
                    status VARCHAR NOT NULL DEFAULT 'OPEN',
                    error_message TEXT NOT NULL,
                    error_traceback TEXT,
                    checkpoint_id VARCHAR,
                    state_data TEXT,
                    resolution_notes TEXT,
                    resolved_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CHECK (status IN ('OPEN', 'INVESTIGATING', 'RESOLVED', 'ABORTED'))
                );
            """)
            conn.commit()
        finally:
            conn.close()

    def list_tickets(self, status: Optional[str] = None) -> List[FailureTicketRecord]:
        """Lists failure tickets, optionally filtered by status ('OPEN', 'INVESTIGATING', 'RESOLVED')."""
        records = []
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            if status:
                cursor = conn.execute("SELECT * FROM failure_tickets WHERE status = ? ORDER BY id DESC", (status,))
            else:
                cursor = conn.execute("SELECT * FROM failure_tickets ORDER BY id DESC")

            for row in cursor.fetchall():
                records.append(
                    FailureTicketRecord(
                        ticket_id=row["ticket_id"],
                        thread_id=row["thread_id"],
                        graph_name=row["graph_name"],
                        failed_node=row["failed_node"],
                        status=row["status"],
                        error_message=row["error_message"],
                        error_traceback=row["error_traceback"],
                        checkpoint_id=row["checkpoint_id"],
                        state_data=json.loads(row["state_data"]) if row["state_data"] else {},
                        resolution_notes=row["resolution_notes"],
                        resolved_at=row["resolved_at"],
                        created_at=row["created_at"],
                    )
                )
        finally:
            conn.close()
        return records

    def get_ticket(self, ticket_id: str) -> Optional[FailureTicketRecord]:
        """Fetches a specific failure ticket by ticket_id."""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute("SELECT * FROM failure_tickets WHERE ticket_id = ?", (ticket_id,))
            row = cursor.fetchone()
            if row:
                return FailureTicketRecord(
                    ticket_id=row["ticket_id"],
                    thread_id=row["thread_id"],
                    graph_name=row["graph_name"],
                    failed_node=row["failed_node"],
                    status=row["status"],
                    error_message=row["error_message"],
                    error_traceback=row["error_traceback"],
                    checkpoint_id=row["checkpoint_id"],
                    state_data=json.loads(row["state_data"]) if row["state_data"] else {},
                    resolution_notes=row["resolution_notes"],
                    resolved_at=row["resolved_at"],
                    created_at=row["created_at"],
                )
        finally:
            conn.close()
        return None

    def create_ticket(
        self,
        thread_id: str,
        graph_name: str,
        failed_node: str,
        error_message: str,
        error_traceback: Optional[str] = None,
        checkpoint_id: Optional[str] = None,
        state_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Registers a new open Failure Ticket in SQLite."""
        ticket_id = f"ticket-{uuid.uuid4().hex[:8]}"
        created_at = datetime.utcnow().isoformat()

        conn = sqlite3.connect(self.db_path, timeout=10.0)
        try:
            conn.execute(
                """
                INSERT INTO failure_tickets (
                    ticket_id, thread_id, graph_name, failed_node,
                    status, error_message, error_traceback, checkpoint_id, state_data, created_at
                ) VALUES (?, ?, ?, ?, 'OPEN', ?, ?, ?, ?, ?)
                """,
                (
                    ticket_id,
                    thread_id,
                    graph_name,
                    failed_node,
                    error_message,
                    error_traceback,
                    checkpoint_id,
                    json.dumps(state_data or {}, default=str),
                    created_at,
                ),
            )
            conn.commit()
        finally:
            conn.close()

        logger.info(f"[TicketEngine] 💥 Created Failure Ticket '{ticket_id}' for thread '{thread_id}' ({failed_node})")
        return ticket_id

    def update_status(self, ticket_id: str, status: str, notes: Optional[str] = None) -> bool:
        """Updates ticket lifecycle status ('INVESTIGATING', 'RESOLVED', 'ABORTED')."""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        try:
            conn.execute(
                "UPDATE failure_tickets SET status = ?, resolution_notes = ? WHERE ticket_id = ?",
                (status, notes, ticket_id),
            )
            conn.commit()
            return True
        finally:
            conn.close()

    def resolve_and_resume_ticket(
        self,
        ticket_id: str,
        state_patch: Optional[Dict[str, Any]] = None,
        resolution_notes: str = "",
        graph: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Resolves a failure ticket by applying a state patch, marking status as RESOLVED,
        and resuming the state graph from the exact failure checkpoint without re-running prior nodes.
        """
        ticket = self.get_ticket(ticket_id)
        if not ticket:
            raise ValueError(f"Failure Ticket '{ticket_id}' not found.")

        if ticket.status == "RESOLVED":
            raise ValueError(f"Failure Ticket '{ticket_id}' is already RESOLVED.")

        resolved_at = datetime.utcnow().isoformat()

        # 1. Update ticket in database
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        try:
            conn.execute(
                """
                UPDATE failure_tickets
                SET status = 'RESOLVED', resolution_notes = ?, resolved_at = ?
                WHERE ticket_id = ?
                """,
                (resolution_notes or "Resolved via administrator state patch and retry.", resolved_at, ticket_id),
            )
            conn.commit()
        finally:
            conn.close()

        logger.info(f"[TicketEngine] 🛠️ Resolved Failure Ticket '{ticket_id}'.")

        # 2. If graph instance provided, resume from checkpoint with patched state
        if graph is not None:
            resume_payload = {
                "ticket_resolved_id": ticket_id,
                "resolution_notes": resolution_notes,
            }
            if state_patch:
                resume_payload.update(state_patch)

            # Update checkpoint state with patch before resuming
            if state_patch:
                patched_state = ticket.state_data.copy()
                patched_state.update(state_patch)
                patched_state["__status__"] = "RUNNING"
                patched_state.pop("__error__", None)
                
                # Write patched state as fresh checkpoint
                graph.checkpointer.save_checkpoint(
                    thread_id=ticket.thread_id,
                    graph_name=ticket.graph_name,
                    current_node=ticket.failed_node,
                    state_data=patched_state,
                    step_number=patched_state.get("__step__", 1),
                    parent_checkpoint_id=ticket.checkpoint_id,
                )

            logger.info(f"[TicketEngine] 🚀 Resuming StateGraph thread '{ticket.thread_id}' from failure point '{ticket.failed_node}'...")
            return graph.run_sync(ticket.thread_id, resume_payload=resume_payload)

        return {"ticket_id": ticket_id, "status": "RESOLVED", "resumed": True}
