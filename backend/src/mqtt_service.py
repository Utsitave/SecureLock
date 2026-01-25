# mqtt_service.py
import os
import ssl
import sys
from typing import Optional
import asyncio
from datetime import datetime
import uuid

from aiomqtt import Client, MqttError
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # jeśli nie masz python-dotenv, to po prostu korzystasz z ENV ustawionych w systemie
    pass

def _require_env(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise RuntimeError(f"Brak zmiennej środowiskowej: {name}")
    return val


def build_tls_context() -> ssl.SSLContext:
    ca_path = _require_env("MQTT_TLS_CA")
    cert_path = _require_env("MQTT_TLS_CERT")
    key_path = _require_env("MQTT_TLS_KEY")
    key_password = os.getenv("MQTT_TLS_KEY_PASSWORD")

    ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=ca_path)
    ctx.load_verify_locations(cafile=ca_path)
    ctx.load_cert_chain(certfile=cert_path, keyfile=key_path, password=key_password)

    if hasattr(ssl, "VERIFY_X509_STRICT"):
        ctx.verify_flags &= ~ssl.VERIFY_X509_STRICT

    return ctx

if sys.platform.lower().startswith("win"):
    from asyncio import set_event_loop_policy, WindowsSelectorEventLoopPolicy
    set_event_loop_policy(WindowsSelectorEventLoopPolicy())


def _get_mqtt_auth() -> tuple[Optional[str], Optional[str]]:
    return os.getenv("MQTT_USER"), os.getenv("MQTT_PASS")

async def publish_to_device(hw_uid: str, command: str) -> None:
    """
    Publikuje komendę MQTT do konkretnego urządzenia.

    Topic: doorlock/<hw_uid>/cmd
    Payload: JSON (np. {"action": "unlock", "cmdId": "123"})
    """
    host = _require_env("MQTT_HOST")
    port = int(os.getenv("MQTT_PORT", "8883"))

    topic = f"doorlock/{hw_uid}/cmd"
    payload = command

    tls_context = build_tls_context()
    username, password = _get_mqtt_auth()

    try:
        async with Client(
            hostname=host,
            port=port,
            username=username,
            password=password,
            keepalive=60,
            tls_context=tls_context,
        ) as client:
            await client.publish(topic, payload, qos=1)
            print(f"[MQTT] {topic} <- {payload}")
    except MqttError as e:
        raise RuntimeError(f"MQTT publish failed: {e}") from e


async def _quick_test() -> None:
    """
    Szybki test połączenia MQTT (mTLS):
    - łączy się z brokerem
    - publikuje wiadomość testową
    """

    test_hw_uid = os.getenv("MQTT_TEST_HW_UID", "TEST_DEVICE")

    test_payload = "1"

    print("[MQTT TEST] Publishing test message...")
    await publish_to_device(test_hw_uid, test_payload)
    print("[MQTT TEST] Done ✔")


if __name__ == "__main__":
    try:
        asyncio.run(_quick_test())
    except KeyboardInterrupt:
        print("Interrupted by user")
    except Exception as e:
        print(f"[MQTT TEST] FAILED ❌: {e}")
        raise