"""
Wanderpath Travel - Model Provider Adapter
Supports standard invocation and structured output binding for ToT and LATS.
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
        elif "LATSActionBatch" in schema_name:
            from planning.vendor.toolkit.planning_lab.algorithms.lats import LATSAction
            res = self.schema(actions=[
                LATSAction(action="rebook_flight", state="Flight rebooked for next_day, hotel confirmed, client notified."),
                LATSAction(action="reroute", state="Alternative route selected, passport validity verified, client notified.")
            ])
        elif "ValueEstimate" in schema_name:
            res = self.schema(score=0.9)
        else:
            res = self.schema()

        self.provider.token_count += 60
        return res

class WanderpathModelProvider:
    def __init__(self):
        self.call_count = 0
        self.token_count = 0

    def with_structured_output(self, schema, method="json_schema", **kwargs):
        return StructuredOutputBound(self, schema)

    def invoke(self, messages, temperature=0.2, **kwargs):
        self.provider_call_count = getattr(self, 'call_count', 0) + 1
        self.call_count = self.provider_call_count
        
        prompt_text = " ".join([str(msg[1]) for msg in messages if isinstance(msg, (list, tuple)) and len(msg) > 1])
        self.token_count += len(prompt_text) // 4

        response_content = "Reflection: Action needed adjustment based on staging rules. Rebooking verified successfully."
        self.token_count += len(response_content) // 4
        return MockResponse(response_content)
    
    def get_metrics(self) -> dict:
        return {"llm_calls": self.call_count, "tokens": self.token_count}