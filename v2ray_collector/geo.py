# -*- coding: utf-8 -*-
"""جغرافیا: resolve آدرس با کش پایدار + موازی async (بدون مسدودکردن لوپ)."""
from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket
from typing import Tuple

import aiohttp

from .config import CFG
from .database import HistoryDB

log = logging.getLogger("v2ray")


class GeoLocator:
    def __init__(self, db: HistoryDB, max_concurrent: int | None = None):
        self.db = db
        self.semaphore = asyncio.Semaphore(max_concurrent or CFG.geo_max_concurrent)
        self.api_calls = 0

    @staticmethod
    def _resolve(host: str) -> str | None:
        try:
            ipaddress.ip_address(host)
            return host
        except ValueError:
            pass
        try:
            return socket.gethostbyname(host)
        except Exception:
            return None

    @staticmethod
    def _flag(cc: str) -> str:
        try:
            return ''.join(chr(127397 + ord(c)) for c in cc.upper()[:2] if c.isalpha())
        except Exception:
            return "🌐"

    async def _fetch_one(self, session: aiohttp.ClientSession, host: str
                          ) -> Tuple[str, str, str, str, str]:
        cached = self.db.get_geo_cached(host)
        if cached:
            return (host, *cached)
        default = (host, "🌐", "XX", "Unknown", "Server")
        if self.api_calls >= CFG.geo_max_calls_per_run:
            return default
        ip = await asyncio.to_thread(self._resolve, host)
        if not ip:
            return default
        async with self.semaphore:
            self.api_calls += 1
            try:
                async with session.get(
                    f"https://ipwho.is/{ip}",
                    timeout=aiohttp.ClientTimeout(total=CFG.geo_timeout),
                    headers={"User-Agent": "V2RayCollector/4.0"}
                ) as r:
                    data = await r.json(content_type=None)
            except Exception as e:
                log.debug(f"geo lookup fail for {host}: {e}")
                return default
        if not data.get("success", True):
            return default
        cc = data.get("country_code", "XX") or "XX"
        country = data.get("country", "Unknown") or "Unknown"
        city = data.get("city") or "Server"
        flag = self._flag(cc)
        self.db.set_geo_cached(host, flag, cc, country, city)
        return (host, flag, cc, country, city)

    async def resolve_all(self, hosts: list) -> dict:
        """host -> (flag, cc, country, city) برای همه به‌صورت موازی."""
        unique_hosts = list(dict.fromkeys(hosts))
        async with aiohttp.ClientSession() as session:
            tasks = [self._fetch_one(session, h) for h in unique_hosts]
            rows = await asyncio.gather(*tasks)
        return {h: (flag, cc, country, city) for h, flag, cc, country, city in rows}