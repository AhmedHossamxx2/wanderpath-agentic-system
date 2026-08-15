"""
Wanderpath Travel - Self-Refine Wrapper
Used for single-pass critique and revision of cheap outputs like client emails.
"""
import argparse
import time
from planning.adapters.model_provider import WanderpathModelProvider
from planning.vendor.toolkit.planning_lab.algorithms.self_refine import reflect_and_refine

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", type=str, required=True)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()

    if args.smoke:
        print(f"\n--- Running Self-Refine Smoke Test ---")
        print(f"Case: {args.case}")
        
        start_time = time.time()
        provider = WanderpathModelProvider()
        
        goal = f"Draft an email to the client explaining the rebooking for case: {args.case}"
        draft = "Your flight changed. Let me know if you need anything."
        
        result = reflect_and_refine(goal=goal, draft=draft, llm=provider)
        
        latency_ms = (time.time() - start_time) * 1000
        metrics = provider.get_metrics()
        
        print(f"\nCritique Generated:\n{result.critique}")
        print(f"\nRevised Output:\n{result.revised}")
        
        print(f"\nPass/Fail: {'PASS' if result.revised != draft else 'FAIL'}")
        print(f"LLM Calls: {metrics['llm_calls']}")
        print(f"Tokens Used: {metrics['tokens']}")
        print(f"Latency: {latency_ms:.2f} ms")
        print("-" * 40)