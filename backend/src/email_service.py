# email_service.py
import os
import smtplib
from email.message import EmailMessage


def _require_env(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise RuntimeError(f"Brak zmiennej środowiskowej: {name}")
    return val


def send_alarm_email(to_email: str, hw_uid: str, device_name: str | None = None) -> None:
    host = _require_env("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = _require_env("SMTP_USER")
    password = _require_env("SMTP_PASS")
    mail_from = os.getenv("SMTP_FROM", user)

    subject = "ALARM: wykryto zdarzenie z urządzenia"
    pretty_name = f" ({device_name})" if device_name else ""
    body = (
        f"Wykryto alarm z urządzenia o hw_uid: {hw_uid}{pretty_name}\n\n"
        f"Jeśli to nie Ty, sprawdź stan zamka w aplikacji."
    )

    msg = EmailMessage()
    msg["From"] = mail_from
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    # STARTTLS
    with smtplib.SMTP(host, port, timeout=15) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(user, password)
        smtp.send_message(msg)
