"""
Wanderpath Travel Agency - Memory Persistence Stores (Updated)
===================================================
Provides decoupled storage implementations for Episodic Memory (event logs)
and Semantic Memory (consolidated facts with versioning & expiry).
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class EpisodicEvent:
    id: int
    content: str
    reasoning: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SemanticFact:
    fact_id: int
    client_id: int
    fact_key: str
    fact_value: str
    version: int
    status: str  # 'ACTIVE', 'SUPERSEDED', 'EXPIRED'
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    superseded_at: Optional[str] = None


class EpisodicStore:
    """Stores promoted episodic memories evicted from short-term memory."""

    def __init__(self):
        self.events: List[EpisodicEvent] = []
        self._counter = 1

    def add_event(self, content: str, reasoning: str, metadata: Optional[Dict[str, Any]] = None) -> EpisodicEvent:
        event = EpisodicEvent(
            id=self._counter,
            content=content,
            reasoning=reasoning,
            metadata=metadata or {},
        )
        self.events.append(event)
        self._counter += 1
        return event

    def get_all_events(self) -> List[EpisodicEvent]:
        return self.events


class SemanticStore:
    """Stores consolidated semantic facts derived strictly via periodic consolidation passes."""

    def __init__(self):
        self.facts: List[SemanticFact] = []
        self._counter = 1

    def get_all_facts(self) -> List[SemanticFact]:
        """Returns all recorded semantic facts."""
        return self.facts

    def add_fact(self, client_id: int, fact_key: str, fact_value: str, version: int = 1) -> SemanticFact:
        fact = SemanticFact(
            fact_id=self._counter,
            client_id=client_id,
            fact_key=fact_key,
            fact_value=fact_value,
            version=version,
            status="ACTIVE",
        )
        self.facts.append(fact)
        self._counter += 1
        return fact

    def get_facts_for_client(self, client_id: int) -> List[SemanticFact]:
        return [f for f in self.facts if f.client_id == client_id]

    def get_active_facts_for_client(self, client_id: int) -> List[SemanticFact]:
        return [f for f in self.facts if f.client_id == client_id and f.status == "ACTIVE"]