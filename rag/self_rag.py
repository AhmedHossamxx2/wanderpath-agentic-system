"""
Wanderpath Travel Agency - Self-RAG Verification Module
======================================================
Provides explicit post-retrieval and post-generation reflection checks
to verify context relevance and answer groundedness (preventing hallucinations).
"""

from typing import Dict, List, Any


class SelfRAGVerifier:
    """
    Self-RAG style verification engine. Evaluates context relevance
    and checks if generated outputs are strictly supported by retrieved facts.
    """

    def evaluate_retrieval_relevance(self, query: str, retrieved_chunks: List[str]) -> Dict[str, Any]:
        """
        [IS_RELEVANT Check]: Verifies if retrieved context chunks contain keywords
        or semantic overlap matching the prompt.
        """
        query_terms = set(query.lower().split())
        relevant_chunks = []

        for chunk in retrieved_chunks:
            chunk_terms = set(chunk.lower().split())
            overlap = query_terms.intersection(chunk_terms)
            # Simple keyword overlap threshold for verification
            if len(overlap) >= 1:
                relevant_chunks.append(chunk)

        is_relevant = len(relevant_chunks) > 0
        return {
            "is_relevant": is_relevant,
            "relevant_chunks": relevant_chunks,
            "status": "RELEVANT" if is_relevant else "REJECTED_IRRELEVANT",
        }

    def evaluate_answer_support(self, answer: str, grounding_chunks: List[str]) -> Dict[str, Any]:
        """
        [IS_SUPPORTED Check]: Verifies if key claims in the generated response
        are grounded in the retrieved context chunks (detects hallucinations).
        """
        if not grounding_chunks:
            return {"is_supported": False, "status": "REJECTED_NO_CONTEXT"}

        combined_context = " ".join(grounding_chunks).lower()
        answer_words = [w for w in answer.lower().split() if len(w) > 4]  # Focus on key terms

        # Count how many substantial terms in the answer are grounded in context
        grounded_terms = [w for w in answer_words if w in combined_context]
        grounding_ratio = len(grounded_terms) / len(answer_words) if answer_words else 1.0

        # Require at least 50% grounding overlap
        is_supported = grounding_ratio >= 0.5

        return {
            "is_supported": is_supported,
            "grounding_ratio": round(grounding_ratio, 2),
            "status": "VERIFIED" if is_supported else "REJECTED_UNSUPPORTED",
        }

    def verify_rag_pipeline(self, query: str, retrieved_chunks: List[str], generated_answer: str) -> Dict[str, Any]:
        """Executes full Self-RAG verification sequence."""
        rel_check = self.evaluate_retrieval_relevance(query, retrieved_chunks)
        if not rel_check["is_relevant"]:
            return {
                "passed": False,
                "stage_failed": "RETRIEVAL_RELEVANCE",
                "details": rel_check["status"],
            }

        supp_check = self.evaluate_answer_support(generated_answer, rel_check["relevant_chunks"])
        if not supp_check["is_supported"]:
            return {
                "passed": False,
                "stage_failed": "ANSWER_GROUNDEDNESS",
                "details": supp_check["status"],
                "grounding_ratio": supp_check["grounding_ratio"],
            }

        return {
            "passed": True,
            "status": "VERIFIED_GROUNDED",
            "grounding_ratio": supp_check["grounding_ratio"],
        }