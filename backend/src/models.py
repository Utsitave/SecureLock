# models.py
from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    String,
    Integer,
    DateTime,
    ForeignKey,
    Text,
    Boolean,
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
    id_user: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id_user", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # nazwa/przyjazny opis urządzenia do wyświetlania w apce
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    opis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # np. identyfikator sprzętowy / MQTT (home/<hw_uid>/events)
    hw_uid: Mapped[Optional[str]] = mapped_column(String(64), unique=True)

    # stan urządzenia (np. ON/OFF)
    state: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="0",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # relacje
    user: Mapped[Optional["User"]] = relationship(back_populates="devices")


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

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
