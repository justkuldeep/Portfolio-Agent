from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    gemini_api_key: str
    gemini_model: str = "gemini-3.5-flash-lite"
    embedding_model: str = "gemini-embedding-001"
    embedding_dim: int = 768

    top_k: int = 5
    kb_path: Path = BASE_DIR / "data" / "kuldeep_portfolio_knowledge_base_v2.md"
    chroma_dir: Path = BASE_DIR / "chroma_db"
    collection_name: str = "portfolio_kb"

    allowed_origins: str = "http://localhost:5173,http://localhost:3000"
    rate_limit: str = "20/minute"
    max_question_chars: int = 500
    max_history_messages: int = 6

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
