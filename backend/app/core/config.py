from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    APP_ENV: str = "development"
    SECRET_KEY: str = "change-me"

    # Gemini
    GEMINI_API_KEY: str = ""

    # PostgreSQL
    DATABASE_URL: str = "postgresql+asyncpg://founderos:founderos@localhost:5432/founderos"

    # MongoDB
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB: str = "founderos"

    # News
    NEWSDATA_API_KEY: str = ""
    GDELT_ENABLED: bool = False
    DUCKDUCKGO_ENABLED: bool = True

    # LlamaIndex
    LLAMA_INDEX_STORAGE_DIR: str = "./storage"
    EMBED_MODEL: str = "models/text-embedding-004"

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
