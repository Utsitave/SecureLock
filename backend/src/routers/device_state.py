from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Literal, Dict, List, Optional
import time

from sqlalchemy.orm import Session

from src.db import get_db
from src.models import Device, User
from src.mqtt_service import publish_to_device
from src.routers.router import get_current_user  # <- MUSI zwracać obiekt User

router = APIRouter(prefix="/devices", tags=["Devices"])

DoorState = Literal["open", "closed"]
AlarmState = Literal["active", "inactive"]

# Tymczasowy cache stanu (per hw_uid, tylko w pamięci backendu)
_state_cache: Dict[str, DoorState] = {}


class DoorStateIn(BaseModel):
    state: DoorState


class DoorStateOut(BaseModel):
    hw_uid: str
    state: DoorState

class AlarmStateIn(BaseModel):
        state: AlarmState

class AlarmStateOut(BaseModel):
        hw_uid: str
        state: AlarmState


class DeviceOut(BaseModel):
    id_device: int
    hw_uid: Optional[str]
    name: str
    is_open: bool
    alarm_active: bool


class DeviceListResponse(BaseModel):
    devices: List[DeviceOut]


@router.get("", response_model=DeviceListResponse)
async def get_user_devices(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Pobiera wszystkie urządzenia przypisane do zalogowanego użytkownika."""
    devices = db.query(Device).filter(Device.id_user == user.id_user).all()
    return {"devices": devices}


def get_owned_device(
    db: Session,
    hw_uid: str,
    user: User,
) -> Device:
    device = db.query(Device).filter(Device.hw_uid == hw_uid).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    if device.id_user != user.id_user:
        raise HTTPException(status_code=403, detail="Forbidden")

    return device


@router.get("/{hw_uid}/state", response_model=DoorStateOut)
async def get_device_state(
    hw_uid: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    device = get_owned_device(db, hw_uid, user)

    state: DoorState = "open" if device.is_open else "closed"

    return {
        "hw_uid": hw_uid,
        "state": state,
    }


@router.post("/{hw_uid}/state", response_model=DoorStateOut)
async def set_device_state(
    hw_uid: str,
    payload: DoorStateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    device = get_owned_device(db, hw_uid, user)

    # mapowanie API -> baza
    new_state_bool = payload.state == "open"

    # zapisz do bazy
    device.is_open = new_state_bool
    db.commit()
    db.refresh(device)

    # mapowanie API -> MQTT
    cmd = "1" if payload.state == "open" else "0"

    try:
        await publish_to_device(hw_uid, cmd)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "hw_uid": hw_uid,
        "state": payload.state,
    }


@router.get("/{hw_uid}/alarm", response_model=AlarmStateOut)
async def get_device_alarm(
    hw_uid: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    device = get_owned_device(db, hw_uid, user)

    state: AlarmState = "active" if device.alarm_active else "inactive"
    return {"hw_uid": hw_uid, "state": state}


@router.post("/{hw_uid}/alarm", response_model=AlarmStateOut)
async def set_device_alarm(
    hw_uid: str,
    payload: AlarmStateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    device = get_owned_device(db, hw_uid, user)

    alarm_bool = payload.state == "active"
    device.alarm_active = alarm_bool
    db.commit()
    db.refresh(device)

    alarm = "1" if alarm_bool else "0"

    try:
        await publish_to_device(hw_uid, alarm, channel="alarm")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "hw_uid": hw_uid,
        "state": payload.state,
    }