# Telegram News Bot

Автоматический сбор русскоязычных новостей с https://qafqazinfo.az/site/ru и публикация в Telegram-канал.

## Technologies

- Python 3.12
- curl_cffi
- BeautifulSoup4 + lxml
- SQLite (ветка `bot-data`)
- GitHub Actions
- Telegram Bot API

## Schedule

- **Timezone:** `Asia/Baku`
- **Working hours:** 07:00–23:00 (каждые 30 минут)
- **Maximum publications:** 30 per day
- **Maximum message length:** 3800 characters

## Structure

- `main` — исходный код и GitHub Actions workflow.
- `bot-data` — изолированная ветка с файлом `state/news.sqlite`.

## Security

Токен бота (`TELEGRAM_BOT_TOKEN`) и ID канала (`TELEGRAM_CHAT_ID`) хранятся исключительно в GitHub Repository Secrets.
