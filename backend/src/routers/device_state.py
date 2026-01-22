from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Literal, Dict
import time

from sqlalchemy.orm import Session

from src.db import get_db
from src.models import Device, User
from src.mqtt_service import publish_to_device
from src.routers.router import get_current_user  # <- MUSI zwracać obiekt User

router = APIRouter(prefix="/devices", tags=["Devices"])

DoorState = Literal["open", "closed"]

# Tymczasowy cache stanu (per hw_uid, tylko w pamięci backendu)
_state_cache: Dict[str, DoorState] = {}


class DoorStateIn(BaseModel):
    state: DoorState


class DoorStateOut(BaseModel):
    hw_uid: str
    state: DoorState


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
    get_owned_device(db, hw_uid, user)

    state = _state_cache.get(hw_uid, "closed")
    return {"hw_uid": hw_uid, "state": state}


@router.post("/{hw_uid}/state", response_model=DoorStateOut)
async def set_device_state(
    hw_uid: str,
    payload: DoorStateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_owned_device(db, hw_uid, user)

    # zapisz stan lokalnie
    _state_cache[hw_uid] = payload.state

    # mapowanie stan -> komenda dla ESP
    action = "unlock" if payload.state == "open" else "lock"

    cmd = {
        "action": action,
        "cmdId": str(int(time.time() * 1000)),
    }

    try:
        await publish_to_device(hw_uid, cmd)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"hw_uid": hw_uid, "state": payload.state}
