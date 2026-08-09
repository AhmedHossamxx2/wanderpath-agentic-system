# Retrieval Architecture Evaluation Suite (`retrieval_eval/`)

## Overview
The `retrieval_eval/` directory contains the domain-specific benchmark dataset and evaluation runner used to compare Naive RAG, Hybrid Search, Agentic RAG, and Graph RAG across Accuracy, Token Consumption, and Latency.

---

## File Manifest
* `test_questions.json`: Dataset containing 6 domain-specific test questions covering general policy, exact numerical citations, multi-hop reasoning, and multi-entity relations.
* `eval_retrieval.py`: Benchmark runner evaluating all 4 retrieval architectures against the question dataset.

---

## Retrieval Benchmark Results

| Architecture | Accuracy | Avg Tokens / Query | Avg Latency (ms) |
|---|---|---|---|
| **Naive RAG (Vector Only)** | 6/6 (100%) | 33 | 162.96 ms |
| **Hybrid Search (Vector + BM25) (Selected)** | **6/6 (100%)** | **33** | **161.02 ms** |
| **Agentic RAG (Multi-Step)** | 6/6 (100%) | 73 | 259.61 ms |
| **Graph RAG (Bonus Knowledge Graph)** | 2/6 (33%) | 68 | 0.06 ms |

---

## Architectural Decision
**Hybrid Search (Vector + BM25)** was selected as the default retrieval engine due to its minimal single-pass latency (161.02 ms) and 100% accuracy on citation and keyword queries. **Graph RAG** is retained as a specialized fallback path for complex multi-entity relational queries.

---

## Running the Benchmark
```powershell
python retrieval_eval/eval_retrieval.py