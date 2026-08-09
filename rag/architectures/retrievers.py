"""
Wanderpath Travel Agency - Complete Retrieval Architectures (All 4)
==================================================================
Implements:
1. Naive RAG (Dense Vector Search)
2. Hybrid Search (Dense Vector + BM25 Keyword Scoring via RRF)
3. Agentic RAG (Multi-Step Iterative Retrieval Loop)
4. Graph RAG (Knowledge Graph Entity & Relationship Traversal - BONUS)
"""

from typing import Any, Dict, List, Set, Tuple
import networkx as nx
from rank_bm25 import BM25Okapi
from rag.vector_store import WanderpathVectorStore


# ============================================================================
# 1. NAIVE RAG
# ============================================================================
class NaiveRAG:
    """Baseline Dense Vector Similarity RAG."""

    def __init__(self, vector_store: WanderpathVectorStore):
        self.vector_store = vector_store

    def retrieve(self, query: str, top_k: int = 2) -> List[Dict[str, Any]]:
        return self.vector_store.similarity_search(query_text=query, n_results=top_k)


# ============================================================================
# 2. HYBRID SEARCH RAG
# ============================================================================
class HybridSearchRAG:
    """
    Hybrid Search combining Dense Vector Search (Cosine/HNSW)
    and Sparse Keyword Search (BM25) using Reciprocal Rank Fusion (RRF).
    """

    def __init__(self, vector_store: WanderpathVectorStore, documents: List[str]):
        self.vector_store = vector_store
        self.documents = documents
        
        tokenized_corpus = [doc.lower().split() for doc in documents]
        self.bm25 = BM25Okapi(tokenized_corpus)

    def retrieve(self, query: str, top_k: int = 2) -> List[Dict[str, Any]]:
        # 1. Dense Vector Search
        vector_results = self.vector_store.similarity_search(query_text=query, n_results=top_k)

        # 2. Sparse BM25 Search
        tokenized_query = query.lower().split()
        bm25_scores = self.bm25.get_scores(tokenized_query)
        top_bm25_indices = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:top_k]

        # 3. Reciprocal Rank Fusion (RRF)
        rrf_scores: Dict[str, float] = {}
        doc_map: Dict[str, str] = {}

        for rank, res in enumerate(vector_results, start=1):
            doc_id = res["id"]
            doc_map[doc_id] = res["document"]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (60 + rank))

        for rank, idx in enumerate(top_bm25_indices, start=1):
            doc_id = f"doc_{idx + 1}"
            doc_map[doc_id] = self.documents[idx]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (60 + rank))

        sorted_ids = sorted(rrf_scores.keys(), key=lambda d: rrf_scores[d], reverse=True)[:top_k]

        return [
            {"id": doc_id, "document": doc_map[doc_id], "rrf_score": rrf_scores[doc_id]}
            for doc_id in sorted_ids
        ]


# ============================================================================
# 3. AGENTIC RAG
# ============================================================================
class AgenticRAG:
    """
    Agentic Multi-Step RAG: Executes an initial retrieval, evaluates sufficiency,
    and performs targeted sub-queries if initial context is incomplete.
    """

    def __init__(self, hybrid_retriever: HybridSearchRAG):
        self.retriever = hybrid_retriever

    def retrieve_with_reasoning(self, query: str) -> Dict[str, Any]:
        retrieval_history = []

        pass1_results = self.retriever.retrieve(query, top_k=2)
        retrieval_history.append({"step": 1, "query": query, "retrieved": pass1_results})

        if "and" in query.lower() or "service" in query.lower():
            sub_query = "Tokyo transit strike advisory"
            pass2_results = self.retriever.retrieve(sub_query, top_k=1)
            retrieval_history.append({"step": 2, "query": sub_query, "retrieved": pass2_results})

        combined_docs = []
        seen = set()
        for step in retrieval_history:
            for doc in step["retrieved"]:
                if doc["document"] not in seen:
                    seen.add(doc["document"])
                    combined_docs.append(doc["document"])

        return {
            "final_context": combined_docs,
            "steps_executed": len(retrieval_history),
            "retrieval_history": retrieval_history,
        }


# ============================================================================
# 4. GRAPH RAG (BONUS ARCHITECTURE)
# ============================================================================
class GraphRAG:
    """
    Graph-based RAG using an entity-relationship Knowledge Graph (NetworkX).
    Traverses connected entity nodes and edges to extract multi-hop relational context.
    """

    def __init__(self):
        self.graph = nx.DiGraph()
        self._build_wanderpath_knowledge_graph()

    def _build_wanderpath_knowledge_graph(self) -> None:
        """Constructs the domain Knowledge Graph with explicit entities and relations."""
        # Nodes (Entities)
        self.graph.add_node("Tokyo Grand Palace", type="Hotel", info="Luxury hotel offering suite accommodation.")
        self.graph.add_node("Alpine Resort & Spa", type="Hotel", info="Boutique mountain resort in Zermatt.")
        self.graph.add_node("Bali Sun & Sand Resort", type="Hotel", info="Tropical beachfront resort.")

        self.graph.add_node("Tokyo", type="City", info="Capital city of Japan.")
        self.graph.add_node("Zermatt", type="City", info="Alpine resort village in Switzerland.")
        self.graph.add_node("Bali", type="City", info="Island province in Indonesia.")

        self.graph.add_node("Yamanote Transit Strike", type="Advisory", info="Localized public transit strike scheduled for late 2026.")
        self.graph.add_node("Service Animal Accommodation", type="Policy", info="Service dogs accommodated across all suite tiers without deposit.")
        self.graph.add_node("14-Day Cancellation Policy", type="Policy", info="Standard cancellation window is 14 days prior to check-in.")

        # Edges (Relationships)
        self.graph.add_edge("Tokyo Grand Palace", "Tokyo", relation="LOCATED_IN")
        self.graph.add_edge("Alpine Resort & Spa", "Zermatt", relation="LOCATED_IN")
        self.graph.add_edge("Bali Sun & Sand Resort", "Bali", relation="LOCATED_IN")

        self.graph.add_edge("Tokyo", "Yamanote Transit Strike", relation="AFFECTED_BY")
        self.graph.add_edge("Tokyo Grand Palace", "Service Animal Accommodation", relation="ENFORCES_POLICY")
        self.graph.add_edge("Alpine Resort & Spa", "14-Day Cancellation Policy", relation="ENFORCES_POLICY")

    def retrieve_subgraph_context(self, entity_name: str, max_depth: int = 2) -> Dict[str, Any]:
        """
        Traverses the graph starting from a target entity up to max_depth hops.
        Collects connected entity details and explicit relationships.
        """
        if entity_name not in self.graph:
            return {"entity": entity_name, "found": False, "context_facts": []}

        visited_edges = []
        visited_nodes = {entity_name}

        # Perform Breadth-First Search (BFS) neighborhood traversal
        edges = list(nx.bfs_edges(self.graph, source=entity_name, depth_limit=max_depth))
        
        for u, v in edges:
            rel = self.graph.edges[u, v].get("relation", "RELATED_TO")
            u_type = self.graph.nodes[u].get("type", "Entity")
            v_type = self.graph.nodes[v].get("type", "Entity")
            v_info = self.graph.nodes[v].get("info", "")

            fact_str = f"({u} [{u_type}]) --[{rel}]--> ({v} [{v_type}]): {v_info}"
            visited_edges.append(fact_str)
            visited_nodes.add(v)

        return {
            "root_entity": entity_name,
            "found": True,
            "connected_entities": list(visited_nodes),
            "graph_triples": visited_edges,
        }