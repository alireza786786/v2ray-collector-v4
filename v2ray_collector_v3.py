#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V2Ray Smart Collector — لانچر سازگار با نسخه‌های قبلی.
معادل:  python -m v2ray_collector run --config config.yaml
"""
import sys

from v2ray_collector.cli import main

if __name__ == "__main__":
    sys.exit(main())