import sys
import pathlib

# Ensure root is in path
sys.path.append(str(pathlib.Path(__file__).parent.parent.resolve()))

from rag.vector_store import WanderpathVectorStore
from rag.architectures.retrievers import NaiveRAG, HybridSearchRAG, AgenticRAG, GraphRAG


def test_all_four_retrieval_architectures():
    print("==================================================================")
    print("🚀 TESTING ALL 4 RETRIEVAL ARCHITECTURES (INCLUDING GRAPH RAG BONUS)")
    print("==================================================================\n")

    # 1. Setup Vector Store & Corpus
    vector_db = WanderpathVectorStore(collection_name="rag_all_4_test", persist_dir="./rag/test_chroma_all4")

    documents = [
        "Alpine Resort & Spa (Zermatt, Switzerland): Standard cancellation window is 14 days prior to check-in. Pre-spa fasting is 2 hours.",
        "Tokyo Grand Palace (Tokyo, Japan): Service animals accommodated. Transit strike on Yamanote line scheduled for late 2026.",
        "Bali Sun & Sand Resort (Bali, Indonesia): Peak season packages in December are strictly non-refundable. Visa on Arrival required.",
    ]
    metadatas = [{"country": "Switzerland"}, {"country": "Japan"}, {"country": "Indonesia"}]
    ids = ["doc_1", "doc_2", "doc_3"]

    vector_db.ingest_documents(documents=documents, metadatas=metadatas, ids=ids)

    # ------------------------------------------------------------------------
    # ARCHITECTURE 1: Naive RAG
    # ------------------------------------------------------------------------
    print("1️⃣ Testing Naive RAG (Dense Vector Similarity)...")
    naive_rag = NaiveRAG(vector_db)
    q1 = "What is the cancellation window in Zermatt?"
    res1 = naive_rag.retrieve(q1, top_k=1)
    print(f"   Query: '{q1}'")
    print(f"   Result: {res1[0]['document']}\n")
    assert len(res1) > 0

    # ------------------------------------------------------------------------
    # ARCHITECTURE 2: Hybrid Search (Vector + BM25)
    # ------------------------------------------------------------------------
    print("2️⃣ Testing Hybrid Search (Vector + BM25 Keyword Scoring)...")
    hybrid_rag = HybridSearchRAG(vector_db, documents)
    q2 = "14 days cancellation policy fasting window"
    res2 = hybrid_rag.retrieve(q2, top_k=1)
    print(f"   Query: '{q2}'")
    print(f"   Result (RRF Score {res2[0]['rrf_score']:.4f}): {res2[0]['document']}\n")
    assert len(res2) > 0

    # ------------------------------------------------------------------------
    # ARCHITECTURE 3: Agentic RAG
    # ------------------------------------------------------------------------
    print("3️⃣ Testing Agentic RAG (Multi-Step Reasoning Loop)...")
    agentic_rag = AgenticRAG(hybrid_rag)
    q3 = "Tokyo Grand Palace service animals and transit strikes"
    res3 = agentic_rag.retrieve_with_reasoning(q3)
    print(f"   Query: '{q3}'")
    print(f"   Multi-Hop Steps: {res3['steps_executed']} | Chunks Retained: {len(res3['final_context'])}\n")
    assert res3["steps_executed"] == 2

    # ------------------------------------------------------------------------
    # ARCHITECTURE 4: Graph RAG (BONUS)
    # ------------------------------------------------------------------------
    print("4️⃣ Testing Graph RAG (Knowledge Graph Entity & Relationship Traversal)...")
    graph_rag = GraphRAG()
    target_entity = "Tokyo Grand Palace"
    graph_res = graph_rag.retrieve_subgraph_context(target_entity, max_depth=2)

    print(f"   Root Entity Target: '{target_entity}'")
    print(f"   Entities Connected in 2-Hop Graph Traversal: {graph_res['connected_entities']}")
    print("   Graph Relational Triples:")
    for triple in graph_res["graph_triples"]:
        print(f"     • {triple}")

    assert graph_res["found"] is True
    assert len(graph_res["graph_triples"]) >= 2

    print("\n==================================================================")
    print("🎉 ALL 4 RETRIEVAL ARCHITECTURES VERIFIED SUCCESSFULLY!")
    print("==================================================================")


if __name__ == "__main__":
    test_all_four_retrieval_architectures()