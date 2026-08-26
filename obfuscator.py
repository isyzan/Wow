#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import random
import string
from typing import Dict

class TrafficObfuscator:
    def __init__(self, config):
        self.config = config
        
    async def apply(self, node: Dict):
        """Применение обфускации к узлу"""
        if not self.config.get('obfuscation.enabled', False):
            return node
            
        # Маскировка TLS-отпечатка
        if node.get('tls') or node.get('security') == 'reality':
            node['fingerprint'] = self._get_chrome_fingerprint()
            
        # Добавление случайного SNI
        fake_sni_list = self.config.get('fake_sni', [])
        if fake_sni_list and node.get('network') == 'ws':
            node['host'] = random.choice(fake_sni_list)
            
        # Добавление случайного пути
        if node.get('network') == 'ws':
            node['path'] = self._generate_random_path()
            
        return node
    
    def _get_chrome_fingerprint(self) -> str:
        """Получение актуального отпечатка Chrome"""
        fingerprints = ['chrome', 'firefox', 'safari', 'edge', 'randomized']
        return random.choice(fingerprints)
    
    def _generate_random_path(self) -> str:
        """Генерация случайного пути для маскировки"""
        paths = [
            '/api/v1/data',
            '/ws/stream',
            '/cdn/connect',
            '/socket.io',
            '/graphql',
            f'/{self._random_string(8)}'
        ]
        return random.choice(paths)
    
    def _random_string(self, length: int) -> str:
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
