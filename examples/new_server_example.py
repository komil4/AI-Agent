#!/usr/bin/env python3
"""
Пример создания нового MCP сервера
Показывает, как легко добавить новый сервер в систему
"""

# Этот файл должен быть помещен в папку mcp_servers/ как your_service_server.py

from .base_fastmcp_server import BaseFastMCPServer, create_tool_schema, format_tool_response
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class YourServiceFastMCPServer(BaseFastMCPServer):
    """MCP сервер для YourService - пример нового сервера"""
    
    def __init__(self):
        """Инициализация сервера YourService"""
        super().__init__("your_service")  # Имя сервиса в конфигурации
        
        # Определяем инструменты в стандарте Anthropic
        self.tools = [
            create_tool_schema(
                name="get_service_info",
                description="Получает информацию о сервисе YourService",
                parameters={
                    "properties": {
                        "include_stats": {
                            "type": "boolean",
                            "description": "Включать статистику сервиса"
                        },
                        "include_users": {
                            "type": "boolean", 
                            "description": "Включать список пользователей"
                        }
                    }
                }
            ),
            create_tool_schema(
                name="create_resource",
                description="Создает новый ресурс в YourService",
                parameters={
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Название ресурса"
                        },
                        "type": {
                            "type": "string",
                            "description": "Тип ресурса",
                            "enum": ["document", "project", "task", "user"]
                        },
                        "description": {
                            "type": "string",
                            "description": "Описание ресурса"
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Теги ресурса"
                        }
                    },
                    "required": ["name", "type"]
                }
            ),
            create_tool_schema(
                name="search_resources",
                description="Ищет ресурсы в YourService по различным критериям",
                parameters={
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Поисковый запрос"
                        },
                        "resource_type": {
                            "type": "string",
                            "description": "Тип ресурса для фильтрации",
                            "enum": ["document", "project", "task", "user", "all"]
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Максимальное количество результатов (по умолчанию 20)",
                            "minimum": 1,
                            "maximum": 100
                        },
                        "sort_by": {
                            "type": "string",
                            "description": "Поле для сортировки",
                            "enum": ["name", "created", "modified", "type"]
                        }
                    },
                    "required": ["query"]
                }
            ),
            create_tool_schema(
                name="update_resource",
                description="Обновляет существующий ресурс в YourService",
                parameters={
                    "properties": {
                        "resource_id": {
                            "type": "string",
                            "description": "ID ресурса для обновления"
                        },
                        "name": {
                            "type": "string",
                            "description": "Новое название ресурса"
                        },
                        "description": {
                            "type": "string",
                            "description": "Новое описание ресурса"
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Новые теги ресурса"
                        },
                        "status": {
                            "type": "string",
                            "description": "Новый статус ресурса",
                            "enum": ["active", "inactive", "archived"]
                        }
                    },
                    "required": ["resource_id"]
                }
            ),
            create_tool_schema(
                name="delete_resource",
                description="Удаляет ресурс из YourService",
                parameters={
                    "properties": {
                        "resource_id": {
                            "type": "string",
                            "description": "ID ресурса для удаления"
                        },
                        "permanent": {
                            "type": "boolean",
                            "description": "Удалить навсегда (true) или переместить в корзину (false)"
                        }
                    },
                    "required": ["resource_id"]
                }
            )
        ]
    
    def _get_description(self) -> str:
        """Возвращает описание сервера"""
        return "YourService MCP сервер - управление ресурсами и данными в YourService"
    
    def _load_config(self):
        """Загружает конфигурацию YourService"""
        your_service_config = self.config_manager.get_service_config('your_service')
        self.api_url = your_service_config.get('url', '')
        self.api_key = your_service_config.get('api_key', '')
        self.timeout = your_service_config.get('timeout', 30)
    
    def _connect(self):
        """Подключение к YourService"""
        try:
            your_service_config = self.config_manager.get_service_config('your_service')
            if not your_service_config.get('enabled', False):
                logger.info("ℹ️ YourService отключен в конфигурации")
                return
            
            if not all([self.api_url, self.api_key]):
                logger.warning("⚠️ Неполная конфигурация YourService")
                return
            
            # Здесь можно добавить проверку подключения к API
            # Например, тестовый запрос к API
            
            logger.info(f"✅ Подключение к YourService успешно: {self.api_url}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к YourService: {e}")
    
    def _test_connection(self) -> bool:
        """Тестирует подключение к YourService"""
        try:
            # Здесь можно добавить реальную проверку подключения
            # Например, запрос к health endpoint
            return True
        except Exception:
            return False
    
    # ============================================================================
    # ИНСТРУМЕНТЫ YOURSERVICE
    # ============================================================================
    
    def get_service_info(self, include_stats: bool = False, include_users: bool = False) -> Dict[str, Any]:
        """Получает информацию о сервисе YourService"""
        try:
            if not self._test_connection():
                return format_tool_response(False, "YourService не подключен")
            
            # Базовая информация о сервисе
            service_info = {
                "name": "YourService",
                "version": "1.0.0",
                "status": "active",
                "api_url": self.api_url,
                "description": "Пример сервиса для демонстрации MCP сервера"
            }
            
            # Статистика
            if include_stats:
                service_info["stats"] = {
                    "total_resources": 150,
                    "active_resources": 120,
                    "archived_resources": 30,
                    "total_users": 25
                }
            
            # Пользователи
            if include_users:
                service_info["users"] = [
                    {"id": "1", "name": "John Doe", "role": "admin"},
                    {"id": "2", "name": "Jane Smith", "role": "user"},
                    {"id": "3", "name": "Bob Johnson", "role": "user"}
                ]
            
            logger.info("✅ Получена информация о YourService")
            return format_tool_response(True, "Информация о сервисе получена", service_info)
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения информации о сервисе: {e}")
            return format_tool_response(False, f"Ошибка получения информации о сервисе: {str(e)}")
    
    def create_resource(self, name: str, resource_type: str, description: str = None,
                       tags: List[str] = None) -> Dict[str, Any]:
        """Создает новый ресурс в YourService"""
        try:
            if not self._test_connection():
                return format_tool_response(False, "YourService не подключен")
            
            # Здесь должна быть реальная логика создания ресурса
            # Например, HTTP запрос к API
            
            # Имитируем создание ресурса
            resource_id = f"{resource_type}_{len(name)}_{hash(name) % 10000}"
            
            resource_data = {
                "id": resource_id,
                "name": name,
                "type": resource_type,
                "description": description or "",
                "tags": tags or [],
                "status": "active",
                "created_at": "2024-01-01T10:00:00Z"
            }
            
            logger.info(f"✅ Создан ресурс: {resource_id}")
            return format_tool_response(
                True,
                f"Ресурс '{name}' создан успешно",
                {
                    "resource_id": resource_id,
                    "name": name,
                    "type": resource_type,
                    "url": f"{self.api_url}/resources/{resource_id}"
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания ресурса: {e}")
            return format_tool_response(False, f"Ошибка создания ресурса: {str(e)}")
    
    def search_resources(self, query: str, resource_type: str = "all", limit: int = 20,
                        sort_by: str = "name") -> Dict[str, Any]:
        """Ищет ресурсы в YourService"""
        try:
            if not self._test_connection():
                return format_tool_response(False, "YourService не подключен")
            
            # Здесь должна быть реальная логика поиска
            # Например, HTTP запрос к search API
            
            # Имитируем поиск ресурсов
            mock_resources = [
                {
                    "id": "doc_1",
                    "name": f"Документ по {query}",
                    "type": "document",
                    "description": f"Документ, содержащий информацию о {query}",
                    "created_at": "2024-01-01T10:00:00Z"
                },
                {
                    "id": "proj_1", 
                    "name": f"Проект {query}",
                    "type": "project",
                    "description": f"Проект, связанный с {query}",
                    "created_at": "2024-01-02T10:00:00Z"
                }
            ]
            
            # Фильтруем по типу
            if resource_type != "all":
                mock_resources = [r for r in mock_resources if r["type"] == resource_type]
            
            # Ограничиваем количество
            mock_resources = mock_resources[:limit]
            
            logger.info(f"✅ Найдено ресурсов: {len(mock_resources)}")
            return format_tool_response(
                True,
                f"Найдено {len(mock_resources)} ресурсов",
                {
                    "total": len(mock_resources),
                    "resources": mock_resources,
                    "query": query,
                    "filters": {
                        "resource_type": resource_type,
                        "sort_by": sort_by
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска ресурсов: {e}")
            return format_tool_response(False, f"Ошибка поиска ресурсов: {str(e)}")
    
    def update_resource(self, resource_id: str, name: str = None, description: str = None,
                       tags: List[str] = None, status: str = None) -> Dict[str, Any]:
        """Обновляет существующий ресурс"""
        try:
            if not self._test_connection():
                return format_tool_response(False, "YourService не подключен")
            
            # Здесь должна быть реальная логика обновления
            # Например, HTTP PUT запрос к API
            
            # Имитируем обновление ресурса
            updated_fields = []
            if name:
                updated_fields.append("name")
            if description:
                updated_fields.append("description")
            if tags:
                updated_fields.append("tags")
            if status:
                updated_fields.append("status")
            
            logger.info(f"✅ Ресурс {resource_id} обновлен")
            return format_tool_response(
                True,
                f"Ресурс {resource_id} обновлен успешно",
                {
                    "resource_id": resource_id,
                    "updated_fields": updated_fields,
                    "url": f"{self.api_url}/resources/{resource_id}"
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления ресурса: {e}")
            return format_tool_response(False, f"Ошибка обновления ресурса: {str(e)}")
    
    def delete_resource(self, resource_id: str, permanent: bool = False) -> Dict[str, Any]:
        """Удаляет ресурс из YourService"""
        try:
            if not self._test_connection():
                return format_tool_response(False, "YourService не подключен")
            
            # Здесь должна быть реальная логика удаления
            # Например, HTTP DELETE запрос к API
            
            action = "удален навсегда" if permanent else "перемещен в корзину"
            
            logger.info(f"✅ Ресурс {resource_id} {action}")
            return format_tool_response(True, f"Ресурс {resource_id} {action}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка удаления ресурса: {e}")
            return format_tool_response(False, f"Ошибка удаления ресурса: {str(e)}")

# ============================================================================
# ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
# ============================================================================

# Глобальный экземпляр сервера YourService
your_service_server = YourServiceFastMCPServer()

# ============================================================================
# КОНФИГУРАЦИЯ ДЛЯ app_config.json
# ============================================================================

"""
Добавьте в app_config.json:

{
  "your_service": {
    "enabled": true,
    "url": "https://your-service.com/api",
    "api_key": "your-api-key-here",
    "timeout": 30,
    "additional_params": {}
  }
}
"""
