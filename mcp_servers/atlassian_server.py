#!/usr/bin/env python3
"""
MCP сервер для работы с Atlassian Confluence с использованием стандарта Anthropic
"""

# ============================================================================
# ИНИЦИАЛИЗАЦИЯ МОДУЛЯ
# ============================================================================

import os
import requests
import logging
from atlassian import Confluence
from typing import Dict, Any, List, Optional
from datetime import datetime
from .base_mcp_server import BaseMCPServer, create_tool_schema, validate_tool_parameters, format_tool_response

logger = logging.getLogger(__name__)

# ============================================================================
# ПРОГРАММНЫЙ ИНТЕРФЕЙС (API)
# ============================================================================

class AtlassianMCPServer(BaseMCPServer):
    """MCP сервер для работы с Atlassian Confluence - создание и управление документацией, страницами и знаниями"""
    
    def __init__(self):
        """Инициализация Atlassian MCP сервера"""
        # Инициализируем переменные ДО вызова super().__init__()
        self.confluence_url = None
        self.username = None
        self.api_token = None
        self.confluence = None
        
        # Теперь вызываем родительский конструктор
        super().__init__("atlassian")
        
        # Настройки для админ-панели
        self.display_name = "Confluence MCP"
        self.icon = "fas fa-confluence"
        self.category = "mcp_servers"
        self.admin_fields = [
            { 'key': 'url', 'label': 'URL Confluence', 'type': 'text', 'placeholder': 'https://your-domain.atlassian.net/wiki' },
            { 'key': 'username', 'label': 'Имя пользователя', 'type': 'text', 'placeholder': 'your-email@domain.com' },
            { 'key': 'api_token', 'label': 'API Token', 'type': 'password', 'placeholder': 'ваш API токен' },
            { 'key': 'space_key', 'label': 'Ключ пространства', 'type': 'text', 'placeholder': 'SPACE' },
            { 'key': 'enabled', 'label': 'Включен', 'type': 'checkbox' }
        ]
        
        # Определяем инструменты в стандарте Anthropic
        self.tools = [
            create_tool_schema(
                name="search_pages",
                description="Ищет страницы в Confluence по текстовому запросу с возможностью фильтрации по пространству",
                parameters={
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Поисковый запрос для поиска страниц"
                        },
                        "space_key": {
                            "type": "string",
                            "description": "Ключ пространства для ограничения поиска"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Максимальное количество результатов (по умолчанию 20)",
                            "minimum": 1,
                            "maximum": 100
                        },
                        "content_type": {
                            "type": "string",
                            "description": "Тип контента для поиска",
                            "enum": ["page", "blogpost", "comment", "attachment"]
                        }
                    },
                    "required": ["query"]
                }
            ),
            create_tool_schema(
                name="create_page",
                description="Создает новую страницу в Confluence с указанным содержимым и структурой",
                parameters={
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Заголовок страницы"
                        },
                        "content": {
                            "type": "string",
                            "description": "Содержимое страницы в формате Confluence Storage Format"
                        },
                        "space_key": {
                            "type": "string",
                            "description": "Ключ пространства для создания страницы"
                        },
                        "parent_page_id": {
                            "type": "string",
                            "description": "ID родительской страницы для создания подстраницы"
                        },
                        "page_type": {
                            "type": "string",
                            "description": "Тип страницы",
                            "enum": ["page", "blogpost"],
                            "default": "page"
                        },
                        "labels": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Метки для страницы"
                        }
                    },
                    "required": ["title", "content", "space_key"]
                }
            ),
            create_tool_schema(
                name="list_pages",
                description="Получает список страниц пространства с возможностью фильтрации и сортировки",
                parameters={
                    "properties": {
                        "space_key": {
                            "type": "string",
                            "description": "Ключ пространства"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Максимальное количество результатов (по умолчанию 20)",
                            "minimum": 1,
                            "maximum": 100
                        },
                        "page_type": {
                            "type": "string",
                            "description": "Тип страниц для фильтрации",
                            "enum": ["page", "blogpost", "comment", "attachment"]
                        },
                        "sort": {
                            "type": "string",
                            "description": "Поле для сортировки",
                            "enum": ["created", "modified", "title"]
                        },
                        "order": {
                            "type": "string",
                            "description": "Порядок сортировки",
                            "enum": ["asc", "desc"]
                        }
                    },
                    "required": ["space_key"]
                }
            ),
            create_tool_schema(
                name="get_page_content",
                description="Получает содержимое и метаданные конкретной страницы",
                parameters={
                    "properties": {
                        "page_id": {
                            "type": "string",
                            "description": "ID страницы"
                        },
                        "include_metadata": {
                            "type": "boolean",
                            "description": "Включать метаданные страницы (автор, дата создания, версия)"
                        },
                        "include_attachments": {
                            "type": "boolean",
                            "description": "Включать информацию о вложениях"
                        },
                        "include_comments": {
                            "type": "boolean",
                            "description": "Включать комментарии к странице"
                        }
                    },
                    "required": ["page_id"]
                }
            ),
            create_tool_schema(
                name="update_page",
                description="Обновляет содержимое существующей страницы с сохранением истории версий",
                parameters={
                    "properties": {
                        "page_id": {
                            "type": "string",
                            "description": "ID страницы для обновления"
                        },
                        "title": {
                            "type": "string",
                            "description": "Новый заголовок страницы"
                        },
                        "content": {
                            "type": "string",
                            "description": "Новое содержимое страницы в формате Confluence Storage Format"
                        },
                        "version": {
                            "type": "integer",
                            "description": "Номер версии для обновления (обязательно для предотвращения конфликтов)"
                        },
                        "minor_edit": {
                            "type": "boolean",
                            "description": "Считать ли это минорным изменением (не уведомлять подписчиков)"
                        }
                    },
                    "required": ["page_id", "content"]
                }
            ),
            create_tool_schema(
                name="list_spaces",
                description="Получает список доступных пространств в Confluence",
                parameters={
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Максимальное количество результатов (по умолчанию 20)",
                            "minimum": 1,
                            "maximum": 100
                        },
                        "space_type": {
                            "type": "string",
                            "description": "Тип пространства для фильтрации",
                            "enum": ["personal", "global"]
                        },
                        "status": {
                            "type": "string",
                            "description": "Статус пространства",
                            "enum": ["current", "archived"]
                        }
                    }
                }
            ),
            create_tool_schema(
                name="get_space_details",
                description="Получает детальную информацию о пространстве",
                parameters={
                    "properties": {
                        "space_key": {
                            "type": "string",
                            "description": "Ключ пространства"
                        },
                        "include_permissions": {
                            "type": "boolean",
                            "description": "Включать информацию о правах доступа"
                        }
                    },
                    "required": ["space_key"]
                }
            ),
            create_tool_schema(
                name="add_comment",
                description="Добавляет комментарий к странице",
                parameters={
                    "properties": {
                        "page_id": {
                            "type": "string",
                            "description": "ID страницы"
                        },
                        "comment": {
                            "type": "string",
                            "description": "Текст комментария"
                        },
                        "parent_id": {
                            "type": "string",
                            "description": "ID родительского комментария для ответа"
                        }
                    },
                    "required": ["page_id", "comment"]
                }
            ),
            create_tool_schema(
                name="get_page_history",
                description="Получает историю версий страницы",
                parameters={
                    "properties": {
                        "page_id": {
                            "type": "string",
                            "description": "ID страницы"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Максимальное количество версий (по умолчанию 10)",
                            "minimum": 1,
                            "maximum": 50
                        }
                    },
                    "required": ["page_id"]
                }
            ),
            create_tool_schema(
                name="delete_page",
                description="Удаляет страницу или перемещает её в корзину",
                parameters={
                    "properties": {
                        "page_id": {
                            "type": "string",
                            "description": "ID страницы для удаления"
                        },
                        "permanent": {
                            "type": "boolean",
                            "description": "Удалить навсегда (true) или переместить в корзину (false)"
                        }
                    },
                    "required": ["page_id"]
                }
            )
        ]
    
    def _get_description(self) -> str:
        """Возвращает описание сервера"""
        return "atlassian: Создание, поиск, обновление страниц в Atlassian Confluence. Инструменты: search_pages, create_page, list_pages, get_page_content, update_page, list_spaces, add_comment, get_page_history, delete_page"
    
    def _load_config(self):
        """Загружает конфигурацию Atlassian"""
        atlassian_config = self.config_manager.get_service_config('atlassian')
        self.confluence_url = atlassian_config.get('url', '')
        self.username = atlassian_config.get('username', '')
        self.api_token = atlassian_config.get('api_token', '')
    
    def _connect(self):
        """Подключение к Confluence"""
        try:
            atlassian_config = self.config_manager.get_service_config('atlassian')
            if not atlassian_config.get('enabled', False):
                logger.info("ℹ️ Atlassian отключен в конфигурации")
                return
            
            if not all([self.confluence_url, self.username, self.api_token]):
                logger.warning("⚠️ Неполная конфигурация Atlassian")
                return
            
            # Подключение к Confluence
            self.confluence = Confluence(
                url=self.confluence_url,
                username=self.username,
                password=self.api_token
            )
            
            # Проверяем подключение
            self.confluence.get_current_user()
            logger.info(f"✅ Подключение к Confluence успешно: {self.confluence_url}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к Confluence: {e}")
            self.confluence = None
    
    def _test_connection(self) -> bool:
        """Тестирует подключение к Confluence"""
        if not self.confluence:
            return False
        
        try:
            self.confluence.get_current_user()
            return True
        except Exception:
            return False
    
    # ============================================================================
    # ИНСТРУМЕНТЫ ATLASSIAN CONFLUENCE
    # ============================================================================
    
    def search_pages(self, query: str, space_key: str = None, limit: int = 20,
                    content_type: str = None) -> Dict[str, Any]:
        """Ищет страницы в Confluence по текстовому запросу"""
        try:
            if not self.confluence:
                return format_tool_response(False, "Confluence не подключен")
            
            # Параметры поиска
            params = {
                'cql': f'text ~ "{query}"',
                'limit': limit
            }
            
            if space_key:
                params['cql'] = f'space = "{space_key}" AND text ~ "{query}"'
            
            if content_type:
                params['cql'] += f' AND type = "{content_type}"'
            
            # Выполняем поиск
            results = self.confluence.cql(params['cql'], limit=limit)
            
            # Форматируем результаты
            pages = []
            for result in results.get('results', []):
                page_data = {
                    "id": result.get('id'),
                    "title": result.get('title'),
                    "type": result.get('type'),
                    "space_key": result.get('space', {}).get('key'),
                    "space_name": result.get('space', {}).get('name'),
                    "url": f"{self.confluence_url}/pages/viewpage.action?pageId={result.get('id')}",
                    "created": result.get('created'),
                    "modified": result.get('modified')
                }
                pages.append(page_data)
            
            logger.info(f"✅ Найдено страниц: {len(pages)}")
            return format_tool_response(
                True,
                f"Найдено {len(pages)} страниц",
                {
                    "total": len(pages),
                    "pages": pages,
                    "query": query
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска страниц: {e}")
            return format_tool_response(False, f"Ошибка поиска страниц: {str(e)}")
    
    def create_page(self, title: str, content: str, space_key: str,
                   parent_page_id: str = None, page_type: str = "page",
                   labels: List[str] = None) -> Dict[str, Any]:
        """Создает новую страницу в Confluence"""
        try:
            if not self.confluence:
                return format_tool_response(False, "Confluence не подключен")
            
            # Параметры для создания страницы
            page_data = {
                'title': title,
                'space': {'key': space_key},
                'body': {
                    'storage': {
                        'value': content,
                        'representation': 'storage'
                    }
                },
                'type': page_type
            }
            
            if parent_page_id:
                page_data['ancestors'] = [{'id': parent_page_id}]
            
            if labels:
                page_data['metadata'] = {'labels': [{'name': label} for label in labels]}
            
            # Создаем страницу
            new_page = self.confluence.create_page(**page_data)
            
            logger.info(f"✅ Создана страница: {new_page['id']}")
            return format_tool_response(
                True,
                f"Страница '{title}' создана успешно",
                {
                    "page_id": new_page['id'],
                    "title": new_page['title'],
                    "space_key": space_key,
                    "url": f"{self.confluence_url}/pages/viewpage.action?pageId={new_page['id']}"
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания страницы: {e}")
            return format_tool_response(False, f"Ошибка создания страницы: {str(e)}")
    
    def list_pages(self, space_key: str, limit: int = 20, page_type: str = None,
                  sort: str = "modified", order: str = "desc") -> Dict[str, Any]:
        """Получает список страниц пространства"""
        try:
            if not self.confluence:
                return format_tool_response(False, "Confluence не подключен")
            
            # Получаем страницы пространства
            pages = self.confluence.get_all_pages_from_space(
                space_key,
                start=0,
                limit=limit,
                status='current',
                expand='version'
            )
            
            # Фильтруем по типу, если указан
            if page_type:
                pages = [p for p in pages if p.get('type') == page_type]
            
            # Сортируем
            reverse = order == "desc"
            if sort == "title":
                pages.sort(key=lambda x: x.get('title', ''), reverse=reverse)
            elif sort == "created":
                pages.sort(key=lambda x: x.get('version', {}).get('when', ''), reverse=reverse)
            else:  # modified
                pages.sort(key=lambda x: x.get('version', {}).get('when', ''), reverse=reverse)
            
            # Форматируем результаты
            page_list = []
            for page in pages:
                page_data = {
                    "id": page.get('id'),
                    "title": page.get('title'),
                    "type": page.get('type'),
                    "space_key": space_key,
                    "url": f"{self.confluence_url}/pages/viewpage.action?pageId={page.get('id')}",
                    "created": page.get('version', {}).get('when'),
                    "version": page.get('version', {}).get('number')
                }
                page_list.append(page_data)
            
            logger.info(f"✅ Получено страниц: {len(page_list)}")
            return format_tool_response(True, f"Получено страниц: {len(page_list)}", page_list)
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения списка страниц: {e}")
            return format_tool_response(False, f"Ошибка получения списка страниц: {str(e)}")
    
    def get_page_content(self, page_id: str, include_metadata: bool = False,
                        include_attachments: bool = False, include_comments: bool = False) -> Dict[str, Any]:
        """Получает содержимое и метаданные страницы"""
        try:
            if not self.confluence:
                return format_tool_response(False, "Confluence не подключен")
            
            # Получаем страницу
            page = self.confluence.get_page_by_id(
                page_id,
                expand='body.storage,version,space,ancestors'
            )
            
            # Базовые данные
            page_data = {
                "id": page.get('id'),
                "title": page.get('title'),
                "content": page.get('body', {}).get('storage', {}).get('value', ''),
                "space_key": page.get('space', {}).get('key'),
                "space_name": page.get('space', {}).get('name'),
                "url": f"{self.confluence_url}/pages/viewpage.action?pageId={page_id}",
                "version": page.get('version', {}).get('number'),
                "created": page.get('version', {}).get('when')
            }
            
            # Метаданные
            if include_metadata:
                page_data["metadata"] = {
                    "author": page.get('version', {}).get('by', {}).get('displayName'),
                    "created_by": page.get('version', {}).get('by', {}).get('displayName'),
                    "version_number": page.get('version', {}).get('number'),
                    "ancestors": [
                        {
                            "id": ancestor.get('id'),
                            "title": ancestor.get('title')
                        }
                        for ancestor in page.get('ancestors', [])
                    ]
                }
            
            # Вложения
            if include_attachments:
                try:
                    attachments = self.confluence.get_attachments_from_content(page_id)
                    page_data["attachments"] = [
                        {
                            "id": att.get('id'),
                            "title": att.get('title'),
                            "file_size": att.get('extensions', {}).get('fileSize'),
                            "media_type": att.get('extensions', {}).get('mediaType'),
                            "url": f"{self.confluence_url}{att.get('_links', {}).get('download', '')}"
                        }
                        for att in attachments
                    ]
                except Exception:
                    page_data["attachments"] = "Недоступно"
            
            # Комментарии
            if include_comments:
                try:
                    comments = self.confluence.get_page_comments(page_id)
                    page_data["comments"] = [
                        {
                            "id": comment.get('id'),
                            "content": comment.get('body', {}).get('storage', {}).get('value', ''),
                            "author": comment.get('version', {}).get('by', {}).get('displayName'),
                            "created": comment.get('version', {}).get('when')
                        }
                        for comment in comments
                    ]
                except Exception:
                    page_data["comments"] = "Недоступно"
            
            logger.info(f"✅ Получено содержимое страницы: {page_id}")
            return format_tool_response(True, "Содержимое страницы получено", page_data)
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения содержимого страницы: {e}")
            return format_tool_response(False, f"Ошибка получения содержимого страницы: {str(e)}")
    
    def update_page(self, page_id: str, content: str, title: str = None,
                   version: int = None, minor_edit: bool = False) -> Dict[str, Any]:
        """Обновляет содержимое существующей страницы"""
        try:
            if not self.confluence:
                return format_tool_response(False, "Confluence не подключен")
            
            # Получаем текущую страницу для версии
            if not version:
                current_page = self.confluence.get_page_by_id(page_id, expand='version')
                version = current_page.get('version', {}).get('number')
            
            # Параметры для обновления
            update_data = {
                'id': page_id,
                'version': {'number': version + 1},
                'body': {
                    'storage': {
                        'value': content,
                        'representation': 'storage'
                    }
                },
                'minorEdit': minor_edit
            }
            
            if title:
                update_data['title'] = title
            
            # Обновляем страницу
            updated_page = self.confluence.update_page(**update_data)
            
            logger.info(f"✅ Страница {page_id} обновлена")
            return format_tool_response(
                True,
                f"Страница {page_id} обновлена успешно",
                {
                    "page_id": page_id,
                    "new_version": updated_page.get('version', {}).get('number'),
                    "url": f"{self.confluence_url}/pages/viewpage.action?pageId={page_id}"
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления страницы: {e}")
            return format_tool_response(False, f"Ошибка обновления страницы: {str(e)}")
    
    def list_spaces(self, limit: int = 20, space_type: str = None,
                   status: str = "current") -> Dict[str, Any]:
        """Получает список доступных пространств"""
        try:
            if not self.confluence:
                return format_tool_response(False, "Confluence не подключен")
            
            # Получаем пространства
            spaces = self.confluence.get_all_spaces(start=0, limit=limit, expand='description')
            
            # Фильтруем по типу и статусу
            if space_type:
                spaces = [s for s in spaces if s.get('type') == space_type]
            
            if status:
                spaces = [s for s in spaces if s.get('status') == status]
            
            # Форматируем результаты
            space_list = []
            for space in spaces:
                space_data = {
                    "key": space.get('key'),
                    "name": space.get('name'),
                    "type": space.get('type'),
                    "status": space.get('status'),
                    "description": space.get('description', {}).get('plain', {}).get('value', ''),
                    "url": f"{self.confluence_url}/spaces/{space.get('key')}"
                }
                space_list.append(space_data)
            
            logger.info(f"✅ Получено пространств: {len(space_list)}")
            return format_tool_response(True, f"Получено пространств: {len(space_list)}", space_list)
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения списка пространств: {e}")
            return format_tool_response(False, f"Ошибка получения списка пространств: {str(e)}")
    
    def get_space_details(self, space_key: str, include_permissions: bool = False) -> Dict[str, Any]:
        """Получает детальную информацию о пространстве"""
        try:
            if not self.confluence:
                return format_tool_response(False, "Confluence не подключен")
            
            # Получаем пространство
            space = self.confluence.get_space(space_key, expand='description,homepage')
            
            # Базовые данные
            space_data = {
                "key": space.get('key'),
                "name": space.get('name'),
                "type": space.get('type'),
                "status": space.get('status'),
                "description": space.get('description', {}).get('plain', {}).get('value', ''),
                "url": f"{self.confluence_url}/spaces/{space_key}",
                "homepage_id": space.get('homepage', {}).get('id')
            }
            
            # Права доступа
            if include_permissions:
                try:
                    permissions = self.confluence.get_space_permissions(space_key)
                    space_data["permissions"] = permissions
                except Exception:
                    space_data["permissions"] = "Недоступно"
            
            logger.info(f"✅ Получены детали пространства: {space_key}")
            return format_tool_response(True, "Детали пространства получены", space_data)
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения деталей пространства: {e}")
            return format_tool_response(False, f"Ошибка получения деталей пространства: {str(e)}")
    
    def add_comment(self, page_id: str, comment: str, parent_id: str = None) -> Dict[str, Any]:
        """Добавляет комментарий к странице"""
        try:
            if not self.confluence:
                return format_tool_response(False, "Confluence не подключен")
            
            # Параметры для создания комментария
            comment_data = {
                'pageId': page_id,
                'body': {
                    'storage': {
                        'value': comment,
                        'representation': 'storage'
                    }
                }
            }
            
            if parent_id:
                comment_data['parentId'] = parent_id
            
            # Создаем комментарий
            new_comment = self.confluence.add_comment(**comment_data)
            
            logger.info(f"✅ Комментарий добавлен к странице: {page_id}")
            return format_tool_response(
                True,
                f"Комментарий добавлен к странице {page_id}",
                {
                    "comment_id": new_comment.get('id'),
                    "page_id": page_id,
                    "url": f"{self.confluence_url}/pages/viewpage.action?pageId={page_id}"
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка добавления комментария: {e}")
            return format_tool_response(False, f"Ошибка добавления комментария: {str(e)}")
    
    def get_page_history(self, page_id: str, limit: int = 10) -> Dict[str, Any]:
        """Получает историю версий страницы"""
        try:
            if not self.confluence:
                return format_tool_response(False, "Confluence не подключен")
            
            # Получаем историю страницы
            history = self.confluence.get_page_history(page_id, limit=limit)
            
            # Форматируем результаты
            versions = []
            for version in history.get('results', []):
                version_data = {
                    "number": version.get('number'),
                    "created": version.get('when'),
                    "author": version.get('by', {}).get('displayName'),
                    "message": version.get('message', ''),
                    "minor_edit": version.get('minorEdit', False)
                }
                versions.append(version_data)
            
            logger.info(f"✅ Получена история страницы: {len(versions)} версий")
            return format_tool_response(True, f"Получена история страницы: {len(versions)} версий", versions)
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения истории страницы: {e}")
            return format_tool_response(False, f"Ошибка получения истории страницы: {str(e)}")
    
    def delete_page(self, page_id: str, permanent: bool = False) -> Dict[str, Any]:
        """Удаляет страницу или перемещает её в корзину"""
        try:
            if not self.confluence:
                return format_tool_response(False, "Confluence не подключен")
            
            if permanent:
                # Удаляем навсегда
                self.confluence.remove_page(page_id)
                message = f"Страница {page_id} удалена навсегда"
            else:
                # Перемещаем в корзину
                self.confluence.remove_page(page_id, status='trashed')
                message = f"Страница {page_id} перемещена в корзину"
            
            logger.info(f"✅ {message}")
            return format_tool_response(True, message)
            
        except Exception as e:
            logger.error(f"❌ Ошибка удаления страницы: {e}")
            return format_tool_response(False, f"Ошибка удаления страницы: {str(e)}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Возвращает статус здоровья Atlassian сервера"""
        try:
            if not self.is_enabled():
                return {
                    'status': 'disabled',
                    'provider': 'atlassian',
                    'message': 'Atlassian отключен в конфигурации'
                }
            
            # Проверяем подключение к Confluence
            if hasattr(self, 'confluence') and self.confluence:
                # Пытаемся получить информацию о текущем пользователе
                current_user = self.confluence.get_current_user()
                return {
                    'status': 'healthy',
                    'provider': 'atlassian',
                    'message': f'Подключение к Confluence успешно. Пользователь: {current_user.get("displayName", "Unknown")}',
                    'server_url': self.confluence_url
                }
            else:
                return {
                    'status': 'unhealthy',
                    'provider': 'atlassian',
                    'message': 'Confluence клиент не инициализирован'
                }
                
        except Exception as e:
            logger.error(f"❌ Ошибка проверки здоровья Atlassian: {e}")
            return {
                'status': 'unhealthy',
                'provider': 'atlassian',
                'error': str(e)
            }
    
    def _get_tools(self) -> List[Dict[str, Any]]:
        """Возвращает список инструментов Atlassian сервера"""
        return self.tools

# ============================================================================
# ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
# ============================================================================

# Глобальный экземпляр Atlassian сервера
atlassian_server = AtlassianMCPServer()
