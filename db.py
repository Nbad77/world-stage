"""
Database layer — PostgreSQL via SQLAlchemy
Table: game_sessions
  session_id  UUID primary key
  game_state  JSONB
  created_at  timestamp
  updated_at  timestamp

Sessions expire after 24 hours (cleaned up lazily on read).
"""

import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, String, DateTime, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, sessionmaker

# ── Load env ────────────────────────────────────────────────────────────────
_ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH)

DATABASE_URL = os.getenv("DATABASE_URL", "")
if not DATABASE_URL:
    raise EnvironmentError("DATABASE_URL not set in environment or .env file")

# ── Engine ───────────────────────────────────────────────────────────────────
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,        # detect stale connections
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

SESSION_TTL_HOURS = 24


# ── Model ────────────────────────────────────────────────────────────────────

class GameSession(Base):
    __tablename__ = "game_sessions"

    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    game_state = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True),
                        default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))


def init_db():
    """Create tables if they don't exist."""
    Base.metadata.create_all(bind=engine)


# ── CRUD helpers ─────────────────────────────────────────────────────────────

def create_session(game_state_data: dict) -> str:
    """Insert a new session, return session_id as string."""
    db = SessionLocal()
    try:
        session_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        record = GameSession(
            session_id=session_id,
            game_state=game_state_data,
            created_at=now,
            updated_at=now,
        )
        db.add(record)
        db.commit()
        return str(session_id)
    finally:
        db.close()


def load_session(session_id: str) -> dict | None:
    """
    Load game_state dict for session_id.
    Returns None if not found or expired (>24h).
    """
    db = SessionLocal()
    try:
        record = db.query(GameSession).filter(
            GameSession.session_id == uuid.UUID(session_id)
        ).first()

        if record is None:
            return None

        # Expire check
        age = datetime.now(timezone.utc) - record.updated_at
        if age > timedelta(hours=SESSION_TTL_HOURS):
            db.delete(record)
            db.commit()
            return None

        return record.game_state
    finally:
        db.close()


def save_session(session_id: str, game_state_data: dict) -> bool:
    """
    Overwrite game_state for existing session.
    Returns False if session not found.
    """
    db = SessionLocal()
    try:
        record = db.query(GameSession).filter(
            GameSession.session_id == uuid.UUID(session_id)
        ).first()

        if record is None:
            return False

        record.game_state = game_state_data
        record.updated_at = datetime.now(timezone.utc)
        db.commit()
        return True
    finally:
        db.close()


def delete_session(session_id: str) -> bool:
    """Delete a session. Returns False if not found."""
    db = SessionLocal()
    try:
        record = db.query(GameSession).filter(
            GameSession.session_id == uuid.UUID(session_id)
        ).first()

        if record is None:
            return False

        db.delete(record)
        db.commit()
        return True
    finally:
        db.close()
