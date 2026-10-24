from typing import List
from app.services.ingestion import ExtractedPage

class ChunkItem:
    def __init__(
        self,
        id: str,
        document_id: str,
        page: int,
        chunk_index: int,
        char_start: int,
        char_end: int,
        text: str,
        char_count: int,
        token_count_estimate: int,
        filename: str = ""
    ):
        self.id = id
        self.document_id = document_id
        self.page = page
        self.chunk_index = chunk_index
        self.char_start = char_start
        self.char_end = char_end
        self.text = text
        self.char_count = char_count
        self.token_count_estimate = token_count_estimate
        self.filename = filename

    def to_dict(self):
        return {
            "id": self.id,
            "document_id": self.document_id,
            "filename": self.filename,
            "page": self.page,
            "chunk_index": self.chunk_index,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "text": self.text,
            "char_count": self.char_count,
            "token_count_estimate": self.token_count_estimate,
        }

def chunk_pages(
    pages: List[ExtractedPage],
    document_id: str,
    chunk_size: int = 800,
    chunk_overlap: int = 150,
    filename: str = ""
) -> List[ChunkItem]:

    """
    Chunks document pages into discrete text segments with stable IDs: {doc_id}:{page}:{index}.
    Respects page boundaries and char offsets.
    """
    if chunk_size <= 50:
        chunk_size = 50
    if chunk_overlap >= chunk_size:
        chunk_overlap = max(0, chunk_size // 4)

    all_chunks: List[ChunkItem] = []

    for page_item in pages:
        page_text = page_item.text.strip()
        page_num = page_item.page_number

        if not page_text:
            continue

        step = chunk_size - chunk_overlap
        pos = 0
        chunk_idx = 0
        text_len = len(page_text)

        while pos < text_len:
            end_pos = min(pos + chunk_size, text_len)
            
            # If not at the very end of page, try to break on a sentence or newline or whitespace
            if end_pos < text_len:
                boundary = _find_natural_break(page_text, pos, end_pos, min_search_ratio=0.7)
                if boundary > pos:
                    end_pos = boundary

            segment = page_text[pos:end_pos].strip()
            if segment:
                chunk_id = f"{document_id}:{page_num}:{chunk_idx}"
                token_estimate = max(1, len(segment) // 4)
                all_chunks.append(
                    ChunkItem(
                        id=chunk_id,
                        document_id=document_id,
                        page=page_num,
                        chunk_index=chunk_idx,
                        char_start=pos,
                        char_end=pos + len(segment),
                        text=segment,
                        char_count=len(segment),
                        token_count_estimate=token_estimate,
                        filename=filename
                    )
                )
                chunk_idx += 1

            if end_pos >= text_len:
                break

            pos += step
            # Ensure forward progress
            if pos <= (all_chunks[-1].char_start if all_chunks else 0):
                pos = end_pos

    return all_chunks

def _find_natural_break(text: str, start: int, target_end: int, min_search_ratio: float = 0.7) -> int:
    min_search = start + int((target_end - start) * min_search_ratio)
    # Search backwards from target_end to min_search for paragraph break
    for sep in ["\n\n", "\n", ". ", "? ", "! ", "; ", " "]:
        idx = text.rfind(sep, min_search, target_end)
        if idx != -1:
            return idx + len(sep)
    return target_end
