import logging
import os
import sys
import time
from datetime import datetime

from bot.config import (
    TIMEZONE,
    MAX_DAILY_POSTS,
    SEED_ONLY,
    TELEGRAM_POST_DELAY,
    DEBUG_HTML_PATH,
)
from bot.scraper import SiteScraper, SiteAccessError
from bot.parser import (
    get_news_links,
    get_article_data,
    format_telegram_message,
)
from bot.database import NewsDatabase
from bot.telegram_api import send_message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

log = logging.getLogger("news_bot")


def now():
    return datetime.now(TIMEZONE)


def save_debug_html(html):
    if not DEBUG_HTML_PATH:
        return
    try:
        debug_dir = os.path.dirname(DEBUG_HTML_PATH)
        if debug_dir:
            os.makedirs(debug_dir, exist_ok=True)
        with open(DEBUG_HTML_PATH, "w", encoding="utf-8") as f:
            f.write(html)
        log.info("HTML статьи сохранён для анализа: %s", DEBUG_HTML_PATH)
    except Exception as error:
        log.warning("Не удалось сохранить debug HTML: %s", error)


def run_bot():
    timestamp = now().isoformat()
    today = now().date().isoformat()

    db = NewsDatabase()
    scraper = SiteScraper()
    debug_saved = False

    try:
        log.info("Запуск Telegram News Bot")

        # 1. Получаем русскоязычную страницу
        html = scraper.get_news_page()

        # 2. Извлекаем ссылки
        news_items = get_news_links(html)

        if not news_items:
            raise RuntimeError(
                "На странице не найдено новостей. "
                "Проверить HTML и структуру сайта."
            )

        log.info("Найдено ссылок: %s", len(news_items))

        # 3. Первоначальная инициализация базы
        if SEED_ONLY:
            db.seed_news(news_items, timestamp)
            log.info(
                "Начальная загрузка завершена (%s записей). "
                "Публикации не отправлялись.",
                len(news_items),
            )
            return

        # 4. Регистрируем обнаруженные новости
        new_count = 0
        for item in news_items:
            if db.add_news(item["url"], item["title"], timestamp):
                new_count += 1

        log.info("Новых ссылок добавлено в базу: %s", new_count)

        published_this_run = 0

        # 5. Обрабатываем только новые новости
        for item in news_items:
            if db.get_daily_count(today) >= MAX_DAILY_POSTS:
                log.warning("Достигнут суточный лимит публикаций (%s)", MAX_DAILY_POSTS)
                break

            if db.get_status(item["url"]) != "discovered":
                continue

            log.info("Обрабатываем: %s", item["title"])

            # Получение страницы статьи
            article_html = scraper.get_article(item["url"])

            if DEBUG_HTML_PATH and not debug_saved:
                save_debug_html(article_html)
                debug_saved = True

            # Извлечение текста
            try:
                article = get_article_data(article_html)
                article["url"] = item["url"]
                message = format_telegram_message(article)
            except ValueError as error:
                status, fails = db.record_failure(item["url"], error)
                log.error(
                    "Ошибка извлечения статьи (попытка %s, статус=%s): %s",
                    fails,
                    status,
                    error,
                )
                continue

            # Отправка в Telegram
            send_message(message)

            # Только после успешной отправки отмечаем новость опубликованной
            db.mark_published(item["url"], now().isoformat())

            published_this_run += 1
            log.info("Успешная публикация: %s", article["title"])

            # Пауза между публикациями в Telegram (защита от flood-limit)
            time.sleep(TELEGRAM_POST_DELAY)

        log.info(
            "Работа завершена. Публикаций за запуск: %s",
            published_this_run,
        )

    finally:
        scraper.close()
        db.close()


if __name__ == "__main__":
    try:
        run_bot()
    except SiteAccessError as error:
        log.error("Проблема доступа к сайту: %s", error)
        sys.exit(1)
    except Exception:
        log.exception("Критическая ошибка бота")
        sys.exit(1)
