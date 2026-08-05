"""SQLite database connection and session management."""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

from app.config import settings
from app.db.models import Base


engine = create_engine(
    f"sqlite:///{settings.db_path}",
    connect_args={"check_same_thread": False},
    echo=False,
    pool_pre_ping=True,
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_conn, connection_record):
    """Set SQLite pragmas for better performance and reliability."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")       # Write-Ahead Logging for concurrent reads
    cursor.execute("PRAGMA busy_timeout=5000")       # Wait 5s instead of failing on lock
    cursor.execute("PRAGMA synchronous=NORMAL")      # Faster writes, still safe with WAL
    cursor.execute("PRAGMA cache_size=-8000")         # 8MB cache
    cursor.close()

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db():
    """Create all tables if they don't exist."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
