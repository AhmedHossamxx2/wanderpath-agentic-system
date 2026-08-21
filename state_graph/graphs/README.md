# Stateful Agent Graphs (`state_graph/graphs/`)

## Overview
The `state_graph/graphs/` directory houses the three production stateful agent problem graphs for **Wanderpath Travel B.** Each graph models a real-world, high-stakes operational problem that genuinely requires persistent state across sittings, external asynchronous waiting states, human approval gates, and cyclic recovery branches.

---

## The Three Stateful Problems & LLM-Call Additions

| Stateful Problem Graph | File | Why It Genuinely Requires a State Graph | 2 Embedded LLM-Call Additions | HITL Escalation Condition |
|---|---|---|---|---|
| **1. Complex International Visa & Consular Application** | `visa_graph.py` | Spans weeks across diplomatic checkpoints; pauses on asynchronous embassy webhooks/slots (`awaiting_consular_webhook`); cycles on document rejection/request. | 1. **Task Decomposition**: Builds dynamic multi-stage milestones.<br>2. **RAG Architecture**: Retrieves live embassy rules from ChromaDB vector store. | Expedited consular fee exceeds \$500.00 threshold or applicant criminal record flag. |
| **2. Supplier Dispute & Chargeback Appeal** | `dispute_graph.py` | Operates on strict 7-day airline dispute windows; pauses on carrier arbitration settlements (`awaiting_carrier_adjudication`); cycles to re-evaluate appeal strategies if rejected. | 1. **Tree of Thoughts (ToT)**: Evaluates competing legal appeal strategies (EU261 vs. Force Majeure).<br>2. **Constrained ReAct**: Executes whitelisted GDS filing tools with schema defense. | Carrier requires fee waiver > \$300.00 or demands Wanderpath legal indemnification. |
| **3. VIP Emergency Medical Evacuation & Repatriation** | `medevac_graph.py` | Mission-critical workflow; pauses on receiving hospital ICU bed confirmation (`awaiting_hospital_admission`); cycles if primary hospital saturates. | 1. **LATS**: Explores and scores medevac flight routings against live airfield and medical constraints.<br>2. **Constrained ReAct**: Issues cryptographically signed guarantee letters and private charter standby. | Irreversible air ambulance aircraft dispatch and guarantee amount > \$5,000.00. |

---

## Architectural Rationale for LLM Additions

### Graph 1: Visa Application (`visa_graph.py`)
- **Task Decomposition**: Consular workflows are not single-step submissions. They require breaking down passport validity validation, certified translation procurement, biometric booking, and courier tracking.
- **RAG Architecture**: Embassy policies change constantly (e.g. Schengen visa fee increases, Indonesian VoA validity windows). The node queries `WanderpathVectorStore` directly to ensure real-time policy compliance.

### Graph 2: Supplier Dispute (`dispute_graph.py`)
- **Tree of Thoughts (ToT)**: In contract disputes, multiple plausible arguments exist (e.g. EU261 statutory claim vs. Carrier breach of contract vs. Commercial goodwill). ToT generates all three thought branches and scores each on estimated monetary recovery and legal confidence.
- **Constrained ReAct**: Direct interaction with airline GDS systems requires strict schema compliance without hallucinated parameters.

### Graph 3: VIP Medical Evacuation (`medevac_graph.py`)
- **LATS (Language Agent Tree Search)**: High-stakes aeromedical dispatch cannot rely on simple prompt generation. LATS tree-searches candidate routings scored against external ground truth (airfield runway length, 24/7 nighttime customs clearance, medical equipment load, and ICU capability).
- **Constrained ReAct**: Executes authorized standby dispatch tools and issues structured guarantees of payment (GOP).

---

## State Graph Transition Diagrams

### 1. Visa Application Graph
```mermaid
flowchart TD
    A[Intake Visa Request] --> B[Task Decomposition: Milestone Roadmap]
    B --> C[RAG: Embassy Policy Retrieval]
    C --> D[Submit Dossier to Consulate]
    D --> E[Awaiting Consular Webhook: Pause]
    E --> F{Evaluate Consular Response}
    F -->|Additional Docs Requested| B
    F -->|Fee > $500: HITL Pause| G[Admin HITL Sign-off]
    G --> H[Finalize Visa Record]
    F -->|Standard Approval| H
    H --> END[__END__]
```

### 2. Supplier Dispute Graph
```mermaid
flowchart TD
    A[Intake Dispute Claim] --> B[Tree of Thoughts: Appeal Strategy Selection]
    B --> C[Constrained ReAct: GDS Chargeback Filing]
    C --> D[Awaiting Carrier Adjudication: Pause]
    D --> E{Evaluate Settlement Offer}
    E -->|Carrier Rebuttal: Cycle| B
    E -->|Waiver > $300: HITL Pause| F[Admin HITL Sign-off]
    F --> G[Finalize Ledger & Refund]
    E -->|Standard Settlement| G
    G --> END[__END__]
```

### 3. Medical Evacuation Graph
```mermaid
flowchart TD
    A[Intake Medical Alert] --> B[LATS: Aeromedical Route Search & Scoring]
    B --> C[Constrained ReAct: Dispatch Standby & Guarantee]
    C --> D[Awaiting Hospital Admission: Pause]
    D --> E{Evaluate Physician Authorization}
    E -->|ICU Beds Saturated: Cycle| B
    E -->|Dispatch > $5,000: HITL Pause| F[Medical Director HITL Sign-off]
    F --> G[Finalize Repatriation: Aircraft Airborne]
    E -->|Standard Authorization| G
    G --> END[__END__]
```

---

## Verification
Run the automated test suite verifying all 3 stateful graphs:
```bash
mcp_server\.venv\Scripts\python.exe state_graph\tests\test_stateful_graphs.py
```
