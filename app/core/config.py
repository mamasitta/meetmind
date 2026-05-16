from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    redis_url: str
    anthropic_api_key: str
    claude_model: str = "claude-sonnet-4-20250514"
    embedding_model: str = "text-embedding-3-small"  

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )


settings = Settings()