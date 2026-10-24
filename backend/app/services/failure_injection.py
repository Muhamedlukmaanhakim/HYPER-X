import copy
import random
from typing import Any, Dict, List, Optional
from app.core.logging import logger
from app.schemas.schemas import FailureInjectionConfig
from app.services.metrics import is_chunk_matching_evidence

def apply_failure_injection(
    retrieved_passages: List[Dict[str, Any]],
    expected_evidence: List[Dict[str, Any]],
    all_available_chunks: List[Dict[str, Any]],
    injection_config: Optional[FailureInjectionConfig]
) -> List[Dict[str, Any]]:
    """
    Simulates retrieval-time failures for evaluation runs.
    IMPORTANT: This ONLY modifies the in-memory candidate list for the current test case.
    The real ChromaDB vector store index is NEVER touched or modified.
    """
    if not injection_config or not injection_config.enabled:
        return retrieved_passages

    # Deep copy to ensure zero side-effects
    passages = copy.deepcopy(retrieved_passages)

    # 1. Remove a relevant chunk from retrieval results
    if injection_config.remove_relevant_chunk and expected_evidence:
        # Find which passages match expected evidence
        matched_indices = [
            idx for idx, p in enumerate(passages)
            if any(is_chunk_matching_evidence(p, ev) for ev in expected_evidence)
        ]
        if matched_indices:
            remove_idx = matched_indices[0]
            logger.info(f"[SIMULATION] Removing relevant chunk '{passages[remove_idx].get('chunk_id')}' from retrieval")
            passages.pop(remove_idx)

    # 2. Inject distractor passages (from other documents or sections)
    if injection_config.inject_distractors:
        num_distractors = injection_config.num_distractors or 2
        # Gather candidate distractors that do not contain expected evidence
        distractor_pool = [
            c for c in all_available_chunks
            if not any(is_chunk_matching_evidence(c, ev) for ev in expected_evidence)
            and c.get("chunk_id") not in {p.get("chunk_id") for p in passages}
        ]

        if not distractor_pool and all_available_chunks:
            # Synthetic fallback distractor if single doc
            distractor_pool = [
                {
                    "chunk_id": "simulated_distractor_999",
                    "document_id": "sim_doc",
                    "page": 99,
                    "score": 0.45,
                    "text": "The corporate cafeteria is closed on alternate Thursdays for deep maintenance of espresso machines.",
                    "metadata": {"document_name": "Facilities Guide"}
                }
            ]

        chosen = distractor_pool[:num_distractors]
        for dist in chosen:
            # Set high score to simulate noise ranking high
            dist_copy = copy.deepcopy(dist)
            dist_copy["score"] = 0.88
            passages.insert(0, dist_copy)
            logger.info(f"[SIMULATION] Injected distractor chunk '{dist_copy.get('chunk_id')}'")

    # 3. Reduce top-K
    if injection_config.reduce_top_k is not None and injection_config.reduce_top_k > 0:
        passages = passages[:injection_config.reduce_top_k]
        logger.info(f"[SIMULATION] Truncated top-K to {injection_config.reduce_top_k}")

    # 4. Truncate context characters
    if injection_config.truncate_context_chars is not None and injection_config.truncate_context_chars > 0:
        max_chars = injection_config.truncate_context_chars
        for p in passages:
            if len(p.get("text", "")) > max_chars:
                p["text"] = p["text"][:max_chars] + "... [TRUNCATED_BY_SIMULATION]"
        logger.info(f"[SIMULATION] Truncated context passages to {max_chars} chars")

    return passages
