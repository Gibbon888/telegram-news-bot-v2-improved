import random
import time
from curl_cffi import requests

from bot.config import (
    SITE_URL,
    REQUEST_TIMEOUT,
    ARTICLE_FETCH_DELAY,
)


class SiteAccessError(Exception):
    pass


class SiteScraper:

    def __init__(self):
        self.session = requests.Session(impersonate="chrome")
        self.session.headers.update({
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;"
                "q=0.9,image/avif,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "ru-RU,ru;q=0.9,az;q=0.8,en-US;q=0.7,en;q=0.6",
            "Referer": SITE_URL,
        })

    def get_html(self, url, referer=None):
        headers = {}
        if referer:
            headers["Referer"] = referer

        try:
            response = self.session.get(
                url,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
            )
        except Exception as error:
            raise SiteAccessError(f"Ошибка HTTP-запроса ({url}): {error}")

        if response.status_code in (403, 429, 503):
            raise SiteAccessError(
                f"Доступ ограничен: HTTP {response.status_code} ({url})"
            )

        if response.status_code != 200:
            raise SiteAccessError(f"HTTP {response.status_code} ({url})")

        html = response.text

        if not html or len(html) < 1000:
            raise SiteAccessError(f"Получена пустая или неполная страница ({url})")

        return html

    def get_news_page(self):
        return self.get_html(SITE_URL)

    def get_article(self, url):
        # Небольшая случайная задержка перед переходом на статью,
        # имитирующая естественное чтение и снижающая риск rate-limit.
        time.sleep(random.uniform(*ARTICLE_FETCH_DELAY))
        return self.get_html(url, referer=SITE_URL)

    def close(self):
        self.session.close()
