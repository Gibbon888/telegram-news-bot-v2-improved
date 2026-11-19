import os
import sqlite3

from bot.config import DB_PATH, MAX_PARSE_RETRIES


class NewsDatabase:

    def __init__(self):
        db_dir = os.path.dirname(DB_PATH)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        self.connection = sqlite3.connect(DB_PATH, timeout=30)
        self.connection.execute("PRAGMA journal_mode=DELETE")

        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                title TEXT,
                status TEXT NOT NULL DEFAULT 'discovered',
                first_seen TEXT NOT NULL,
                published_at TEXT,
                fail_count INTEGER NOT NULL DEFAULT 0,
                last_error TEXT
            )
        """)

        # Мягкая миграция, если таблица уже существовала без новых колонок
        existing_cols = {
            row[1]
            for row in self.connection.execute("PRAGMA table_info(news)").fetchall()
        }
        if "fail_count" not in existing_cols:
            self.connection.execute(
                "ALTER TABLE news ADD COLUMN fail_count INTEGER NOT NULL DEFAULT 0"
            )
        if "last_error" not in existing_cols:
            self.connection.execute(
                "ALTER TABLE news ADD COLUMN last_error TEXT"
            )

        self.connection.commit()

    def add_news(self, url, title, timestamp):
        cursor = self.connection.execute(
            """
            INSERT OR IGNORE INTO news
            (url, title, status, first_seen)
            VALUES (?, ?, 'discovered', ?)
            """,
            (url, title, timestamp),
        )
        self.connection.commit()
        return cursor.rowcount == 1

    def seed_news(self, items, timestamp):
        for item in items:
            self.connection.execute(
                """
                INSERT OR IGNORE INTO news
                (url, title, status, first_seen)
                VALUES (?, ?, 'ignored', ?)
                """,
                (item["url"], item["title"], timestamp),
            )
        self.connection.commit()

    def get_status(self, url):
        row = self.connection.execute(
            "SELECT status FROM news WHERE url=?",
            (url,),
        ).fetchone()
        return row[0] if row else None

    def mark_published(self, url, timestamp):
        self.connection.execute(
            """
            UPDATE news
            SET status='published',
                published_at=?,
                last_error=NULL
            WHERE url=?
            """,
            (timestamp, url),
        )
        self.connection.commit()

    def record_failure(self, url, error_message):
        row = self.connection.execute(
            "SELECT fail_count FROM news WHERE url=?",
            (url,),
        ).fetchone()
        current_fails = (row[0] if row else 0) + 1
        new_status = "failed" if current_fails >= MAX_PARSE_RETRIES else "discovered"

        self.connection.execute(
            """
            UPDATE news
            SET fail_count=?,
                status=?,
                last_error=?
            WHERE url=?
            """,
            (current_fails, new_status, str(error_message)[:500], url),
        )
        self.connection.commit()
        return new_status, current_fails

    def get_daily_count(self, date_prefix):
        row = self.connection.execute(
            """
            SELECT COUNT(*)
            FROM news
            WHERE status='published'
              AND published_at LIKE ?
            """,
            (date_prefix + "%",),
        ).fetchone()
        return row[0]

    def close(self):
        self.connection.commit()
        self.connection.close()
