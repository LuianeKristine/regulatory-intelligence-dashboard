from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    database_url: str = Field(..., env="DATABASE_URL")
    openai_api_key: str | None = Field(None, env="OPENAI_API_KEY")
    ai_provider: str = Field("openai", env="AI_PROVIDER")
    api_base_url: str = Field("http://localhost:8000", env="API_BASE_URL")
    daily_scrape_seconds: int = Field(86400, env="DAILY_SCRAPE_SECONDS")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
