"""SQLite via SQLAlchemy. Local dev only — Postgres later via the same SQLAlchemy interface."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

from compas_api.config import get_settings

log = logging.getLogger("compas.db")

_engine = None
_SessionLocal: sessionmaker[Session] | None = None


def _get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        settings = get_settings()
        db_path = Path(settings.db_path).resolve()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{db_path}"
        log.info("Opening SQLite at %s", url)
        _engine = create_engine(url, echo=False, future=True, connect_args={"check_same_thread": False})
        _SessionLocal = sessionmaker(
            bind=_engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,  # so we can read attrs after commit within the request
        )
    return _engine


def get_session() -> Session:
    _get_engine()
    assert _SessionLocal is not None
    return _SessionLocal()


class Base(DeclarativeBase):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="user")
    trust_score: Mapped[int] = mapped_column(Integer, default=0)
    banned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Song(Base):
    __tablename__ = "songs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    artist: Mapped[str] = mapped_column(String(255))
    album: Mapped[str | None] = mapped_column(String(255), nullable=True)
    genre: Mapped[str] = mapped_column(String(16))
    style: Mapped[str | None] = mapped_column(String(64), nullable=True)
    duration_sec: Mapped[float] = mapped_column(Float, default=0.0)
    bpm: Mapped[float | None] = mapped_column(Float, nullable=True)
    key_signature: Mapped[str | None] = mapped_column(String(16), nullable=True)
    visibility: Mapped[str] = mapped_column(String(16), default="private")
    moderation_status: Mapped[str] = mapped_column(String(16), default="pending")
    analysis_status: Mapped[str] = mapped_column(String(16), default="none")
    analysis_version: Mapped[int] = mapped_column(Integer, default=0)
    source_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class SongAnalysis(Base):
    """Immutable, versioned. Each model upgrade creates a new row, never overwrites."""

    __tablename__ = "song_analyses"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    song_id: Mapped[str] = mapped_column(String(36), ForeignKey("songs.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    model_set: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(16), default="queued")
    confidence_overall: Mapped[float] = mapped_column(Float, default=0.0)
    result: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


def init_db() -> None:
    _get_engine()
    Base.metadata.create_all(_engine)  # type: ignore[misc]
    log.info("DB schema initialized")
