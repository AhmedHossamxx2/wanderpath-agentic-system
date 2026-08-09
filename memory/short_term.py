"""
Wanderpath Travel Agency - Short-Term Memory Module
==================================================
Manages rolling message history for active sessions with automated capacity pruning.
"""

from typing import List, Dict, Any


class ShortTermMemory:
    def __init__(self, max_messages: int = 10):
        self.max_messages = max_messages
        self.messages: List[Dict[str, Any]] = []

    def add_message(self, role: str, content: str, tool_calls: Any = None) -> None:
        """Appends a new turn to the rolling transcript."""
        msg = {"role": role, "content": content}
        if tool_calls:
            msg["tool_calls"] = tool_calls
        self.messages.append(msg)
        self._prune_if_needed()

    def _prune_if_needed(self) -> None:
        """Enforces max_messages capacity using a sliding window strategy."""
        if len(self.messages) > self.max_messages:
            # Retain system messages if present at index 0, otherwise drop oldest
            if self.messages[0].get("role") == "system":
                self.messages = [self.messages[0]] + self.messages[-(self.max_messages - 1):]
            else:
                self.messages = self.messages[-self.max_messages:]

    def get_transcript(self) -> List[Dict[str, Any]]:
        """Returns the current unpruned message stack."""
        return self.messages

    def clear(self) -> None:
        """Clears the conversational transcript."""
        self.messages = []