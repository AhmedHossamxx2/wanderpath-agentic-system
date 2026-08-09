### Folder 4: `memory/README.md` — Long-Term Memory Architecture

```markdown
# Long-Term Memory Architecture (`memory/`)

## Overview
The `memory/` directory implements the dual-component short-term memory buffer, active plan scratchpad, overflow promote-or-drop router, and periodic semantic consolidation engine with conflict resolution.

---

## File Manifest
* `short_term.py`: Implements `ShortTermMemory`, a rolling message history buffer with automated sliding-window capacity pruning.
* `scratchpad.py`: Implements `Scratchpad`, a state tracker for active primary goals, pending sub-goals, completed steps, and working notes.
* `stores.py`: Defines data models (`EpisodicEvent`, `SemanticFact`) and storage classes (`EpisodicStore`, `SemanticStore`).
* `routing.py`: Implements `PromoteDropRouter`, which evaluates short-term overflow messages and routes high-value items to `EpisodicStore` while dropping transient small talk (`FORGET`).
* `consolidation.py`: Implements `ConsolidationEngine`, a periodic batch pass that scans `EpisodicStore` to synthesize, version (`v1` -> `v2`), and reconcile semantic facts.

---

## Memory Flow Architecture

Short-Term Memory (Rolling Buffer) ──(Overflow)──> Promote-or-Drop Router ──> Episodic Store
│
(Periodic Consolidation)
▼
Scratchpad (Active Goal / Sub-goals) <── [Injected in Prompt] ─────────── Semantic Store (v1, v2)


---

## Architectural Rules
1. **Pruning Invariance**: `ShortTermMemory` capacity pruning operates independently of `Scratchpad`. Dropping old dialogue turns never alters active goals or working notes.
2. **Router Decoupling**: `PromoteDropRouter` writes exclusively to `EpisodicStore`. It **never** writes directly to `SemanticStore`.
3. **Auditability & Conflict Resolution**: Contradictory facts (e.g., seat preference changing from Window to Aisle) are resolved by marking `v1` as `SUPERSEDED` with a timestamp and instantiating `v2` as `ACTIVE`. Ol