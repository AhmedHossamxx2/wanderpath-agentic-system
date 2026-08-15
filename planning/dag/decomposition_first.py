"""
Wanderpath Travel - Decomposition First
Builds the full sub-task DAG in one shot for mechanical/predictable plans.
"""
from planning.vendor.toolkit.planning_lab.algorithms.decomposition import TaskDecomposer
from planning.dag.acyclicity import verify_acyclic, CycleDetectedError

WANDERPATH_DECOMPOSITION_PROMPT = """
You are the Wanderpath Trip Disruption Agent. Break down the following rebooking request into a DAG of sub-tasks.
Available tools: [create_booking, modify_booking_dates, cancel_booking, check_entry_requirements, notify_client]

Generate the full plan up front assuming the happy path (same-day rebooking succeeds).
Request: {request}
"""

class WanderpathDecompositionFirst(TaskDecomposer):
    def __init__(self, llm_client=None):
        # We will use the model provider adapter later, pass None to use toolkit default for now
        super().__init__(llm_client)
        self.prompt_template = WANDERPATH_DECOMPOSITION_PROMPT

    def generate_and_execute_dag(self, request: str):
        print("\n--- Running DECOMPOSITION-FIRST (Up-Front Plan) ---")
        # 1. Generate the DAG using the vendor's internal logic
        dag = super().generate_dag(request)
        
        # 2. Enforce acyclicity at construction time!
        verify_acyclic(dag.get('dependencies', {}))
        
        # 3. Execute blindly in topological order (Vendor's execute method)
        return super().execute_dag(dag)