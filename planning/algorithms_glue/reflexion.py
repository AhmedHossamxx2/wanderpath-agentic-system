"""
Wanderpath Travel - Reflexion Wrapper
Used for high-value sub-tasks where a single failure requires multi-trial learning and verbal reflection.
"""
import argparse
import time
from planning.adapters.model_provider import WanderpathModelProvider
from planning.grounding.environment_feedback import WanderpathEnvironment
from planning.vendor.toolkit.planning_lab.algorithms.reflexion import reflexion

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", type=str, required=True)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()

    if args.smoke:
        print(f"\n--- Running Reflexion Smoke Test ---")
        print(f"Case: {args.case}")
        
        start_time = time.time()
        provider = WanderpathModelProvider()
        env = WanderpathEnvironment()
        
        # We simulate a case where the agent initially outputs an invalid passport state,
        # forcing the environment to fail it, generating a reflection, and trying again.
        result = reflexion(
            task=f"Rebook travel ensuring all constraints (including passport rules) are met for: {args.case}",
            llm=provider,
            environment=env,
            max_trials=2,
            memory_size=3
        )
        
        latency_ms = (time.time() - start_time) * 1000
        metrics = provider.get_metrics()
        
        print(f"\nSuccess: {result.success}")
        if result.memory:
            print(f"Carried Memory/Reflection:\n- {result.memory[0]}")
        print(f"\nBest Output State:\n{result.output}")
        
        print(f"\nPass/Fail: {'PASS' if result.output else 'FAIL'}")
        print(f"LLM Calls: {metrics['llm_calls']}")
        print(f"Tokens Used: {metrics['tokens']}")
        print(f"Latency: {latency_ms:.2f} ms")
        print("-" * 40)