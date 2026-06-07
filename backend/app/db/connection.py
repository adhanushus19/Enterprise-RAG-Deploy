from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from typing import Generator
from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db() -> Generator:
    """
    FastAPI dependency that provides a transactional database session.
    Automatically closes the session at the end of the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
