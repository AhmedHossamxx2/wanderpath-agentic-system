import asyncio
import sys
import pathlib

# Ensure root is in path
sys.path.append(str(pathlib.Path(__file__).parent.parent.resolve()))

from memory.short_term import ShortTermMemory
from memory.scratchpad import Scratchpad


def test_short_term_and_scratchpad():
    print("--- Testing Decoupled Short-Term Memory and Scratchpad ---")

    # 1. Initialize Scratchpad and Set Active Plan
    scratchpad = Scratchpad()
    scratchpad.set_goal(
        goal="Process non-refundable cancellation for Sophia Chen (Booking #3)",
        sub_goals=[
            "Lookup itinerary details",
            "Authenticate manager override",
            "Obtain human elicitation confirmation",
            "Execute cancellation",
        ],
    )
    scratchpad.update_note("client_id", 2)
    scratchpad.update_note("passport_status", "EXPIRED")

    print("Initial Scratchpad State:")
    print(scratchpad.render_context_header())

    # 2. Initialize Short-Term Memory with small capacity (e.g., 5 messages)
    memory = ShortTermMemory(max_messages=5)

    # 3. Simulate 15 turns of conversation and heavy tool logs
    print("\nSimulating 15 dialogue turns to trigger heavy short-term pruning...")
    for i in range(1, 16):
        memory.add_message("user", f"User dialogue message {i}")
        memory.add_message("assistant", f"Tool output observation {i}")

    transcript = memory.get_transcript()
    print(f"\nTotal messages in transcript post-pruning: {len(transcript)} (Max limit was 5)")
    print(f"Oldest retained message: '{transcript[0]['content']}'")

    # 4. CRITICAL CHECK: Verify Scratchpad is 100% intact after pruning
    print("\nScratchpad State Post-Pruning:")
    print(scratchpad.render_context_header())

    assert len(transcript) <= 5, "Short-term memory failed to prune transcript!"
    assert scratchpad.current_goal != "", "Scratchpad was wiped during pruning!"
    assert len(scratchpad.sub_goals) == 4, "Sub-goals were corrupted!"
    assert scratchpad.working_notes["passport_status"] == "EXPIRED", "Working notes were lost!"

    print("\n✅ Decoupled Short-Term Memory & Scratchpad Test Passed Flawlessly!")


if __name__ == "__main__":
    test_short_term_and_scratchpad()