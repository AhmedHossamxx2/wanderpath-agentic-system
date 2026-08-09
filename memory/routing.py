"""
Wanderpath Travel Agency - Promote-or-Drop Router
=================================================
Evaluates short-term memory overflow items and decides whether to forget them
or promote them into episodic memory with explicit reasoning.
"""

import logging
from typing import Any, Dict, Tuple
from memory.stores import EpisodicStore

logger = logging.getLogger("PromoteDropRouter")


class PromoteDropRouter:
    """
    Evaluates evicted messages from short-term memory buffer.
    Routes important state changes/facts to EpisodicStore and drops conversational noise.
    """

    def __init__(self, episodic_store: EpisodicStore):
        self.episodic_store = episodic_store

    def evaluate_and_route(self, evicted_message: Dict[str, Any]) -> Tuple[str, str]:
        """
        Evaluates an evicted message turn.

        Returns:
            Tuple[decision, reasoning]: ('FORGET'|'PROMOTE', reasoning_text)
        """
        content = evicted_message.get("content", "")
        role = evicted_message.get("role", "")
        content_lower = content.lower()

        # Rule 1: High-value actions, errors, cancellations, or preferences -> PROMOTE
        if any(kw in content_lower for kw in ["cancelled", "fee", "allergy", "expired", "override", "booking #", "itinerary #"]):
            decision = "PROMOTE"
            reasoning = f"Message contains high-value operational or domain event keywords ({role})."
            self.episodic_store.add_event(
                content=content,
                reasoning=reasoning,
                metadata={"role": role, "source": "short_term_overflow"},
            )
            logger.info(f" [ROUTER DECISION: PROMOTE] {reasoning} | Content: '{content[:60]}...'")
            return decision, reasoning

        # Rule 2: Casual greetings, general small talk, or routine system confirmations -> FORGET
        decision = "FORGET"
        reasoning = f"Message contains low-value conversational turn or transient output ({role})."
        logger.info(f"🗑️ [ROUTER DECISION: FORGET] {reasoning} | Content: '{content[:60]}...'")
        return decision, reasoning