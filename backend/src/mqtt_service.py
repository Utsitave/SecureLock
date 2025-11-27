import asyncio
import json
import os
import sys

from aiomqtt import Client, MqttError

BROKER_HOST = os.getenv("MQTT_HOST", "localhost")
BROKER_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_USER = os.getenv("MQTT_USER", "backend")
MQTT_PASS = os.getenv("MQTT_PASS", "12345678")

DEVICE_ID = os.getenv("DEVICE_ID", "esp32")
TOPIC_CMD = f"doorlock/{DEVICE_ID}/cmd"
TOPIC_STATE = f"doorlock/{DEVICE_ID}/state"
TOPIC_EVENTS = f"doorlock/{DEVICE_ID}/events"


# --- ważne na Windowsie (Python 3.13 itd.) ---
if sys.platform.lower().startswith("win"):
    from asyncio import set_event_loop_policy, WindowsSelectorEventLoopPolicy

    set_event_loop_policy(WindowsSelectorEventLoopPolicy())


async def handle_incoming(topic: str, payload: str):
    """Obsługa przychodzących wiadomości MQTT."""
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        print(f"[WARN] Non-JSON message on {topic}: {payload}")
        return

    if topic.endswith("/state"):
        print(f"[STATE] {data}")
    elif topic.endswith("/events"):
        print(f"[EVENT] {data}")
    else:
        print(f"[INFO] {topic}: {data}")


async def publish(client: Client, command: dict):
    """
    Wyślij komendę do urządzenia ESP32 przez MQTT.

    Args:
        client: aiomqtt.Client już połączony z brokerem.
        command: np. {"action": "unlock", "cmdId": "cmd-1"}
    """
    payload = json.dumps(command)
    await client.publish(TOPIC_CMD, payload, qos=1)
    print(f"[PUBLISH] Sent to {TOPIC_CMD}: {payload}")


async def mqtt_main():
    """Połącz z brokerem, subskrybuj tematy i okresowo wysyłaj komendy."""
    try:
        async with Client(
            hostname=BROKER_HOST,
            port=BROKER_PORT,
            username=MQTT_USER,
            password=MQTT_PASS,
            # client_id w aiomqtt jest opcjonalny, brak parametru w __init__,
            # więc korzystamy z domyślnego (losowego) ID paho-mqtt
            keepalive=60,
        ) as client:

            # Subskrypcje – wywołujemy dwukrotnie, zgodnie z przykładami z dokumentacji aiomqtt
            await client.subscribe(TOPIC_STATE, qos=1)
            await client.subscribe(TOPIC_EVENTS, qos=1)

            print(f"[MQTT] Connected to {BROKER_HOST}:{BROKER_PORT}")
            print(f"[MQTT] Subscribed to {TOPIC_STATE} and {TOPIC_EVENTS}")

            async def listener():
                """Nasłuchiwanie wszystkich wiadomości z brokera."""
                # W aiomqtt używamy globalnej kolejki client.messages
                async for msg in client.messages:
                    await handle_incoming(msg.topic, msg.payload.decode())

            async def periodic_publisher():
                """Wysyłanie testowej komendy co 10 sekund."""
                while True:
                    cmd = {"action": "unlock", "cmdId": "cmd-1"}
                    await publish(client, cmd)
                    await asyncio.sleep(10)

            # Uruchamiamy równolegle nasłuchiwanie i okresowe wysyłanie
            await asyncio.gather(listener(), periodic_publisher())

    except MqttError as e:
        print(f"[ERROR] MQTT connection failed: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(mqtt_main())
    except KeyboardInterrupt:
        print("\n[EXIT] Stopped by user.")
