from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    redis_url: str
    anthropic_api_key: str
    claude_model: str = "claude-sonnet-4-20250514"
   
    # Voyage AI for embeddings
    voyage_api_key: str
    embedding_model: str = "voyage-3"  # or "voyage-3-lite", "voyage-code-3"
    
    # Optional: Dimension reduction for cost savings
    embedding_dimension: int = 1024  # Reduce from 1536 to save storage

    # qdrant vector database
    qdrant_url:         str = "http://localhost:6333"
    qdrant_collection:  str = "meetmind_chunks" 

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )


settings = Settings()