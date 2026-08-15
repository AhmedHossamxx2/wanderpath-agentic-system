"""
Wanderpath Travel - Plan and Solve Wrapper
Used for deterministic, mechanical sub-tasks with no branching (e.g., formatting tickets).
"""
import argparse
import time
from planning.adapters.model_provider import WanderpathModelProvider
from planning.vendor.toolkit.planning_lab.algorithms.plan_and_solve import plan_and_solve

def run_plan_and_solve(question: str, llm_client) -> str:
    """Wraps the vendor toolkit's plan_and_solve function."""
    return plan_and_solve(question, llm_client)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", type=str, required=True)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()

    if args.smoke:
        print(f"\n--- Running Plan-and-Solve Smoke Test ---")
        print(f"Case: {args.case}")
        
        start_time = time.time()
        provider = WanderpathModelProvider()
        
        # Run the trivial known case using the toolkit function
        result = run_plan_and_solve(f"Format final ticket output for case: {args.case}", provider)
        
        latency_ms = (time.time() - start_time) * 1000
        metrics = provider.get_metrics()
        
        print(f"Result:\n{result}")
        print(f"\nPass/Fail: {'PASS' if result else 'FAIL'}")
        print(f"LLM Calls: {metrics['llm_calls']}")
        print(f"Tokens Used: {metrics['tokens']}")
        print(f"Latency: {latency_ms:.2f} ms")
        print("-" * 40)