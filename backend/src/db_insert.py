from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, User, Device, RefreshSession
from auth.security import hash_password

# =========================
# KONFIGURACJA BAZY
# =========================

# SQLite
DATABASE_URL = "sqlite:///app.db"

# PostgreSQL (opcjonalnie)
# DATABASE_URL = "postgresql+psycopg2://user:haslo@localhost:5432/nazwa_bazy"

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine)

# =========================
# TWORZENIE TABEL
# =========================
Base.metadata.create_all(bind=engine)

# =========================
# SEED DANYCH
# =========================
def seed():
    session = SessionLocal()

    try:
        # ---------- USERS ----------
        user1 = User(
            username="uladzislau",
            email="utsitavets@gmail.com",
            password_hash=hash_password("haslo123"),
            nr_telefonu="576243480",
        )

        user2 = User(
            username="ania",
            email="ania@example.com",
            password_hash="hashed_password_456",
        )

        session.add_all([user1, user2])
        session.flush()  # <-- mamy id_user

        # ---------- DEVICES ----------
        device1 = Device(
            name="Smart Drzwi 1",
            opis="Drzwi do CS 301",
            hw_uid="1",
            is_open=True,   # OPEN
            user=user1,
        )

        device2 = Device(
            name="Smart Drzwi 2",
            opis="Drzwi do LAB 403",
            hw_uid="2",
            is_open=False,  # OFF
            user=user1,
        )

        device3 = Device(
            name="Lampka nocna",
            opis="Smart LED",
            hw_uid="3",
            is_open=True,   # ON
            user=user2,
        )

        session.add_all([device1, device2, device3])

        # ---------- REFRESH SESSIONS ----------
        refresh1 = RefreshSession(
            id_user=user1.id_user,
            token_hash="token_hash_abc123",
            expires_at=datetime.utcnow() + timedelta(days=7),
        )

        refresh2 = RefreshSession(
            id_user=user2.id_user,
            token_hash="token_hash_def456",
            expires_at=datetime.utcnow() + timedelta(days=7),
        )

        session.add_all([refresh1, refresh2])

        # ---------- COMMIT ----------
        session.commit()
        print("✅ Baza została poprawnie zainicjalizowana")

    except Exception as e:
        session.rollback()
        print("❌ Błąd seedowania:", e)

    finally:
        session.close()


if __name__ == "__main__":
    seed()