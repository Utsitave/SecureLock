# mqtt_service.py
import os
import ssl
import sys
from typing import Optional, Literal
import asyncio

from aiomqtt import Client, MqttError

from src.db import SessionLocal
from src.alarm_repo import get_alarm_recipient_by_hw_uid
from src.email_service import send_alarm_email

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


PublishChannel = Literal["cmd", "alarm"]


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

    # Czasem potrzebne przy "dziwnych" CA (np. z ESP), zostawiamy jak było
    if hasattr(ssl, "VERIFY_X509_STRICT"):
        ctx.verify_flags &= ~ssl.VERIFY_X509_STRICT

    return ctx


# Na Windowsie aiomqtt często wymaga Selector loop
if sys.platform.lower().startswith("win"):
    from asyncio import set_event_loop_policy, WindowsSelectorEventLoopPolicy

    set_event_loop_policy(WindowsSelectorEventLoopPolicy())


def _get_mqtt_auth() -> tuple[Optional[str], Optional[str]]:
    return os.getenv("MQTT_USER"), os.getenv("MQTT_PASS")


def _sync_publish(hw_uid: str, payload: str, channel: str) -> None:
    """Synchroniczna wersja publish w osobnym wątku z SelectorEventLoop (Windows fix)."""
    host = _require_env("MQTT_HOST")
    port = int(os.getenv("MQTT_PORT", "8883"))

    topic = f"doorlock/{hw_uid}/{channel}"

    tls_context = build_tls_context()
    username, password = _get_mqtt_auth()

    async def _do_publish():
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

    loop = asyncio.SelectorEventLoop()
    try:
        loop.run_until_complete(_do_publish())
    finally:
        loop.close()


async def publish_to_device(
    hw_uid: str,
    payload: str,
    channel: PublishChannel = "cmd",
) -> None:
    """
    Publikuje wiadomość MQTT do konkretnego urządzenia.

    Kanały:
    - cmd   -> doorlock/<hw_uid>/cmd
    - alarm -> doorlock/<hw_uid>/alarm
    """
    try:
        await asyncio.to_thread(_sync_publish, hw_uid, payload, channel)
    except Exception as e:
        raise RuntimeError(f"MQTT publish failed: {e}") from e


async def listen_alarm_states(hw_uid: Optional[str] = None) -> None:
    """
    Ciągły nasłuch alarmów.
    - Jeśli hw_uid jest podany: subskrybuje doorlock/<hw_uid>/alarm/state
    - Jeśli hw_uid=None: subskrybuje doorlock/+/alarm/state (wszystkie urządzenia)

    Gdy payload == "1" -> wypisuje alert + próbuje wysłać mail do przypisanego usera.
    """
    loop = asyncio.get_running_loop()
    print("[MQTT DEBUG] loop type:", type(loop))
    print("[MQTT DEBUG] can add_reader:", hasattr(loop, "add_reader"))

    host = _require_env("MQTT_HOST")
    port = int(os.getenv("MQTT_PORT", "8883"))

    tls_context = build_tls_context()
    username, password = _get_mqtt_auth()

    topic = f"doorlock/{hw_uid}/alarm/state" if hw_uid else "doorlock/+/alarm/state"
    print(f"[MQTT LISTENER] Subscribing: {topic}")

    # Prosty auto-reconnect w pętli
    while True:
        try:
            async with Client(
                hostname=host,
                port=port,
                username=username,
                password=password,
                keepalive=60,
                tls_context=tls_context,
            ) as client:
                await client.subscribe(topic, qos=1)
                print("[MQTT LISTENER] Connected ✔ Waiting for messages...")

                async for msg in client.messages:
                    try:
                        payload = msg.payload.decode("utf-8", errors="ignore").strip()
                    except Exception:
                        payload = str(msg.payload)

                    # topic: doorlock/<hw_uid>/alarm/state
                    parts = msg.topic.value.split("/")
                    got_hw_uid = (
                        parts[1]
                        if len(parts) >= 4 and parts[0] == "doorlock"
                        else "UNKNOWN"
                    )

                    if payload == "1":
                        print(f"[ALARM] Otrzymano alarm od urządzenia o hw_uid: {got_hw_uid}")

                        db = SessionLocal()
                        try:
                            recipient = get_alarm_recipient_by_hw_uid(db, got_hw_uid)
                        finally:
                            db.close()

                        if not recipient:
                            print(
                                f"[ALARM] Brak przypisanego użytkownika/email dla hw_uid={got_hw_uid} – nie wysyłam maila."
                            )
                            continue

                        email, device_name = recipient

                        # wyślij maila w osobnym wątku, żeby nie blokować listenera
                        try:
                            await asyncio.to_thread(
                                send_alarm_email, email, got_hw_uid, device_name
                            )
                            print(f"[ALARM] Mail wysłany do: {email}")
                        except Exception as e:
                            print(f"[ALARM] Błąd wysyłki maila do {email}: {e}")
                    else:
                        # jeśli nie chcesz logować innych wartości, usuń ten print
                        print(f"[MQTT] {msg.topic.value} -> {payload}")

        except MqttError as e:
            print(f"[MQTT LISTENER] Disconnected / error: {e}. Reconnecting in 3s...")
            await asyncio.sleep(3)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"[MQTT LISTENER] Unexpected error: {e}. Reconnecting in 3s...")
            await asyncio.sleep(3)


async def _quick_test_publish() -> None:
    """
    Szybki test publikacji.
    Ustaw:
    - MQTT_TEST_HW_UID (opcjonalnie)
    - MQTT_TEST_CHANNEL (opcjonalnie: cmd/alarm)
    - MQTT_TEST_PAYLOAD (opcjonalnie)
    """
    test_hw_uid = os.getenv("MQTT_TEST_HW_UID", "TEST_DEVICE")
    test_channel = os.getenv("MQTT_TEST_CHANNEL", "cmd").strip().lower()
    test_payload = os.getenv("MQTT_TEST_PAYLOAD", "1")

    # Walidacja kanału, żeby nie wpuścić literówki z env
    if test_channel not in ("cmd", "alarm"):
        raise RuntimeError("MQTT_TEST_CHANNEL musi być 'cmd' albo 'alarm'")

    print(f"[MQTT TEST] Publishing test message to {test_channel}...")
    await publish_to_device(test_hw_uid, test_payload, channel=test_channel)  # type: ignore[arg-type]
    print("[MQTT TEST] Done ✔")


if __name__ == "__main__":
    """
    TRYB:
    - MQTT_MODE=publish  -> odpala test publish
    - MQTT_MODE=listen   -> odpala listener alarmów
      opcjonalnie: MQTT_LISTEN_HW_UID=ABC (nasłuch tylko jednego urządzenia)
    """
    mode = os.getenv("MQTT_MODE", "listen").lower()
    listen_hw_uid = os.getenv("MQTT_LISTEN_HW_UID")  # może być None

    try:
        if mode == "publish":
            asyncio.run(_quick_test_publish())
        else:
            asyncio.run(listen_alarm_states(listen_hw_uid))
    except KeyboardInterrupt:
        print("Interrupted by user")
    except Exception as e:
        print(f"[MQTT] FAILED ❌: {e}")
        raise
