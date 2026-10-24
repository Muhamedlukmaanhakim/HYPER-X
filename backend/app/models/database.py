from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

# SQLite configuration with check_same_thread=False for FastAPI concurrency
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_database() -> dict:
    """
    Lightweight health check that verifies SQLite database connectivity,
    a successful SELECT 1 query, and schema initialization.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        expected_tables = {
            "documents", "chunks", "configurations", "test_cases",
            "evaluation_runs", "case_results", "reviewer_overrides",
            "comparisons", "jobs", "metric_definitions"
        }
        initialized = expected_tables.issubset(set(table_names))
        
        return {
            "status": "connected",
            "dialect": engine.dialect.name,
            "tables_initialized": initialized,
            "table_count": len(table_names),
            "tables": sorted(table_names),
            "healthy": True
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "dialect": "sqlite",
            "tables_initialized": False,
            "error": str(e),
            "healthy": False
        }

