# -*- coding: utf-8 -*-
"""ظ¾غŒع©ط±ط¨ظ†ط¯غŒ v4: ظ¾غŒط´â€Œظپط±ط¶â€Œظ‡ط§ â†گ ظپط§غŒظ„ config.yaml â†گ override ظ…طھط؛غŒط± ظ…ط­غŒط·غŒ.

طھظˆع©ظ†/ط¢غŒط¯غŒ طھظ„ع¯ط±ط§ظ… ظپظ‚ط· ط§ط² env (BOT_TOKEN / CHAT_ID) ط®ظˆط§ظ†ط¯ظ‡ ظ…غŒâ€Œط´ظˆط¯ ظˆ ظ‡ط±ع¯ط²
ط¯ط± ظپط§غŒظ„ YAML ظ‚ط±ط§ط± ظ†ظ…غŒâ€Œع¯غŒط±ط¯.
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
    """ظ‡ظ…ظ‡ طھظ†ط¸غŒظ…ط§طھ ط¨ط±ظ†ط§ظ…ظ‡. ظ†ط§ظ… ظپغŒظ„ط¯ظ‡ط§ = ع©ظ„غŒط¯ظ‡ط§غŒ config.yaml."""

    # طھظ„ع¯ط±ط§ظ… ظˆ ع©ط§ظ†ط§ظ„
    bot_token: str = ""
    chat_id: str = ""
    channel_tag: str = "Goodbaye_filtering"
    telegram_link: str = "https://t.me/Goodbaye_filtering"
    group_link: str = "https://t.me/CONFIG_V2RAY_VIP"

    # ظ…ظ†ط§ط¨ط¹
    sources: Tuple[str, ...] = field(default_factory=lambda: _DEFAULT_SOURCES)

    # ظ…ط­ط¯ظˆط¯غŒطھâ€Œظ‡ط§ ظˆ ط²ظ…ط§ظ†â€Œظ‡ط§
    max_workers: int = 50
    max_candidates: int = 1500
    top_n_final: int = 500
    chunk_size: int = 150
    stability_rounds: int = 2
    tcp_timeout: float = 1.5
    tls_timeout: float = 2.5
    max_ping_ms: int = 400
    max_tls_ping_ms: int = 600

    # ظ¾ط±ظˆطھع©ظ„â€Œظ‡ط§
    include_vmess: bool = True

    # ظ¾ظˆط±طھâ€Œظ‡ط§غŒ ط·ظ„ط§غŒغŒ
    golden_ports_t1: Tuple[int, ...] = (443, 2053, 2083, 2087, 2096, 8443)
    golden_ports_t2: Tuple[int, ...] = (80, 2052, 2082, 2086, 8080, 8880)
    golden_bonus_t1: int = 180
    golden_bonus_t2: int = 80
    golden_t1_reality_extra: int = 60
    golden_only_tls: bool = True
    golden_filter_only: bool = False

    # ط§ظ…طھغŒط§ط²ط¯ظ‡غŒ ظ†ط³ظ„ ط¬ط¯غŒط¯ (EWMA)
    ewma_decay: float = 0.7
    min_history_samples: int = 3

    # ظپغŒظ„طھط± SNI
    sni_check: bool = True

    # ط¬ط؛ط±ط§ظپغŒط§
    geo_max_concurrent: int = 20
    geo_timeout: float = 3.0
    geo_max_calls_per_run: int = 800

    # طھط³طھ ظˆط§ظ‚ط¹غŒ Xray
    real_test_enabled: bool = True
    real_test_max_candidates: int = 250
    real_test_concurrency: int = 15
    real_test_url: str = "http://cp.cloudflare.com/generate_204"
    real_test_timeout: float = 5.0

    # ط¯غŒطھط§ط¨غŒط³
    db_path: str = "history.db"

    @property
    def ALLOWED_SCHEMES(self) -> Tuple[str, ...]:
        return _BASE_SCHEMES + (("vmess://",) if self.include_vmess else ())


# Globals â€” ط¨ظ‡â€Œط±ظˆط²ط±ط³ط§ظ†غŒ طھظˆط³ط· load_config
CFG: Config = Config()


def load_config(path: Optional[str] = None) -> Config:
    """ط¨ط§ط±ع¯غŒط±غŒ ظ¾غŒع©ط±ط¨ظ†ط¯غŒ: ظ¾غŒط´â€Œظپط±ط¶â€Œظ‡ط§ â†گ YAML â†گ ظ…طھط؛غŒط± ظ…ط­غŒط·غŒ (ظپظ‚ط· طھظˆع©ظ†/ط¢غŒط¯غŒ).

    ظ†ع©طھظ‡â€ŒغŒ ظ…ظ‡ظ…: ط¨ظ‡â€Œط¬ط§غŒ ط³ط§ط®طھظ† غŒع© ط´غŒط، Config ط¬ط¯غŒط¯ ظˆ ط¬ط§غŒع¯ط²غŒظ† ع©ط±ط¯ظ† CFG ط³ط±ط§ط³ط±غŒ
    (ع©ظ‡ ط¨ط§ط¹ط« ظ…غŒâ€Œط´ط¯ ظپط§غŒظ„â€Œظ‡ط§غŒغŒ ظ…ط«ظ„ telegram.py ع©ظ‡ ط¨ط§ آ«from .config import CFGآ»
    غŒع© ع©ظ¾غŒ ط§ط² ط±ظپط±ظ†ط³ ظ‚ط¯غŒظ…غŒ ع¯ط±ظپطھظ‡â€Œط§ظ†ط¯طŒ ظ‡غŒع†â€Œظˆظ‚طھ ظ…ظ‚ط¯ط§ط± طھط§ط²ظ‡ ط±ط§ ظ†ط¨غŒظ†ظ†ط¯)طŒ ظ…ظ‚ط¯ط§ط±ظ‡ط§
    ط±ط§ ظ…ط³طھظ‚غŒظ…ط§ظ‹ ط±ظˆغŒ ظ‡ظ…ط§ظ† ط´غŒط، CFG ظ…ظˆط¬ظˆط¯ ظ…غŒâ€Œظ†ظˆغŒط³غŒظ… طھط§ ظ‡ظ…ظ‡â€Œط¬ط§ ظ‡ظ…â€Œط²ظ…ط§ظ† ط¨ظ‡â€Œط±ظˆط² ط´ظˆط¯.
    """
    global CFG

    defaults = Config()
    for f in defaults.__dataclass_fields__:
        setattr(CFG, f, getattr(defaults, f))

    if yaml is not None:
        ypath = path or os.path.join(os.getcwd(), "config.yaml")
        if os.path.exists(ypath):
            with open(ypath, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            for key, value in data.items():
                if hasattr(CFG, key) and key not in ("bot_token", "chat_id"):
                    if isinstance(value, list):
                        value = tuple(value)
                    setattr(CFG, key, value)

    # ط§ظ…ظ†غŒطھ: طھظˆع©ظ† ظˆ ط¢غŒط¯غŒ ظپظ‚ط· ط§ط² env â€” ظ‡ط±ع¯ط² ط§ط² ظپط§غŒظ„ ظ¾غŒع©ط±ط¨ظ†ط¯غŒ
    CFG.bot_token = os.environ.get("BOT_TOKEN", "")
    CFG.chat_id = os.environ.get("CHAT_ID", "")

    return CFG
