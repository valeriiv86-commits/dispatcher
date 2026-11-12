import json
import logging
import urllib.request

from .config import settings

log = logging.getLogger("dispatcher")


def _send(text: str) -> None:
    try:
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_TOKEN}/sendMessage"
        req = urllib.request.Request(
            url, data=json.dumps({"chat_id": settings.TELEGRAM_CHAT_ID, "text": text}).encode(),
            headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5).close()
    except Exception as e:  # never log URL (contains token)
        log.warning("Telegram notify failed: %s", type(e).__name__)


def notify(background, text: str) -> None:
    if settings.TELEGRAM_TOKEN and settings.TELEGRAM_CHAT_ID:
        background.add_task(_send, text)
