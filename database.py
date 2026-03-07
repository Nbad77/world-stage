"""
Accounts Infrastructure — SQLModel Tables
Tables: users, game_states

User: Clerk-authenticated player identity
GameState: Persisted game state blob, owned by a user

This module is separate from db.py (legacy session storage).
Both coexist during migration; db.py will be retired once all
routes use authenticated game state via database.py.
"""

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from sqlmodel import SQLModel, Field, create_engine, Session, JSON, Column
from sqlalchemy.dialects.postgresql import JSONB

# ── Load env ────────────────────────────────────────────────────────────────
_ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=False)

DATABASE_URL = os.getenv("DATABASE_URL", "")
if not DATABASE_URL:
    raise EnvironmentError("DATABASE_URL not set in environment or .env file")

# ── Engine ───────────────────────────────────────────────────────────────────
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)


# ── Models ───────────────────────────────────────────────────────────────────

class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    clerk_user_id: str = Field(index=True, unique=True)
    email: str
    is_test: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GameStatePersisted(SQLModel, table=True):
    """Persisted game state, owned by a user.
    Named GameStatePersisted to avoid collision with the existing
    game_state.py GameState class used throughout the codebase."""
    __tablename__ = "game_states"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    state_data: dict = Field(sa_column=Column(JSONB, nullable=False))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── Session helper ───────────────────────────────────────────────────────────

def get_session():
    """Yield a SQLModel session for FastAPI dependency injection."""
    with Session(engine) as session:
        yield session


# ── Init ─────────────────────────────────────────────────────────────────────

def init_accounts_db():
    """Create users and game_states tables if they don't exist."""
    SQLModel.metadata.create_all(engine)
    print("[DB] Tables created: User, GameState")
