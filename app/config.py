from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days
    DATABASE_URL: str = "sqlite:///./kanban.db"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()