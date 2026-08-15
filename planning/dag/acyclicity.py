"""
Wanderpath Travel - DAG Acyclicity Checker
Ensures that a generated plan of sub-tasks does not contain deadlocks/cycles.
"""
from typing import Dict, List, Set

class CycleDetectedError(Exception):
    """Raised when a cycle is detected in the DAG."""
    pass

def verify_acyclic(graph: Dict[str, List[str]]) -> bool:
    """
    Verifies that a directed graph (adjacency list mapping node -> list of dependent nodes)
    contains no cycles using Depth-First Search (DFS).
    
    Raises:
        CycleDetectedError: If a cycle is found.
    Returns:
        bool: True if acyclic.
    """
    visited: Set[str] = set()
    rec_stack: Set[str] = set()

    def dfs(node: str) -> bool:
        visited.add(node)
        rec_stack.add(node)

        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                if dfs(neighbor):
                    return True
            elif neighbor in rec_stack:
                return True

        rec_stack.remove(node)
        return False

    for node in graph.keys():
        if node not in visited:
            if dfs(node):
                raise CycleDetectedError(f"Cycle detected involving task: {node}")

    return True