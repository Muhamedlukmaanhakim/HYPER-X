import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.api.routers import (
    comparisons,
    documents,
    evaluations,
    exports,
    jobs,
    rag,
    settings as settings_router,
    testcases
)
from app.core.config import settings
from app.core.errors import (
    AppError,
    app_error_handler,
    generic_error_handler,
    http_error_handler
)
from app.core.logging import logger
from app.core.security import is_api_key_configured
from app.models.database import Base, SessionLocal, engine, verify_database
from app.models.models import Configuration, Document, TestCase
from app.services.embeddings import verify_embedding_model
from app.services.vectorstore import verify_vectorstore


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing AI Truth Inspector SQLite database tables...")
    Base.metadata.create_all(bind=engine)

    # Initialize default config and sample data if empty
    db = SessionLocal()
    try:
        # Check default config
        cfg = db.query(Configuration).filter(Configuration.id == "cfg_default").first()
        if not cfg:
            cfg = Configuration(
                id="cfg_default",
                name="Balanced Default RAG",
                description="800-char chunks, 150-char overlap, top-3 retrieval with cosine distance",
                chunk_size=800,
                chunk_overlap=150,
                top_k=3,
                similarity_threshold=0.0,
                embedding_model=settings.EMBEDDING_MODEL,
                llm_model=settings.LLM_MODEL,
                is_default=True
            )
            db.add(cfg)
            db.commit()
            logger.info("Initialized default RAG configuration.")

        # Auto-seed sample document if none exists
        doc_count = db.query(Document).count()
        if doc_count == 0:
            sample_file = os.path.join(settings.SAMPLE_DIR, "sample_document.txt")
            if os.path.exists(sample_file):
                logger.info("Auto-seeding sample document for instant zero-config exploration...")
                from app.api.routers.documents import seed_sample_document
                seed_sample_document(db)

        # Auto-seed sample test cases if none exists
        tc_count = db.query(TestCase).count()
        if tc_count == 0:
            sample_tc_file = os.path.join(settings.SAMPLE_DIR, "sample_testcases.json")
            if os.path.exists(sample_tc_file):
                logger.info("Auto-seeding sample test cases for deterministic evaluation...")
                from app.api.routers.testcases import seed_sample_test_cases
                seed_sample_test_cases(db)

    except Exception as e:
        logger.warning(f"Startup initialization notice: {str(e)}")
    finally:
        db.close()

    yield
    logger.info("Shutting down AI Truth Inspector.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Trust, but verify. RAG Evaluation & Failure Diagnosis Platform",
    version=settings.VERSION,
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Consistent Error Envelope Handlers
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(HTTPException, http_error_handler)
app.add_exception_handler(Exception, generic_error_handler)

# Include API Routers
app.include_router(documents.router)
app.include_router(rag.router)
app.include_router(testcases.router)
app.include_router(evaluations.router)
app.include_router(comparisons.router)
app.include_router(settings_router.router)
app.include_router(exports.router)
app.include_router(jobs.router)

@app.get("/api/health")
def health_check():
    db_health = verify_database()
    vector_health = verify_vectorstore()
    embedding_health = verify_embedding_model()

    # Determine LLM status safely
    prov = (settings.LLM_PROVIDER or "demo").lower()
    has_gemini = is_api_key_configured(settings.GEMINI_API_KEY or settings.GOOGLE_API_KEY)
    has_anthropic = is_api_key_configured(settings.ANTHROPIC_API_KEY)
    llm_configured = prov == "demo" or (prov == "gemini" and has_gemini) or (prov == "anthropic" and has_anthropic)

    all_healthy = db_health.get("healthy", False) and vector_health.get("healthy", False) and embedding_health.get("healthy", False)

    return {
        "status": "healthy" if all_healthy else "degraded",
        "product": settings.PROJECT_NAME,
        "tagline": settings.TAGLINE,
        "version": settings.VERSION,
        "database": db_health,
        "vectorstore": vector_health,
        "embeddings": embedding_health,
        "llm_provider": {
            "provider": prov,
            "configured": llm_configured,
            "model": settings.LLM_MODEL
        }
    }

@app.get("/api/health/db")
def db_health_check():
    db_health = verify_database()
    vector_health = verify_vectorstore()
    embedding_health = verify_embedding_model()
    return {
        "status": "healthy" if (db_health.get("healthy") and vector_health.get("healthy") and embedding_health.get("healthy")) else "degraded",
        "database": db_health,
        "vectorstore": vector_health,
        "embeddings": embedding_health
    }

