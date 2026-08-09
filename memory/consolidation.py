"""
Wanderpath Travel Agency - Semantic Consolidation Layer
======================================================
Executes a periodic pass over EpisodicStore to build, version, and reconcile
semantic facts in SemanticStore without silent overwrites.
"""

import logging
from datetime import datetime
from typing import List
from memory.stores import EpisodicStore, SemanticStore, SemanticFact

logger = logging.getLogger("SemanticConsolidation")


class ConsolidationEngine:
    """
    Periodic consolidation engine. Reads episodic event logs and synthesizes
    long-term semantic facts. Explicitly handles fact versioning and conflict resolution.
    """

    def __init__(self, episodic_store: EpisodicStore, semantic_store: SemanticStore):
        self.episodic_store = episodic_store
        self.semantic_store = semantic_store

    def run_consolidation_pass(self) -> List[SemanticFact]:
        """
        Scans un-consolidated episodic events, detects updates or contradictions,
        and produces versioned semantic facts.
        """
        logger.info("⚙️ Starting periodic semantic consolidation pass...")
        events = self.episodic_store.get_all_events()
        newly_consolidated: List[SemanticFact] = []

        for event in events:
            content = event.content
            client_id = event.metadata.get("client_id", 1)  # Default client context

            # Pattern 1: Seat preference facts
            if "seat" in content.lower() or "aisle" in content.lower() or "window" in content.lower():
                key = "seating_preference"
                val = content

                # Check if an ACTIVE fact already exists for this client key
                existing_facts = [
                    f for f in self.semantic_store.get_facts_for_client(client_id)
                    if f.fact_key == key and f.status == "ACTIVE"
                ]

                if existing_facts:
                    # CONFLICT RESOLUTION: Supersede old version rather than overwriting
                    active_fact = existing_facts[0]
                    if active_fact.fact_value != val:
                        logger.info(
                            f"⚔️ CONFLICT DETECTED for Client #{client_id} [{key}]: "
                            f"Existing: '{active_fact.fact_value}' vs New: '{val}'"
                        )
                        active_fact.status = "SUPERSEDED"
                        active_fact.superseded_at = datetime.utcnow().isoformat()
                        
                        # Create v2 fact
                        new_fact = self.semantic_store.add_fact(
                            client_id=client_id,
                            fact_key=key,
                            fact_value=val,
                            version=active_fact.version + 1,
                        )
                        newly_consolidated.append(new_fact)
                        logger.info(f"✅ Resolved conflict -> Created Fact v{new_fact.version} (Active)")
                else:
                    # Create initial v1 fact
                    new_fact = self.semantic_store.add_fact(
                        client_id=client_id,
                        fact_key=key,
                        fact_value=val,
                        version=1,
                    )
                    newly_consolidated.append(new_fact)
                    logger.info(f"➕ Synthesized new Fact v1 for Client #{client_id}: '{val}'")

            # Pattern 2: Allergy / Medical facts
            elif "allergy" in content.lower() or "shellfish" in content.lower():
                key = "dietary_medical_restriction"
                val = content
                existing_facts = [
                    f for f in self.semantic_store.get_facts_for_client(client_id)
                    if f.fact_key == key and f.status == "ACTIVE"
                ]
                if not existing_facts:
                    new_fact = self.semantic_store.add_fact(
                        client_id=client_id,
                        fact_key=key,
                        fact_value=val,
                        version=1,
                    )
                    newly_consolidated.append(new_fact)

        logger.info(f"🏁 Consolidation pass completed. Total facts in store: {len(self.semantic_store.facts)}")
        return newly_consolidated