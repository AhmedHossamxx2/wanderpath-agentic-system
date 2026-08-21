"""
Wanderpath Travel Agency - Durable SQLite State Checkpointer
============================================================
Persists graph execution state to durable SQLite storage after every meaningful
node transition. Enables true crash-and-resume without state loss or node re-execution.
"""

import json
import os
import pathlib
import sqlite3
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class CheckpointRecord:
    checkpoint_id: str
    thread_id: str
    graph_name: str
    current_node: str
    state_data: Dict[str, Any]
    step_number: int
    parent_checkpoint_id: Optional[str]
    created_at: str


class DurableCheckpointer:
    """
    SQLite-backed durable state checkpointer.
    Writes full state snapshots to disk after every node execution.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            project_root = pathlib.Path(__file__).parent.parent.resolve()
            db_dir = project_root / "db"
            os.makedirs(db_dir, exist_ok=True)
            self.db_path = str(db_dir / "wanderpath.sqlite3")
        else:
            self.db_path = db_path
            
        self._ensure_table()

    def _ensure_table(self) -> None:
        """Ensures the state_checkpoints table exists."""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS state_checkpoints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thread_id VARCHAR NOT NULL,
                    checkpoint_id VARCHAR UNIQUE NOT NULL,
                    parent_checkpoint_id VARCHAR,
                    graph_name VARCHAR NOT NULL,
                    current_node VARCHAR NOT NULL,
                    state_data TEXT NOT NULL,
                    step_number INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_thread_id ON state_checkpoints(thread_id);")
            conn.commit()
        finally:
            conn.close()

    def save_checkpoint(
        self,
        thread_id: str,
        graph_name: str,
        current_node: str,
        state_data: Dict[str, Any],
        step_number: int,
        parent_checkpoint_id: Optional[str] = None,
    ) -> str:
        """
        Atomically saves a state checkpoint to durable storage.
        Returns the generated checkpoint_id.
        """
        checkpoint_id = f"chk-{uuid.uuid4().hex[:12]}"
        state_json = json.dumps(state_data, default=str)
        created_at = datetime.utcnow().isoformat()

        conn = sqlite3.connect(self.db_path, timeout=10.0)
        try:
            conn.execute(
                """
                INSERT INTO state_checkpoints (
                    thread_id, checkpoint_id, parent_checkpoint_id,
                    graph_name, current_node, state_data, step_number, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    thread_id,
                    checkpoint_id,
                    parent_checkpoint_id,
                    graph_name,
                    current_node,
                    state_json,
                    step_number,
                    created_at,
                ),
            )
            conn.commit()
        finally:
            conn.close()

        return checkpoint_id

    def load_latest_checkpoint(self, thread_id: str, graph_name: Optional[str] = None) -> Optional[CheckpointRecord]:
        """Loads the most recent checkpoint for a given thread_id and optional graph_name."""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            if graph_name:
                cursor = conn.execute(
                    """
                    SELECT checkpoint_id, thread_id, graph_name, current_node,
                           state_data, step_number, parent_checkpoint_id, created_at
                    FROM state_checkpoints
                    WHERE thread_id = ? AND graph_name = ?
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (thread_id, graph_name),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT checkpoint_id, thread_id, graph_name, current_node,
                           state_data, step_number, parent_checkpoint_id, created_at
                    FROM state_checkpoints
                    WHERE thread_id = ?
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (thread_id,),
                )
            row = cursor.fetchone()
            if row:
                return CheckpointRecord(
                    checkpoint_id=row["checkpoint_id"],
                    thread_id=row["thread_id"],
                    graph_name=row["graph_name"],
                    current_node=row["current_node"],
                    state_data=json.loads(row["state_data"]),
                    step_number=row["step_number"],
                    parent_checkpoint_id=row["parent_checkpoint_id"],
                    created_at=row["created_at"],
                )
        finally:
            conn.close()
        return None

    def list_checkpoints(self, thread_id: str, graph_name: Optional[str] = None) -> List[CheckpointRecord]:
        """Lists all sequential checkpoints saved for a thread_id and optional graph_name."""
        records = []
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            if graph_name:
                cursor = conn.execute(
                    """
                    SELECT checkpoint_id, thread_id, graph_name, current_node,
                           state_data, step_number, parent_checkpoint_id, created_at
                    FROM state_checkpoints
                    WHERE thread_id = ? AND graph_name = ?
                    ORDER BY step_number ASC, id ASC
                    """,
                    (thread_id, graph_name),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT checkpoint_id, thread_id, graph_name, current_node,
                           state_data, step_number, parent_checkpoint_id, created_at
                    FROM state_checkpoints
                    WHERE thread_id = ?
                    ORDER BY step_number ASC, id ASC
                    """,
                    (thread_id,),
                )
            for row in cursor.fetchall():
                records.append(
                    CheckpointRecord(
                        checkpoint_id=row["checkpoint_id"],
                        thread_id=row["thread_id"],
                        graph_name=row["graph_name"],
                        current_node=row["current_node"],
                        state_data=json.loads(row["state_data"]),
                        step_number=row["step_number"],
                        parent_checkpoint_id=row["parent_checkpoint_id"],
                        created_at=row["created_at"],
                    )
                )
        finally:
            conn.close()
        return records

    def delete_checkpoints(self, thread_id: str) -> int:
        """Deletes all checkpoints associated with a thread_id."""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        try:
            cursor = conn.execute("DELETE FROM state_checkpoints WHERE thread_id = ?", (thread_id,))
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()
