# Context Management Evaluation Suite (`context_eval/`)

## Overview
The `context_eval/` directory contains the implementations, test transcripts, and benchmarking script used to evaluate four distinct context window management strategies against long, tool-heavy transcripts.

---

## File Manifest
* `strategies.py`: Implements `ContextManager` containing all 4 context pruning strategies (`sliding_window`, `tool_output_masking`, `recursive_summarization`, `zone_based_pruning`).
* `test_suite.py`: Defines 3 long-context test transcripts where critical target facts (shellfish allergy, expired passport date, aisle seat requirement) are buried under noisy tool outputs.
* `eval_context.py`: Benchmark runner executing all 4 strategies against the test suite, recording Accuracy, Token Consumption, and Latency.

---

## Strategy Benchmark Results

| Strategy | Task Accuracy | Avg Tokens / Run | Avg Latency (ms) |
|---|---|---|---|
| **Sliding Window** | 1/3 (33%) | 448 | 0.004 ms |
| **Tool Output Masking (Selected)** | **3/3 (100%)** | **109** | **0.009 ms** |
| **Recursive Summarization** | 2/3 (66%) | 534 | 0.002 ms |
| **Zone-Based Pruning** | 1/3 (33%) | 448 | 0.005 ms |

---

## Architectural Decision
**Tool Output Masking** was selected as Wanderpath's default context strategy. Because MCP context bloat is heavily dominated by large JSON tool observations (rather than conversational dialogue), truncating tool outputs achieves 100% target fact recall at the lowest token footprint.

---

## Running the Benchmark
```powershell
python context_eval/eval_context.py