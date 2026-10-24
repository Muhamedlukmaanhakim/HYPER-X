import pytest
from app.services.metrics import (
    compute_abstention_correctness,
    compute_citation_correctness,
    compute_exact_match,
    compute_hit_rate_at_k,
    compute_mrr,
    compute_normalized_match,
    compute_numeric_match,
    compute_retrieval_recall_at_k,
    is_chunk_matching_evidence
)

def test_recall_at_k_hand_computed_fixture():
    # 2 expected evidence items
    expected = [
        {"chunk_id": "doc:1:0"},
        {"chunk_id": "doc:1:2"}
    ]
    # Retrieved 4 chunks in order:
    retrieved = [
        {"chunk_id": "doc:1:0", "page": 1, "text": "evidence 1"},  # Matches item 1
        {"chunk_id": "doc:1:1", "page": 1, "text": "distractor"},
        {"chunk_id": "doc:1:2", "page": 1, "text": "evidence 2"},  # Matches item 2
        {"chunk_id": "doc:2:0", "page": 2, "text": "distractor 2"}
    ]

    # Recall@1: 1 out of 2 -> 0.5
    assert compute_retrieval_recall_at_k(retrieved, expected, k=1) == 0.5
    # Recall@2: still 1 out of 2 -> 0.5
    assert compute_retrieval_recall_at_k(retrieved, expected, k=2) == 0.5
    # Recall@3: 2 out of 2 -> 1.0
    assert compute_retrieval_recall_at_k(retrieved, expected, k=3) == 1.0
    # Recall@5: 2 out of 2 -> 1.0
    assert compute_retrieval_recall_at_k(retrieved, expected, k=5) == 1.0

def test_hit_rate_at_k_and_mrr():
    expected = [{"chunk_id": "target_chunk"}]
    
    # Case A: target chunk at rank 1
    retrieved_a = [{"chunk_id": "target_chunk"}]
    assert compute_hit_rate_at_k(retrieved_a, expected, k=1) == 1.0
    assert compute_mrr(retrieved_a, expected) == 1.0

    # Case B: target chunk at rank 2
    retrieved_b = [{"chunk_id": "distractor"}, {"chunk_id": "target_chunk"}]
    assert compute_hit_rate_at_k(retrieved_b, expected, k=1) == 0.0
    assert compute_hit_rate_at_k(retrieved_b, expected, k=2) == 1.0
    assert compute_mrr(retrieved_b, expected) == 0.5

    # Case C: target chunk not retrieved
    retrieved_c = [{"chunk_id": "distractor_1"}, {"chunk_id": "distractor_2"}]
    assert compute_hit_rate_at_k(retrieved_c, expected, k=2) == 0.0
    assert compute_mrr(retrieved_c, expected) == 0.0

def test_evidence_mapping_across_chunkings():
    # Demonstrates mapping when chunking splits differently across configurations
    evidence_spec = {
        "page": 2,
        "text_span": "Standard API consumers are strictly capped at 120 requests per minute"
    }

    # Configuration A chunk (exact span)
    chunk_a = {
        "chunk_id": "cfgA:2:0",
        "page": 2,
        "text": "Standard API consumers are strictly capped at 120 requests per minute with burst allowance."
    }
    assert is_chunk_matching_evidence(chunk_a, evidence_spec) is True

    # Configuration B chunk (smaller chunk size; includes substantial token overlap)
    chunk_b = {
        "chunk_id": "cfgB:2:1",
        "page": 2,
        "text": "API consumers are strictly capped at 120 requests per minute."
    }
    assert is_chunk_matching_evidence(chunk_b, evidence_spec) is True

    # Different page should fail
    chunk_wrong_page = {
        "chunk_id": "cfgA:1:0",
        "page": 1,
        "text": "Standard API consumers are strictly capped at 120 requests per minute."
    }
    assert is_chunk_matching_evidence(chunk_wrong_page, evidence_spec) is False

def test_match_metrics():
    # Exact Match
    assert compute_exact_match("The answer is 42.", "the answer is 42") == 1.0
    assert compute_exact_match("Answer is 43.", "Answer is 42.") == 0.0

    # Normalized Match (F1)
    f1 = compute_normalized_match("Acme Corp encrypts data with AES-256.", "Data is encrypted with AES-256 by Acme Corp.")
    assert f1 > 0.70

    # Numeric Match
    assert compute_numeric_match("The rate limit is 120 req/min with 180 burst.", "120 requests and 180 burst") == 1.0
    assert compute_numeric_match("Rate limit is 500 req/min.", "120 requests") == 0.0

def test_citation_and_abstention_correctness():
    expected = [{"chunk_id": "doc:1:0", "page": 1}]
    retrieved = [{"chunk_id": "doc:1:0", "page": 1, "text": "evidence"}]

    # Citation correctness
    assert compute_citation_correctness(["doc:1:0"], expected, retrieved) == 1.0
    assert compute_citation_correctness(["Page 1"], expected, retrieved) == 1.0
    assert compute_citation_correctness(["doc:99:99"], expected, retrieved) == 0.0

    # Abstention correctness
    assert compute_abstention_correctness(should_abstain=True, abstained=True) == 1.0
    assert compute_abstention_correctness(should_abstain=True, abstained=False) == 0.0
    assert compute_abstention_correctness(should_abstain=False, abstained=False) == 1.0
    assert compute_abstention_correctness(should_abstain=False, abstained=True) == 0.0
