import os
import tempfile
from pathlib import Path
from pydantic_settings import BaseSettings


def get_default_database_url() -> str:
    custom_dir = os.environ.get("KJU_DATA_DIR")
    if custom_dir:
        data_dir = Path(custom_dir).expanduser()
    elif os.name == "nt":
        data_dir = Path(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()) / "KJU"
    else:
        data_dir = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "kju"

    return f"sqlite:///{(data_dir / 'kanban.db').as_posix()}"


class Settings(BaseSettings):
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080
    DATABASE_URL: str = get_default_database_url()
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
