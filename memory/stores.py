"""
Wanderpath Travel Agency - Memory Persistence Stores
===================================================
Provides decoupled storage implementations for Episodic Memory (event logs)
and Semantic Memory (consolidated facts).
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
    """Placeholder for Consolidated Semantic Facts (populated strictly via consolidation pass)."""

    def __init__(self):
        self.facts: List[Dict[str, Any]] = []

    def get_all_facts(self) -> List[Dict[str, Any]]:
        return self.facts