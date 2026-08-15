"""
Wanderpath Travel - Sub-Task Router
Deterministically routes sub-tasks to Plan-and-Solve, Tree of Thoughts, or LATS
based on task characteristics, branching needs, and risk profiles.
"""

def route_subtask(subtask_description: str, risk_level: str = "low", requires_branching: bool = False) -> str:
    """
    Routes a given sub-task to the appropriate planning algorithm based on the decision matrix:
    
    Decision Matrix Rationale:
    1. Plan-and-Solve (PS): Used for linear, deterministic, mechanical sub-tasks with a single 
       correct path and zero branching or high risk (e.g., final ticket formatting, arithmetic).
    2. Tree of Thoughts (ToT): Used when there are multiple plausible orderings or candidate 
       paths to explore, but no cheap external grounding validator exists, relying on LLM self-evaluation.
    3. LATS (Language Agent Tree Search): Used for high-risk final execution steps where mistakes carry 
       real-world costs and require strict grounding against live environment/database validators.
    """
    subtask_lower = subtask_description.lower()
    
    # High-risk tasks or final execution steps with database/environment constraints -> LATS
    if risk_level.lower() == "high" or "finalize" in subtask_lower or "execute" in subtask_lower:
        return "LATS"
    
    # Tasks with branching options or path selection without external ground truth -> Tree of Thoughts
    if requires_branching or "choose" in subtask_lower or "optimize" in subtask_lower or "alternative" in subtask_lower:
        return "Tree of Thoughts"
        
    # Default fallback for linear, mechanical, deterministic steps -> Plan-and-Solve
    return "Plan-and-Solve"

if __name__ == "__main__":
    print("\n--- Running Sub-Task Router Verification ---")
    
    # Test cases representing the three shapes
    t1 = ("Format final ticket confirmation output", "low", False)
    t2 = ("Choose the best rebooking schedule option among alternatives", "medium", True)
    t3 = ("Execute final rebooking and downstream updates", "high", True)
    
    r1 = route_subtask(*t1)
    r2 = route_subtask(*t2)
    r3 = route_subtask(*t3)
    
    print(f"Task 1 Routing: {r1} (Expected: Plan-and-Solve)")
    print(f"Task 2 Routing: {r2} (Expected: Tree of Thoughts)")
    print(f"Task 3 Routing: {r3} (Expected: LATS)")
    
    assert r1 == "Plan-and-Solve", "Task 1 routing failed!"
    assert r2 == "Tree of Thoughts", "Task 2 routing failed!"
    assert r3 == "LATS", "Task 3 routing failed!"
    
    print("\n✅ Sub-task router verification PASSED successfully!")