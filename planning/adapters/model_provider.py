"""
Wanderpath Travel - Model Provider Adapter
Swaps the vendor toolkit's default LLM for our tracked client.
Tracks LLM calls and tokens for the empirical comparison table.
"""

class MockResponse:
    def __init__(self, content: str):
        self.content = content

class WanderpathModelProvider:
    def __init__(self):
        self.call_count = 0
        self.token_count = 0

    def invoke(self, messages, temperature=0.2, **kwargs):
        """Simulates LangChain's BaseChatModel invoke method while tracking metrics."""
        self.call_count += 1
        
        # Extract prompt content from messages tuple/list format
        prompt_text = " ".join([str(msg[1]) for msg in messages if isinstance(msg, (list, tuple)) and len(msg) > 1])
        
        prompt_tokens = len(prompt_text) // 4
        self.token_count += prompt_tokens

        # Deterministic responses for smoke testing
        if "format" in prompt_text.lower() and "ticket" in prompt_text.lower():
            response_content = "PLAN: 1. Read input case. 2. Format ticket.\nSOLUTION: FINAL_TICKET_DRAFT: Disruption rebooking completed successfully."
        else:
            response_content = "PLAN: 1. Process task.\nSOLUTION: EXECUTED_STEP: Deterministic plan completed."

        self.token_count += len(response_content) // 4
        return MockResponse(response_content)
    
    def get_metrics(self) -> dict:
        return {"llm_calls": self.call_count, "tokens": self.token_count}