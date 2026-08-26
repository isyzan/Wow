#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, Optional

class XrayWrapper:
    def __init__(self, config):
        self.config = config
        self.process = None
        self.config_file = None
        
    def generate_xray_config(self, node: Dict) -> str:
        """Генерация конфигурации Xray"""
        protocol = node.get('protocol', 'vmess')
        
        if protocol == 'vmess':
            config = {
                "log": {"loglevel": "warning"},
                "inbounds": [{
                    "port": 10808,
                    "listen": "127.0.0.1",
                    "protocol": "socks",
                    "settings": {
                        "udp": True,
                        "auth": "noauth"
                    },
                    "sniffing": {
                        "enabled": True,
                        "destOverride": ["http", "tls"]
                    }
                }],
                "outbounds": [{
                    "protocol": "vmess",
                    "settings": {
                        "vnext": [{
                            "address": node['address'],
                            "port": int(node['port']),
                            "users": [{
                                "id": node['uuid'],
                                "alterId": int(node.get('aid', 0)),
                                "security": "auto"
                            }]
                        }]
                    },
                    "streamSettings": {
                        "network": node.get('network', 'ws'),
                        "security": node.get('tls', 'none'),
                        "wsSettings": {
                            "path": node.get('path', '/'),
                            "headers": {
                                "Host": node.get('host', '')
                            }
                        } if node.get('network') == 'ws' else None,
                        "tlsSettings": {
                            "serverName": node.get('sni', node['address']),
                            "allowInsecure": False,
                            "fingerprint": "chrome"
                        } if node.get('tls') == 'tls' else None
                    },
                    "tag": "proxy"
                }],
                "dns": {
                    "servers": [
                        "https+local://1.1.1.1/dns-query",
                        "https+local://8.8.8.8/dns-query"
                    ]
                },
                "routing": {
                    "domainStrategy": "IPIfNonMatch",
                    "rules": [
                        {
                            "type": "field",
                            "outboundTag": "proxy",
                            "network": "tcp,udp"
                        }
                    ]
                }
            }
            
        elif protocol == 'vless':
            config = {
                "log": {"loglevel": "warning"},
                "inbounds": [{
                    "port": 10808,
                    "listen": "127.0.0.1",
                    "protocol": "socks",
                    "settings": {"udp": True}
                }],
                "outbounds": [{
                    "protocol": "vless",
                    "settings": {
                        "vnext": [{
                            "address": node['address'],
                            "port": int(node['port']),
                            "users": [{
                                "id": node['uuid'],
                                "encryption": "none",
                                "flow": node.get('flow', '')
                            }]
                        }]
                    },
                    "streamSettings": {
                        "network": node.get('network', 'tcp'),
                        "security": node.get('security', 'reality'),
                        "realitySettings": {
                            "serverName": node.get('sni', 'www.microsoft.com'),
                            "publicKey": node.get('public_key', ''),
                            "shortId": node.get('short_id', ''),
                            "fingerprint": "chrome"
                        } if node.get('security') == 'reality' else None,
                        "tlsSettings": {
                            "serverName": node.get('sni', ''),
                            "fingerprint": "chrome"
                        } if node.get('security') == 'tls' else None
                    },
                    "tag": "proxy"
                }],
                "routing": {
                    "rules": [{
                        "type": "field",
                        "outboundTag": "proxy",
                        "network": "tcp,udp"
                    }]
                }
            }
            
        else:
            raise ValueError(f"Неподдерживаемый протокол: {protocol}")
            
        return json.dumps(config, indent=2)
    
    async def start(self, node: Dict):
        """Запуск Xray"""
        self.stop()
        
        config_json = self.generate_xray_config(node)
        
        # Запись временного конфига
        self.config_file = tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.json',
            delete=False
        )
        self.config_file.write(config_json)
        self.config_file.close()
        
        # Запуск процесса
        self.process = subprocess.Popen(
            [self.config.get('xray_path'), '-config', self.config_file.name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        await asyncio.sleep(1)
        return self.process.poll() is None
    
    def stop(self):
        """Остановка Xray"""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
            
        if self.config_file and os.path.exists(self.config_file.name):
            os.unlink(self.config_file.name)
            self.config_file = None
    
    async def test_latency(self, node: Dict) -> float:
        """Тестирование задержки узла"""
        start_time = time.time()
        try:
            if await self.start(node):
                # Проверка соединения через прокси
                result = subprocess.run(
                    ['curl', '-s', '-o', '/dev/null', '-w', '%{time_total}',
                     '--socks5', '127.0.0.1:10808', '--max-time', '5',
                     'https://www.google.com'],
                    capture_output=True,
                    timeout=6
                )
                if result.returncode == 0:
                    latency = float(result.stdout.decode()) * 1000
                    self.stop()
                    return latency
            self.stop()
            return -1
        except Exception:
            self.stop()
            return -1
    
    async def check_connection(self) -> bool:
        """Проверка активности соединения"""
        if not self.process:
            return False
            
        try:
            result = subprocess.run(
                ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}',
                 '--socks5', '127.0.0.1:10808', '--max-time', '3',
                 'http://www.gstatic.com/generate_204'],
                capture_output=True,
                timeout=4
            )
            return result.returncode == 0 and result.stdout.decode() == '204'
        except:
            return False
