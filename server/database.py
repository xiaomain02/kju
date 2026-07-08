import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

from models import Base

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
DB_PATH = os.path.join(DATA_DIR, 'kanban.db')

os.makedirs(DATA_DIR, exist_ok=True)

DATABASE_URL = os.environ.get('DATABASE_URL', f'sqlite:///{DB_PATH}')