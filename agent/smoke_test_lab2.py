import sys
import pathlib

# Ensure root is in path
sys.path.append(str(pathlib.Path(__file__).parent.parent.resolve()))

from memory.short_term import ShortTermMemory
from memory.scratchpad import Scratchpad
from memory.stores import EpisodicStore, SemanticStore
from memory.routing import PromoteDropRouter
from memory.consolidation import ConsolidationEngine
from rag.vector_store import WanderpathVectorStore
from rag.architectures.retrievers import NaiveRAG, HybridSearchRAG, AgenticRAG, GraphRAG
from rag.self_rag import SelfRAGVerifier


def run_master_lab2_smoke_test():
    print("==================================================================")
    print("🚀 STARTING MASTER LAB 2 SMOKE TEST (ALL MEMORY & RAG CONCERNS)")
    print("==================================================================\n")

    # 1. Decoupled Short-Term Memory & Scratchpad
    print("1️⃣ Testing Short-Term Memory & Scratchpad Decoupling...")
    sp = Scratchpad()
    sp.set_goal("Sophia Chen Tokyo Cancellation")
    stm = ShortTermMemory(max_messages=2)
    stm.add_message("user", "Msg 1")
    stm.add_message("user", "Msg 2")
    stm.add_message("user", "Msg 3")  # Triggers pruning
    assert len(stm.get_transcript()) == 2
    assert sp.current_goal == "Sophia Chen Tokyo Cancellation"
    print("   ✅ Pruning retained scratchpad state perfectly.\n")

    # 2. Promote-or-Drop Router & Episodic Store
    print("2️⃣ Testing Promote-or-Drop Router...")
    epi = EpisodicStore()
    sem = SemanticStore()
    router = PromoteDropRouter(epi)
    router.evaluate_and_route({"role": "user", "content": "Cancel non-refundable Booking #3"})
    assert len(epi.get_all_events()) == 1
    assert len(sem.get_all_facts()) == 0
    print("   ✅ Event routed to EpisodicStore without writing to SemanticStore.\n")

    # 3. Semantic Consolidation & Conflict Resolution
    print("3️⃣ Testing Semantic Consolidation & Conflict Resolution...")
    epi.add_event("Client prefers Window seat", "Initial preference", {"client_id": 101})
    engine = ConsolidationEngine(epi, sem)
    engine.run_consolidation_pass()
    
    epi.add_event("Client requires Aisle seat due to leg injury", "Injury update", {"client_id": 101})
    engine.run_consolidation_pass()
    
    facts = sem.get_facts_for_client(101)
    assert len(facts) == 2
    assert facts[0].status == "SUPERSEDED" and facts[1].status == "ACTIVE"
    print("   ✅ Conflict resolved: Fact v1 SUPERSEDED, Fact v2 ACTIVE.\n")

    # 4. Vector Store & All 4 Retrieval Architectures
    print("4️⃣ Testing Vector Store & All 4 RAG Architectures...")
    vdb = WanderpathVectorStore(collection_name="smoke_l2_db", persist_dir="./rag/chroma_l2_smoke")
    docs = ["Alpine Resort Zermatt: 14 days cancellation policy.", "Tokyo Grand Palace: Service animals welcome."]
    vdb.ingest_documents(docs, [{"country": "CH"}, {"country": "JP"}], ["d1", "d2"])

    n_rag = NaiveRAG(vdb)
    h_rag = HybridSearchRAG(vdb, docs)
    a_rag = AgenticRAG(h_rag)
    g_rag = GraphRAG()

    assert len(n_rag.retrieve("Zermatt", 1)) == 1
    assert len(h_rag.retrieve("14 days", 1)) == 1
    assert a_rag.retrieve_with_reasoning("Tokyo service animals")["steps_executed"] == 2
    assert g_rag.retrieve_subgraph_context("Tokyo Grand Palace")["found"] is True
    print("   ✅ Naive, Hybrid, Agentic, and Graph RAG all functional.\n")

    # 5. Self-RAG Verification
    print("5️⃣ Testing Self-RAG Verification Layer...")
    verifier = SelfRAGVerifier()
    v_res = verifier.verify_rag_pipeline("Cancellation Zermatt", [docs[0]], "14 days prior to check-in")
    assert v_res["passed"] is True
    print("   ✅ Self-RAG relevance and groundedness checks verified.\n")

    print("==================================================================")
    print("🎉 MASTER LAB 2 SMOKE TEST PASSED FLAWLESSLY!")
    print("==================================================================")


if __name__ == "__main__":
    run_master_lab2_smoke_test()