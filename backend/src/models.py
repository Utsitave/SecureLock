# models.py
from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy import (
    String,
    Integer,
    BigInteger,
    DateTime,
    ForeignKey,
    JSON,
    Text,
    func,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


class Base(DeclarativeBase):
    """Bazowa klasa dla wszystkich modeli."""
    pass


# =========================
#  USERS
# =========================
class User(Base):
    __tablename__ = "users"

    id_user: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nr_telefonu: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # relacja 1 -> N: user ma wiele devices
    devices: Mapped[List["Device"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


# =========================
#  DEVICES
# =========================
class Device(Base):
    __tablename__ = "devices"

    id_device: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    id_user: Mapped[int] = mapped_column(
        ForeignKey("users.id_user", ondelete="CASCADE"),
        nullable=False,
    )

    # nazwa/przyjazny opis urządzenia do wyświetlania w apce
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    opis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # np. identyfikator sprzętowy / MQTT (home/<hw_uid>/events)
    hw_uid: Mapped[Optional[str]] = mapped_column(String(64), unique=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # relacje
    user: Mapped["User"] = relationship(back_populates="devices")
    events: Mapped[List["Event"]] = relationship(
        back_populates="device",
        cascade="all, delete-orphan",
        order_by="desc(Event.created_at)",
    )


# =========================
#  EVENTS
# =========================
class Event(Base):
    __tablename__ = "events"

    id_event: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    id_device: Mapped[int] = mapped_column(
        ForeignKey("devices.id_device", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # np. "alarm_triggered", "door_opened", "guest_detected"
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # szczegóły zdarzenia – elastyczne JSON
    # w SQLite też działa, traktowane jako TEXT
    payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    device: Mapped["Device"] = relationship(back_populates="events")

# =========================
#  REFRESH SESSION
# =========================
class RefreshSession(Base):
    __tablename__ = "refresh_sessions"
    id_session: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    id_user: Mapped[int] = mapped_column(
    ForeignKey("users.id_user", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column (
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
