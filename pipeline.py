# -*- coding: utf-8 -*-
"""خط لوله اصلی v4: دریافت ← رمزگشایی ← پارس ← dedup هوشمند ← فیلتر SNI
← تست ← جغرافیا ← امتیازدهی ← فیلتر طلایی ← تست واقعی Xray ← انتشار.
"""
from __future__ import annotations

import logging
import random
import time
from typing import List

from .config import CFG
from .database import HistoryDB
from .geo import GeoLocator
from .models import ParsedConfig, ScoredNode, config_rank
from .net import AdvancedTester, AsyncFetcher, ConfigDecoder, SniChecker
from .parser import ConfigParser
from .scorer import SmartScorer
from .telegram import TelegramSender
from .xray_test import run_real_tests

log = logging.getLogger("v2ray")


async def _stage_fetch() -> List[str]:
    log.info("📥 مرحله 1: دریافت از منابع...")
    fetcher = AsyncFetcher()
    raw = await fetcher.fetch_all(list(CFG.sources))
    ok = sum(1 for t in raw if t)
    log.info(f"   ✅ {ok}/{len(CFG.sources)} منبع موفق")
    return raw


def _stage_parse(raw: List[str]) -> List[ParsedConfig]:
    log.info("🔓 مرحله 2: رمزگشایی، پارس و dedup هوشمند...")
    all_configs = set()
    for text in raw:
        if not text:
            continue
        for decoded in ConfigDecoder.decode_all(text):
            for line in decoded.splitlines():
                line = line.strip()
                if line.startswith(CFG.ALLOWED_SCHEMES):
                    all_configs.add(line)
    log.info(f"   ✅ {len(all_configs)} کانفیگ یکتا (رشته‌ای)")

    parsed_list: List[ParsedConfig] = []
    parse_fail = 0
    for c in all_configs:
        pc = ConfigParser.parse(c)
        if pc:
            parsed_list.append(pc)
        else:
            parse_fail += 1
    log.info(f"   ✅ {len(parsed_list)} پارس موفق | {parse_fail} پارس ناموفق")

    # dedup هوشمند: در host:port تکراری، باارزش‌ترین پروتکل می‌ماند
    by_hostport = {}
    for pc in parsed_list:
        key = (pc.host, pc.port)
        cur = by_hostport.get(key)
        if cur is None or config_rank(pc) > config_rank(cur):
            by_hostport[key] = pc
    parsed_list = list(by_hostport.values())
    log.info(f"   ✅ {len(parsed_list)} پس از dedup هوشمند بر اساس host:port")

    if len(parsed_list) > CFG.max_candidates:
        random.shuffle(parsed_list)
        parsed_list = parsed_list[:CFG.max_candidates]
    return parsed_list


async def run_pipeline(dry_run: bool = False, top: int = 0) -> int:
    start = time.time()
    log.info("=" * 60)
    log.info("🚀 V2Ray Smart Collector v4 (Modular/Golden)")
    log.info("=" * 60)
    with HistoryDB(CFG.db_path,
                   ewma_decay=CFG.ewma_decay,
                   min_history_samples=CFG.min_history_samples) as db:
        try:
            raw = await _stage_fetch()
            parsed = _stage_parse(raw)

            # فیلتر SNI — نسل جدید: فقط کانفیگ‌های TLS/Reality، DNS+اعتبار SNI
            log.info("🛰 مرحله 2.5: فیلتر SNI...")
            sni = SniChecker(check=CFG.sni_check)
            parsed = await sni.filter(parsed)
            log.info(f"   ✅ {len(parsed)} پس از فیلتر SNI")

            log.info("🧪 مرحله 3: تست شبکه...")
            tester = AdvancedTester()
            tested = tester.test_all(parsed)

            log.info("🌍 مرحله 4: جغرافیا (async)...")
            geo = GeoLocator(db)
            geo_map = await geo.resolve_all([r.host for r in tested])
            log.info(f"   ✅ {len(geo_map)} میزبان geo-resolve شد ({geo.api_calls} کال API)")

            log.info("🎯 مرحله 5: امتیازدهی (EWMA + پورت طلایی)...")
            scorer = SmartScorer(db, geo_map)
            scored = scorer.score_all(tested)

            if CFG.golden_filter_only:
                golden = set(CFG.golden_ports_t1) | set(CFG.golden_ports_t2)
                before = len(scored)
                scored = [n for n in scored if n.port in golden]
                log.info(f"   🔥 فیلتر پورت طلایی: {before} -> {len(scored)}")

            log.info("🧪 مرحله 5.5: تست واقعی اتصال (Xray)...")
            scored = await run_real_tests(scored)

            seen = set()
            final: List[ScoredNode] = []
            for n in scored:
                key = f"{n.host}:{n.port}"
                if key not in seen:
                    seen.add(key)
                    final.append(n)
                if len(final) >= CFG.top_n_final:
                    break
            log.info(f"   🏆 {len(final)} کانفیگ نهایی")

            for n in final:
                db.record(n.host, n.port, n.ping, n.score, success=True)

            if top and top > 0:
                log.info(f"📋 {min(top, len(final))} نود برتر:")
                for n in final[:top]:
                    log.info(f"   [{n.score:7.1f}] {n.protocol:9} {n.flag} {n.host}:{n.port} ping={n.ping}ms")

            log.info("📤 مرحله 6: ساخت فایل‌ها و ارسال تلگرام...")
            sender = TelegramSender()
            parts = sender.build(final)
            if not dry_run:
                await sender.send_all(parts)

            log.info("=" * 60)
            log.info(f"✨ تمام شد در {time.time() - start:.1f}s — پارت‌ها: {len(parts)}")
            log.info(f"📊 منابع: {len(CFG.sources)} | پارس: {len(parsed)} | "
                      f"تست: {len(tested)} | ارسال: {len(final)}")
            log.info("=" * 60)
            return 0
        except Exception as e:
            log.exception(f"❌ خطای بحرانی: {e}")
            return 1