import sys
import pathlib

# Ensure root is in path
sys.path.append(str(pathlib.Path(__file__).parent.parent.resolve()))

from memory.stores import EpisodicStore, SemanticStore
from memory.consolidation import ConsolidationEngine


def test_semantic_consolidation_and_conflict_resolution():
    print("--- Testing Semantic Consolidation Pass & Conflict Resolution ---")

    episodic_store = EpisodicStore()
    semantic_store = SemanticStore()
    engine = ConsolidationEngine(episodic_store, semantic_store)

    client_id = 101

    # STEP 1: Add initial preference episode (Client prefers Window seat)
    print("\n--- Step 1: Ingesting Initial Preference Episode ---")
    episodic_store.add_event(
        content="Client prefers Window seats for all long-haul flights.",
        reasoning="Customer explicitly stated window preference during onboarding.",
        metadata={"client_id": client_id},
    )

    # Run Pass #1
    engine.run_consolidation_pass()
    facts_after_pass1 = semantic_store.get_facts_for_client(client_id)
    print(f"Facts in Semantic Store after Pass 1: {len(facts_after_pass1)}")
    print(f"Fact v1: Value='{facts_after_pass1[0].fact_value}', Status={facts_after_pass1[0].status}, Version={facts_after_pass1[0].version}")

    assert len(facts_after_pass1) == 1
    assert facts_after_pass1[0].version == 1
    assert facts_after_pass1[0].status == "ACTIVE"

    # STEP 2: Ingest contradictory episode (Client injured leg, requires Aisle seat)
    print("\n--- Step 2: Ingesting Contradictory Episode (Leg Injury) ---")
    episodic_store.add_event(
        content="Client recently suffered a leg injury and now requires an Aisle seat for legroom.",
        reasoning="Medical update from recent triage call.",
        metadata={"client_id": client_id},
    )

    # Run Pass #2
    print("\nExecuting periodic consolidation pass over updated episodic store...")
    engine.run_consolidation_pass()

    # STEP 3: Verify Conflict Resolution Outcome
    all_facts = semantic_store.get_facts_for_client(client_id)
    active_facts = semantic_store.get_active_facts_for_client(client_id)

    print("\n============================================================")
    print("FINAL SEMANTIC STORE AUDIT TRAIL:")
    print("============================================================")
    for f in all_facts:
        print(f"Fact ID #{f.fact_id} | Key: '{f.fact_key}' | Version: v{f.version} | Status: {f.status}")
        print(f"  Value: '{f.fact_value}'")
        if f.superseded_at:
            print(f"  Superseded At: {f.superseded_at}")
        print("-" * 60)

    # RUBRIC CHECKS
    assert len(all_facts) == 2, "Both fact versions must be preserved for auditability!"
    assert all_facts[0].version == 1 and all_facts[0].status == "SUPERSEDED", "Fact v1 was not properly marked SUPERSEDED!"
    assert all_facts[1].version == 2 and all_facts[1].status == "ACTIVE", "Fact v2 was not created as ACTIVE!"
    assert len(active_facts) == 1, "Only one fact should be ACTIVE!"
    assert "Aisle" in active_facts[0].fact_value, "Active fact value failed to update to latest preference!"

    print("\n✅ Semantic Consolidation & Conflict Resolution Test Passed Flawlessly!")


if __name__ == "__main__":
    test_semantic_consolidation_and_conflict_resolution()