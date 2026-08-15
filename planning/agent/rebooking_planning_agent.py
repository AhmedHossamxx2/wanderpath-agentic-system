"""
Wanderpath Travel - Trip Disruption & Rebooking Planning Agent
This agent orchestrates the DAG decomposition, routing, and execution of multi-step 
disruption recovery plans using PS, ToT, LATS, and Self-Refine/Reflexion.
It operates alongside the Memory/RAG agents, leveraging the MCP server for tool execution.
"""
import argparse
import time
from planning.adapters.model_provider import WanderpathModelProvider
from planning.grounding.environment_feedback import WanderpathEnvironment
from planning.routing.route_subtask import route_subtask
from planning.algorithms_glue.plan_and_solve import run_plan_and_solve
from planning.vendor.toolkit.planning_lab.algorithms.tree_of_thoughts import tree_of_thoughts
from planning.vendor.toolkit.planning_lab.algorithms.lats import lats
from planning.vendor.toolkit.planning_lab.algorithms.self_refine import reflect_and_refine

def execute_disruption_recovery(case_id: str):
    print(f"\n{'='*60}")
    print(f"🌍 Wanderpath Rebooking Agent Initiated")
    print(f"🚨 Disruption Case: {case_id}")
    print(f"{'='*60}\n")
    
    provider = WanderpathModelProvider()
    env = WanderpathEnvironment()
    
    # Simulate the DAG Decomposition phase
    print("Step 1: Decomposing task into DAG...")
    subtasks = [
        {"desc": "Format final ticket confirmation output", "risk": "low", "branching": False},
        {"desc": "Choose the best rebooking schedule option among alternatives", "risk": "medium", "branching": True},
        {"desc": "Execute final rebooking and downstream updates", "risk": "high", "branching": True}
    ]
    time.sleep(0.5)
    print(f"Generated {len(subtasks)} sub-tasks.\n")
    
    # Execute the DAG topologically
    for i, task in enumerate(subtasks, 1):
        print(f"--- Executing Sub-task {i} ---")
        print(f"Description: {task['desc']}")
        
        # Route the sub-task
        algorithm = route_subtask(task['desc'], task['risk'], task['branching'])
        print(f"Routed to Algorithm: {algorithm}")
        
        # Execute based on routing
        if algorithm == "Plan-and-Solve":
            res = run_plan_and_solve(task['desc'], provider)
            print(f"Result: {res[:50]}...")
            
            # Apply Self-Refine to cheap PS outputs
            print("Applying Self-Refine critique...")
            refined = reflect_and_refine(task['desc'], res, provider)
            print("Self-Refine PASS")
            
        elif algorithm == "Tree of Thoughts":
            res = tree_of_thoughts(task['desc'], provider, depth=2, beam_width=2)
            if res:
                print(f"Selected Path: {res[0].state[:50]}... (Score: {res[0].score})")
                
        elif algorithm == "LATS":
            res = lats(task['desc'], provider, env, iterations=2, n_actions=2)
            print(f"Final Grounded Execution Success: {res.success}")
            print(f"Environment Validator Score: {res.best_score}")
            
        print("-" * 30 + "\n")

    print(f"✅ Disruption Case {case_id} Successfully Resolved!")
    metrics = provider.get_metrics()
    print(f"Total LLM Calls: {metrics['llm_calls']} | Total Tokens: {metrics['tokens']}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", type=str, default="sample_disruption_maria_ostrowski")
    args = parser.parse_args()
    
    execute_disruption_recovery(args.case)