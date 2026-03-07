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
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, sessionmaker

# pgvector import — optional, degrades gracefully if not installed
try:
    from pgvector.sqlalchemy import Vector
    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False
    Vector = None

# ── Load env ────────────────────────────────────────────────────────────────
# override=False: Railway's injected env vars always win over local .env file.
# On Railway there is no .env file; DATABASE_URL is injected directly.
_ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=False)

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
    player_id = Column(String(36), nullable=True, index=True)
    game_state = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True),
                        default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))


# ── Session 5: NPC Memory Tables ───────────────────────────────────────────

class NpcMemory(Base):
    __tablename__ = "npc_memories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(String(36), nullable=False, index=True)
    npc = Column(String(10), nullable=False)          # 'usa'|'arabia'|'eu'|'dprg'
    era = Column(Integer, nullable=False, default=0)   # era counter (increments on regime collapse)
    turn = Column(Integer, nullable=False)
    event_type = Column(String(50), nullable=False)    # 'deal_accepted'|'promise_broken'|etc.
    description = Column(Text, nullable=False)         # human-readable event description
    embedding = Column(Vector(512) if HAS_PGVECTOR else Text, nullable=True)  # Voyage AI voyage-3-lite
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_accessed = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class NpcRelationshipSummary(Base):
    __tablename__ = "npc_relationship_summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(String(36), nullable=False, index=True)
    npc = Column(String(10), nullable=False)
    summary_text = Column(Text, nullable=False)        # 2-3 sentence gist
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class EraSummary(Base):
    __tablename__ = "era_summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(String(36), nullable=False, index=True)
    npc = Column(String(10), nullable=False)
    era = Column(Integer, nullable=False)
    summary_text = Column(Text, nullable=False)        # paragraph compressing episodic memories
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


def init_db():
    """Create tables if they don't exist, and run incremental column migrations.
    Wrapped in try/except so pgvector extension absence doesn't crash startup."""
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        # If pgvector extension is missing, create only non-vector tables
        print(f"  [db] WARNING: create_all failed ({e}). Memory tables may not be created.")
        print(f"  [db] Game will run without vector memory features.")

    # ── Column migrations (ALTER TABLE IF NOT EXISTS for each new column) ──
    # These are idempotent: they do nothing if the column already exists.
    _migrations = [
        # Session 5: player_id added to game_sessions
        "ALTER TABLE game_sessions ADD COLUMN IF NOT EXISTS player_id VARCHAR(36)",
        # Session 5: index on player_id (CREATE INDEX IF NOT EXISTS is idempotent)
        "CREATE INDEX IF NOT EXISTS ix_game_sessions_player_id ON game_sessions (player_id)",
    ]
    with engine.connect() as conn:
        for sql in _migrations:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception as mig_err:
                print(f"  [db] Migration skipped ({sql[:60]}...): {mig_err}")
                try:
                    conn.rollback()
                except Exception:
                    pass


# ── CRUD helpers ─────────────────────────────────────────────────────────────

def create_session(game_state_data: dict, player_id: str = None, session_id: str = None) -> str:
    """Insert a new session, return session_id as string.
    If session_id is provided, use that UUID instead of generating a new one."""
    db = SessionLocal()
    try:
        sid = uuid.UUID(session_id) if session_id else uuid.uuid4()
        now = datetime.now(timezone.utc)
        record = GameSession(
            session_id=sid,
            player_id=player_id or str(uuid.uuid4()),
            game_state=game_state_data,
            created_at=now,
            updated_at=now,
        )
        db.add(record)
        db.commit()
        return str(sid)
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
