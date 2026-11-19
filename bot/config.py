import os
from zoneinfo import ZoneInfo

SITE_URL = os.getenv("SITE_URL", "https://qafqazinfo.az/site/ru")
BASE_URL = os.getenv("BASE_URL", "https://qafqazinfo.az")

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

DB_PATH = os.getenv("DB_PATH", "data/state/news.sqlite")

TIMEZONE = ZoneInfo("Asia/Baku")

MAX_DAILY_POSTS = int(os.getenv("MAX_DAILY_POSTS", "30"))
MAX_MESSAGE_LENGTH = int(os.getenv("MAX_MESSAGE_LENGTH", "3800"))

REQUEST_TIMEOUT = 25

# Вежливые паузы между запросами к сайту и Telegram (в секундах)
ARTICLE_FETCH_DELAY = (1.5, 3.5)
TELEGRAM_POST_DELAY = 1.5

# Максимальное число неудачных попыток парсинга одной статьи перед переводом в статус failed
MAX_PARSE_RETRIES = 3

# Для ручного первого запуска:
SEED_ONLY = os.getenv("SEED_ONLY", "false").lower() == "true"

# Путь для сохранения сырого HTML одной статьи при отладке селекторов
DEBUG_HTML_PATH = os.getenv("DEBUG_HTML_PATH", "").strip()
