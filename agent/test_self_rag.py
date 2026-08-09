import sys
import pathlib

# Ensure root is in path
sys.path.append(str(pathlib.Path(__file__).parent.parent.resolve()))

from rag.self_rag import SelfRAGVerifier


def test_self_rag_verification():
    print("--- Testing Self-RAG Verification Engine (Relevance & Support Checks) ---")

    verifier = SelfRAGVerifier()

    # TEST 1: Valid Grounded Answer (Should Pass)
    print("\n1️⃣ Scenario 1: Valid Query, Relevant Context, Grounded Answer")
    q1 = "What is the cancellation window for Alpine Resort in Zermatt?"
    ctx1 = ["Alpine Resort & Spa (Zermatt): Standard cancellation window is 14 days prior to check-in."]
    ans1 = "The cancellation window for Alpine Resort in Zermatt is 14 days prior to check-in."

    res1 = verifier.verify_rag_pipeline(q1, ctx1, ans1)
    print(f"   Result: {res1}")
    assert res1["passed"] is True, "Valid grounded pipeline failed verification!"

    # TEST 2: Irrelevant Context (Should Fail Relevance Check)
    print("\n2️⃣ Scenario 2: Relevant Query, Irrelevant Context Returned")
    q2 = "What is the passport expiration rule for Bali?"
    ctx2 = ["Tokyo Grand Palace accommodates service animals across all suite tiers."]
    ans2 = "Passports require 6 months validity."

    res2 = verifier.verify_rag_pipeline(q2, ctx2, ans2)
    print(f"   Result: {res2}")
    assert res2["passed"] is False
    assert res2["stage_failed"] == "RETRIEVAL_RELEVANCE", "Failed to catch irrelevant context!"

    # TEST 3: Hallucinated / Unsupported Answer (Should Fail Groundedness Check)
    print("\n3️⃣ Scenario 3: Relevant Context, but Hallucinated Answer")
    q3 = "What is the pet policy for Tokyo Grand Palace?"
    ctx3 = ["Tokyo Grand Palace in Tokyo, Japan: Service animals accommodated across all suite tiers."]
    ans3 = "Tokyo Grand Palace charges a mandatory $500 cash deposit for all animals and prohibits dogs."

    res3 = verifier.verify_rag_pipeline(q3, ctx3, ans3)
    print(f"   Result: {res3}")
    assert res3["passed"] is False
    assert res3["stage_failed"] == "ANSWER_GROUNDEDNESS", "Failed to catch hallucinated answer!"

    print("\n✅ Self-RAG Verification Test Passed Flawlessly!")


if __name__ == "__main__":
    test_self_rag_verification()