"""Canali di notifica. Configurati con variabili d'ambiente (mai credenziali nel codice).

RADAR_TELEGRAM_TOKEN, RADAR_TELEGRAM_CHAT_ID         -> Telegram
RADAR_SMTP_HOST, RADAR_SMTP_USER, RADAR_SMTP_PASS,
RADAR_MAIL_TO                                        -> email
"""
from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage

import httpx

from .models import Alert


def _format(alerts: list[Alert]) -> str:
    return "\n".join(f"• {a.text}\n  {a.url}" for a in alerts)


def to_console(alerts: list[Alert]) -> None:
    print(_format(alerts) if alerts else "Nessuna novità.")


def to_telegram(alerts: list[Alert]) -> None:
    token, chat = os.getenv("RADAR_TELEGRAM_TOKEN"), os.getenv("RADAR_TELEGRAM_CHAT_ID")
    if not (token and chat and alerts):
        return
    httpx.post(f"https://api.telegram.org/bot{token}/sendMessage",
               json={"chat_id": chat, "text": "Radar PhD\n\n" + _format(alerts)}, timeout=20)


def to_email(alerts: list[Alert]) -> None:
    host, user, pwd, to = (os.getenv(k) for k in ("RADAR_SMTP_HOST", "RADAR_SMTP_USER", "RADAR_SMTP_PASS", "RADAR_MAIL_TO"))
    if not (host and user and pwd and to and alerts):
        return
    msg = EmailMessage()
    msg["Subject"] = f"Radar PhD — {len(alerts)} novità"
    msg["From"], msg["To"] = user, to
    msg.set_content(_format(alerts))
    with smtplib.SMTP_SSL(host) as s:
        s.login(user, pwd)
        s.send_message(msg)


def send_all(alerts: list[Alert]) -> None:
    to_console(alerts)
    to_telegram(alerts)
    to_email(alerts)
