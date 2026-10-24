import os
import shutil
import uuid
from typing import List
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.errors import AppError
from app.core.logging import logger
from app.models.database import get_db
from app.models.models import Chunk, Configuration, Document
from app.schemas.schemas import ChunkResponse, DocumentDetailResponse, DocumentResponse
from app.services.chunking import chunk_pages
from app.services.embeddings import embed_texts
from app.services.ingestion import extract_text_from_file
from app.services.vectorstore import delete_document_from_chroma, upsert_chunks

router = APIRouter(prefix="/api/documents", tags=["documents"])

@router.get("", response_model=List[DocumentResponse])
def list_documents(db: Session = Depends(get_db)):
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    return docs

@router.get("/{document_id}", response_model=DocumentDetailResponse)
def get_document(document_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    chunks = db.query(Chunk).filter(Chunk.document_id == document_id).order_by(Chunk.chunk_index).all()
    res = DocumentDetailResponse.model_validate(doc)
    res.chunks = [ChunkResponse.model_validate(c) for c in chunks]
    return res

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    chunk_size: int = Form(800),
    chunk_overlap: int = Form(150),
    db: Session = Depends(get_db)
):
    original_name = file.filename or "unknown"
    _, ext = os.path.splitext(original_name)
    ext_clean = ext.lower().lstrip(".")
    if ext_clean not in ["pdf", "docx", "txt", "md", "csv"]:
        raise AppError("INVALID_EXTENSION", f"Unsupported file type: {ext_clean}. Supported: PDF, DOCX, TXT.", status_code=400)

    # Check for existing document with same original_name to prevent duplicate chunk ingestion
    existing_doc = db.query(Document).filter(Document.original_name == original_name).first()

    doc_id = f"doc_{uuid.uuid4().hex[:10]}"
    saved_filename = f"{doc_id}_{original_name}"
    saved_path = os.path.join(settings.UPLOAD_DIR, saved_filename)

    with open(saved_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = os.path.getsize(saved_path)
    if file_size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        os.remove(saved_path)
        raise AppError("FILE_TOO_LARGE", f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB} MB", status_code=413)

    if existing_doc:
        # If identical and already successfully indexed, avoid duplicate chunk ingestion
        if existing_doc.status == "indexed" and existing_doc.file_size_bytes == file_size:
            if os.path.exists(saved_path) and saved_filename != existing_doc.filename:
                try:
                    os.remove(saved_path)
                except Exception:
                    pass
            logger.info(f"Document '{original_name}' already indexed (id={existing_doc.id}). Skipping duplicate ingestion.")
            return existing_doc
        else:
            # Re-uploading an updated or errored document: clean up previous vector embeddings and record
            logger.info(f"Replacing previous version of document '{original_name}' (id={existing_doc.id}).")
            delete_document_from_chroma(existing_doc.id, collection_name="default_rag")
            db.delete(existing_doc)
            db.commit()

    # Ingest and extract text
    extraction = extract_text_from_file(saved_path, max_size_mb=settings.MAX_UPLOAD_SIZE_MB)
    
    # Chunk text
    chunk_items = chunk_pages(
        pages=extraction.pages,
        document_id=doc_id,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        filename=original_name
    )

    # Create Document record
    doc_record = Document(
        id=doc_id,
        filename=saved_filename,
        original_name=original_name,
        file_type=ext_clean,
        file_size_bytes=file_size,
        page_count=extraction.page_count,
        chunk_count=len(chunk_items),
        char_count=extraction.total_char_count,
        is_sample=False,
        status="indexed" if not extraction.is_scanned else "error",
        error_message=extraction.warning
    )
    db.add(doc_record)

    # Save chunks in SQLite
    db_chunks = []
    chunk_texts = []
    for c in chunk_items:
        chunk_rec = Chunk(
            id=c.id,
            document_id=doc_id,
            page=c.page,
            chunk_index=c.chunk_index,
            char_start=c.char_start,
            char_end=c.char_end,
            text=c.text,
            char_count=c.char_count,
            token_count_estimate=c.token_count_estimate
        )
        db.add(chunk_rec)
        db_chunks.append(chunk_rec)
        chunk_texts.append(c.text)

    db.commit()
    db.refresh(doc_record)

    # Embed and index into ChromaDB locally (if text was extracted)
    if chunk_texts and not extraction.is_scanned:
        try:
            embeddings = embed_texts(chunk_texts)
            upsert_chunks(chunk_items, embeddings, collection_name="default_rag")
        except Exception as e:
            logger.error(f"Error vector indexing document {doc_id}: {str(e)}")
            doc_record.status = "error"
            doc_record.error_message = f"Vector indexing error: {str(e)}"
            db.commit()

    return doc_record


@router.delete("/{document_id}")
def delete_document(document_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Remove from Chroma
    delete_document_from_chroma(document_id, collection_name="default_rag")

    # Remove file on disk if exists
    file_path = os.path.join(settings.UPLOAD_DIR, doc.filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass

    db.delete(doc)
    db.commit()
    return {"message": f"Document '{doc.original_name}' and its chunks were deleted successfully."}

@router.post("/seed-sample", response_model=DocumentResponse)
def seed_sample_document(db: Session = Depends(get_db)):
    """Seeds the built-in deterministic sample document so zero uploads are needed."""
    sample_file = os.path.join(settings.SAMPLE_DIR, "sample_document.txt")
    if not os.path.exists(sample_file):
        raise HTTPException(status_code=404, detail="Sample document file not found on disk")

    # Check if already seeded
    existing = db.query(Document).filter(Document.original_name == "sample_document.txt").first()
    if existing:
        try:
            from app.services.vectorstore import get_collection
            col = get_collection("default_rag")
            if col.count() == 0:
                chunks = db.query(Chunk).filter(Chunk.document_id == existing.id).order_by(Chunk.chunk_index).all()
                if chunks:
                    chunk_texts = [c.text for c in chunks]
                    embeddings = embed_texts(chunk_texts)
                    upsert_chunks(chunks, embeddings, collection_name="default_rag")
        except Exception as e:
            logger.warning(f"Error checking/reindexing sample document: {e}")
        return existing

    doc_id = "sample_doc"
    extraction = extract_text_from_file(sample_file)
    chunk_items = chunk_pages(
        pages=extraction.pages,
        document_id=doc_id,
        chunk_size=800,
        chunk_overlap=150,
        filename="sample_document.txt"
    )

    doc_record = Document(
        id=doc_id,
        filename="sample_document.txt",
        original_name="sample_document.txt",
        file_type="txt",
        file_size_bytes=os.path.getsize(sample_file),
        page_count=extraction.page_count,
        chunk_count=len(chunk_items),
        char_count=extraction.total_char_count,
        is_sample=True,
        status="indexed"
    )
    db.add(doc_record)

    chunk_texts = []
    for c in chunk_items:
        chunk_rec = Chunk(
            id=c.id,
            document_id=doc_id,
            page=c.page,
            chunk_index=c.chunk_index,
            char_start=c.char_start,
            char_end=c.char_end,
            text=c.text,
            char_count=c.char_count,
            token_count_estimate=c.token_count_estimate
        )
        db.add(chunk_rec)
        chunk_texts.append(c.text)

    db.commit()
    db.refresh(doc_record)

    # Embed and index locally
    embeddings = embed_texts(chunk_texts)
    upsert_chunks(chunk_items, embeddings, collection_name="default_rag")

    return doc_record
