"""
Wanderpath Travel Agency - Core State Graph Engine
==================================================
Implements cyclic state graphs with durable transitions, conditional routing,
Human-in-the-Loop (HITL) pause interrupts, and automatic failure ticket recording.
"""

import asyncio
import inspect
import json
import logging
import os
import pathlib
import sqlite3
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from state_graph.checkpointer import CheckpointRecord, DurableCheckpointer

logger = logging.getLogger("StateGraph")

# Special End Node identifier
END = "__END__"


@dataclass
class InterruptSignal(Exception):
    """Raised by a node to gracefully pause graph execution for HITL or external events."""
    reason: str
    interrupt_type: str = "HITL"  # 'HITL' | 'AWAITING_EXTERNAL'
    payload: Dict[str, Any] = field(default_factory=dict)
    threshold_info: Optional[str] = None


@dataclass
class NodeResult:
    state: Dict[str, Any]
    next_node: Optional[str] = None
    interrupted: bool = False
    interrupt_reason: Optional[str] = None


class StateGraph:
    """
    Durable cyclic state graph orchestrator.
    Persists state after every node and allows pausing, inspecting, and resuming.
    """

    def __init__(self, name: str, checkpointer: Optional[DurableCheckpointer] = None, db_path: Optional[str] = None):
        self.name = name
        self.nodes: Dict[str, Callable] = {}
        self.edges: Dict[str, str] = {}
        self.conditional_edges: Dict[str, Tuple[Callable, Dict[str, str]]] = {}
        self.entry_point: Optional[str] = None
        self.checkpointer = checkpointer or DurableCheckpointer(db_path=db_path)
        self.db_path = self.checkpointer.db_path

    def add_node(self, name: str, fn: Callable) -> None:
        """Registers a node function with signature `fn(state: dict) -> dict`."""
        self.nodes[name] = fn

    def add_edge(self, from_node: str, to_node: str) -> None:
        """Adds a deterministic edge from one node to another."""
        self.edges[from_node] = to_node

    def add_conditional_edge(
        self,
        from_node: str,
        condition_fn: Callable[[Dict[str, Any]], str],
        path_map: Dict[str, str],
    ) -> None:
        """
        Adds dynamic conditional routing.
        `condition_fn(state)` returns a key present in `path_map`.
        """
        self.conditional_edges[from_node] = (condition_fn, path_map)

    def set_entry_point(self, name: str) -> None:
        """Sets the initial entry node of the state graph."""
        if name not in self.nodes:
            raise ValueError(f"Entry point '{name}' is not registered as a node in the graph.")
        self.entry_point = name

    def _get_next_node(self, current_node: str, state: Dict[str, Any]) -> str:
        """Calculates the next node using direct edges or conditional branches."""
        if current_node in self.conditional_edges:
            condition_fn, path_map = self.conditional_edges[current_node]
            route_key = condition_fn(state)
            if route_key not in path_map:
                raise ValueError(f"Condition function returned unknown route key '{route_key}' for node '{current_node}'")
            return path_map[route_key]
        
        if current_node in self.edges:
            return self.edges[current_node]

        return END

    def _record_failure_ticket(
        self, thread_id: str, failed_node: str, error_msg: str, tb_str: str, state_data: Dict[str, Any], checkpoint_id: Optional[str]
    ) -> str:
        """Records an unexpected failure in the failure_tickets table."""
        ticket_id = f"ticket-{uuid.uuid4().hex[:8]}"
        with sqlite3.connect(self.db_path) as conn:
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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.execute(
                """
                INSERT INTO failure_tickets (
                    ticket_id, thread_id, graph_name, failed_node,
                    status, error_message, error_traceback, checkpoint_id, state_data
                ) VALUES (?, ?, ?, ?, 'OPEN', ?, ?, ?, ?)
                """,
                (
                    ticket_id,
                    thread_id,
                    self.name,
                    failed_node,
                    error_msg,
                    tb_str,
                    checkpoint_id,
                    json.dumps(state_data, default=str),
                ),
            )
            conn.commit()
        return ticket_id

    def _record_hitl_task(
        self, thread_id: str, node_name: str, reason: str, threshold_info: Optional[str], payload: Dict[str, Any]
    ) -> str:
        """Records a planned HITL escalation in the hitl_tasks table."""
        task_id = f"hitl-{uuid.uuid4().hex[:8]}"
        with sqlite3.connect(self.db_path) as conn:
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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.execute(
                """
                INSERT INTO hitl_tasks (
                    task_id, thread_id, graph_name, node_name,
                    status, reason, threshold_info, payload
                ) VALUES (?, ?, ?, ?, 'PENDING', ?, ?, ?)
                """,
                (
                    task_id,
                    thread_id,
                    self.name,
                    node_name,
                    reason,
                    threshold_info,
                    json.dumps(payload, default=str),
                ),
            )
            conn.commit()
        return task_id

    async def _execute_node_fn(self, fn: Callable, state: Dict[str, Any]) -> Dict[str, Any]:
        """Executes a node function, supporting both synchronous and asynchronous functions."""
        if inspect.iscoroutinefunction(fn):
            return await fn(state)
        else:
            return fn(state)

    async def execute(
        self,
        thread_id: str,
        initial_state: Optional[Dict[str, Any]] = None,
        resume_payload: Optional[Dict[str, Any]] = None,
        max_steps: int = 50,
    ) -> Dict[str, Any]:
        """
        Executes or resumes the state graph with durable checkpoints after each node.
        """
        latest_chk = self.checkpointer.load_latest_checkpoint(thread_id)
        
        # 1. Determine starting node and state
        if latest_chk:
            # Resuming from existing checkpoint
            state = latest_chk.state_data
            step_number = latest_chk.step_number
            parent_chk_id = latest_chk.checkpoint_id
            
            # Check if this node was paused/interrupted or failed
            if state.get("__status__") in ["INTERRUPTED", "FAILED"] or (resume_payload and resume_payload.get("ticket_resolved_id")):
                # Resuming an interrupted or failed node with admin or external payload
                current_node = latest_chk.current_node
                state["__status__"] = "RUNNING"
                state.pop("__error__", None)
                if resume_payload:
                    state["__resume_payload__"] = resume_payload
                    state.update(resume_payload)
            else:
                # Progress to the next node
                current_node = self._get_next_node(latest_chk.current_node, state)
        else:
            # Starting fresh
            if not self.entry_point:
                raise ValueError("Cannot execute graph: No entry point set.")
            current_node = self.entry_point
            state = initial_state or {}
            step_number = 0
            parent_chk_id = None

        state["__thread_id__"] = thread_id
        state["__graph__"] = self.name
        state["__status__"] = "RUNNING"

        # 2. Main Execution Loop
        while current_node != END and step_number < max_steps:
            if current_node not in self.nodes:
                raise ValueError(f"Node '{current_node}' is not registered in graph '{self.name}'.")

            step_number += 1
            node_fn = self.nodes[current_node]
            
            # Log transition
            logger.info(f"[{self.name}:{thread_id}] Step {step_number} -> Executing node: '{current_node}'")
            state["__current_node__"] = current_node
            state["__step__"] = step_number
            
            # Record execution history
            history = state.setdefault("__history__", [])
            history.append({"node": current_node, "step": step_number, "timestamp": datetime.utcnow().isoformat()})

            try:
                # Execute Node
                updated_state = await self._execute_node_fn(node_fn, state)
                if isinstance(updated_state, dict):
                    state.update(updated_state)
                
                # Check for explicit interrupt in state
                if state.get("__interrupt__"):
                    reason = state.pop("__interrupt__")
                    raise InterruptSignal(reason=reason, interrupt_type=state.get("__interrupt_type__", "HITL"))

                # Save durable checkpoint after node completion
                chk_id = self.checkpointer.save_checkpoint(
                    thread_id=thread_id,
                    graph_name=self.name,
                    current_node=current_node,
                    state_data=state,
                    step_number=step_number,
                    parent_checkpoint_id=parent_chk_id,
                )
                parent_chk_id = chk_id

                # Calculate next transition
                current_node = self._get_next_node(current_node, state)

            except InterruptSignal as sig:
                # Expected HITL or External Pause
                logger.info(f"[{self.name}:{thread_id}] ⏸️ Graph Paused at '{current_node}': {sig.reason}")
                state["__status__"] = "INTERRUPTED"
                state["__interrupt_reason__"] = sig.reason
                state["__interrupt_type__"] = sig.interrupt_type
                
                # Record HITL task
                hitl_task_id = self._record_hitl_task(
                    thread_id=thread_id,
                    node_name=current_node,
                    reason=sig.reason,
                    threshold_info=sig.threshold_info,
                    payload=sig.payload or state,
                )
                state["__hitl_task_id__"] = hitl_task_id

                # Persist interrupted checkpoint
                chk_id = self.checkpointer.save_checkpoint(
                    thread_id=thread_id,
                    graph_name=self.name,
                    current_node=current_node,
                    state_data=state,
                    step_number=step_number,
                    parent_checkpoint_id=parent_chk_id,
                )
                return state

            except Exception as e:
                # Unplanned Runtime Failure -> Open Ticket
                logger.error(f"[{self.name}:{thread_id}] 💥 Exception in node '{current_node}': {e}")
                tb_str = traceback.format_exc()
                state["__status__"] = "FAILED"
                state["__error__"] = str(e)
                
                # Create Failure Ticket
                ticket_id = self._record_failure_ticket(
                    thread_id=thread_id,
                    failed_node=current_node,
                    error_msg=str(e),
                    tb_str=tb_str,
                    state_data=state,
                    checkpoint_id=parent_chk_id,
                )
                state["__failure_ticket_id__"] = ticket_id

                # Save failure checkpoint
                self.checkpointer.save_checkpoint(
                    thread_id=thread_id,
                    graph_name=self.name,
                    current_node=current_node,
                    state_data=state,
                    step_number=step_number,
                    parent_checkpoint_id=parent_chk_id,
                )
                return state

        # Graph execution completed to END
        state["__status__"] = "COMPLETED"
        logger.info(f"[{self.name}:{thread_id}] 🏁 Graph execution reached END successfully in {step_number} steps.")
        
        # Save final terminal checkpoint
        self.checkpointer.save_checkpoint(
            thread_id=thread_id,
            graph_name=self.name,
            current_node=END,
            state_data=state,
            step_number=step_number + 1,
            parent_checkpoint_id=parent_chk_id,
        )
        return state

    def run_sync(
        self,
        thread_id: str,
        initial_state: Optional[Dict[str, Any]] = None,
        resume_payload: Optional[Dict[str, Any]] = None,
        max_steps: int = 50,
    ) -> Dict[str, Any]:
        """Synchronous convenience helper for execute()."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(
                    asyncio.run,
                    self.execute(
                        thread_id=thread_id,
                        initial_state=initial_state,
                        resume_payload=resume_payload,
                        max_steps=max_steps,
                    )
                )
                return future.result()
        else:
            return asyncio.run(
                self.execute(
                    thread_id=thread_id,
                    initial_state=initial_state,
                    resume_payload=resume_payload,
                    max_steps=max_steps,
                )
            )
