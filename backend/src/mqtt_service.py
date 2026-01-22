import json
import os
import sys
from aiomqtt import Client, MqttError

BROKER_HOST = os.getenv("MQTT_HOST", "192.168.229.169")
BROKER_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_USER = os.getenv("MQTT_USER", "backend")
MQTT_PASS = os.getenv("MQTT_PASS", "12345678")

# --- ważne na Windowsie ---
if sys.platform.lower().startswith("win"):
    from asyncio import set_event_loop_policy, WindowsSelectorEventLoopPolicy
    set_event_loop_policy(WindowsSelectorEventLoopPolicy())


async def publish_to_device(hw_uid: str, command: dict) -> None:
    """
    Publikuje komendę MQTT do konkretnego urządzenia.

    Topic: doorlock/<hw_uid>/cmd
    Payload: JSON (np. {"action": "unlock", "cmdId": "123"})
    """
    topic = f"doorlock/{hw_uid}/cmd"
    payload = json.dumps(command)

    try:
        async with Client(
            hostname=BROKER_HOST,
            port=BROKER_PORT,
            username=MQTT_USER,
            password=MQTT_PASS,
            keepalive=60,
        ) as client:
            await client.publish(topic, payload, qos=1)
            print(f"[MQTT] {topic} <- {payload}")
    except MqttError as e:
        raise RuntimeError(f"MQTT publish failed: {e}") from e
