# -*- coding: utf-8 -*-
"""رابط خط فرمان v4 — بدون دست‌زدن به کد، همه‌چیز از CLI و config.yaml.

نمونه‌ها:
  python -m v2ray_collector run
  python -m v2ray_collector run --config my.yaml --dry-run --top 10
  v2ray-collector run -v
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from .pipeline import run_pipeline

log = logging.getLogger("v2ray")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="v2ray-collector",
        description="V2Ray Smart Collector v4 — خودکار، هوشمند، مهندسی",
    )
    p.add_argument("--config", default=None,
                   help="مسیر config.yaml (پیش‌فرض: config.yaml در پوشه جاری؛ اگر نبود، پیش‌فرض‌ها)")
    p.add_argument("--dry-run", action="store_true",
                   help="فقط ساخت فایل‌ها و گزارش — بدون ارسال تلگرام")
    p.add_argument("--top", type=int, default=0,
                   help="چاپ N نود برتر در پایان")
    p.add_argument("-v", "--verbose", action="store_true",
                   help="لاگ دقیق‌تر (DEBUG)")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )

    from .config import load_config
    cfg = load_config(args.config)
    log.info(f"⚙️  پیکربندی: {len(cfg.sources)} منبع | vmess={'بله' if cfg.include_vmess else 'خیر'} "
             f"| پورت طلایی T1={tuple(cfg.golden_ports_t1)}")

    try:
        exit_code = asyncio.run(run_pipeline(dry_run=args.dry_run, top=args.top))
        return exit_code or 0
    except KeyboardInterrupt:
        log.warning("⚠️ لغو شد توسط کاربر")
        return 130