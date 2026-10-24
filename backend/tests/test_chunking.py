import pytest
from app.services.chunking import chunk_pages
from app.services.ingestion import ExtractedPage

def test_chunk_pages_preserves_page_numbers_and_stable_ids():
    pages = [
        ExtractedPage(page_number=1, text="This is page one text containing policy facts."),
        ExtractedPage(page_number=2, text="This is page two text with rate limits and numbers 120."),
    ]
    chunks = chunk_pages(pages, document_id="doc_test", chunk_size=200, chunk_overlap=30)
    
    assert len(chunks) >= 2
    assert chunks[0].id == "doc_test:1:0"
    assert chunks[0].page == 1
    assert "page one" in chunks[0].text
    
    # Check page 2 chunk
    p2_chunks = [c for c in chunks if c.page == 2]
    assert len(p2_chunks) >= 1
    assert p2_chunks[0].id == "doc_test:2:0"
    assert "page two" in p2_chunks[0].text

def test_chunking_overlap():
    long_text = "Sentence one. " * 30  # ~420 chars
    pages = [ExtractedPage(page_number=1, text=long_text)]
    
    chunk_size = 150
    chunk_overlap = 50
    chunks = chunk_pages(pages, document_id="doc_overlap", chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    
    assert len(chunks) > 1
    # Check that adjacent chunks share text
    c0 = chunks[0].text
    c1 = chunks[1].text
    # Common overlap substring
    assert any(c0[i:i+20] in c1 for i in range(len(c0) - 20))

def test_chunking_token_and_char_estimates():
    pages = [ExtractedPage(page_number=1, text="Short test string.")]
    chunks = chunk_pages(pages, document_id="doc_est", chunk_size=100, chunk_overlap=20)
    assert len(chunks) == 1
    assert chunks[0].char_count == len("Short test string.")
    assert chunks[0].token_count_estimate >= 1
