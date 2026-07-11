import os
import tempfile
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

from models import Base

def get_default_data_dir() -> Path:
    custom_dir = os.environ.get('KJU_DATA_DIR')
    if custom_dir:
        return Path(custom_dir).expanduser()

    if os.name == 'nt':
        base_dir = os.environ.get('LOCALAPPDATA') or tempfile.gettempdir()
        return Path(base_dir) / 'KJU'

    base_dir = os.environ.get('XDG_DATA_HOME') or Path.home() / '.local' / 'share'
    return Path(base_dir) / 'kju'


DATA_DIR = get_default_data_dir()
DB_PATH = DATA_DIR / 'kanban.db'

try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    DATA_DIR = Path(tempfile.gettempdir()) / 'KJU'
    DB_PATH = DATA_DIR / 'kanban.db'
    DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.environ.get('DATABASE_URL') or f'sqlite:///{DB_PATH.as_posix()}'

engine = create_engine(
    DATABASE_URL,
    echo=False,
    poolclass=NullPool,
    connect_args={'check_same_thread': False} if 'sqlite' in DATABASE_URL else {}
)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)
    print(f"Database is ready: {DB_PATH}")


def get_connection():    return engine.connect()

if __name__ == '__main__':
    init_db()
