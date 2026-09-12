# -*- coding: utf-8 -*-
"""تست واقعی اتصال با Xray-core: دانلود باینری، ساخت outbound، اجرای پروکسی.

ایمن در برابر خطا: هر مشکل زیرساختی فقط آن کاندید (یا کل مرحله) را کنار
می‌گذارد و کل فرآیند متوقف نمی‌شود.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import tempfile
import zipfile
from typing import List, Optional
from urllib.parse import parse_qs, unquote, urlparse

import aiohttp

from .config import CFG
from .models import ScoredNode

log = logging.getLogger("v2ray")

_XRAY_PORT_COUNTER = {"n": 28000}


def _next_local_port() -> int:
    _XRAY_PORT_COUNTER["n"] += 1
    return _XRAY_PORT_COUNTER["n"]


async def ensure_xray_binary() -> Optional[str]:
    """دانلود یک‌باره باینری Xray-core. در صورت شکست، None (تست واقعی غیرفعال)."""
    bin_dir = os.path.join(".", ".xray_bin")
    bin_path = os.path.join(bin_dir, "xray")
    if os.path.exists(bin_path) and os.access(bin_path, os.X_OK):
        return bin_path
    try:
        os.makedirs(bin_dir, exist_ok=True)
        url = "https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip"
        zip_path = bin_path + ".zip"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as r:
                if r.status != 200:
                    log.warning(f"⚠️ دانلود Xray ناموفق (HTTP {r.status}) — تست واقعی رد شد")
                    return None
                data = await r.read()
        with open(zip_path, "wb") as f:
            f.write(data)
        with zipfile.ZipFile(zip_path) as z:
            z.extract("xray", bin_dir)
        os.chmod(bin_path, 0o755)
        os.remove(zip_path)
        return bin_path
    except Exception as e:
        log.warning(f"⚠️ آماده‌سازی Xray ناموفق: {e} — تست واقعی رد شد")
        return None


def build_xray_outbound(raw: str, scheme: str) -> Optional[dict]:
    """ساخت outbound سازگار با Xray از روی لینک. vless/trojan/ss؛ hy2 توسط
    Xray-core پشتیبانی نمی‌شود."""
    try:
        p = urlparse(raw)
        qs = {k: v[0] for k, v in parse_qs(p.query).items()}
        host, port = p.hostname, p.port
        if not host or not port:
            return None
        network = qs.get("type", "tcp") or "tcp"
        security = qs.get("security", "") or ""
        sni = qs.get("sni") or qs.get("host") or host
        fp = qs.get("fp", "chrome") or "chrome"
        stream: dict = {"network": network}
        if security == "reality":
            stream["security"] = "reality"
            stream["realitySettings"] = {
                "serverName": sni, "fingerprint": fp,
                "shortId": qs.get("sid", ""), "publicKey": qs.get("pbk", ""),
                "spiderX": qs.get("spx", ""),
            }
        elif security == "tls":
            stream["security"] = "tls"
            stream["tlsSettings"] = {
                "serverName": sni, "allowInsecure": True, "fingerprint": fp,
            }
        if network == "ws":
            stream["wsSettings"] = {
                "path": qs.get("path", "/") or "/",
                "headers": {"Host": qs.get("host", sni)},
            }
        elif network == "grpc":
            stream["grpcSettings"] = {"serviceName": qs.get("serviceName", "")}
        if scheme == "vless":
            uid = unquote(p.username or "")
            return {
                "protocol": "vless",
                "settings": {"vnext": [{
                    "address": host, "port": port,
                    "users": [{
                        "id": uid,
                        "encryption": qs.get("encryption", "none") or "none",
                        "flow": qs.get("flow", "") or "",
                    }],
                }]},
                "streamSettings": stream,
            }
        if scheme == "trojan":
            password = unquote(p.username or "")
            if not stream.get("security"):
                stream["security"] = "tls"
                stream["tlsSettings"] = {"serverName": sni, "allowInsecure": True, "fingerprint": fp}
            return {
                "protocol": "trojan",
                "settings": {"servers": [{"address": host, "port": port, "password": password}]},
                "streamSettings": stream,
            }
        if scheme == "ss":
            userinfo = unquote(p.username or "")
            method, password = None, None
            try:
                pad = "=" * (-len(userinfo) % 4)
                decoded = base64.urlsafe_b64decode(userinfo + pad).decode()
                method, password = decoded.split(":", 1)
            except Exception:
                if ":" in userinfo:
                    method, password = userinfo.split(":", 1)
            if not method or not password:
                return None
            return {
                "protocol": "shadowsocks",
                "settings": {"servers": [{
                    "address": host, "port": port, "method": method, "password": password,
                }]},
            }
        return None
    except Exception:
        return None


async def real_test_one(xray_path: str, raw_config: str, scheme: str) -> bool:
    """اجرای واقعی پروکسی و رد کردن یک درخواست اینترنتی از آن.
    True = کار می‌کند / جریمه نمی‌شود؛ False = حذف شود."""
    if scheme in ("hysteria2", "hy2"):
        return True  # پشتیبانی‌نشده توسط Xray — بدون قضاوت
    outbound = build_xray_outbound(raw_config, scheme)
    if outbound is None:
        return True  # نتوانستیم بسازیم — جریمه نکن
    local_port = _next_local_port()
    conf_path = os.path.join(tempfile.gettempdir(), f"xray_{local_port}.json")
    conf = {
        "log": {"loglevel": "none"},
        "inbounds": [{"listen": "127.0.0.1", "port": local_port,
                      "protocol": "http", "settings": {}}],
        "outbounds": [outbound],
    }
    proc = None
    try:
        with open(conf_path, "w") as f:
            json.dump(conf, f)
        proc = await asyncio.create_subprocess_exec(
            xray_path, "run", "-c", conf_path,
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.sleep(0.8)
        if proc.returncode is not None:
            return False
        proxy_url = f"http://127.0.0.1:{local_port}"
        for attempt in range(2):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        CFG.real_test_url, proxy=proxy_url,
                        timeout=aiohttp.ClientTimeout(total=CFG.real_test_timeout),
                    ) as r:
                        return r.status in (200, 204)
            except Exception:
                if attempt == 0:
                    await asyncio.sleep(0.5)
                    continue
                return False
        return False
    except Exception:
        return True  # خطای زیرساختی ما — جریمه نکن
    finally:
        if proc is not None and proc.returncode is None:
            try:
                proc.kill()
                await proc.wait()
            except Exception:
                pass
        try:
            os.remove(conf_path)
        except Exception:
            pass


async def run_real_tests(scored: List[ScoredNode]) -> List[ScoredNode]:
    if not CFG.real_test_enabled:
        return scored
    try:
        xray_path = await ensure_xray_binary()
    except Exception as e:
        log.warning(f"⚠️ تست واقعی به‌طور کامل رد شد: {e}")
        return scored
    if not xray_path:
        return scored
    candidates = scored[:CFG.real_test_max_candidates]
    rest = scored[CFG.real_test_max_candidates:]
    sem = asyncio.Semaphore(CFG.real_test_concurrency)

    async def _check(n: ScoredNode):
        async with sem:
            try:
                ok = await real_test_one(xray_path, n.config, n.scheme)
            except Exception:
                ok = True
            return n, ok

    log.info(f"   🔎 تست واقعی روی {len(candidates)} کاندیدای برتر...")
    results = await asyncio.gather(*[_check(n) for n in candidates])
    verified = [n for n, ok in results if ok]
    log.info(f"   ✅ {len(verified)} تأیید شد | ❌ {len(candidates) - len(verified)} رد شد")
    return verified + rest