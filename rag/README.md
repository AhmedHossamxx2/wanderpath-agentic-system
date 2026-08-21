# Unstructured RAG Architecture (`rag/`)

## Overview
The `rag/` directory contains the unstructured policy knowledge base, ChromaDB vector store wrapper (HNSW ANN index with metadata pre-filtering and dynamic document CRUD), 4 retrieval architectures (Naive, Hybrid, Agentic, Graph RAG), and the Self-RAG verification engine.

---

## File Manifest
* `vector_store.py`: Implements `WanderpathVectorStore` using ChromaDB with persistent HNSW cosine indexing, pre-search metadata filtering, and live document CRUD methods (`add_document`, `delete_document`, `list_documents`, `get_document`) for real-time admin knowledge updates.
* `self_rag.py`: Implements `SelfRAGVerifier` enforcing `IS_RELEVANT` (retrieval relevance) and `IS_SUPPORTED` (answer groundedness) checks to catch hallucinations.
* `corpus/wanderpath_guide.md`: Unstructured document corpus containing boutique hotel policies, pet regulations, cancellation rules, and travel advisories.
* `architectures/retrievers.py`: Contains retriever implementations for:
  1. `NaiveRAG`: Dense vector similarity search.
  2. `HybridSearchRAG`: Reciprocal Rank Fusion (RRF) combining dense vector search and sparse BM25 keyword scoring (`rank_bm25`). Selected default for production.
  3. `AgenticRAG`: Multi-step reasoning loop that issues sub-queries for multi-part intents.
  4. `GraphRAG`: Knowledge Graph implementation (`networkx`) performing 2-hop neighborhood traversals across `Hotel`, `City`, `Advisory`, and `Policy` entities.

---

## Dynamic Knowledge Base Management
The `WanderpathVectorStore` provides dynamic document management methods driven directly by the platform admin panel:
- `add_document(doc_id, document, metadata)`: Upserts a new policy chunk into the active vector collection.
- `delete_document(doc_id)`: Removes a policy chunk from the vector collection.
- `list_documents()`: Lists all indexed document IDs, content snippets, and metadatas.

Changes made by an admin in the platform immediately alter subsequent similarity retrieval results without restarting the server or re-indexing the entire database from scratch.

---

## Self-RAG Verification Gate
Before an answer reaches the user, `SelfRAGVerifier` evaluates:
1. **Context Relevance**: Filters out retrieved chunks that do not match query terms (`REJECTED_IRRELEVANT`).
2. **Answer Groundedness**: Verifies that key claims in the response are supported by retrieved context (`REJECTED_UNSUPPORTED`).

---

## Verification
Run the Sub-Module 1 verification suite to test dynamic RAG operations:
```bash
python agent/test_dynamic_mcp_rag.py
```