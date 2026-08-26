#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Isyzan VPN - клиент с автоматическим получением подписок
Версия: 1.0.0
"""

import asyncio
import json
import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, Dict, List

from config import Config
from subscription_fetcher import SubscriptionFetcher
from xray_wrapper import XrayWrapper
from obfuscator import TrafficObfuscator
from auto_updater import AutoUpdater

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler('/var/log/isyzan.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('isyzan')

class IsyzanVPN:
    def __init__(self, config_path: str = 'configs/default_config.json'):
        self.config = Config(config_path)
        self.xray = XrayWrapper(self.config)
        self.fetcher = SubscriptionFetcher(self.config)
        self.obfuscator = TrafficObfuscator(self.config)
        self.updater = AutoUpdater(self.config)
        self.running = False
        self.current_node = None
        
    async def fetch_subscriptions(self) -> List[Dict]:
        """Получение подписок с популярных сервисов"""
        subscriptions = []
        
        # Автоматический сбор с публичных источников
        sources = self.config.get('subscription_sources', [])
        for source in sources:
            try:
                data = await self.fetcher.fetch(source['url'])
                parsed = self.fetcher.parse_v2ray_subscription(data)
                subscriptions.extend(parsed)
                logger.info(f"Получено {len(parsed)} узлов от {source['name']}")
            except Exception as e:
                logger.error(f"Ошибка получения от {source['name']}: {e}")
                
        # Дублирование конфигов с автоматическим клонированием
        if self.config.get('auto_clone_popular', False):
            cloned = await self.fetcher.clone_popular_service()
            subscriptions.extend(cloned)
            
        return self.deduplicate(subscriptions)
    
    def deduplicate(self, nodes: List[Dict]) -> List[Dict]:
        """Удаление дубликатов"""
        seen = set()
        unique = []
        for node in nodes:
            key = f"{node.get('address')}:{node.get('port')}:{node.get('protocol')}"
            if key not in seen:
                seen.add(key)
                unique.append(node)
        return unique
    
    async def select_best_node(self, nodes: List[Dict]) -> Optional[Dict]:
        """Выбор оптимального узла по скорости и доступности"""
        best_node = None
        best_latency = float('inf')
        
        for node in nodes:
            latency = await self.xray.test_latency(node)
            if latency < best_latency and latency > 0:
                best_latency = latency
                best_node = node
                
        logger.info(f"Выбран узел: {best_node['address']} (latency: {best_latency}ms)")
        return best_node
    
    async def run(self):
        """Основной цикл"""
        self.running = True
        signal.signal(signal.SIGTERM, self.shutdown)
        signal.signal(signal.SIGINT, self.shutdown)
        
        # Запуск автообновления
        asyncio.create_task(self.updater.watch_updates())
        
        while self.running:
            try:
                # Получение подписок
                nodes = await self.fetch_subscriptions()
                
                if not nodes:
                    logger.warning("Нет доступных узлов, повтор через 60с")
                    await asyncio.sleep(60)
                    continue
                
                # Выбор узла
                self.current_node = await self.select_best_node(nodes)
                
                if self.current_node:
                    # Запуск Xray с обфускацией
                    await self.obfuscator.apply(self.current_node)
                    await self.xray.start(self.current_node)
                    
                    # Мониторинг соединения
                    while self.running and self.current_node:
                        if not await self.xray.check_connection():
                            logger.warning("Соединение потеряно, переподключение")
                            break
                        await asyncio.sleep(10)
                    
                    self.xray.stop()
                    
            except Exception as e:
                logger.error(f"Ошибка: {e}")
                await asyncio.sleep(5)
    
    def shutdown(self, signum=None, frame=None):
        """Корректное завершение"""
        logger.info("Завершение работы...")
        self.running = False
        self.xray.stop()

if __name__ == '__main__':
    vpn = IsyzanVPN()
    asyncio.run(vpn.run())
