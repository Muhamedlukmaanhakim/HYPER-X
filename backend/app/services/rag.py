import re
import time
from typing import Any, Dict, List, Optional
from app.core.config import settings
from app.core.logging import logger
from app.core.security import is_api_key_configured
from app.schemas.schemas import AskResponse, RetrievedPassage
from app.services.embeddings import embed_query
from app.services.providers import get_llm_provider, is_llm_configured
from app.services.vectorstore import query_collection

ABSTENTION_SENTINEL = "INSUFFICIENT_EVIDENCE"

STRICT_GROUNDED_SYSTEM_PROMPT = """You are a strictly grounded AI Truth Inspector assistant.
Your job is to answer questions using ONLY the facts explicitly stated in the retrieved context below.

CRITICAL RULES:
1. If the retrieved context DOES NOT contain sufficient factual evidence to answer the question, you MUST reply with the exact sentinel word:
INSUFFICIENT_EVIDENCE
Do NOT guess, do NOT extrapolate, and do NOT use external knowledge.
2. If you can answer, cite your evidence using the Chunk ID and Page from the context header, e.g. [Page 2] or [sample_doc:2:0].
3. Be concise, direct, and factual. Never fabricate citations."""

def build_grounded_prompt(question: str, passages: List[Dict[str, Any]]) -> str:
    context_blocks = []
    for idx, p in enumerate(passages):
        chunk_id = p.get("chunk_id", f"chunk_{idx}")
        page = p.get("page", 1)
        score = p.get("score", 0.0)
        text = p.get("text", "").strip()
        context_blocks.append(
            f"--- PASSAGE {idx + 1} [ID: {chunk_id} | Page: {page} | Similarity: {score:.3f}] ---\n{text}"
        )

    context_str = "\n\n".join(context_blocks) if context_blocks else "[NO CONTEXT RETRIEVED]"
    return (
        f"RETRIEVED CONTEXT:\n{context_str}\n\n"
        f"USER QUESTION: {question}\n\n"
        "Provide your grounded answer citing specific chunk IDs/pages, or output INSUFFICIENT_EVIDENCE:"
    )

def extract_citations(text: str) -> List[str]:
    """
    Extracts citation tags such as [doc:1:0], [Page 2], [chunk_1] from text.
    """
    matches = re.findall(r"\[([a-zA-Z0-9_\-:]+)\]", text)
    # Deduplicate while preserving order
    seen = set()
    citations = []
    for m in matches:
        if m not in seen and m.upper() != "INSUFFICIENT_EVIDENCE":
            seen.add(m)
            citations.append(m)
    return citations

def ask_question(
    question: str,
    top_k: int = 3,
    similarity_threshold: float = 0.0,
    collection_name: str = "default_rag",
    provider_name: str = "anthropic",
    model_name: Optional[str] = None,
    custom_passages: Optional[List[Dict[str, Any]]] = None,
    demo_answer_fallback: Optional[str] = None,
    demo_citations_fallback: Optional[List[str]] = None
) -> AskResponse:
    """
    Full RAG generation pipeline:
    1. Embeds query (locally).
    2. Retrieves top-K passages from ChromaDB (or uses custom passages e.g. failure injection).
    3. Filters by similarity threshold.
    4. Generates grounded answer via LLMProvider (or uses labelled demo fallback if key missing).
    5. Detects abstention sentinel and extracts citations.
    """
    start_time = time.perf_counter()

    if custom_passages is not None:
        passages = custom_passages
    else:
        query_vec = embed_query(question)
        passages = query_collection(query_vec, top_k=top_k, collection_name=collection_name)
        if similarity_threshold > 0.0:
            passages = [p for p in passages if p.get("score", 0.0) >= similarity_threshold]

    prompt_used = build_grounded_prompt(question, passages)
    key_configured = is_llm_configured()

    # Demo mode handling
    if not key_configured:
        logger.info(f"Demo mode: No API key configured for {settings.LLM_PROVIDER}; returning illustrative demo response.")
        if demo_answer_fallback:
            answer = demo_answer_fallback
            citations = demo_citations_fallback or extract_citations(answer)
            abstained = (ABSTENTION_SENTINEL in answer.upper())
        else:
            # If passages empty or scores low, abstain cleanly
            if not passages:
                answer = ABSTENTION_SENTINEL
                citations = []
                abstained = True
            else:
                top_p = passages[0]
                answer = f"DEMO MODE: Evidence found on Page {top_p.get('page', 1)} [{top_p.get('chunk_id')}]: {top_p.get('text', '')[:200]}..."
                citations = [top_p.get("chunk_id", "")]
                abstained = False

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return AskResponse(
            question=question,
            answer=answer,
            citations=citations,
            abstained=abstained,
            retrieved_passages=[
                RetrievedPassage(
                    chunk_id=p.get("chunk_id", ""),
                    document_id=p.get("document_id", ""),
                    document_name=p.get("metadata", {}).get("document_name", "Document"),
                    page=p.get("page", 1),
                    score=p.get("score", 0.0),
                    text=p.get("text", "")
                )
                for p in passages
            ],
            prompt_used=prompt_used,
            provider="demo-mode",
            model="illustrative-pre-recorded",
            latency_ms=round(elapsed_ms, 2),
            is_demo=True
        )

    # Real Provider execution
    provider = get_llm_provider(model=model_name)
    response = provider.generate(
        prompt=prompt_used,
        system_prompt=STRICT_GROUNDED_SYSTEM_PROMPT,
        temperature=0.0
    )

    answer = response.text.strip()
    abstained = (ABSTENTION_SENTINEL in answer.upper())
    citations = extract_citations(answer)
    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

    return AskResponse(
        question=question,
        answer=answer,
        citations=citations,
        abstained=abstained,
        retrieved_passages=[
            RetrievedPassage(
                chunk_id=p.get("chunk_id", ""),
                document_id=p.get("document_id", ""),
                document_name=p.get("metadata", {}).get("document_name", "Document"),
                page=p.get("page", 1),
                score=p.get("score", 0.0),
                text=p.get("text", "")
            )
            for p in passages
        ],
        prompt_used=prompt_used,
        provider=response.provider,
        model=response.model,
        latency_ms=round(elapsed_ms, 2),
        is_demo=False
    )
