import os
from pathlib import Path
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
WORKSPACE_DIR = BASE_DIR.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Truth Inspector"
    TAGLINE: str = "Trust, but verify."
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    
    # Provider & Model Settings ("gemini" or "anthropic")
    LLM_PROVIDER: str = "gemini"
    GEMINI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    LLM_MODEL: str = "gemini-1.5-flash"
    
    # Local Embeddings (Runs locally, zero API cost)
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    
    # Storage
    UPLOAD_DIR: str = str(WORKSPACE_DIR / "data" / "uploads")
    CHROMA_DIR: str = str(WORKSPACE_DIR / "data" / "chroma")
    SAMPLE_DIR: str = str(WORKSPACE_DIR / "data" / "sample")
    DATABASE_URL: str = f"sqlite:///{WORKSPACE_DIR / 'data' / 'truth_inspector.db'}"
    
    # Ingestion Defaults
    MAX_UPLOAD_SIZE_MB: int = 20
    DEFAULT_CHUNK_SIZE_CHARS: int = 800
    DEFAULT_CHUNK_OVERLAP_CHARS: int = 150
    
    # Server
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @model_validator(mode="after")
    def resolve_paths(self) -> "Settings":
        # Resolve UPLOAD_DIR
        upload_path = Path(self.UPLOAD_DIR)
        if not upload_path.is_absolute():
            self.UPLOAD_DIR = str((WORKSPACE_DIR / upload_path).resolve())
        
        # Resolve CHROMA_DIR
        chroma_path = Path(self.CHROMA_DIR)
        if not chroma_path.is_absolute():
            self.CHROMA_DIR = str((WORKSPACE_DIR / chroma_path).resolve())

        # Resolve SAMPLE_DIR
        sample_path = Path(self.SAMPLE_DIR)
        if not sample_path.is_absolute():
            self.SAMPLE_DIR = str((WORKSPACE_DIR / sample_path).resolve())

        # Resolve SQLite DATABASE_URL
        if self.DATABASE_URL.startswith("sqlite:///"):
            raw_db_path = self.DATABASE_URL.replace("sqlite:///", "", 1)
            # Remove leading './' if present
            if raw_db_path.startswith("./"):
                raw_db_path = raw_db_path[2:]
            db_p = Path(raw_db_path)
            if not db_p.is_absolute():
                abs_db_p = (WORKSPACE_DIR / db_p).resolve()
                self.DATABASE_URL = f"sqlite:///{abs_db_p.as_posix()}"
            else:
                self.DATABASE_URL = f"sqlite:///{db_p.as_posix()}"

        return self

settings = Settings()

# Ensure directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.CHROMA_DIR, exist_ok=True)
os.makedirs(settings.SAMPLE_DIR, exist_ok=True)
if settings.DATABASE_URL.startswith("sqlite:///"):
    db_file = settings.DATABASE_URL.replace("sqlite:///", "", 1)
    db_dir = os.path.dirname(db_file)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

