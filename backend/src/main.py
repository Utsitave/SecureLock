from fastapi import FastAPI

from src.db import init_db
from src.routers.router import router as auth_router
from src.routers.device_state import router as device_state_router
from dotenv import load_dotenv

load_dotenv()
app = FastAPI(title="DoorLock API")

@app.on_event("startup")
def on_startup():
    init_db()

app.include_router(auth_router)
app.include_router(device_state_router)
