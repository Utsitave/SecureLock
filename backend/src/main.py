import os
import asyncio
import threading
from fastapi import FastAPI
from dotenv import load_dotenv

from src.db import init_db
from src.mqtt_service import listen_alarm_states

from src.routers.router import router as auth_router
from src.routers.device_state import router as device_state_router

load_dotenv()
app = FastAPI(title="DoorLock API")

mqtt_thread: threading.Thread | None = None


def _mqtt_thread_entry(listen_hw_uid: str | None):
    loop = asyncio.SelectorEventLoop()
    asyncio.set_event_loop(loop)
    print("[APP] MQTT thread loop:", type(loop))
    try:
        loop.run_until_complete(listen_alarm_states(listen_hw_uid))
    finally:
        loop.close()


@app.on_event("startup")
async def on_startup():
    global mqtt_thread

    listen_hw_uid = os.getenv("MQTT_LISTEN_HW_UID")  # None => wszystkie
    mqtt_thread = threading.Thread(
        target=_mqtt_thread_entry,
        args=(listen_hw_uid,),
        daemon=True,
        name="mqtt-listener",
    )
    mqtt_thread.start()
    print("[APP] MQTT listener started in background thread ✔")


@app.on_event("shutdown")
async def on_shutdown():
    # daemon thread padnie przy zamknięciu procesu
    print("[APP] shutdown ✔")


app.include_router(auth_router)
app.include_router(device_state_router)
