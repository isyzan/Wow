#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import aiohttp
import base64
import json
import re
from typing import Dict, List, Optional
from urllib.parse import unquote, urlparse

class SubscriptionFetcher:
    def __init__(self, config):
        self.config = config
        self.session = None
        
    async def fetch(self, url: str) -> str:
        """Получение подписки"""
        if not self.session:
            self.session = aiohttp.ClientSession()
            
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
        }
        
        async with self.session.get(url, headers=headers, timeout=30) as response:
            if response.status == 200:
                return await response.text()
            raise Exception(f"HTTP {response.status}")
    
    def parse_v2ray_subscription(self, data: str) -> List[Dict]:
        """Парсинг подписки формата v2ray"""
        nodes = []
        
        # Проверка на base64
        if re.match(r'^[A-Za-z0-9+/=]+$', data.strip()):
            try:
                data = base64.b64decode(data).decode('utf-8')
            except:
                pass
        
        # Парсинг каждой строки
        for line in data.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
                
            try:
                node = self.parse_single_node(line)
                if node:
                    nodes.append(node)
            except Exception:
                continue
                
        return nodes
    
    def parse_single_node(self, uri: str) -> Optional[Dict]:
        """Парсинг одного узла"""
        parsed = urlparse(uri)
        
        if parsed.scheme == 'vmess':
            return self._parse_vmess(parsed, uri)
        elif parsed.scheme == 'vless':
            return self._parse_vless(parsed, uri)
        elif parsed.scheme == 'trojan':
            return self._parse_trojan(parsed, uri)
        elif parsed.scheme == 'ss':
            return self._parse_shadowsocks(parsed, uri)
            
        return None
    
    def _parse_vmess(self, parsed, uri: str) -> Dict:
        """Парсинг VMess"""
        try:
            decoded = base64.b64decode(parsed.netloc + '==').decode('utf-8')
            data = json.loads(decoded)
            return {
                'protocol': 'vmess',
                'address': data.get('add', ''),
                'port': int(data.get('port', 443)),
                'uuid': data.get('id', ''),
                'aid': int(data.get('aid', 0)),
                'network': data.get('net', 'ws'),
                'path': data.get('path', '/'),
                'host': data.get('host', ''),
                'tls': data.get('tls', 'none'),
                'sni': data.get('sni', data.get('host', ''))
            }
        except:
            return None
    
    def _parse_vless(self, parsed, uri: str) -> Dict:
        """Парсинг VLESS"""
        try:
            netloc_parts = parsed.netloc.split('@')
            user_info = netloc_parts[0]
            server_info = netloc_parts[1]
            
            uuid = user_info
            address = server_info.split(':')[0]
            port = int(server_info.split(':')[1])
            
            query_params = {}
            for param in parsed.query.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    query_params[key] = unquote(value)
            
            return {
                'protocol': 'vless',
                'address': address,
                'port': port,
                'uuid': uuid,
                'network': query_params.get('type', 'tcp'),
                'security': query_params.get('security', 'none'),
                'sni': query_params.get('sni', ''),
                'flow': query_params.get('flow', ''),
                'public_key': query_params.get('pbk', ''),
                'short_id': query_params.get('sid', ''),
                'path': query_params.get('path', '/'),
                'host': query_params.get('host', '')
            }
        except:
            return None
    
    def _parse_trojan(self, parsed, uri: str) -> Dict:
        """Парсинг Trojan"""
        try:
            netloc_parts = parsed.netloc.split('@')
            password = netloc_parts[0]
            server_info = netloc_parts[1]
            address = server_info.split(':')[0]
            port = int(server_info.split(':')[1])
            
            query_params = {}
            for param in parsed.query.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    query_params[key] = unquote(value)
            
            return {
                'protocol': 'trojan',
                'address': address,
                'port': port,
                'password': password,
                'sni': query_params.get('sni', address)
            }
        except:
            return None
    
    def _parse_shadowsocks(self, parsed, uri: str) -> Dict:
        """Парсинг Shadowsocks"""
        try:
            user_info = base64.b64decode(parsed.netloc.split('@')[0] + '==').decode('utf-8')
            method, password = user_info.split(':', 1)
            server_info = parsed.netloc.split('@')[1]
            address = server_info.split(':')[0]
            port = int(server_info.split(':')[1])
            
            return {
                'protocol': 'shadowsocks',
                'address': address,
                'port': port,
                'method': method,
                'password': password
            }
        except:
            return None
    
    async def clone_popular_service(self) -> List[Dict]:
        """Автоматическое клонирование подписок с популярных сервисов"""
        nodes = []
        
        # Источники подписок
        urls = [
            'https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/Sub1.txt',
            'https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/Sub2.txt',
            'https://raw.githubusercontent.com/aiboboxx/v2rayfree/main/v2',
            'https://raw.githubusercontent.com/Pawdroid/Free-servers/main/sub',
            'https://raw.githubusercontent.com/mahdibland/V2RayAggregator/master/sub/sub_merge.txt'
        ]
        
        for url in urls:
            try:
                data = await self.fetch(url)
                parsed = self.parse_v2ray_subscription(data)
                nodes.extend(parsed)
            except:
                continue
                
        return nodes
    
    async def close(self):
        if self.session:
            await self.session.close()
