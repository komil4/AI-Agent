#!/usr/bin/env python3
"""
Базовый класс для MCP серверов с использованием стандарта Anthropic
"""

# ============================================================================
# ИНИЦИАЛИЗАЦИЯ МОДУЛЯ
# ============================================================================

import logging
import time
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
from config.config_manager import ConfigManager

logger = logging.getLogger(__name__)

# ============================================================================
# ПРОГРАММНЫЙ ИНТЕРФЕЙС (API)
# ============================================================================

class BaseMCPServer(ABC):
    """Базовый класс для MCP серверов с использованием стандарта Anthropic"""
    
    def __init__(self, server_name: str):
        """Инициализация базового MCP сервера"""
        self.server_name = server_name
        self.description = self._get_description()
        self.config_manager = ConfigManager()
        
        # Кэширование состояния подключения
        self._connection_status = None  # None, True, False
        self._last_connection_check = 0
        self._connection_check_interval = 30  # секунд
        
        # Инициализация будет выполнена через initialize()
    
    async def initialize(self):
        """Асинхронная инициализация сервера"""
        try:
            self._load_config()
            self._connect()
            logger.info(f"[OK] Сервер {self.server_name} инициализирован")
        except Exception as e:
            logger.error(f"[ERROR] Ошибка инициализации сервера {self.server_name}: {e}")
            raise
    
    @abstractmethod
    def _get_description(self) -> str:
        """Возвращает описание сервера"""
        pass
    
    def get_description(self) -> str:
        """Возвращает описание сервера (публичный метод)"""
        return self._get_description()
    
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
            logger.error(f"[ERROR] Ошибка проверки статуса сервера {self.server_name}: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Тестирует подключение к сервису с кэшированием"""
        try:
            current_time = time.time()
            
            # Проверяем, нужно ли обновить кэш
            if (self._connection_status is None or 
                current_time - self._last_connection_check > self._connection_check_interval):
                
                # Выполняем проверку подключения
                self._connection_status = self._test_connection()
                self._last_connection_check = current_time
                
                if self._connection_status:
                    logger.debug(f"[OK] Подключение к {self.server_name} проверено: OK")
                else:
                    logger.debug(f"[ERROR] Подключение к {self.server_name} проверено: FAILED")
            
            return self._connection_status
            
        except Exception as e:
            logger.error(f"[ERROR] Ошибка тестирования подключения {self.server_name}: {e}")
            self._connection_status = False
            self._last_connection_check = time.time()
            return False
    
    @abstractmethod
    def _test_connection(self) -> bool:
        """Внутренний метод тестирования подключения"""
        pass
    
    def reconnect(self):
        """Переподключается к сервису"""
        try:
            logger.info(f"[RELOAD] Переподключение к {self.server_name}...")
            self._load_config()
            self._connect()
            
            # Сбрасываем кэш после переподключения
            self._connection_status = None
            self._last_connection_check = 0
            
            logger.info(f"[OK] Переподключение к {self.server_name} завершено")
        except Exception as e:
            logger.error(f"[ERROR] Ошибка переподключения к {self.server_name}: {e}")
            # Помечаем как недоступный
            self._connection_status = False
            self._last_connection_check = time.time()
    
    def invalidate_connection_cache(self):
        """Принудительно сбрасывает кэш подключения"""
        self._connection_status = None
        self._last_connection_check = 0
        logger.debug(f"[RELOAD] Кэш подключения {self.server_name} сброшен")
    
    def get_server_info(self) -> Dict[str, Any]:
        """Возвращает информацию о сервере"""
        return {
            "name": self.server_name,
            "description": self.description,
            "enabled": self.is_enabled(),
            "connected": self.test_connection()
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Возвращает статус здоровья сервера с кэшированием"""
        try:
            is_enabled = self.is_enabled()
            
            if not is_enabled:
                return {
                    'status': 'disabled',
                    'provider': self.server_name,
                    'message': 'Сервер отключен в конфигурации'
                }
            
            # Используем кэшированное состояние подключения
            is_connected = self.test_connection()
            
            if is_connected:
                return {
                    'status': 'healthy',
                    'provider': self.server_name,
                    'message': 'Сервер работает нормально',
                    'cached': True,
                    'last_check': self._last_connection_check
                }
            else:
                return {
                    'status': 'unhealthy',
                    'provider': self.server_name,
                    'message': 'Не удается подключиться к серверу',
                    'cached': True,
                    'last_check': self._last_connection_check
                }
                
        except Exception as e:
            logger.error(f"[ERROR] Ошибка получения статуса здоровья {self.server_name}: {e}")
            return {
                'status': 'unhealthy',
                'provider': self.server_name,
                'error': str(e)
            }
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Возвращает список доступных инструментов сервера"""
        try:
            if not self.is_enabled():
                logger.debug(f"[TOOLS] Сервер {self.server_name} отключен, инструменты недоступны")
                return []
            
            # Получаем инструменты через _get_tools (должен быть реализован в наследниках)
            if hasattr(self, '_get_tools') and callable(self._get_tools):
                tools = self._get_tools()
                logger.debug(f"[TOOLS] Получено {len(tools)} инструментов от {self.server_name}")
                return tools
            else:
                logger.warning(f"[WARN] Сервер {self.server_name} не реализует метод _get_tools")
                return []
                
        except Exception as e:
            logger.error(f"[ERROR] Ошибка получения инструментов от {self.server_name}: {e}")
            return []
    
    def get_tools_info(self) -> List[Dict[str, Any]]:
        """Возвращает информацию об инструментах сервера (алиас для get_tools)"""
        return self.get_tools()
    
    def get_info(self) -> Dict[str, Any]:
        """Возвращает информацию о сервере"""
        return self.get_server_info()
    
    def get_admin_settings(self) -> Dict[str, Any]:
        """
        Возвращает настройки для админ-панели
        
        Returns:
            Словарь с настройками для отображения в админ-панели
        """
        try:
            # Получаем имя сервера из класса
            server_name = self.__class__.__name__.lower().replace('mcp', '').replace('server', '')
            
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
            logger.error(f"[ERROR] Ошибка получения настроек админ-панели: {e}")
            return {
                'name': 'unknown',
                'display_name': 'Unknown MCP',
                'description': 'Неизвестный MCP сервер',
                'icon': 'fas fa-question',
                'category': 'mcp_servers',
                'fields': [],
                'enabled': False
            }
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Вызывает инструмент сервера
        
        Args:
            tool_name: Имя инструмента
            arguments: Аргументы для инструмента
            
        Returns:
            Результат выполнения инструмента
        """
        try:
            # Проверяем, что инструмент существует
            tools = self.get_tools()
            tool_found = False
            
            for tool in tools:
                if tool.get('name') == tool_name:
                    tool_found = True
                    break
            
            if not tool_found:
                return format_tool_response(False, f"Инструмент '{tool_name}' не найден")
            
            # Валидируем аргументы
            validation_result = validate_tool_parameters(tool_name, arguments, tools)
            if not validation_result['valid']:
                return format_tool_response(False, f"Ошибка валидации: {validation_result['error']}")
            
            # Вызываем конкретный инструмент
            return self._call_tool_impl(tool_name, arguments)
            
        except Exception as e:
            logger.error(f"[ERROR] Ошибка вызова инструмента {tool_name}: {e}")
            return format_tool_response(False, f"Ошибка выполнения инструмента: {str(e)}")
    
    def _call_tool_impl(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Реализация вызова конкретного инструмента
        Должна быть переопределена в дочерних классах
        
        Args:
            tool_name: Имя инструмента
            arguments: Аргументы для инструмента
            
        Returns:
            Результат выполнения инструмента
        """
        return format_tool_response(False, f"Инструмент '{tool_name}' не реализован")

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

def validate_tool_parameters(tool_name: str, arguments: Dict[str, Any], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Валидирует параметры инструмента"""
    try:
        # Находим схему инструмента
        tool_schema = None
        for tool in tools:
            if tool.get('name') == tool_name:
                tool_schema = tool.get('inputSchema', {})
                break
        
        if not tool_schema:
            return {'valid': False, 'error': f'Схема инструмента {tool_name} не найдена'}
        
        # Получаем обязательные параметры
        required_params = tool_schema.get('properties', {}).get('required', [])
        
        # Проверяем обязательные параметры
        for param in required_params:
            if param not in arguments:
                return {'valid': False, 'error': f'Отсутствует обязательный параметр: {param}'}
        
        return {'valid': True, 'error': None}
        
    except Exception as e:
        return {'valid': False, 'error': f'Ошибка валидации: {str(e)}'}

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
