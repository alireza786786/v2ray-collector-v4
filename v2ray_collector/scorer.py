# -*- coding: utf-8 -*-
"""امتیازدهی نسل جدید: پینگ + پروتکل + کشور + پورت طلایی + پایداری + EWMA."""
from __future__ import annotations

import logging
from typing import Optional

from .config import CFG
from .database import HistoryDB
from .models import ScoredNode, TestResult
from .parser import ConfigParser

log = logging.getLogger("v2ray")


class SmartScorer:
    PROTO_BONUS = {
        "REALITY": 600, "HYSTERIA2": 500, "TROJAN": 350,
        "VLESS": 200, "VMESS": 180, "SS": 100,
    }
    COUNTRY_BONUS = {
        "IR": 300, "TR": 250, "AE": 230, "AZ": 220, "AM": 200,
        "IQ": 210, "TM": 200, "GE": 190, "RU": 150, "OM": 180,
        "DE": 80, "NL": 70, "FI": 60, "FR": 50, "GB": 40,
        "IT": 30, "PL": 30, "CA": 20, "US": 10,
    }

    def __init__(self, db: HistoryDB, geo_map: dict):
        self.db = db
        self.geo_map = geo_map  # host -> (flag, cc, country, city)

    def _golden_bonus(self, r: TestResult) -> int:
        """بونس پورت طلایی: ردیف ۱ > ردیف ۲. با golden_only_tls فقط پروتکل‌های
        TLS‌دار بونس می‌گیرند (vmess فقط با tls/reality در لینک؛ ss بی‌بونس)."""
        if r.port in CFG.golden_ports_t1:
            base = CFG.golden_bonus_t1
        elif r.port in CFG.golden_ports_t2:
            base = CFG.golden_bonus_t2
        else:
            return 0
        if not CFG.golden_only_tls:
            return base
        if r.scheme in ("vless", "trojan", "hysteria2", "hy2"):
            return base
        if r.scheme == "vmess":
            low = r.config.lower()
            return base if ("tls" in low or "reality" in low) else 0
        return 0

    def score_one(self, r: TestResult) -> Optional[ScoredNode]:
        try:
            ping = r.tls_ping or r.tcp_ping
            if not ping:
                return None
            score = 1000 - ping
            if r.is_reality:
                score += self.PROTO_BONUS["REALITY"]; protocol = "Reality"
            elif r.is_hysteria2:
                score += self.PROTO_BONUS["HYSTERIA2"]; protocol = "Hysteria2"
            elif r.is_trojan:
                score += self.PROTO_BONUS["TROJAN"]; protocol = "Trojan"
            elif r.is_vless:
                score += self.PROTO_BONUS["VLESS"]; protocol = "Vless"
            elif r.is_vmess:
                score += self.PROTO_BONUS["VMESS"]; protocol = "Vmess"
            elif r.is_ss:
                score += self.PROTO_BONUS["SS"]; protocol = "SS"
            else:
                score += self.PROTO_BONUS["SS"]; protocol = "Unknown"

            flag, cc, country, city = self.geo_map.get(
                r.host, ("🌐", "XX", "Unknown", "Server"))
            score += self.COUNTRY_BONUS.get(cc, 0)

            # پورت‌های طلایی
            score += self._golden_bonus(r)
            if r.is_reality and r.port in CFG.golden_ports_t1:
                score += CFG.golden_t1_reality_extra

            if r.tls_ping and r.tls_ping > 350:
                score -= 150
            if r.handshake_ok and r.is_reality:
                score += 100
            score += r.stability * 50
            # اعتبار تاریخی با EWMA (از دیتابیس)
            score += self.db.get_reliability_bonus(r.host, r.port)

            name = f"👉🆔@{CFG.channel_tag}📡{flag}®️{country}©️{city}🅿️ping:{ping}ms"
            final_link = ConfigParser.rename(r.config, r.scheme, name)
            if not final_link:
                return None
            return ScoredNode(
                score=score, config=final_link, name=name, ping=ping,
                country=country, city=city, flag=flag, protocol=protocol,
                host=r.host, port=r.port, scheme=r.scheme,
            )
        except Exception as e:
            log.debug(f"score_one fail {r.host}: {e}")
            return None

    def score_all(self, results) -> list:
        scored = [s for s in (self.score_one(r) for r in results) if s]
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored