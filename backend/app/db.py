from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import create_engine, String, Float, DateTime, JSON, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from app.config import settings


def sqlalchemy_database_url(url: str) -> str:
    """Use psycopg v3 explicitly for Railway-style PostgreSQL URLs."""
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    return url


class Base(DeclarativeBase):
    pass

class InvestigationRecord(Base):
    __tablename__ = "investigations"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    place: Mapped[str] = mapped_column(String(255), default="India")
    payload: Mapped[dict] = mapped_column(JSON)

class AlertRecord(Base):
    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    source: Mapped[str] = mapped_column(String(100))
    severity: Mapped[str] = mapped_column(String(30))
    confidence: Mapped[float] = mapped_column(Float, default=0)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    geometry_geojson: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)

class SourceHealthRecord(Base):
    __tablename__ = "source_health"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    source: Mapped[str] = mapped_column(String(100))
    ok: Mapped[str] = mapped_column(String(10))
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)

class FireObservationRecord(Base):
    __tablename__ = "fire_observations"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    fingerprint: Mapped[str] = mapped_column(String(96), unique=True, index=True)
    source: Mapped[str] = mapped_column(String(100))
    observed_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    frp: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)

engine = create_engine(sqlalchemy_database_url(settings.database_url), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def init_db():
    Base.metadata.create_all(engine)
