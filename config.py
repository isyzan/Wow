#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from pathlib import Path
from typing import Any, Dict

class Config:
    def __init__(self, config_path: str):
        self.path = Path(config_path)
        self.data = self._load()
        
    def _load(self) -> Dict[str, Any]:
        if not self.path.exists():
            # Создание конфигурации по умолчанию
            default = {
                "xray_path": "/usr/local/bin/xray",
                "log_level": "info",
                "subscription_sources": [
                    {
                        "name": "v2ray_free",
                        "url": "https://raw.githubusercontent.com/freefq/free/master/v2",
                        "type": "v2ray"
                    },
                    {
                        "name": "proxy_list",
                        "url": "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/vless/data.txt",
                        "type": "vless"
                    }
                ],
                "auto_clone_popular": True,
                "update_interval_seconds": 3600,
                "obfuscation": {
                    "enabled": True,
                    "method": "tls_fingerprint",
                    "tls_camouflage": "chrome_120",
                    "padding_enabled": True,
                    "traffic_mixing": True
                },
                "dns_over_https": [
                    "https://1.1.1.1/dns-query",
                    "https://dns.google/dns-query"
                ],
                "fake_sni": [
                    "www.google.com",
                    "www.microsoft.com",
                    "www.cloudflare.com"
                ]
            }
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(default, indent=4, ensure_ascii=False))
            return default
        return json.loads(self.path.read_text(encoding='utf-8'))
    
    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split('.')
        value = self.data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
            else:
                return default
        return value
    
    def set(self, key: str, value: Any):
        keys = key.split('.')
        data = self.data
        for k in keys[:-1]:
            if k not in data:
                data[k] = {}
            data = data[k]
        data[keys[-1]] = value
        self.save()
        
    def save(self):
        self.path.write_text(json.dumps(self.data, indent=4, ensure_ascii=False))
