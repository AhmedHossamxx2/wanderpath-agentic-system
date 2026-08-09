import asyncio
import pathlib
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# ============================================================================
# MOCK LLM ROUTER
# Simulates an LLM evaluating a prompt against a list of dynamically provided tools
# ============================================================================
def simulate_llm_tool_selection(user_prompt: str, available_tools: list) -> dict | None:
    """
    Acts as our 'LLM'. It looks at the user prompt, reads the available tool descriptions,
    and returns a structured tool call (or None if no tool matches).
    """
    prompt = user_prompt.lower()
    tool_names = [t.name for t in available_tools]

    print("\n🧠 [LLM Router] Thinking...")
    
    if "itinerary" in prompt and "get_itinerary_details" in tool_names:
        print("🧠 [LLM Router] Decision: The user wants itinerary details. Selecting 'get_itinerary_details'.")
        # Extract numbers from prompt to act as the ID
        extracted_id = int(''.join(filter(str.isdigit, prompt)) or 101)
        return {
            "tool": "get_itinerary_details",
            "arguments": {"itinerary_id": extracted_id}
        }
        
    if "manager" in prompt and "authenticate_manager" in tool_names:
        print("🧠 [LLM Router] Decision: The user wants to elevate privileges. Selecting 'authenticate_manager'.")
        return {
            "tool": "authenticate_manager",
            "arguments": {"passcode": "admin123"}  # The LLM "knows" this from its system prompt/context
        }
        
    print("🧠 [LLM Router] Decision: No suitable tool found for this prompt.")
    return None

# ============================================================================
# AGENT MAIN LOOP
# ============================================================================
async def run_minimal_agent():
    root_dir = pathlib.Path(__file__).parent.parent.resolve()
    python_venv = root_dir / "mcp_server" / ".venv" / "Scripts" / "python.exe"
    server_script = root_dir / "mcp_server" / "server.py"

    server_params = StdioServerParameters(
        command=str(python_venv),
        args=[str(server_script), "--transport", "stdio"], # Force stdio for local agent loop
    )

    print("🤖 Agent booting up...")
    print("🔌 Connecting to MCP Server...")

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("✅ Agent successfully connected to server environment.\n")

            # ---------------------------------------------------------
            # PHASE 1: DISCOVERY
            # ---------------------------------------------------------
            print("🔍 AGENT PHASE 1: DISCOVERING CAPABILITIES")
            tools_response = await session.list_tools()
            available_tools = tools_response.tools
            
            print(f"Agent discovered {len(available_tools)} tools:")
            for tool in available_tools:
                print(f"  - {tool.name}: {tool.description}")

            # ---------------------------------------------------------
            # PHASE 2: AGENTIC LOOP (Query 1)
            # ---------------------------------------------------------
            print("\n🗣️ AGENT PHASE 2: PROCESSING USER INTENT")
            user_prompt_1 = "Can you pull up my itinerary for booking 105?"
            print(f"User Prompt: '{user_prompt_1}'")
            
            tool_call_1 = simulate_llm_tool_selection(user_prompt_1, available_tools)
            
            if tool_call_1:
                print(f"⚡ [Agent] Executing tool: {tool_call_1['tool']} with args {tool_call_1['arguments']}")
                result = await session.call_tool(tool_call_1['tool'], arguments=tool_call_1['arguments'])
                print(f"📥 [Agent] Observation from Server:\n   {result.content[0].text}")

            # ---------------------------------------------------------
            # PHASE 3: AGENTIC LOOP (Query 2)
            # ---------------------------------------------------------
            print("\n🗣️ AGENT PHASE 3: PROCESSING SECOND INTENT")
            user_prompt_2 = "I need manager access to override a fee."
            print(f"User Prompt: '{user_prompt_2}'")
            
            tool_call_2 = simulate_llm_tool_selection(user_prompt_2, available_tools)
            
            if tool_call_2:
                print(f"⚡ [Agent] Executing tool: {tool_call_2['tool']} with args {tool_call_2['arguments']}")
                result = await session.call_tool(tool_call_2['tool'], arguments=tool_call_2['arguments'])
                print(f"📥 [Agent] Observation from Server:\n   {result.content[0].text}")

            print("\n🎉 Minimal Agent Loop Completed!")

if __name__ == "__main__":
    asyncio.run(run_minimal_agent())