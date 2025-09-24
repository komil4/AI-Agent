#!/usr/bin/env python3
"""
Базовый класс для MCP серверов с использованием стандарта Anthropic
"""

# ============================================================================
# ИНИЦИАЛИЗАЦИЯ МОДУЛЯ
# ============================================================================

import logging
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
from config.config_manager import ConfigManager

logger = logging.getLogger(__name__)

# ============================================================================
# ПРОГРАММНЫЙ ИНТЕРФЕЙС (API)
# ============================================================================

class BaseFastMCPServer(ABC):
    """Базовый класс для MCP серверов с использованием стандарта Anthropic"""
    
    def __init__(self, server_name: str):
        """Инициализация базового MCP сервера"""
        self.server_name = server_name
        self.description = self._get_description()
        self.config_manager = ConfigManager()
        self._load_config()
        self._connect()
    
    @abstractmethod
    def _get_description(self) -> str:
        """Возвращает описание сервера"""
        pass
    
    @abstractmethod
    def _load_config(self):
        """Загружает конфигурацию сервера"""
        pass
    
    @abstractmethod
    def _connect(self):
        """Подключается к внешнему сервису"""
        pass
    
    def is_enabled(self) -> bool:
        """Проверяет, включен ли сервер"""
        try:
            service_config = self.config_manager.get_service_config(self.server_name)
            return service_config.get('enabled', False)
        except Exception as e:
            logger.error(f"❌ Ошибка проверки статуса сервера {self.server_name}: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Тестирует подключение к сервису"""
        try:
            return self._test_connection()
        except Exception as e:
            logger.error(f"❌ Ошибка тестирования подключения {self.server_name}: {e}")
            return False
    
    @abstractmethod
    def _test_connection(self) -> bool:
        """Внутренний метод тестирования подключения"""
        pass
    
    def reconnect(self):
        """Переподключается к сервису"""
        try:
            logger.info(f"🔄 Переподключение к {self.server_name}...")
            self._load_config()
            self._connect()
            logger.info(f"✅ Переподключение к {self.server_name} завершено")
        except Exception as e:
            logger.error(f"❌ Ошибка переподключения к {self.server_name}: {e}")
    
    def get_server_info(self) -> Dict[str, Any]:
        """Возвращает информацию о сервере"""
        return {
            "name": self.server_name,
            "description": self.description,
            "enabled": self.is_enabled(),
            "connected": self.test_connection()
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Возвращает статус здоровья сервера"""
        try:
            is_enabled = self.is_enabled()
            is_connected = self.test_connection()
            
            if not is_enabled:
                return {
                    'status': 'disabled',
                    'provider': self.server_name,
                    'message': 'Сервер отключен в конфигурации'
                }
            
            if is_connected:
                return {
                    'status': 'healthy',
                    'provider': self.server_name,
                    'message': 'Сервер работает нормально'
                }
            else:
                return {
                    'status': 'unhealthy',
                    'provider': self.server_name,
                    'message': 'Не удается подключиться к серверу'
                }
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения статуса здоровья {self.server_name}: {e}")
            return {
                'status': 'unhealthy',
                'provider': self.server_name,
                'error': str(e)
            }
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Возвращает список доступных инструментов сервера"""
        try:
            if not self.is_enabled():
                logger.debug(f"🔧 Сервер {self.server_name} отключен, инструменты недоступны")
                return []
            
            # Получаем инструменты через _get_tools (должен быть реализован в наследниках)
            if hasattr(self, '_get_tools') and callable(self._get_tools):
                tools = self._get_tools()
                logger.debug(f"🔧 Получено {len(tools)} инструментов от {self.server_name}")
                return tools
            else:
                logger.warning(f"⚠️ Сервер {self.server_name} не реализует метод _get_tools")
                return []
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения инструментов от {self.server_name}: {e}")
            return []
    
    def get_admin_settings(self) -> Dict[str, Any]:
        """
        Возвращает настройки для админ-панели
        
        Returns:
            Словарь с настройками для отображения в админ-панели
        """
        try:
            # Получаем имя сервера из класса
            server_name = self.__class__.__name__.lower().replace('fastmcp', '').replace('mcp', '').replace('server', '')
            
            # Базовые настройки
            settings = {
                'name': server_name,
                'display_name': getattr(self, 'display_name', f'{server_name.title()} MCP'),
                'description': getattr(self, 'description', f'MCP сервер для {server_name}'),
                'icon': getattr(self, 'icon', 'fas fa-server'),
                'category': getattr(self, 'category', 'mcp_servers'),
                'fields': getattr(self, 'admin_fields', []),
                'enabled': self.is_enabled()
            }
            
            return settings
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения настроек админ-панели: {e}")
            return {
                'name': 'unknown',
                'display_name': 'Unknown MCP',
                'description': 'Неизвестный MCP сервер',
                'icon': 'fas fa-question',
                'category': 'mcp_servers',
                'fields': [],
                'enabled': False
            }

# ============================================================================
# СЛУЖЕБНЫЕ ФУНКЦИИ
# ============================================================================

def create_tool_schema(name: str, description: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Создает схему инструмента в стандарте Anthropic"""
    return {
        "name": name,
        "description": description,
        "inputSchema": {
            "type": "object",
            "properties": parameters.get("properties", {}),
            "required": parameters.get("required", [])
        }
    }

def validate_tool_parameters(parameters: Dict[str, Any], required: List[str]) -> bool:
    """Валидирует параметры инструмента"""
    for param in required:
        if param not in parameters:
            return False
    return True

def format_tool_response(success: bool, message: str, data: Any = None) -> Dict[str, Any]:
    """Форматирует ответ инструмента"""
    response = {
        "success": success,
        "message": message
    }
    if data is not None:
        response["data"] = data
    return response

# ============================================================================
# ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
# ============================================================================

# Стандартные типы параметров для инструментов
STANDARD_PARAMETER_TYPES = {
    "string": {"type": "string"},
    "integer": {"type": "integer"},
    "boolean": {"type": "boolean"},
    "array": {"type": "array"},
    "object": {"type": "object"}
}

# Стандартные описания для общих параметров
STANDARD_PARAMETER_DESCRIPTIONS = {
    "id": "Уникальный идентификатор",
    "name": "Название",
    "description": "Описание",
    "status": "Статус",
    "priority": "Приоритет",
    "assignee": "Исполнитель",
    "project": "Проект",
    "created_at": "Дата создания",
    "updated_at": "Дата обновления",
    "url": "URL адрес",
    "token": "Токен доступа",
    "username": "Имя пользователя",
    "password": "Пароль"
}
