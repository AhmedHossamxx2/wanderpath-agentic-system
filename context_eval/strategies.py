"""
Wanderpath Travel Agency - Context Management Strategies
========================================================
Implements 4 distinct transcript pruning strategies:
1. Sliding Window
2. Tool Output Masking
3. Recursive Summarization
4. Zone-Based Pruning
"""

import time
from typing import Dict, List, Any, Tuple


class ContextManager:
    """Provides implementations for all 4 context management strategies."""

    @staticmethod
    def sliding_window(messages: List[Dict[str, Any]], window_size: int = 6) -> Tuple[List[Dict[str, Any]], float]:
        """Strategy 1: Keeps only the last N turns."""
        start_time = time.perf_counter()
        
        # Retain system prompt at index 0 if present
        if messages and messages[0].get("role") == "system":
            pruned = [messages[0]] + messages[-(window_size - 1):]
        else:
            pruned = messages[-window_size:]
            
        latency = (time.perf_counter() - start_time) * 1000
        return pruned, latency

    @staticmethod
    def tool_output_masking(messages: List[Dict[str, Any]], max_tool_chars: int = 50) -> Tuple[List[Dict[str, Any]], float]:
        """Strategy 2: Truncates heavy tool JSON outputs while preserving dialogue."""
        start_time = time.perf_counter()
        pruned = []

        for msg in messages:
            msg_copy = msg.copy()
            # Mask tool/observation outputs if they exceed threshold
            if msg.get("role") in ["tool", "observation"] or "Observation" in msg.get("content", ""):
                content = msg["content"]
                if len(content) > max_tool_chars:
                    msg_copy["content"] = content[:max_tool_chars] + "... [MASKED HEAVY TOOL OUTPUT]"
            pruned.append(msg_copy)

        latency = (time.perf_counter() - start_time) * 1000
        return pruned, latency

    @staticmethod
    def recursive_summarization(messages: List[Dict[str, Any]], compact_threshold: int = 8) -> Tuple[List[Dict[str, Any]], float]:
        """Strategy 3: Compacts older turns into a summary block."""
        start_time = time.perf_counter()

        if len(messages) <= compact_threshold:
            return messages, (time.perf_counter() - start_time) * 1000

        # Compact older turns into a single summary system message
        old_turns = messages[:-4]
        recent_turns = messages[-4:]
        
        summary_text = f"[SUMMARY OF {len(old_turns)} PAST TURNS]: User discussed itinerary options and passport checks."
        pruned = [{"role": "system", "content": summary_text}] + recent_turns

        latency = (time.perf_counter() - start_time) * 1000
        return pruned, latency

    @staticmethod
    def zone_based_pruning(messages: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], float]:
        """
        Strategy 4: Protects System Zone & Active Goal Zone while aggressively
        pruning intermediate tool chatter zone.
        """
        start_time = time.perf_counter()

        system_zone = [m for m in messages if m.get("role") == "system" or "SCRATCHPAD" in m.get("content", "")]
        recent_buffer_zone = messages[-3:]  # Retain latest 3 turns

        # Intermediate chatter zone is dropped
        pruned = system_zone + [m for m in recent_buffer_zone if m not in system_zone]

        latency = (time.perf_counter() - start_time) * 1000
        return pruned, latency