### Folder 6: `rag/README.md` — Unstructured RAG Architecture

```markdown
# Unstructured RAG Architecture (`rag/`)

## Overview
The `rag/` directory contains the unstructured policy knowledge base, ChromaDB vector store wrapper (HNSW ANN index with metadata pre-filtering), 4 retrieval architectures (Naive, Hybrid, Agentic, Graph RAG), and the Self-RAG verification engine.

---

## File Manifest
* `vector_store.py`: Implements `WanderpathVectorStore` using ChromaDB with persistent HNSW cosine indexing and pre-search metadata index filtering (`where={"country": "Switzerland"}`).
* `self_rag.py`: Implements `SelfRAGVerifier` enforcing `IS_RELEVANT` (retrieval relevance) and `IS_SUPPORTED` (answer groundedness) checks to catch hallucinations.
* `corpus/wanderpath_guide.md`: Unstructured document corpus containing boutique hotel policies, pet regulations, cancellation rules, and travel advisories.
* `architectures/retrievers.py`: Contains retriever implementations for:
  1. `NaiveRAG`: Dense vector similarity search.
  2. `HybridSearchRAG`: Reciprocal Rank Fusion (RRF) combining dense vector search and sparse BM25 keyword scoring (`rank_bm25`).
  3. `AgenticRAG`: Multi-step reasoning loop that issues sub-queries for multi-part intents.
  4. `GraphRAG`: Knowledge Graph implementation (`networkx`) performing 2-hop neighborhood traversals across `Hotel`, `City`, `Advisory`, and `Policy` entities.

---

## Self-RAG Verification Gate
Before an answer reaches the user, `SelfRAGVerifier` evaluates:
1. **Context Relevance**: Filters out retrieved chunks that do not match query terms (`REJECTED_IRRELEVANT`).
2. **Answer Groundedness**: Verifies that key claims in the response are supported by retrieved context (`REJECTED_UNSUPPORTED`).