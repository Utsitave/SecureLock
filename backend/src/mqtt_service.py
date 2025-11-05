import asyncio
import json
import os
from asyncio_mqtt import Client, MqttError


BROKER_HOST = os.getenv("MQTT_HOST", "localhost")
BROKER_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_USER = os.getenv("MQTT_USER", "backend")
MQTT_PASS = os.getenv("MQTT_PASS", "backend123")

DEVICE_ID = os.getenv("DEVICE_ID", "esp32")
TOPIC_CMD = f"doorlock/{DEVICE_ID}/cmd"
TOPIC_STATE = f"doorlock/{DEVICE_ID}/state"
TOPIC_EVENTS = f"doorlock/{DEVICE_ID}/events"


async def handle_incoming(topic: str, payload: str):
    # Handle incoming MQTT messages from ESP32.
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
    Publish a command to the ESP32 device.

    Args:
        client: asyncio_mqtt.Client object already connected to broker
        command: dict containing the command, e.g. {"action": "unlock", "cmdId": "cmd-1"}
    """
    payload = json.dumps(command)
    await client.publish(TOPIC_CMD, payload, qos=1)
    print(f"[PUBLISH] Sent to {TOPIC_CMD}: {payload}")


async def mqtt_main():
    # Connect, subscribe, and periodically publish test commands.
    try:
        async with Client(
            hostname=BROKER_HOST,
            port=BROKER_PORT,
            username=MQTT_USER,
            password=MQTT_PASS,
            client_id="python_backend",
        ) as client:

            # Subscribe to topics
            await client.subscribe([(TOPIC_STATE, 1), (TOPIC_EVENTS, 1)])
            print(f"[MQTT] Connected to {BROKER_HOST}:{BROKER_PORT}")
            print(f"[MQTT] Subscribed to {TOPIC_STATE} and {TOPIC_EVENTS}")

            async def listener():
                # Continuously handle incoming messages.
                async with client.unfiltered_messages() as messages:
                    async for msg in messages:
                        await handle_incoming(msg.topic, msg.payload.decode())

            async def periodic_publisher():
                # Send a command every 10 seconds (demo).
                while True:
                    cmd = {"action": "unlock", "cmdId": "cmd-1"}
                    await publish(client, cmd)
                    await asyncio.sleep(10)

            # Run both tasks concurrently
            await asyncio.gather(listener(), periodic_publisher())

    except MqttError as e:
        print(f"[ERROR] MQTT connection failed: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(mqtt_main())
    except KeyboardInterrupt:
        print("\n[EXIT] Stopped by user.")
