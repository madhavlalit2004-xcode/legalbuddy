from typing import Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # ── Application ──────────────────────────────────────────────────────────
    APP_NAME: str = Field(default="AI Legal Buddy")
    APP_VERSION: str = Field(default="0.1.0")
    DEBUG: bool = Field(default=False)

    # ── Server ────────────────────────────────────────────────────────────────
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434")
    OLLAMA_MODEL: str = Field(default="llama3")
    OLLAMA_EMBEDDING_MODEL: str = Field(default="nomic-embed-text")
    OLLAMA_TIMEOUT_SECONDS: float = Field(default=30.0)
    TEMPERATURE: float = Field(default=0.7)
    MAX_TOKENS: int = Field(default=2048)

    # ── VectorDB ──────────────────────────────────────────────────────────────
    CHROMA_HOST: str = Field(default="localhost")
    CHROMA_PORT: int = Field(default=8000)
    CHROMA_COLLECTION_NAME: str = Field(default="legal_docs")
    CHROMA_PERSIST_DIR: str = Field(default="./chroma_db")
    TOP_K_RESULTS: int = Field(default=5)
    SIMILARITY_THRESHOLD: float = Field(default=0.7)
    EMBEDDING_MODEL: str = Field(default="all-MiniLM-L6-v2")
    EMBEDDING_BATCH_SIZE: int = Field(default=32)

    # ── Logging ──────────────────────────────────────────────────────────────
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(default="INFO")
    LOG_FORMAT: Literal["json", "console"] = Field(default="json")
    LOG_FILE: str = Field(default="logs/legal_buddy.log")

    # ── Document Processing ───────────────────────────────────────────────────
    CHUNK_SIZE: int = Field(default=1000)
    CHUNK_OVERLAP: int = Field(default=200)
    UPLOAD_DIR: str = Field(default="./data/uploads")
    MAX_FILE_SIZE_MB: int = Field(default=50)
    MIN_CHUNK_LENGTH: int = Field(default=50)

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = Field(default="sqlite:///./legal_buddy.db")

    # ── Security ──────────────────────────────────────────────────────────────
    SECRET_KEY: str = Field()
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)

    # ── Cors & Legal ──────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: list[str] = Field(default=["http://localhost:3000"])
    LEGAL_DISCLAIMER: bool = Field(default=True)
    DEFAULT_JURISDICTION: str = Field(default="general")

settings = Settings()
