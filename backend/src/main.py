# main.py
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from mqtt_service import MQTTService

app = FastAPI()

connected_websockets: list[WebSocket] = []
mqtt_service: MQTTService | None = None

# Tu trzymasz ostatnie stany, na start może być dict zamiast bazy:
device_states: dict[str, dict] = {}


async def on_mqtt_message(topic: str, payload: str):
    # np. topic: "devices/esp1/state"
    _, device_id, _ = topic.split("/")
    # Zapisz stan
    device_states[device_id] = {"raw": payload}  # tu możesz zrobić json.loads(payload)
    # Wyślij do wszystkich po WebSocket
    for ws in connected_websockets:
        await ws.send_json({"device_id": device_id, "payload": payload})


@app.on_event("startup")
async def startup():
    global mqtt_service
    mqtt_service = MQTTService("localhost", on_mqtt_message)
    await mqtt_service.start()


@app.get("/devices/{device_id}/state")
async def get_device_state(device_id: str):
    return device_states.get(device_id, {})


@app.post("/devices/{device_id}/command")
async def send_device_command(device_id: str, body: dict):
    # tu możesz walidować body, np. Pydantic model
    if mqtt_service is None:
        raise RuntimeError("MQTT not ready")
    import json
    await mqtt_service.publish_command(device_id, json.dumps(body))
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_websockets.append(websocket)
    try:
        while True:
            # Aplikacja mobilna może coś wysłać, jeśli chce – albo ignorujemy recv
            await websocket.receive_text()
    except WebSocketDisconnect:
        connected_websockets.remove(websocket)
