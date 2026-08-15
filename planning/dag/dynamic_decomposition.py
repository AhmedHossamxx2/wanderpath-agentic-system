"""
Wanderpath Travel - Dynamic Decomposition
Generates the next sub-task only after observing the result of the previous one.
"""
from planning.vendor.toolkit.planning_lab.algorithms.dynamic_decomposition import DynamicDecomposer
from planning.adapters.mcp_tool_bridge import execute_mcp_tool

WANDERPATH_DYNAMIC_PROMPT = """
You are the Wanderpath Trip Disruption Agent. Generate the NEXT sub-task based on the request and previous observations.
Available tools: [create_booking, modify_booking_dates, cancel_booking, check_entry_requirements, notify_client]

If rebooking fails, you MUST reshape the plan (e.g., check entry requirements against the new date before modifying hotels).
Request: {request}
Previous Observations: {observations}
"""

class WanderpathDynamicDecomposer(DynamicDecomposer):
    def __init__(self, llm_client=None):
        super().__init__(llm_client)
        self.prompt_template = WANDERPATH_DYNAMIC_PROMPT

    def observe_and_execute(self, tool_name: str, arguments: dict) -> str:
        # Wire the 'observe last result' hook to our REAL mcp tool bridge!
        return execute_mcp_tool(tool_name, arguments)
        
    def run_interleaved(self, request: str):
        print("\n--- Running DYNAMIC DECOMPOSITION (Reactive Plan) ---")
        return super().run_interleaved(request)