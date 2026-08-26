#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Optional

class AutoUpdater:
    def __init__(self, config):
        self.config = config
        self.current_version = "1.0.0"
        self.update_url = "https://api.github.com/repos/isyzan/isyzan-vpn/releases/latest"
        
    async def watch_updates(self):
        """Наблюдение за обновлениями"""
        interval = self.config.get('update_interval_seconds', 3600)
        
        while True:
            try:
                await self.check_and_update()
            except Exception as e:
                print(f"Ошибка обновления: {e}")
                
            await asyncio.sleep(interval)
    
    async def check_and_update(self):
        """Проверка и установка обновлений"""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get(self.update_url) as response:
                if response.status == 200:
                    data = await response.json()
                    latest_version = data.get('tag_name', '').lstrip('v')
                    
                    if latest_version > self.current_version:
                        await self.perform_update(data)
    
    async def perform_update(self, release_data: Dict):
        """Выполнение обновления"""
        import aiohttp
        import aiofiles
        
        # Поиск ассета
        assets = release_data.get('assets', [])
        if not assets:
            return
            
        asset = assets[0]
        download_url = asset.get('browser_download_url')
        
        if not download_url:
            return
            
        # Скачивание обновления
        async with aiohttp.ClientSession() as session:
            async with session.get(download_url) as response:
                if response.status == 200:
                    content = await response.read()
                    
                    # Сохранение
                    async with aiofiles.open('/tmp/isyzan_update', 'wb') as f:
                        await f.write(content)
                    
                    # Замена бинарника
                    subprocess.run(['chmod', '+x', '/tmp/isyzan_update'])
                    subprocess.run(['mv', '/tmp/isyzan_update', '/usr/local/bin/isyzan-vpn'])
                    
                    print("Обновление установлено, перезапуск...")
                    subprocess.run(['systemctl', 'restart', 'isyzan-vpn'])
