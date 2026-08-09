### Folder 3: `agent/README.md` — Agent Core & Verification Suite

```markdown
# Agent Core & Verification Suite (`agent/`)

## Overview
The `agent/` directory contains the production agent execution loop and individual protocol verification runners. The agent integrates MCP tool discovery, REST-based Mistral LLM function calling, long-term memory management, and Self-RAG verification into a unified loop.

---

## File Manifest
* `agent.py`: Production agent execution loop connecting MCP tool discovery with Mistral AI via direct REST API calls (`httpx`).
* `smoke_test_all.py`: Master Lab 1 smoke test runner verifying all 7 MCP protocol concerns sequentially.
* `smoke_test_lab2.py`: Master Lab 2 smoke test runner verifying all memory and RAG concerns.
* `test_handshake.py`: Unit test verifying server initialization and capability negotiation over `stdio`.
* `test_resources_prompts.py`: Unit test verifying resource listing/reading and prompt template rendering.
* `test_notifications.py`: Unit test verifying `notifications/tools/list_changed` handling upon role elevation.
* `test_elicitation.py`: Unit test verifying mid-call elicitation pause for non-refundable cancellations.
* `test_progress.py`: Unit test verifying progress token streaming during long-running operations.
* `test_defensive_design.py`: Unit test verifying JSON schema constraints, RBAC blocks, and date validation.
* `test_transport.py`: Unit test verifying complete handshake and tool execution over HTTP/SSE.

---

## Execution Instructions

### Running the Master Protocol Verification (Lab 1)
```powershell
python agent/smoke_test_all.py
Running the Master Memory & RAG Verification (Lab 2)
PowerShell
python agent/smoke_test_lab2.py
Launching the Production Agent
Ensure MISTRAL_API_KEY is configured in your .env file, then execute:

PowerShell
python agent/agent.py