import sys
import pathlib

# Ensure root is in path
sys.path.append(str(pathlib.Path(__file__).parent.parent.resolve()))

from rag.vector_store import WanderpathVectorStore


def test_vector_store_and_metadata_filter():
    print("--- Testing Vector DB Architecture & Metadata Filtering ---")

    # 1. Initialize Vector Store
    vector_db = WanderpathVectorStore(collection_name="test_collection", persist_dir="./rag/test_chroma")

    # 2. Define Sample Chunks & Metadata Payloads
    chunks = [
        "Alpine Resort & Spa in Zermatt, Switzerland: Standard cancellation window is 14 days prior to check-in.",
        "Tokyo Grand Palace in Tokyo, Japan: Service dogs accommodated across all suite tiers. Transit strike advisory in effect.",
        "Bali Sun & Sand Resort in Bali, Indonesia: Peak season holiday packages are strictly non-refundable.",
    ]
    metadatas = [
        {"city": "Zermatt", "country": "Switzerland", "category": "Hotel Policy"},
        {"city": "Tokyo", "country": "Japan", "category": "Hotel Policy"},
        {"city": "Bali", "country": "Indonesia", "category": "Travel Advisory"},
    ]
    ids = ["doc_1", "doc_2", "doc_3"]

    print("\nIngesting document chunks into ChromaDB HNSW Index...")
    vector_db.ingest_documents(documents=chunks, metadatas=metadatas, ids=ids)
    print("✅ Ingestion complete.")

    # 3. Test Query WITHOUT Metadata Filter
    query = "What is the policy on service animals and transit strikes?"
    print(f"\nQuery 1 (Unfiltered): '{query}'")
    results_unfiltered = vector_db.similarity_search(query_text=query, n_results=2)
    
    print("Results:")
    for r in results_unfiltered:
        print(f"  [{r['id']}] {r['document']} (Metadata: {r['metadata']})")

    assert len(results_unfiltered) > 0

    # 4. Test Query WITH Metadata Pre-Filter (Targeting strictly Switzerland)
    print(f"\nQuery 2 (Pre-Filtered where country == 'Switzerland'): '{query}'")
    results_filtered = vector_db.similarity_search(
        query_text=query,
        n_results=2,
        metadata_filter={"country": "Switzerland"}
    )

    print("Filtered Results:")
    for r in results_filtered:
        print(f"  [{r['id']}] {r['document']} (Metadata: {r['metadata']})")

    # RUBRIC CHECKS
    assert len(results_filtered) == 1, "Metadata filter failed to restrict search scope!"
    assert results_filtered[0]["metadata"]["country"] == "Switzerland", "Returned record failed metadata condition!"

    print("\n✅ Vector DB Architecture & Metadata Pre-Filtering Test Passed Flawlessly!")


if __name__ == "__main__":
    test_vector_store_and_metadata_filter()