#!/usr/bin/env python3
"""
Автоматическое обнаружение MCP серверов
"""

import os
import importlib
import inspect
import logging
from typing import Dict, Any, List, Type
from pathlib import Path

logger = logging.getLogger(__name__)

class MCPServerDiscovery:
    """Автоматическое обнаружение MCP серверов"""
    
    def __init__(self, servers_dir: str = None):
        """
        Инициализирует обнаружение серверов
        
        Args:
            servers_dir: Путь к папке с серверами (по умолчанию текущая папка)
        """
        self.servers_dir = servers_dir or os.path.dirname(__file__)
        self.discovered_servers = {}
        self._server_instances = {}  # Кэш экземпляров серверов
        self._scan_servers()
    
    def _scan_servers(self):
        """Сканирует папку с серверами и обнаруживает классы"""
        try:
            # Получаем все Python файлы в папке
            servers_path = Path(self.servers_dir)
            python_files = list(servers_path.glob("*.py"))
            
            # Исключаем служебные файлы
            excluded_files = {
                "__init__.py",
                "base_mcp_server.py", 
                "server_discovery.py"
            }
            
            for file_path in python_files:
                if file_path.name in excluded_files:
                    continue
                
                # Извлекаем имя модуля
                module_name = file_path.stem
                
                try:
                    # Импортируем модуль
                    full_module_name = f"mcp_servers.{module_name}"
                    module = importlib.import_module(full_module_name)
                    
                    # Ищем классы серверов
                    server_classes = self._find_server_classes(module, module_name)
                    
                    for server_name, server_class in server_classes.items():
                        self.discovered_servers[server_name] = {
                            'class': server_class,
                            'module': module,
                            'module_name': full_module_name,
                            'file_name': file_path.name
                        }
                        
                        logger.info(f"✅ Обнаружен сервер: {server_name} в {file_path.name}")
                        
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось загрузить модуль {module_name}: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Ошибка сканирования серверов: {e}")
    
    def _find_server_classes(self, module: Any, module_name: str) -> Dict[str, Type]:
        """Находит классы серверов в модуле"""
        server_classes = {}
        
        try:
            # Получаем все классы из модуля
            for name, obj in inspect.getmembers(module, inspect.isclass):
                # Проверяем, что класс определен в этом модуле
                if obj.__module__ == module.__name__:
                    # Ищем классы, которые заканчиваются на MCPServer
                    if name.endswith('MCPServer'):
                        # Извлекаем имя сервера из имени класса
                        server_name = self._extract_server_name(name, module_name)
                        server_classes[server_name] = obj
                        
        except Exception as e:
            logger.warning(f"⚠️ Ошибка поиска классов в модуле {module_name}: {e}")
            
        return server_classes
    
    def _extract_server_name(self, class_name: str, module_name: str) -> str:
        """Извлекает имя сервера из имени класса или модуля"""
        # Убираем суффиксы
        name = class_name.replace('MCPServer', '')
        
        # Если имя пустое, используем имя модуля
        if not name:
            name = module_name
            
        # Приводим к нижнему регистру
        return name.lower()
    
    def get_discovered_servers(self) -> Dict[str, Dict[str, Any]]:
        """Возвращает словарь обнаруженных серверов"""
        return self.discovered_servers.copy()
    
    def get_server_class(self, server_name: str) -> Type:
        """Возвращает класс сервера по имени"""
        server_info = self.discovered_servers.get(server_name)
        if server_info:
            return server_info['class']
        return None
    
    def get_server_names(self) -> List[str]:
        """Возвращает список имен обнаруженных серверов"""
        return list(self.discovered_servers.keys())
    
    def create_server_instance(self, server_name: str) -> Any:
        """Создает экземпляр сервера по имени с кэшированием"""
        # Возвращаем кэшированный экземпляр, если он есть
        if server_name in self._server_instances:
            logger.debug(f"🔄 Используем кэшированный экземпляр сервера {server_name}")
            return self._server_instances[server_name]
        
        server_class = self.get_server_class(server_name)
        if server_class:
            try:
                instance = server_class()
                # Кэшируем экземпляр
                self._server_instances[server_name] = instance
                logger.debug(f"✅ Создан и закэширован экземпляр сервера {server_name}")
                return instance
            except Exception as e:
                logger.error(f"❌ Ошибка создания экземпляра сервера {server_name}: {e}")
                return None
        return None
    
    def rescan_servers(self):
        """Пересканирует серверы (полезно при добавлении новых файлов)"""
        self.discovered_servers.clear()
        self._server_instances.clear()  # Сбрасываем кэш экземпляров
        self._scan_servers()
        logger.info(f"🔄 Пересканирование завершено. Обнаружено серверов: {len(self.discovered_servers)}")
    
    def clear_instance_cache(self):
        """Очищает кэш экземпляров серверов"""
        self._server_instances.clear()
        logger.info("🔄 Кэш экземпляров серверов очищен")

# Глобальный экземпляр для использования в других модулях
server_discovery = MCPServerDiscovery()
