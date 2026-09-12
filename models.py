# -*- coding: utf-8 -*-
"""مدل‌های داده و اولویت‌بندی dedup."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ParsedConfig:
    """نتیجهٔ پارس یک لینک کانفیگ، مستقل از پروتکل."""
    raw: str
    scheme: str
    host: str
    port: int
    remark: str = ""


@dataclass
class TestResult:
    config: str
    host: str
    port: int
    tcp_ping: Optional[int] = None
    tls_ping: Optional[int] = None
    handshake_ok: bool = False
    is_reality: bool = False
    is_hysteria2: bool = False
    is_trojan: bool = False
    is_vless: bool = False
    is_vmess: bool = False
    is_ss: bool = False
    scheme: str = ""
    stability: float = 0.0


@dataclass
class ScoredNode:
    score: float
    config: str
    name: str
    ping: int
    country: str
    city: str
    flag: str
    protocol: str
    host: str
    port: int
    scheme: str = ""


# اولویت پروتکل برای dedup هوشمند: در host:port تکراری، با‌ارزش‌ترین می‌ماند
PROTO_RANK = {"vless": 50, "trojan": 40, "hysteria2": 30, "hy2": 30,
              "vmess": 20, "ss": 10}


def config_rank(pc: ParsedConfig) -> int:
    """امتیاز اولویت یک کانفیگ برای dedup: Reality بر هر پروتکل می‌چربد."""
    rank = PROTO_RANK.get(pc.scheme, 0)
    if "reality" in pc.raw.lower():
        rank += 100
    return rank