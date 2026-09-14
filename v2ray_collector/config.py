# -*- coding: utf-8 -*-
"""پیکربندی v4: پیش‌فرض‌ها ← فایل config.yaml ← override محیطی.

توکن/آیدی تلگرام فقط از env (BOT_TOKEN / CHAT_ID) خوانده می‌شود و هرگز
در فایل YAML قرار نمی‌گیرد.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional, Tuple

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # pragma: no cover
    pass

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


_DEFAULT_SOURCES: Tuple[str, ...] = (
    "https://raw.githubusercontent.com/iboxz/free-v2ray-collector/main/main/vless.txt",
    "https://raw.githubusercontent.com/0xRadikal/Free-v2ray-Configs/main/top100.txt",
    "https://raw.githubusercontent.com/mohamadfg-dev/telegram-v2ray-configs-collector/main/category/vless.txt",
    "https://raw.githubusercontent.com/SoliSpirit/SolVPN/main/Protocols/vless.txt",
    "https://raw.githubusercontent.com/V2RAYCONFIGSPOOL/V2RAY_SUB/main/v2ray_configs_no1.txt",
    "https://raw.githubusercontent.com/V2RAYCONFIGSPOOL/V2RAY_SUB/main/v2ray_configs_no2.txt",
    "https://raw.githubusercontent.com/V2RAYCONFIGSPOOL/V2RAY_SUB/main/v2ray_configs_no3.txt",
    "https://raw.githubusercontent.com/V2RAYCONFIGSPOOL/V2RAY_SUB/main/v2ray_configs_no4.txt",
    "https://raw.githubusercontent.com/V2RAYCONFIGSPOOL/V2RAY_SUB/main/v2ray_configs_no5.txt",
    "https://raw.githubusercontent.com/V2RAYCONFIGSPOOL/V2RAY_SUB/main/v2ray_configs_no6.txt",
    "https://raw.githubusercontent.com/V2RAYCONFIGSPOOL/V2RAY_SUB/main/v2ray_configs_no7.txt",
    "https://raw.githubusercontent.com/V2RAYCONFIGSPOOL/V2RAY_SUB/main/v2ray_configs_no8.txt",
    "https://raw.githubusercontent.com/V2RAYCONFIGSPOOL/V2RAY_SUB/main/v2ray_configs_no9.txt",
    "https://raw.githubusercontent.com/V2RAYCONFIGSPOOL/V2RAY_SUB/main/v2ray_configs_no10.txt",
    "https://raw.githubusercontent.com/Q3dlaXpoaQ/Q3dlaXpoaQ.github.io/main/APIs/cg1.txt",
    "https://raw.githubusercontent.com/mahsanet/MahsaFreeConfig/main/mci/sub_1.txt",
    "https://raw.githubusercontent.com/mahsanet/MahsaFreeConfig/main/mtn/sub_1.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/Vless-Reality-White-Lists-Rus-Mobile.txt",
    "https://raw.githubusercontent.com/ShatakVPN/ConfigForge-V2Ray/main/configs/ir/vless.txt",
    "https://raw.githubusercontent.com/Surfboardv2ray/TGParse/main/splitted/hysteria2",
    "https://raw.githubusercontent.com/MohammadBahemmat/V2ray-Collector/main/all_servers.txt",
    "https://raw.githubusercontent.com/MahanKenway/Freedom-V2Ray/main/configs/vless_sub.txt",
)

_BASE_SCHEMES: Tuple[str, ...] = (
    "vless://", "ss://", "hysteria2://", "hy2://", "trojan://",
)


@dataclass
class Config:
    """همه تنظیمات برنامه. نام فیلدها = کلیدهای config.yaml."""

    # تلگرام و کانال
    bot_token: str = ""
    chat_id: str = ""
    channel_tag: str = "Goodbaye_filtering"
    telegram_link: str = "https://t.me/Goodbaye_filtering"
    group_link: str = "https://t.me/CONFIG_V2RAY_VIP"

    # منابع
    sources: Tuple[str, ...] = field(default_factory=lambda: _DEFAULT_SOURCES)

    # محدودیت‌ها و زمان‌ها
    max_workers: int = 50
    max_candidates: int = 1500
    top_n_final: int = 500
    chunk_size: int = 150
    stability_rounds: int = 2
    tcp_timeout: float = 1.5
    tls_timeout: float = 2.5
    max_ping_ms: int = 400
    max_tls_ping_ms: int = 600

    # پروتکل‌ها
    include_vmess: bool = False  # ✅ پیش‌فرض: false برای کیفیت بهتر

    # پورت‌های طلایی (برای Iran خاص‌شده)
    golden_ports_t1: Tuple[int, ...] = (443, 2053, 2083, 2087, 2096, 8443)
    golden_ports_t2: Tuple[int, ...] = (80, 2052, 2082, 2086, 8080, 8880)
    golden_bonus_t1: int = 180
    golden_bonus_t2: int = 80
    golden_t1_reality_extra: int = 60
    golden_only_tls: bool = True  # فقط TLS/Reality
    golden_filter_only: bool = False  # اگر True، فقط پورت‌های طلایی

    # امتیازدهی نسل جدید (EWMA)
    ewma_decay: float = 0.7
    min_history_samples: int = 3

    # فیلتر SNI
    sni_check: bool = True
    sni_timeout: float = 2.0  # ✅ اضافه شد: timeout برای DNS

    # جغرافیا
    geo_max_concurrent: int = 20
    geo_timeout: float = 3.0
    geo_max_calls_per_run: int = 800

    # تست واقعی Xray
    real_test_enabled: bool = True
    real_test_max_candidates: int = 100  # ✅ کاهش برای کیفیت بهتر
    real_test_concurrency: int = 10      # ✅ کاهش
    real_test_url: str = "http://cp.cloudflare.com/generate_204"
    real_test_timeout: float = 3.0       # ✅ کاهش برای تست سریع‌تر

    # دیتابیس
    db_path: str = "history.db"

    @property
    def ALLOWED_SCHEMES(self) -> Tuple[str, ...]:
        return _BASE_SCHEMES + (("vmess://",) if self.include_vmess else ())


# Globals — به‌روزرسانی توسط load_config
CFG: Config = Config()


def load_config(path: Optional[str] = None) -> Config:
    """بارگیری پیکربندی: پیش‌فرض‌ها ← YAML ← متغیر محیطی.

    نکته مهم: برای امنیت، توکن و آیدی تنها از env خوانده می‌شود و هرگز
    (حتی اگر در YAML باشد) override نمی‌شود.
    """
    global CFG

    defaults = Config()
    for f in defaults.__dataclass_fields__:
        setattr(CFG, f, getattr(defaults, f))

    if yaml is not None:
        ypath = path or os.path.join(os.getcwd(), "config.yaml")
        if os.path.exists(ypath):
            try:
                with open(ypath, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                for key, value in data.items():
                    if hasattr(CFG, key) and key not in ("bot_token", "chat_id"):
                        if isinstance(value, list):
                            value = tuple(value)
                        setattr(CFG, key, value)
            except Exception as e:
                import logging
                logging.getLogger("v2ray").warning(f"⚠️ خطا در خواندن {ypath}: {e}")

    # امنیت: توکن و آیدی فقط از env
    CFG.bot_token = os.environ.get("BOT_TOKEN", "")
    CFG.chat_id = os.environ.get("CHAT_ID", "")

    return CFG
