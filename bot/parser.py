import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

from bot.config import BASE_URL, MAX_MESSAGE_LENGTH


def clean_text(value):
    return re.sub(r"\s+", " ", value or "").strip()


def clean_multiline_text(paragraphs):
    cleaned = []
    for p in paragraphs:
        text = clean_text(p)
        if text:
            cleaned.append(text)
    return "\n\n".join(cleaned)


def get_news_links(html):
    soup = BeautifulSoup(html, "lxml")

    result = []
    seen = set()

    for anchor in soup.select("a[href]"):
        href = anchor.get("href", "")
        title = clean_text(anchor.get_text(" ", strip=True))

        url = urljoin(BASE_URL, href)
        parsed = urlparse(url)

        if parsed.hostname not in ("qafqazinfo.az", "www.qafqazinfo.az"):
            continue

        # Строго фильтруем только русскоязычные материалы (/news/detailru/...)
        if not re.search(r"/news/detailru/", parsed.path):
            continue

        if not title or len(title) < 8:
            continue

        # Удаляем параметры и фрагменты
        url = parsed._replace(query="", fragment="").geturl()

        if url in seen:
            continue

        seen.add(url)
        result.append({
            "url": url,
            "title": title,
        })

    # Переворачиваем список, чтобы публиковать новости в хронологическом порядке
    # (от более ранних на странице к самым свежим)
    result.reverse()
    return result


def extract_body_from_element(element):
    paragraphs = [
        p.get_text(" ", strip=True)
        for p in element.find_all("p")
    ]
    if len(paragraphs) >= 2:
        text = clean_multiline_text(paragraphs)
        if len(text) >= 200:
            return text

    return clean_text(element.get_text(" ", strip=True))


def get_article_data(html):
    soup = BeautifulSoup(html, "lxml")

    # Ищем дату до удаления тегов, так как она может быть в meta или header статьи
    article_date = ""
    meta_date = soup.find("meta", property="article:published_time")
    if meta_date and meta_date.get("content"):
        iso_match = re.search(
            r"(\d{4})-(\d{2})-(\d{2})[T ](\d{2}:\d{2})",
            meta_date["content"],
        )
        if iso_match:
            y, m, d, hm = iso_match.groups()
            article_date = f"{d}.{m}.{y} {hm}"

    for tag in soup.select(
        "script, style, nav, footer, header, aside, iframe, form, "
        ".related-news, .similar-news, .share, .social, .comments"
    ):
        tag.decompose()

    # Заголовок
    title = ""
    h1 = soup.find("h1")
    if h1:
        title = clean_text(h1.get_text(" ", strip=True))

    if not title:
        og = soup.find("meta", property="og:title")
        if og:
            title = clean_text(og.get("content"))

    if not title:
        raise ValueError("Не удалось получить заголовок")

    # Поиск основного текста с сохранением абзацев
    selectors = [
        ".news-text",
        ".news_text",
        ".detail-text",
        ".detail_text",
        ".news-detail",
        ".news_detail",
        ".article-content",
        ".article__content",
        ".content-text",
        "article",
    ]

    candidates = []
    for selector in selectors:
        for element in soup.select(selector):
            text = extract_body_from_element(element)
            if len(text) >= 200:
                candidates.append(text)

    if not candidates:
        raise ValueError(
            "Не найден основной текст статьи. "
            "Требуется проверка HTML и CSS-селектора."
        )

    body = max(candidates, key=len)

    if not article_date:
        page_text = soup.get_text(" ", strip=True)
        match = re.search(
            r"\b\d{2}\.\d{2}\.\d{4}(?:\s+\d{2}:\d{2})?",
            page_text,
        )
        article_date = match.group(0) if match else ""

    return {
        "title": title,
        "body": body,
        "date": article_date,
    }


def smart_truncate(text, limit):
    if len(text) <= limit:
        return text

    truncated = text[: limit - 1]
    # Стараемся обрезать по концу последнего предложения или пробелу
    sentence_end = max(
        truncated.rfind(". "),
        truncated.rfind("! "),
        truncated.rfind("? "),
        truncated.rfind("\n"),
    )
    if sentence_end > int(limit * 0.65):
        return truncated[: sentence_end + 1].rstrip() + " …"

    last_space = truncated.rfind(" ")
    if last_space > int(limit * 0.8):
        return truncated[:last_space].rstrip() + "…"

    return truncated.rstrip() + "…"


def format_telegram_message(article):
    title = article["title"]
    body = article["body"]
    date = article["date"]
    url = article["url"]

    header = f"📰 {title}\n"
    if date:
        header += f"\n📅 {date}\n"

    footer = f"\n\nИсточник: Qafqazinfo.az\n{url}"

    available = MAX_MESSAGE_LENGTH - len(header) - len(footer) - 2

    if available <= 100:
        raise ValueError("Заголовок слишком длинный для публикации")

    body = smart_truncate(body, available)

    return f"{header}\n{body}{footer}"
