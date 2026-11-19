from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Union


class Settings(BaseSettings):
    # App
    APP_ENV: str = "development"
    SECRET_KEY: str = "founderos-hackathon-secret-key-2026"

    # Gemini
    GEMINI_API_KEY: str = ""

    # SQLite (via async SQLAlchemy)
    DATABASE_URL: str = "sqlite+aiosqlite:///./founderos.db"

    # MongoDB Atlas
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB: str = "founderos"

    # News
    NEWSDATA_API_KEY: str = ""
    GDELT_ENABLED: bool = False
    DUCKDUCKGO_ENABLED: bool = True

    # LlamaIndex
    LLAMA_INDEX_STORAGE_DIR: str = "./storage"
    EMBED_MODEL: str = "models/text-embedding-004"

    # JWT
    JWT_SECRET: str = "founderos-jwt-secret-2026"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440  # 24 hours

    # CORS
    ALLOWED_ORIGINS: Union[List[str], str] = ["http://localhost:5173", "http://localhost:3000"]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
