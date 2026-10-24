import re
import string
from typing import Any, Dict, List, Optional, Set, Tuple

def normalize_text(text: str) -> str:
    """Lowercases text, removes punctuation, articles, and excess whitespace."""
    if not text:
        return ""
    text = text.lower()
    # Remove punctuation
    text = "".join(ch for ch in text if ch not in string.punctuation)
    # Remove articles
    text = re.sub(r"\b(a|an|the)\b", " ", text)
    # Normalize whitespace
    return " ".join(text.split())

def extract_numbers(text: str) -> List[float]:
    """Extracts all integers and floating point numbers from text."""
    clean = text.replace(",", "")
    matches = re.findall(r"[-+]?(?:\d*\.\d+|\d+)", clean)
    numbers = []
    for m in matches:
        try:
            numbers.append(float(m))
        except ValueError:
            pass
    return numbers

def is_chunk_matching_evidence(
    chunk: Dict[str, Any],
    evidence_item: Dict[str, Any],
    min_overlap_ratio: float = 0.50
) -> bool:
    """
    Evidence mapping rule:
    Determines whether a retrieved chunk matches an expected evidence specification.
    Supports both direct chunk ID matching AND cross-chunking page + text span overlap.
    """
    chunk_id = chunk.get("chunk_id", "")
    chunk_page = chunk.get("page")
    chunk_text = chunk.get("text", "")

    # Direct chunk ID match
    target_id = evidence_item.get("chunk_id")
    if target_id and target_id == chunk_id:
        return True

    # Page + Text Span Overlap Match (for cross-chunking comparison)
    target_page = evidence_item.get("page")
    target_span = evidence_item.get("text_span")

    if target_page is not None and chunk_page is not None:
        if int(target_page) != int(chunk_page):
            return False

    if target_span:
        norm_span = normalize_text(target_span)
        norm_chunk = normalize_text(chunk_text)
        
        if not norm_span or not norm_chunk:
            return False

        # Substring check
        if norm_span in norm_chunk or norm_chunk in norm_span:
            return True

        # Token set overlap ratio
        span_tokens = set(norm_span.split())
        chunk_tokens = set(norm_chunk.split())
        if not span_tokens:
            return False
            
        intersection = span_tokens.intersection(chunk_tokens)
        overlap_ratio = len(intersection) / len(span_tokens)
        if overlap_ratio >= min_overlap_ratio:
            return True

    return False

def compute_retrieval_recall_at_k(
    retrieved_chunks: List[Dict[str, Any]],
    expected_evidence: List[Dict[str, Any]],
    k: int
) -> float:
    """
    Recall@K: fraction of expected evidence items matched within the top-K retrieved chunks.
    If expected evidence is empty (e.g. unanswerable), returns 1.0 if k>=1 else 0.0.
    """
    if not expected_evidence:
        return 1.0

    top_k_chunks = retrieved_chunks[:k]
    if not top_k_chunks:
        return 0.0

    matched_evidence_count = 0
    for ev in expected_evidence:
        if any(is_chunk_matching_evidence(chunk, ev) for chunk in top_k_chunks):
            matched_evidence_count += 1

    return round(matched_evidence_count / len(expected_evidence), 4)

def compute_hit_rate_at_k(
    retrieved_chunks: List[Dict[str, Any]],
    expected_evidence: List[Dict[str, Any]],
    k: int
) -> float:
    """Hit Rate@K: 1.0 if at least one expected evidence piece appears in top-K; else 0.0."""
    if not expected_evidence:
        return 1.0
    recall = compute_retrieval_recall_at_k(retrieved_chunks, expected_evidence, k)
    return 1.0 if recall > 0.0 else 0.0

def compute_mrr(
    retrieved_chunks: List[Dict[str, Any]],
    expected_evidence: List[Dict[str, Any]]
) -> float:
    """
    Mean Reciprocal Rank: Reciprocal of the 1-indexed rank of the FIRST relevant chunk.
    Returns 0.0 if no relevant chunk found.
    """
    if not expected_evidence:
        return 1.0

    for idx, chunk in enumerate(retrieved_chunks):
        if any(is_chunk_matching_evidence(chunk, ev) for ev in expected_evidence):
            return round(1.0 / (idx + 1), 4)
    return 0.0

def compute_exact_match(prediction: str, reference: str) -> float:
    norm_p = normalize_text(prediction)
    norm_r = normalize_text(reference)
    return 1.0 if norm_p == norm_r else 0.0

def compute_normalized_match(prediction: str, reference: str) -> float:
    """Computes Token F1 score between prediction and reference answer."""
    p_tokens = normalize_text(prediction).split()
    r_tokens = normalize_text(reference).split()

    if not p_tokens or not r_tokens:
        return 1.0 if p_tokens == r_tokens else 0.0

    common = set(p_tokens) & set(r_tokens)
    if not common:
        return 0.0

    precision = len(common) / len(p_tokens)
    recall = len(common) / len(r_tokens)
    f1 = 2 * (precision * recall) / (precision + recall)
    return round(f1, 4)

def compute_numeric_match(prediction: str, reference: str, tolerance: float = 0.01) -> Optional[float]:
    """
    For numerical questions: checks if numbers in reference appear in prediction within tolerance.
    """
    ref_nums = extract_numbers(reference)
    if not ref_nums:
        return None

    pred_nums = extract_numbers(prediction)
    if not pred_nums:
        return 0.0

    # Every reference number should have a matching number in prediction
    for r in ref_nums:
        matched = False
        for p in pred_nums:
            diff = abs(p - r)
            rel_diff = diff / max(abs(r), 1e-9)
            if diff <= 1e-5 or rel_diff <= tolerance:
                matched = True
                break
        if not matched:
            return 0.0

    return 1.0

def compute_citation_correctness(
    citations: List[str],
    expected_evidence: List[Dict[str, Any]],
    retrieved_chunks: List[Dict[str, Any]]
) -> Optional[float]:
    """
    Citation correctness: fraction of generated citations that match expected evidence
    or actually point to retrieved chunks containing the evidence.
    """
    if not citations:
        return None

    correct_count = 0
    for cit in citations:
        # Check if citation is a page citation e.g. "Page 2" or "2"
        page_match = re.search(r"\d+", cit)
        cit_page = int(page_match.group(0)) if page_match else None

        matched = False
        # Check against expected evidence
        for ev in expected_evidence:
            if ev.get("chunk_id") == cit:
                matched = True
                break
            if cit_page and ev.get("page") == cit_page:
                matched = True
                break

        # Check against retrieved chunks
        if not matched:
            for rc in retrieved_chunks:
                if rc.get("chunk_id") == cit or (cit_page and rc.get("page") == cit_page):
                    # If cited chunk contains expected evidence
                    if any(is_chunk_matching_evidence(rc, ev) for ev in expected_evidence):
                        matched = True
                        break

        if matched:
            correct_count += 1

    return round(correct_count / len(citations), 4)

def compute_abstention_correctness(should_abstain: bool, abstained: bool) -> float:
    """1.0 if correctly abstained (or correctly answered), 0.0 if failed."""
    if should_abstain:
        return 1.0 if abstained else 0.0
    else:
        return 0.0 if abstained else 1.0
