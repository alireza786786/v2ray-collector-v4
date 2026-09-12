# -*- coding: utf-8 -*-
"""پارسر کانفیگ: همه پروتکل‌ها + اعتبارسنجی یکپارچه host/port.

vless/trojan/hysteria2/hy2 => URL استاندارد (urlparse)
vmess://  => base64(JSON) ; فیلد add/port (و ps برای نام)
ss://     => base64(method:pass)@host:port  یا کل‌بخش base64 (SIP002 هم پشتیبانی)
"""
from __future__ import annotations

import base64
import ipaddress
import json
import re
from typing import Optional
from urllib.parse import unquote, quote, urlparse

from .models import ParsedConfig

# الگوی لیبل دامنه: ۱ تا ۶۳ کاراکتر، الفبا/عدد/خط تیره، بدون خط تیره ابتدا/انتها
HOST_LABEL_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")


class ConfigParser:

    @staticmethod
    def parse(conf: str) -> Optional[ParsedConfig]:
        try:
            conf = conf.strip()
            if not conf:
                return None
            if conf.startswith("vmess://"):
                return ConfigParser._parse_vmess(conf)
            if conf.startswith("ss://"):
                return ConfigParser._parse_ss(conf)
            p = urlparse(conf)
            if not p.hostname or p.port is None:
                return None
            if not (1 <= p.port <= 65535):
                return None
            if not ConfigParser.is_valid_host(p.hostname):
                return None
            return ParsedConfig(
                raw=conf, scheme=p.scheme, host=p.hostname, port=p.port,
                remark=unquote(p.fragment or ""),
            )
        except Exception:
            return None

    @staticmethod
    def _parse_vmess(conf: str) -> Optional[ParsedConfig]:
        body = conf[len("vmess://"):].split("#", 1)[0]
        pad = "=" * (-len(body) % 4)
        try:
            data = base64.b64decode(body + pad, validate=False)
            obj = json.loads(data.decode("utf-8", errors="ignore"))
        except Exception:
            return None
        host = obj.get("add")
        port = obj.get("port")
        if not host:
            return None
        try:
            port = int(port)
        except (TypeError, ValueError):
            return None
        if not (1 <= port <= 65535):
            return None
        if not ConfigParser.is_valid_host(host):
            return None
        return ParsedConfig(raw=conf, scheme="vmess", host=host, port=port,
                             remark=str(obj.get("ps", "")))

    @staticmethod
    def _parse_ss(conf: str) -> Optional[ParsedConfig]:
        body = conf[len("ss://"):]
        remark = ""
        if "#" in body:
            body, frag = body.split("#", 1)
            remark = unquote(frag)

        # حالت جدید: ss://base64(method:pass)@host:port[?plugin=...]
        if "@" in body:
            _, hostport = body.rsplit("@", 1)
            hostport = hostport.split("/", 1)[0]   # SIP002: plugin/query حذف
            host, _, port_s = hostport.rpartition(":")
            if host.startswith("[") and host.endswith("]"):
                host = host[1:-1]                  # IPv6 براکت‌دار
            if not ConfigParser.is_valid_host(host):
                return None
            try:
                port = int(port_s)
            except ValueError:
                return None
            if not (1 <= port <= 65535):
                return None
            return ParsedConfig(raw=conf, scheme="ss", host=host, port=port, remark=remark)

        # حالت قدیمی: کل بخش base64(method:pass@host:port)
        pad = "=" * (-len(body) % 4)
        try:
            decoded = base64.b64decode(body + pad).decode("utf-8", errors="ignore")
            if "@" not in decoded or ":" not in decoded:
                return None
            _, hostport = decoded.rsplit("@", 1)
            hostport = hostport.split("/", 1)[0]
            host, _, port_s = hostport.rpartition(":")
            if host.startswith("[") and host.endswith("]"):
                host = host[1:-1]
            if not ConfigParser.is_valid_host(host):
                return None
            port = int(port_s)
            if not (1 <= port <= 65535):
                return None
            return ParsedConfig(raw=conf, scheme="ss", host=host, port=port, remark=remark)
        except Exception:
            return None

    @staticmethod
    def rename(raw: str, scheme: str, new_name: str) -> str:
        """بازنویسی تضمینی نام:
        - vmess: فیلد JSON «ps» (تنها جایی که کلاینت‌ها نام را می‌خوانند)
        - بقیه: حذف کامل فرگمنت قبلی و جایگزینی با #{new_name}
        """
        if scheme == "vmess":
            return ConfigParser._rename_vmess(raw, new_name)
        base = raw.split("#", 1)[0]
        return f"{base}#{quote(new_name)}"

    @staticmethod
    def _rename_vmess(raw: str, new_name: str) -> str:
        body = raw[len("vmess://"):].split("#", 1)[0]
        pad = "=" * (-len(body) % 4)
        try:
            data = base64.b64decode(body + pad, validate=False)
            obj = json.loads(data.decode("utf-8", errors="ignore"))
        except Exception:
            return ""  # JSON خراب → قابل rename نیست → منتشر نشود
        obj["ps"] = new_name
        new_body = base64.b64encode(
            json.dumps(obj, ensure_ascii=False).encode("utf-8")
        ).decode()
        return f"vmess://{new_body}"

    @staticmethod
    def is_valid_host(host: str) -> bool:
        """IP (ipaddress) یا دامنه با regex لیبل‌ها؛ سخت‌گیرانه."""
        if not host or len(host) > 253:
            return False
        try:
            ipaddress.ip_address(host)
            return True
        except ValueError:
            pass
        if any(ord(c) > 127 for c in host):
            try:
                host = host.encode("idna").decode("ascii")
            except Exception:
                return False
        host = host.rstrip(".")
        if not host:
            return False
        return all(HOST_LABEL_RE.match(label) for label in host.split("."))