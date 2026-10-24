import copy
import pytest
from app.schemas.schemas import FailureInjectionConfig
from app.services.failure_injection import apply_failure_injection

def test_failure_injection_removes_relevant_chunk():
    original_passages = [
        {"chunk_id": "c1", "page": 1, "text": "target relevant evidence", "score": 0.95},
        {"chunk_id": "c2", "page": 1, "text": "second distractor", "score": 0.60}
    ]
    expected_evidence = [{"chunk_id": "c1"}]

    config = FailureInjectionConfig(
        enabled=True,
        remove_relevant_chunk=True
    )

    passages_before = copy.deepcopy(original_passages)
    injected = apply_failure_injection(
        retrieved_passages=original_passages,
        expected_evidence=expected_evidence,
        all_available_chunks=[],
        injection_config=config
    )

    # Injected result should have removed c1
    assert len(injected) == 1
    assert injected[0]["chunk_id"] == "c2"
    # Proves the original list / source structures are untouched
    assert original_passages == passages_before

def test_failure_injection_injects_distractors():
    passages = [{"chunk_id": "c1", "page": 1, "text": "evidence", "score": 0.9}]
    expected_ev = [{"chunk_id": "c1"}]
    all_chunks = [
        {"chunk_id": "d1", "page": 5, "text": "noise 1", "score": 0.1},
        {"chunk_id": "d2", "page": 6, "text": "noise 2", "score": 0.1}
    ]

    config = FailureInjectionConfig(
        enabled=True,
        inject_distractors=True,
        num_distractors=2
    )

    injected = apply_failure_injection(
        retrieved_passages=passages,
        expected_evidence=expected_ev,
        all_available_chunks=all_chunks,
        injection_config=config
    )

    assert len(injected) == 3
    # Distractors should be inserted at front with high score
    assert injected[0]["chunk_id"] in ["d1", "d2"]

def test_failure_injection_disabled_does_nothing():
    passages = [{"chunk_id": "c1", "score": 0.9}]
    config = FailureInjectionConfig(enabled=False, remove_relevant_chunk=True)
    res = apply_failure_injection(passages, [{"chunk_id": "c1"}], [], config)
    assert len(res) == 1
    assert res[0]["chunk_id"] == "c1"
