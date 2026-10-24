import pytest
from app.services.diagnosis import (
    CAT_CITATION_ERROR,
    CAT_INCOMPLETE_OR_IRRELEVANT,
    CAT_INCORRECT_DESPITE_CONTEXT,
    CAT_NEEDS_REVIEW,
    CAT_PASS,
    CAT_RETRIEVAL_MISS,
    CAT_UNANSWERABLE_ANSWERED,
    CAT_UNSUPPORTED_ANSWER,
    diagnose_case
)

def test_rule_1_missing_expected_evidence_gives_needs_review():
    res = diagnose_case(
        question="What is the encryption standard?",
        question_type="direct_factual",
        reference_answer="AES-256",
        generated_answer="AES-256",
        expected_evidence=[],  # Missing expected evidence!
        retrieved_chunks=[{"chunk_id": "c1", "text": "AES-256"}],
        abstained=False,
        should_abstain=False,
        citations=["c1"],
        metrics={"exact_match": 1.0, "recall": 1.0, "hit_rate": 1.0}
    )
    assert res.category == CAT_NEEDS_REVIEW
    assert "Rule 1" in res.rule_fired

def test_rule_2_unanswerable_answered_gives_unanswerable_answered():
    res = diagnose_case(
        question="What is the quantum processor cooling temp?",
        question_type="unanswerable",
        reference_answer="INSUFFICIENT_EVIDENCE",
        generated_answer="The temperature is minus 270 degrees Celsius.",
        expected_evidence=[],
        retrieved_chunks=[],
        abstained=False,  # Failed to abstain!
        should_abstain=True,
        citations=[],
        metrics={"exact_match": 0.0, "recall": 1.0, "hit_rate": 0.0}
    )
    assert res.category == CAT_UNANSWERABLE_ANSWERED
    assert "Rule 2" in res.rule_fired

def test_rule_3_retrieval_miss():
    res = diagnose_case(
        question="What is the rate limit?",
        question_type="numerical",
        reference_answer="120 req/min",
        generated_answer="INSUFFICIENT_EVIDENCE",
        expected_evidence=[{"chunk_id": "c_target"}],
        retrieved_chunks=[{"chunk_id": "c_distractor", "text": "Unrelated topic"}],
        abstained=True,
        should_abstain=False,
        citations=[],
        metrics={"recall": 0.0, "hit_rate": 0.0, "exact_match": 0.0}
    )
    assert res.category == CAT_RETRIEVAL_MISS
    assert "Rule 3" in res.rule_fired

def test_rule_4_incomplete_or_irrelevant_context():
    res = diagnose_case(
        question="What triggers failover and what regional quorum vote occurs?",
        question_type="multi_passage",
        reference_answer="3 timeouts trigger failover and Region B quorum vote requires 3 nodes.",
        generated_answer="Failover is triggered by timeouts.",
        expected_evidence=[{"chunk_id": "c1"}, {"chunk_id": "c2"}],
        retrieved_chunks=[{"chunk_id": "c1", "text": "Timeouts trigger failover."}],
        abstained=False,
        should_abstain=False,
        citations=["c1"],
        metrics={"recall": 0.5, "hit_rate": 1.0, "exact_match": 0.0, "normalized_match": 0.4}
    )
    assert res.category == CAT_INCOMPLETE_OR_IRRELEVANT
    assert "Rule 4" in res.rule_fired

def test_rule_5_unsupported_answer():
    res = diagnose_case(
        question="What is the audit log retention?",
        question_type="direct_factual",
        reference_answer="90 days",
        generated_answer="Audit logs are permanently archived in deep oceanic vaults forever.",
        expected_evidence=[{"chunk_id": "c1"}],
        retrieved_chunks=[{"chunk_id": "c1", "text": "Audit logs are retained for 90 days."}],
        abstained=False,
        should_abstain=False,
        citations=["c1"],
        metrics={
            "recall": 1.0,
            "hit_rate": 1.0,
            "exact_match": 0.0,
            "normalized_match": 0.0,
            "judge_faithfulness": 0.1  # Low faithfulness
        }
    )
    assert res.category == CAT_UNSUPPORTED_ANSWER
    assert "Rule 5" in res.rule_fired

def test_rule_6_incorrect_despite_relevant_context():
    res = diagnose_case(
        question="How many primary GPU nodes are in production?",
        question_type="numerical",
        reference_answer="64 primary nodes",
        generated_answer="There are 32 primary nodes.",
        expected_evidence=[{"chunk_id": "c1"}],
        retrieved_chunks=[{"chunk_id": "c1", "text": "The production inference fleet comprises 64 primary nodes."}],
        abstained=False,
        should_abstain=False,
        citations=["c1"],
        metrics={
            "recall": 1.0,
            "hit_rate": 1.0,
            "exact_match": 0.0,
            "numeric_match": 0.0,
            "judge_faithfulness": 0.9  # Faithful to context structure, but synthesized wrong number
        }
    )
    assert res.category == CAT_INCORRECT_DESPITE_CONTEXT
    assert "Rule 6" in res.rule_fired

def test_rule_7_citation_error():
    res = diagnose_case(
        question="What encryption is used?",
        question_type="direct_factual",
        reference_answer="AES-256-GCM",
        generated_answer="AES-256-GCM is used.",  # Correct answer, but citations missing!
        expected_evidence=[{"chunk_id": "c1"}],
        retrieved_chunks=[{"chunk_id": "c1", "text": "Customer data is secured using AES-256-GCM."}],
        abstained=False,
        should_abstain=False,
        citations=[],  # Missing citations!
        metrics={"recall": 1.0, "hit_rate": 1.0, "exact_match": 1.0}
    )
    assert res.category == CAT_CITATION_ERROR
    assert "Rule 7" in res.rule_fired

def test_pass_case():
    res = diagnose_case(
        question="What encryption is used?",
        question_type="direct_factual",
        reference_answer="AES-256-GCM",
        generated_answer="AES-256-GCM is used [c1].",
        expected_evidence=[{"chunk_id": "c1"}],
        retrieved_chunks=[{"chunk_id": "c1", "text": "Customer data is secured using AES-256-GCM."}],
        abstained=False,
        should_abstain=False,
        citations=["c1"],
        metrics={"recall": 1.0, "hit_rate": 1.0, "exact_match": 1.0, "citation_correctness": 1.0}
    )
    assert res.category == CAT_PASS
