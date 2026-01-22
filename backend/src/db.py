# db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.models import Base

DATABASE_URL = "sqlite:///./app.db"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    connect_args={"check_same_thread": False}  # tylko dla SQLite
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True, expire_on_commit=False,)

def init_db():
    Base.metadata.create_all(bind=engine)  # <-- tworzy wszystkie tabele z modeli

def get_db() -> Session:
    """
    Dependency FastAPI.
    Otwiera sesję DB i zamyka ją po zakończeniu requestu.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()