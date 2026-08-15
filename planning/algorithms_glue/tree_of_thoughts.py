"""
Wanderpath Travel - Tree of Thoughts Wrapper
Used for optimizing multi-branch rebooking strategies via beam search and self-evaluation.
"""
import argparse
import time
from planning.adapters.model_provider import WanderpathModelProvider
from planning.vendor.toolkit.planning_lab.algorithms.tree_of_thoughts import tree_of_thoughts

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", type=str, required=True)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()

    if args.smoke:
        print(f"\n--- Running Tree of Thoughts Smoke Test ---")
        print(f"Case: {args.case}")
        
        start_time = time.time()
        provider = WanderpathModelProvider()
        
        # Run Tree of Thoughts using the toolkit function
        thoughts = tree_of_thoughts(
            problem=f"Optimize rebooking path for case: {args.case}",
            llm=provider,
            depth=2,
            beam_width=2
        )
        
        latency_ms = (time.time() - start_time) * 1000
        metrics = provider.get_metrics()
        
        print(f"Resulting Best Thoughts:")
        for t in thoughts:
            print(f" - State: {t.state} | Score: {t.score} | Rationale: {t.rationale}")
            
        print(f"\nPass/Fail: {'PASS' if thoughts else 'FAIL'}")
        print(f"LLM Calls: {metrics['llm_calls']}")
        print(f"Tokens Used: {metrics['tokens']}")
        print(f"Latency: {latency_ms:.2f} ms")
        print("-" * 40)