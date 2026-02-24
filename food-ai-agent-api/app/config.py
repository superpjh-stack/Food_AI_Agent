from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Application
    app_name: str = "food-ai-agent-api"
    app_env: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/food_ai_agent"
    database_echo: bool = False

    # JWT
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # Anthropic
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-6"
    claude_max_tokens: int = 4096

    # OpenAI (Embeddings)
    openai_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536

    # RAG
    rag_chunk_size: int = 1000
    rag_chunk_overlap: int = 200
    rag_top_k: int = 5
    rag_keyword_weight: float = 0.3
    rag_vector_weight: float = 0.7

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
