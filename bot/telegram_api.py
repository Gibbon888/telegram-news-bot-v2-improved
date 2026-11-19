import json
import time
import urllib.request
import urllib.error

from bot.config import (
    TELEGRAM_TOKEN,
    TELEGRAM_CHAT_ID,
)


def send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "link_preview_options": {
            "is_disabled": False
        },
    }

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    for attempt in range(3):
        request = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))

            if result.get("ok"):
                return result["result"]

            raise RuntimeError(f"Telegram API: {result}")

        except urllib.error.HTTPError as error:
            response_body = error.read().decode("utf-8", errors="replace")

            try:
                result = json.loads(response_body)
            except Exception:
                result = {}

            if error.code == 429 and attempt < 2:
                retry_after = result.get("parameters", {}).get("retry_after", 10)
                time.sleep(min(retry_after, 60))
                continue

            raise RuntimeError(
                f"Ошибка Telegram HTTP {error.code}: {response_body}"
            )

        except Exception:
            if attempt == 2:
                raise
            time.sleep(5)

    raise RuntimeError("Не удалось отправить сообщение")
