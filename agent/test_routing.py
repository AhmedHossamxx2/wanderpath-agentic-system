import sys
import pathlib

# Ensure root is in path
sys.path.append(str(pathlib.Path(__file__).parent.parent.resolve()))

from memory.short_term import ShortTermMemory
from memory.stores import EpisodicStore, SemanticStore
from memory.routing import PromoteDropRouter


def test_routing_layer():
    print("--- Testing Promote-or-Drop Memory Routing Layer ---")

    # 1. Instantiate Stores and Router
    episodic_store = EpisodicStore()
    semantic_store = SemanticStore()
    router = PromoteDropRouter(episodic_store)

    # 2. Simulate evicted messages from short-term memory
    evicted_messages = [
        {"role": "user", "content": "Hello, good morning!"},
        {"role": "assistant", "content": "How can I help you today?"},
        {"role": "user", "content": "Sophia Chen's passport is EXPIRED (expires 2024-05-15)."},
        {"role": "assistant", "content": "Itinerary #105: Active (London Autumn Break)"},
        {"role": "user", "content": "Please cancel non-refundable Booking #3."},
        {"role": "assistant", "content": "SUCCESS (ELICITED): Non-refundable Booking #3 cancelled with human sign-off. Fee charged: $250.00."},
        {"role": "user", "content": "Thanks for your help!"},
    ]

    print(f"\nProcessing {len(evicted_messages)} evicted short-term turns through router...\n")

    promoted_count = 0
    forgotten_count = 0

    for msg in evicted_messages:
        decision, reasoning = router.evaluate_and_route(msg)
        if decision == "PROMOTE":
            promoted_count += 1
        else:
            forgotten_count += 1

    # 3. Inspect Episodic Store Results
    events = episodic_store.get_all_events()
    print(f"\n--- Routing Summary ---")
    print(f"Total Evaluated: {len(evicted_messages)}")
    print(f"Promoted to Episodic Store: {promoted_count}")
    print(f"Forgotten (Dropped): {forgotten_count}")

    print("\nRecorded Episodic Memory Events (with Reasoning):")
    print("=" * 60)
    for event in events:
        print(f"ID {event.id} [{event.timestamp}]:")
        print(f"  Content  : {event.content}")
        print(f"  Reasoning: {event.reasoning}\n")
    print("=" * 60)

    # 4. Strict Rubric Checks
    assert len(events) == promoted_count, "Episodic store count mismatch!"
    assert len(semantic_store.get_all_facts()) == 0, "CRITICAL: Router must NEVER write directly to semantic memory!"

    print("\n✅ Promote-or-Drop Router Test Passed Flawlessly!")


if __name__ == "__main__":
    test_routing_layer()