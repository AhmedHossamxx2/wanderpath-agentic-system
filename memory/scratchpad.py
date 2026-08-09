"""
Wanderpath Travel Agency - Agent Scratchpad Module
==================================================
Maintains the agent's active plan, current sub-goal, and working memory state
independently from conversational transcript turns.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class Scratchpad:
    current_goal: str = ""
    sub_goals: List[str] = field(default_factory=list)
    completed_steps: List[str] = field(default_factory=list)
    working_notes: Dict[str, Any] = field(default_factory=dict)

    def set_goal(self, goal: str, sub_goals: Optional[List[str]] = None) -> None:
        """Sets the primary objective and optional breakdown steps."""
        self.current_goal = goal
        self.sub_goals = sub_goals or []
        self.completed_steps = []

    def complete_sub_goal(self, step: str) -> None:
        """Marks a sub-goal as completed."""
        if step in self.sub_goals:
            self.sub_goals.remove(step)
        self.completed_steps.append(step)

    def update_note(self, key: str, value: Any) -> None:
        """Stores temporary working observations."""
        self.working_notes[key] = value

    def render_context_header(self) -> str:
        """Formats the scratchpad for injection into the model's system prompt."""
        return (
            f"=== ACTIVE PLAN SCRATCHPAD ===\n"
            f"PRIMARY GOAL: {self.current_goal or 'None'}\n"
            f"PENDING SUB-GOALS: {self.sub_goals}\n"
            f"COMPLETED STEPS: {self.completed_steps}\n"
            f"WORKING NOTES: {self.working_notes}\n"
            f"=============================="
        )