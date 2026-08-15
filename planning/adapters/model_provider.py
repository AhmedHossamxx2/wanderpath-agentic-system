"""
Wanderpath Travel - Model Provider Adapter
Supports both standard invocation and LangChain-style structured output binding.
Tracks LLM calls and tokens for the empirical comparison table.
"""

class MockResponse:
    def __init__(self, content: str):
        self.content = content

class StructuredOutputBound:
    """Helper that mocks LangChain's structured output binding."""
    def __init__(self, provider, schema):
        self.provider = provider
        self.schema = schema

    def invoke(self, messages, **kwargs):
        self.provider.call_count += 1
        
        prompt_text = " ".join([str(msg[1]) for msg in messages if isinstance(msg, (list, tuple)) and len(msg) > 1])
        self.provider.token_count += len(prompt_text) // 4

        # Dynamically return the appropriate Pydantic model instance expected by the toolkit
        schema_name = getattr(self.schema, "__name__", str(self.schema))
        
        if "ThoughtCandidates" in schema_name:
            res = self.schema(candidates=[
                "Same-day flight rebooking via partner airline", 
                "Next-day morning flight with hotel voucher"
            ])
        elif "ThoughtEvaluation" in schema_name:
            res = self.schema(
                score=0.85, 
                rationale="Feasible option with high compliance and passenger satisfaction."
            )
        else:
            res = self.schema()

        self.provider.token_count += 50 # estimated response token footprint
        return res

class WanderpathModelProvider:
    def __init__(self):
        self.call_count = 0
        self.token_count = 0

    def with_structured_output(self, schema, method="json_schema", **kwargs):
        """Binds the schema for structured parsing."""
        return StructuredOutputBound(self, schema)

    def invoke(self, messages, temperature=0.2, **kwargs):
        self.call_count += 1
        prompt_text = " ".join([str(msg[1]) for msg in messages if isinstance(msg, (list, tuple)) and len(msg) > 1])
        self.token_count += len(prompt_text) // 4

        response_content = "PLAN: Analyze paths.\nSOLUTION: Success."
        self.token_count += len(response_content) // 4
        return MockResponse(response_content)
    
    def get_metrics(self) -> dict:
        return {"llm_calls": self.call_count, "tokens": self.token_count}