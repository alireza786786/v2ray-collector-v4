# -*- coding: utf-8 -*-
"""دیتابیس SQLite: تاریخچه نودها (با EWMA) + کش Geo. thread-safe + WAL.

نسل جدید: به‌جای شمارش ساده موفقیت/شکست، یک میانگین نمایی وزنی (EWMA)
نگه می‌داریم؛ رکوردهای جدیدتر وزن بیشتری دارند و امتیاز اعتبار به‌مرور
با واقعیت هماهنگ می‌شود.
"""
from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timezone
from typing import Optional, Tuple


class HistoryDB:
    def __init__(self, path: str = "history.db",
                 ewma_decay: float = 0.7, min_history_samples: int = 3):
        self.path = path
        self.ewma_decay = ewma_decay
        self.min_history_samples = min_history_samples
        self._lock = threading.RLock()
        self.conn = sqlite3.connect(path, check_same_thread=False)
        if path != ":memory:":
            try:
                self.conn.execute("PRAGMA journal_mode=WAL")
                self.conn.execute("PRAGMA synchronous=NORMAL")
            except Exception:
                pass
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS node_history (
                host TEXT NOT NULL, port INTEGER NOT NULL,
                last_ping INTEGER, last_score REAL,
                success_count INTEGER DEFAULT 0, fail_count INTEGER DEFAULT 0,
                last_seen TEXT, ewma REAL DEFAULT 0.5,
                PRIMARY KEY (host, port)
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS geo_cache (
                host TEXT PRIMARY KEY, flag TEXT, cc TEXT,
                country TEXT, city TEXT, cached_at TEXT
            )
        """)
        # مهاجرت: ستون ewma برای دیتابیس‌های قدیمی تر
        cols = {r[1] for r in self.conn.execute("PRAGMA table_info(node_history)")}
        if "ewma" not in cols:
            try:
                self.conn.execute("ALTER TABLE node_history ADD COLUMN ewma REAL DEFAULT 0.5")
            except Exception:
                pass
        self.conn.execute("DELETE FROM geo_cache WHERE country = 'Unknown' OR cc = 'XX'")
        self.conn.commit()

    def __enter__(self) -> "HistoryDB":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def record(self, host: str, port: int, ping: int, score: float, success: bool):
        now = datetime.now(timezone.utc).isoformat()
        obs = 1.0 if success else 0.0
        # مقداردهی اولین رکورد از حالت خنثی 0.5 (نه از خود observation)
        init_ewma = self.ewma_decay * 0.5 + (1.0 - self.ewma_decay) * obs
        with self._lock:
            try:
                if success:
                    self.conn.execute("""
                        INSERT INTO node_history (host, port, last_ping, last_score,
                                                  success_count, last_seen, ewma)
                        VALUES (?, ?, ?, ?, 1, ?, ?)
                        ON CONFLICT(host, port) DO UPDATE SET
                            last_ping=excluded.last_ping, last_score=excluded.last_score,
                            success_count=success_count+1, last_seen=excluded.last_seen,
                            ewma=?*ewma+(1-?)*excluded.ewma
                    """, (host, port, ping, score, now, init_ewma,
                          self.ewma_decay, self.ewma_decay))
                else:
                    self.conn.execute("""
                        INSERT INTO node_history (host, port, fail_count, last_seen, ewma)
                        VALUES (?, ?, 1, ?, ?)
                        ON CONFLICT(host, port) DO UPDATE SET
                            fail_count=fail_count+1, last_seen=excluded.last_seen,
                            ewma=?*ewma+(1-?)*excluded.ewma
                    """, (host, port, now, init_ewma, self.ewma_decay, self.ewma_decay))
                self.conn.commit()
            except Exception:
                pass

    def get_reliability_bonus(self, host: str, port: int) -> float:
        """بونس اعتبار بر اساس EWMA: (ewma - 0.5) * 200 با حداقل نمونه."""
        with self._lock:
            try:
                cur = self.conn.execute(
                    "SELECT success_count, fail_count, ewma FROM node_history "
                    "WHERE host=? AND port=?",
                    (host, port))
                row = cur.fetchone()
                if not row:
                    return 0.0
                success, fail, ewma = row
                if success + fail < self.min_history_samples:
                    return 0.0
                return (ewma - 0.5) * 200
            except Exception:
                return 0.0

    def get_geo_cached(self, host: str) -> Optional[Tuple[str, str, str, str]]:
        with self._lock:
            try:
                cur = self.conn.execute(
                    "SELECT flag, cc, country, city FROM geo_cache WHERE host=?", (host,))
                row = cur.fetchone()
                return tuple(row) if row else None
            except Exception:
                return None

    def set_geo_cached(self, host: str, flag: str, cc: str, country: str, city: str):
        with self._lock:
            try:
                self.conn.execute("""
                    INSERT INTO geo_cache (host, flag, cc, country, city, cached_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(host) DO UPDATE SET
                        flag=excluded.flag, cc=excluded.cc,
                        country=excluded.country, city=excluded.city,
                        cached_at=excluded.cached_at
                """, (host, flag, cc, country, city,
                      datetime.now(timezone.utc).isoformat()))
                self.conn.commit()
            except Exception:
                pass

    def close(self):
        with self._lock:
            try:
                self.conn.close()
            except Exception:
                pass