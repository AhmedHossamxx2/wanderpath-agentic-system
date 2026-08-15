"""
Wanderpath Travel - LATS (Language Agent Tree Search) Wrapper
Used for high-risk final rebooking actions with grounded environment validation.
"""
import argparse
import time
from planning.adapters.model_provider import WanderpathModelProvider
from planning.grounding.environment_feedback import WanderpathEnvironment
from planning.vendor.toolkit.planning_lab.algorithms.lats import lats

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", type=str, required=True)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()

    if args.smoke:
        print(f"\n--- Running LATS Smoke Test ---")
        print(f"Case: {args.case}")
        
        start_time = time.time()
        provider = WanderpathModelProvider()
        env = WanderpathEnvironment()
        
        result = lats(
            task=f"Execute final rebooking and downstream updates for case: {args.case}",
            llm=provider,
            environment=env,
            iterations=2,
            n_actions=2
        )
        
        latency_ms = (time.time() - start_time) * 1000
        metrics = provider.get_metrics()
        
        print(f"\nLATS Result Success: {result.success}")
        print(f"Best Score: {result.best_score}")
        print(f"Iterations: {result.iterations}")
        print(f"Best Output State:\n{result.output}")
        
        print(f"\nPass/Fail: {'PASS' if result.success or result.best_score > 0.7 else 'FAIL'}")
        print(f"LLM Calls: {metrics['llm_calls']}")
        print(f"Tokens Used: {metrics['tokens']}")
        print(f"Latency: {latency_ms:.2f} ms")
        print("-" * 40)