# -*- coding: utf-8 -*-
"""لایه شبکه: دریافت async منابع، رمزگشایی، تست TCP/TLS/Reality و فیلتر SNI."""
from __future__ import annotations

import asyncio
import base64
import gzip
import logging
import random
import socket
import ssl
import time
import zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

import aiohttp

from .config import CFG
from .models import ParsedConfig, TestResult
from .parser import ConfigParser

log = logging.getLogger("v2ray")


# =============================================================================
# دریافت Async منابع
# =============================================================================

class AsyncFetcher:
    def __init__(self, max_concurrent: int = 30):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.timeout = aiohttp.ClientTimeout(total=15, connect=5)

    async def fetch_one(self, session: aiohttp.ClientSession, url: str) -> str:
        async with self.semaphore:
            for attempt in range(2):
                try:
                    async with session.get(
                        url, timeout=self.timeout,
                        headers={"User-Agent": "V2RayCollector/4.0"}
                    ) as r:
                        if r.status == 200:
                            return await r.text()
                        log.debug(f"fetch {url} -> status {r.status}")
                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    log.debug(f"fetch {url} attempt {attempt}: {e}")
                    if attempt == 0:
                        await asyncio.sleep(0.5 + random.random() * 0.5)
            return ""

    async def fetch_all(self, urls: List[str]) -> List[str]:
        connector = aiohttp.TCPConnector(limit=50, ttl_dns_cache=300)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [self.fetch_one(session, u) for u in urls]
            return await asyncio.gather(*tasks)


class ConfigDecoder:
    """رمزگشایی سطح فایل منبع (کل sub ممکن است base64/gzip باشد)."""

    @staticmethod
    def try_b64(text: str) -> Optional[str]:
        try:
            clean = text.replace('\n', '').replace('\r', '').replace(' ', '')
            if len(clean) < 16:
                return None
            pad = '=' * (-len(clean) % 4)
            decoded = base64.b64decode(clean + pad, validate=True)
            txt = decoded.decode('utf-8', errors='ignore')
            return txt if any(p in txt for p in CFG.ALLOWED_SCHEMES) else None
        except Exception:
            return None

    @classmethod
    def decode_all(cls, raw: str) -> List[str]:
        results = {raw}
        b64 = cls.try_b64(raw)
        if b64:
            results.add(b64)
            b64_n = cls.try_b64(b64)
            if b64_n:
                results.add(b64_n)
        try:
            data = raw.encode()
            for fn in (gzip.decompress, zlib.decompress):
                try:
                    t = fn(data).decode('utf-8', errors='ignore')
                    if "://" in t:
                        results.add(t)
                except Exception:
                    pass
        except Exception:
            pass
        return list(results)


# =============================================================================
# فیلتر SNI — عامل واقعی عبور از فیلترینگ (نسل جدید)
# =============================================================================

class SniChecker:
    """برای کانفیگ‌های TLS/Reality، SNI را اعتبارسنجی و DNS-resolve می‌کند.

    اگر dامنه SNI رزول نشود، نود عملاً قابل اتصال نیست و حذف می‌شود.
    رزولوشن فقط برای پروتکل‌های دارای security=tls/reality انجام می‌شود
    و per-hostname با کش، یک بار در هر اجرا.
    """

    def __init__(self, check: bool = True, max_concurrent: int = 20):
        self.check = check
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self._cache: dict = {}

    @staticmethod
    def _extract_sni(pc: ParsedConfig) -> Optional[str]:
        if pc.scheme not in ("vless", "trojan"):
            return None
        qs = parse_qs(urlparse(pc.raw).query)
        security = (qs.get("security") or [""])[0]
        if security not in ("tls", "reality"):
            return None
        return (qs.get("sni") or qs.get("host") or [pc.host])[0]

    async def _resolve(self, host: str) -> bool:
        if host in self._cache:
            return self._cache[host]
        try:
            await asyncio.to_thread(socket.gethostbyname, host)
            ok = True
        except Exception:
            ok = False
        self._cache[host] = ok
        return ok

    async def filter(self, parsed: List[ParsedConfig]) -> List[ParsedConfig]:
        if not self.check:
            return parsed
        kept: List[ParsedConfig] = []
        dropped = 0
        for pc in parsed:
            sni = self._extract_sni(pc)
            if sni is None:
                kept.append(pc)
                continue
            if not ConfigParser.is_valid_host(sni):
                dropped += 1
                continue
            async with self.semaphore:
                if not await self._resolve(sni):
                    dropped += 1
                    continue
            kept.append(pc)
        if dropped:
            log.info(f"   🛰 فیلتر SNI: {dropped} کانفیگ با SNI نامعتبر/بدون DNS حذف شد")
        return kept


# =============================================================================
# تست شبکه
# =============================================================================

class AdvancedTester:
    def __init__(self, max_workers: Optional[int] = None):
        self.max_workers = max_workers or CFG.max_workers

    @staticmethod
    def tcp_ping(host: str, port: int, timeout: float) -> Optional[int]:
        try:
            start = time.perf_counter()
            with socket.create_connection((host, port), timeout=timeout):
                return int((time.perf_counter() - start) * 1000)
        except Exception:
            return None

    @staticmethod
    def tls_handshake(host: str, port: int, timeout: float,
                       allow_self_signed: bool) -> Tuple[bool, Optional[int]]:
        try:
            start = time.perf_counter()
            ctx = ssl.create_default_context()
            if allow_self_signed:
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
            ctx.minimum_version = ssl.TLSVersion.TLSv1_2
            with socket.create_connection((host, port), timeout=timeout) as sock:
                with ctx.wrap_socket(sock, server_hostname=host) as ss:
                    ss.do_handshake()
                    if not ss.cipher():
                        return False, None
            return True, int((time.perf_counter() - start) * 1000)
        except Exception:
            return False, None

    def test_single(self, pc: ParsedConfig) -> Optional[TestResult]:
        try:
            if not ConfigParser.is_valid_host(pc.host):
                return None
            upper = pc.raw.upper()
            is_reality = "REALITY" in upper
            is_hy2 = pc.scheme in ("hysteria2", "hy2")
            is_trojan = pc.scheme == "trojan"
            is_vless = pc.scheme == "vless"
            is_vmess = pc.scheme == "vmess"
            is_ss = pc.scheme == "ss"
            # hysteria2/hy2 پروتکل QUIC/UDP هستند؛ تست TLS روی TCP معتبر نیست
            needs_tls = pc.scheme in ("vless", "trojan")
            tcp = self.tcp_ping(pc.host, pc.port, CFG.tcp_timeout)
            if tcp is None or tcp > CFG.max_ping_ms:
                return None
            result = TestResult(
                config=pc.raw, host=pc.host, port=pc.port, tcp_ping=tcp,
                is_reality=is_reality, is_hysteria2=is_hy2, is_trojan=is_trojan,
                is_vless=is_vless, is_vmess=is_vmess, is_ss=is_ss, scheme=pc.scheme,
            )
            if needs_tls and not is_reality:
                ok, tls_p = self.tls_handshake(pc.host, pc.port, CFG.tls_timeout,
                                                allow_self_signed=False)
                result.handshake_ok = ok
                result.tls_ping = tls_p
                if not ok or (tls_p and tls_p > CFG.max_tls_ping_ms):
                    return None
            if is_reality:
                ok, tls_p = self.tls_handshake(pc.host, pc.port, CFG.tls_timeout,
                                                allow_self_signed=True)
                if not ok:
                    return None
                result.handshake_ok = ok
                result.tls_ping = tls_p
            pings = [tcp]
            for _ in range(max(CFG.stability_rounds - 1, 0)):
                p = self.tcp_ping(pc.host, pc.port, CFG.tcp_timeout)
                if p:
                    pings.append(p)
                else:
                    return None
            result.tcp_ping = min(pings)
            result.stability = 1.0 - (max(pings) - min(pings)) / max(max(pings), 1)
            return result
        except Exception as e:
            log.debug(f"test_single fail {pc.host}:{pc.port}: {e}")
            return None

    def test_all(self, parsed: List[ParsedConfig]) -> List[TestResult]:
        log.info(f"🔬 تست شبکه روی {len(parsed)} کانفیگ...")
        results: List[TestResult] = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as ex:
            futures = {ex.submit(self.test_single, p): p for p in parsed}
            done = 0
            for fut in as_completed(futures):
                done += 1
                if done % 200 == 0:
                    log.info(f"   پیشرفت: {done}/{len(parsed)} | قبول: {len(results)}")
                r = fut.result()
                if r:
                    results.append(r)
        log.info(f"✅ {len(results)} کانفیگ سالم از {len(parsed)}")
        return results