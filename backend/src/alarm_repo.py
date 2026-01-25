 #alarm_repo.py
from sqlalchemy.orm import Session
from src.models import Device  # albo z Twojej ścieżki importów

def get_alarm_recipient_by_hw_uid(db: Session, hw_uid: str) -> tuple[str, str | None] | None:
    """
    Zwraca (email, device_name) dla urządzenia o hw_uid.
    None jeśli:
    - brak device
    - device nie ma przypisanego usera
    - user nie ma email (u Ciebie email jest NOT NULL więc odpada)
    """
    device = db.query(Device).filter(Device.hw_uid == hw_uid).first()
    if not device:
        return None
    if not device.user:
        return None
    return device.user.email, device.name