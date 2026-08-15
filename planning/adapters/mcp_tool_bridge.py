"""
Wanderpath Travel - MCP Tool Bridge
Exposes server tools to the planning nodes and simulates the mid-flight failure.
"""
def execute_mcp_tool(tool_name: str, arguments: dict) -> str:
    """
    Executes the tool. Intentionally simulates a mid-flight failure for same-day
    flight rebooking to trigger dynamic decomposition reshaping.
    """
    print(f"\n[Tool Execution] {tool_name} with args: {arguments}")
    
    # 💥 THE MID-FLIGHT FAILURE POINT 💥
    if tool_name == "create_booking" and arguments.get("target_date") == "same_day":
        obs = "OBSERVATION: FAILURE. No seats available in required fare class for same-day rebooking. Earliest available is tomorrow."
        print(f"  -> {obs}")
        return obs
        
    obs = f"OBSERVATION: SUCCESS. {tool_name} completed."
    print(f"  -> {obs}")
    return obs