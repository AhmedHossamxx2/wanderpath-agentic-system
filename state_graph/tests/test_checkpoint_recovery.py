"""
Wanderpath Travel Agency - Durable Checkpoint Crash-and-Resume Verification
=============================================================================
Proves that the state graph persists state to SQLite after every node transition,
and that an abrupt process kill (SIGKILL / os._exit) allows resuming from the exact
checkpoint with zero state loss and zero re-execution of completed nodes.
"""

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure project root is in sys.path
project_root = pathlib.Path(__file__).parent.parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from state_graph.base import StateGraph, END
from state_graph.checkpointer import DurableCheckpointer


# --- Worker Process Execution Script (Invoked directly or via CLI) ---
def build_test_graph(db_path: str, crash_at_node_b: bool = False) -> StateGraph:
    checkpointer = DurableCheckpointer(db_path=db_path)
    graph = StateGraph("CrashRecoveryTestGraph", checkpointer=checkpointer)

    def node_a(state: dict) -> dict:
        print("[Node A] Running Step 1: Initializing data...")
        visited = state.get("visited_nodes", [])
        visited.append("node_a")
        return {"visited_nodes": visited, "val_a": 100, "node_a_count": state.get("node_a_count", 0) + 1}

    def node_b(state: dict) -> dict:
        print("[Node B] Running Step 2: Processing intermediate calculations...")
        visited = state.get("visited_nodes", [])
        visited.append("node_b")
        state["visited_nodes"] = visited
        state["val_b"] = 200

        if crash_at_node_b:
            print("[Node B] 💥 SIMULATING FATAL PROCESS CRASH (os._exit(77))!")
            # First write checkpoint to test crash right after node finish
            graph.checkpointer.save_checkpoint(
                thread_id=state["__thread_id__"],
                graph_name=graph.name,
                current_node="node_b",
                state_data=state,
                step_number=state.get("__step__", 2),
            )
            sys.stdout.flush()
            os._exit(77)  # Abrupt process termination without normal python exit hooks

        return {"visited_nodes": visited, "val_b": 200, "node_b_count": state.get("node_b_count", 0) + 1}

    def node_c(state: dict) -> dict:
        print("[Node C] Running Step 3: Finalizing outputs...")
        visited = state.get("visited_nodes", [])
        visited.append("node_c")
        return {
            "visited_nodes": visited,
            "val_c": 300,
            "final_sum": state.get("val_a", 0) + state.get("val_b", 0) + 300,
        }

    graph.add_node("node_a", node_a)
    graph.add_node("node_b", node_b)
    graph.add_node("node_c", node_c)

    graph.add_edge("node_a", "node_b")
    graph.add_edge("node_b", "node_c")
    graph.add_edge("node_c", END)

    graph.set_entry_point("node_a")
    return graph


def run_worker():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--thread-id", type=str, required=True)
    parser.add_argument("--db-path", type=str, required=True)
    parser.add_argument("--crash", action="store_true")
    args = parser.parse_args()

    graph = build_test_graph(args.db_path, crash_at_node_b=args.crash)
    res = graph.run_sync(args.thread_id, initial_state={"initial_seed": "Wanderpath-2026"})
    print("WORKER_RESULT:" + json.dumps(res))


# --- Main Test Runner ---
def test_checkpoint_crash_and_resume():
    print("==================================================================")
    print("🧪 RUNNING DURABLE CHECKPOINT CRASH-AND-RESUME TEST (Issue #62)")
    print("==================================================================\n")

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        db_path = str(pathlib.Path(tmp_dir) / "test_crash_recovery.sqlite3")
        thread_id = "thread-crash-test-001"
        python_exec = sys.executable

        # ------------------------------------------------------------
        # PHASE 1: Run process 1 which abruptly crashes at Node B
        # ------------------------------------------------------------
        print("1️⃣ Launching Process 1 (Configured to crash mid-run at Node B)...")
        cmd_crash = [
            python_exec,
            __file__,
            "--thread-id", thread_id,
            "--db-path", db_path,
            "--crash"
        ]
        
        proc1 = subprocess.run(cmd_crash, capture_output=True, text=True)
        print(f"   Process 1 exited with code: {proc1.returncode} (Expected: 77)")
        assert proc1.returncode == 77, f"Process did not terminate with expected crash code 77! Out: {proc1.stdout}"
        print("   ✅ Process 1 abruptly terminated mid-run as simulated.\n")

        # ------------------------------------------------------------
        # PHASE 2: Verify Checkpoint state persisted on disk before crash
        # ------------------------------------------------------------
        print("2️⃣ Inspecting durable SQLite checkpoints from disk...")
        checkpointer = DurableCheckpointer(db_path=db_path)
        checkpoints = checkpointer.list_checkpoints(thread_id)
        
        print(f"   Found {len(checkpoints)} checkpoints saved before the crash:")
        for chk in checkpoints:
            print(f"   - Checkpoint: {chk.checkpoint_id} | Node: {chk.current_node} | Step: {chk.step_number}")
        
        assert len(checkpoints) >= 2, f"Expected at least 2 checkpoints, found {len(checkpoints)}"
        latest_chk = checkpointer.load_latest_checkpoint(thread_id)
        assert latest_chk is not None
        assert latest_chk.current_node == "node_b"
        assert latest_chk.state_data.get("val_a") == 100
        assert "node_a" in latest_chk.state_data.get("visited_nodes", [])
        print("   ✅ Verified: State from completed steps (node_a, node_b) is intact in SQLite.\n")

        # ------------------------------------------------------------
        # PHASE 3: Launch Process 2 to RESUME execution from checkpoint
        # ------------------------------------------------------------
        print("3️⃣ Launching Process 2 to RESUME from latest checkpoint...")
        cmd_resume = [
            python_exec,
            __file__,
            "--thread-id", thread_id,
            "--db-path", db_path
        ]
        
        proc2 = subprocess.run(cmd_resume, capture_output=True, text=True)
        print(f"   Process 2 exited with code: {proc2.returncode}")
        assert proc2.returncode == 0, f"Process 2 failed to resume! Err: {proc2.stderr} Out: {proc2.stdout}"
        
        # Parse result
        result_line = [l for l in proc2.stdout.splitlines() if l.startswith("WORKER_RESULT:")]
        assert len(result_line) == 1, f"Missing WORKER_RESULT in output: {proc2.stdout}"
        final_state = json.loads(result_line[0].replace("WORKER_RESULT:", ""))

        print("\n4️⃣ Evaluating Final State & Execution Trace:")
        print(f"   - Final Status: {final_state.get('__status__')}")
        print(f"   - Node A Executions Count: {final_state.get('node_a_count', 0)} (Must be 1)")
        print(f"   - Final Sum (val_a + val_b + val_c): {final_state.get('final_sum')} (Expected: 600)")
        print(f"   - Visited Nodes: {final_state.get('visited_nodes')}")

        # Assertions
        assert final_state.get("__status__") == "COMPLETED", "Graph did not reach COMPLETED status!"
        assert final_state.get("node_a_count") == 1, "Node A was re-executed upon resume! (Violates recovery invariant)"
        assert final_state.get("final_sum") == 600, f"Expected final sum 600, got {final_state.get('final_sum')}"
        assert final_state.get("initial_seed") == "Wanderpath-2026", "Initial seed data was lost!"

        print("\n==================================================================")
        print("🎉 CRASH-AND-RESUME VERIFICATION PASSED 100%!")
        print("==================================================================")


if __name__ == "__main__":
    if len(sys.argv) > 1 and "--thread-id" in sys.argv:
        run_worker()
    else:
        test_checkpoint_crash_and_resume()
