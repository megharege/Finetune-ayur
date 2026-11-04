import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "AyurLLM Hospital & Classical Shloka RAG Platform"
    API_V1_STR: str = "/api"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "ayurllm-super-secure-jwt-secret-key-2026")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    MEILI_URL: str = os.getenv("MEILI_URL", "http://localhost:7700")
    MEILI_MASTER_KEY: str = os.getenv("MEILI_MASTER_KEY", "ayurveda-dev-key")
    MEILI_INDEX: str = "ayurveda"
    
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "ayurveda123")
    
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./ayur_hospital.db")
    
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ]

    class Config:
        env_file = ".env"

settings = Settings()
