"""
Wanderpath Travel Agency - Three Stateful Agent Problem Graphs
==============================================================
Provides three genuinely stateful agent graphs, each embedding two distinct LLM-call additions:
1. Visa & Consular Application Graph (Task Decomposition + RAG)
2. Supplier Contract Dispute Graph (Tree of Thoughts + Constrained ReAct)
3. VIP Medical Evacuation Graph (LATS + Constrained ReAct)
"""

from state_graph.graphs.visa_graph import create_visa_processing_graph
from state_graph.graphs.dispute_graph import create_dispute_reconciliation_graph
from state_graph.graphs.medevac_graph import create_medevac_repatriation_graph

__all__ = [
    "create_visa_processing_graph",
    "create_dispute_reconciliation_graph",
    "create_medevac_repatriation_graph",
]
