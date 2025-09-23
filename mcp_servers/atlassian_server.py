import os
import requests
from atlassian import Confluence
from typing import Dict, Any, List
from config.config_manager import ConfigManager
from . import BaseMCPServer

class AtlassianMCPServer(BaseMCPServer):
    """MCP сервер для работы с Atlassian Confluence - создание и управление документацией, страницами и знаниями"""
    
    def __init__(self):
        super().__init__()
        self.description = "Atlassian Confluence - создание и управление документацией, страницами и знаниями"
        self.tools = [
            {
                "name": "search_pages",
                "description": "Ищет страницы в Confluence",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Поисковый запрос"},
                        "space_key": {"type": "string", "description": "Ключ пространства"},
                        "limit": {"type": "integer", "description": "Максимальное количество результатов"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "create_page",
                "description": "Создает новую страницу в Confluence",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Заголовок страницы"},
                        "content": {"type": "string", "description": "Содержимое страницы"},
                        "space_key": {"type": "string", "description": "Ключ пространства"},
                        "parent_page_id": {"type": "string", "description": "ID родительской страницы"}
                    },
                    "required": ["title", "content", "space_key"]
                }
            },
            {
                "name": "list_pages",
                "description": "Получает список страниц пространства",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "space_key": {"type": "string", "description": "Ключ пространства"},
                        "limit": {"type": "integer", "description": "Максимальное количество результатов"}
                    }
                }
            },
            {
                "name": "get_page_content",
                "description": "Получает содержимое страницы",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "page_id": {"type": "string", "description": "ID страницы"}
                    },
                    "required": ["page_id"]
                }
            },
            {
                "name": "update_page",
                "description": "Обновляет содержимое страницы",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "page_id": {"type": "string", "description": "ID страницы"},
                        "title": {"type": "string", "description": "Новый заголовок"},
                        "content": {"type": "string", "description": "Новое содержимое"}
                    },
                    "required": ["page_id", "content"]
                }
            }
        ]
        self.config_manager = ConfigManager()
        self.confluence_url = None
        self.username = None
        self.api_token = None
        self.confluence = None
        self._load_config()
        self._connect()
    
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
                print("⚠️ Atlassian отключен в конфигурации")
                return
                
            if self.confluence_url and self.username and self.api_token:
                self.confluence = Confluence(
                    url=self.confluence_url,
                    username=self.username,
                    password=self.api_token
                )
                print("✅ Подключение к Confluence успешно")
            else:
                print("⚠️ Confluence не настроен - отсутствуют данные в конфигурации")
        except Exception as e:
            print(f"❌ Ошибка подключения к Confluence: {e}")
    
    def reconnect(self):
        """Переподключается к Confluence с новой конфигурацией"""
        self._load_config()
        self._connect()
    
    def process_command(self, message: str) -> str:
        """Обрабатывает команды для Confluence (упрощенный метод)"""
        if not self.confluence:
            return "❌ Confluence не настроен. Проверьте переменные окружения."
        
        message_lower = message.lower()
        
        try:
            if any(word in message_lower for word in ['создать', 'новая', 'создай', 'страница']):
                return self._create_page(message)
            elif any(word in message_lower for word in ['найти', 'поиск', 'найди']):
                return self._search_pages(message)
            elif any(word in message_lower for word in ['список', 'все', 'показать', 'страницы']):
                return self._list_pages()
            elif any(word in message_lower for word in ['обновить', 'изменить', 'редактировать']):
                return self._update_page(message)
            else:
                return self._get_help()
        except Exception as e:
            return f"❌ Ошибка при работе с Confluence: {str(e)}"
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Вызывает инструмент Confluence по имени"""
        if not self.confluence:
            return {"error": "Confluence не настроен"}
        
        try:
            if tool_name == "search_pages":
                return self._search_pages_tool(arguments)
            elif tool_name == "create_page":
                return self._create_page_tool(arguments)
            elif tool_name == "list_pages":
                return self._list_pages_tool(arguments)
            elif tool_name == "get_page_content":
                return self._get_page_content_tool(arguments)
            elif tool_name == "update_page":
                return self._update_page_tool(arguments)
            else:
                return {"error": f"Неизвестный инструмент: {tool_name}"}
        except Exception as e:
            return {"error": str(e)}
    
    def process_command_intelligent(self, message: str, intent_result, user_context: dict = None) -> str:
        """Обрабатывает команды для Confluence на основе анализа намерений"""
        if not self.confluence:
            return "❌ Confluence не настроен. Проверьте переменные окружения."
        
        try:
            # Временная заглушка для intent_analyzer
            class IntentType:
                CONFLUENCE_CREATE = "confluence_create"
                CONFLUENCE_SEARCH = "confluence_search"
                CONFLUENCE_LIST = "confluence_list"
            
            # Обрабатываем на основе намерения
            if intent_result.intent == IntentType.CONFLUENCE_CREATE:
                return self._create_page_intelligent(message, intent_result)
            elif intent_result.intent == IntentType.CONFLUENCE_SEARCH:
                return self._search_pages_intelligent(message, intent_result)
            elif intent_result.intent == IntentType.CONFLUENCE_LIST:
                return self._list_pages_intelligent(message, intent_result)
            else:
                # Fallback к старому методу
                return self.process_command(message)
        except Exception as e:
            return f"❌ Ошибка при работе с Confluence: {str(e)}"
    
    def _create_page(self, message: str) -> str:
        """Создает новую страницу в Confluence"""
        try:
            # Извлекаем заголовок из сообщения
            title = "Новая страница из чат-бота"
            if 'заголовок' in message.lower():
                # Простое извлечение заголовка
                parts = message.split('заголовок')
                if len(parts) > 1:
                    title = parts[1].strip().strip('"').strip("'")
            
            page_data = {
                'title': title,
                'body': f'<p>{message}</p>',
                'space': 'TEST',  # Замените на ваш space
                'type': 'page'
            }
            
            result = self.confluence.create_page(**page_data)
            page_id = result.get('id')
            page_url = f"{self.confluence_url}/pages/viewpage.action?pageId={page_id}"
            
            return f"✅ Создана страница: {title}\n🔗 Ссылка: {page_url}"
        except Exception as e:
            return f"❌ Ошибка создания страницы: {str(e)}"
    
    def _search_pages(self, message: str) -> str:
        """Поиск страниц в Confluence"""
        try:
            # Простой поиск по тексту
            cql = f'text ~ "{message}"'
            pages = self.confluence.cql(cql, limit=5)
            
            if not pages or not pages.get('results'):
                return "🔍 Страницы не найдены"
            
            result = "🔍 Найденные страницы:\n"
            for page in pages['results']:
                title = page.get('title', 'Без названия')
                page_id = page.get('id')
                page_url = f"{self.confluence_url}/pages/viewpage.action?pageId={page_id}"
                result += f"• {title}\n  🔗 {page_url}\n"
            
            return result
        except Exception as e:
            return f"❌ Ошибка поиска: {str(e)}"
    
    def _list_pages(self) -> str:
        """Список последних страниц"""
        try:
            # Получаем последние страницы
            pages = self.confluence.get_all_pages_from_space('TEST', limit=10)  # Замените на ваш space
            
            if not pages:
                return "📋 Страниц не найдено"
            
            result = "📋 Последние страницы:\n"
            for page in pages:
                title = page.get('title', 'Без названия')
                page_id = page.get('id')
                page_url = f"{self.confluence_url}/pages/viewpage.action?pageId={page_id}"
                result += f"• {title}\n  🔗 {page_url}\n"
            
            return result
        except Exception as e:
            return f"❌ Ошибка получения списка: {str(e)}"
    
    def _update_page(self, message: str) -> str:
        """Обновляет существующую страницу"""
        try:
            # Простое извлечение ID страницы из сообщения
            words = message.split()
            page_id = None
            for word in words:
                if word.isdigit():
                    page_id = word
                    break
            
            if not page_id:
                return "❌ Не указан ID страницы для обновления"
            
            # Получаем текущую страницу
            page = self.confluence.get_page_by_id(page_id)
            if not page:
                return f"❌ Страница с ID {page_id} не найдена"
            
            # Обновляем содержимое
            new_content = f"{page['body']['storage']['value']}\n\n<p>Обновлено из чат-бота: {message}</p>"
            
            self.confluence.update_page(
                page_id=page_id,
                title=page['title'],
                body=new_content
            )
            
            return f"✅ Страница {page['title']} обновлена"
        except Exception as e:
            return f"❌ Ошибка обновления страницы: {str(e)}"
    
    def _get_help(self) -> str:
        """Справка по командам Confluence"""
        return """
🔧 Команды для работы с Confluence:

• Создать страницу: "создай страницу в confluence"
• Найти страницы: "найди страницы по ключевому слову"
• Список страниц: "покажи все страницы"
• Обновить страницу: "обнови страницу с ID 123456"

Примеры:
- "создай страницу с заголовком 'Новая документация'"
- "найди все страницы про API"
- "покажи последние страницы"
- "обнови страницу 123456 новым содержимым"
        """
    
    def _create_page_intelligent(self, message: str, intent_result) -> str:
        """Создает новую страницу в Confluence на основе анализа намерений"""
        try:
            entities = intent_result.entities
            page_title = entities.get('page_title', '')
            
            # Если не указан заголовок, извлекаем из сообщения
            if not page_title:
                # Ищем заголовок в сообщении
                import re
                title_match = re.search(r'заголовком\s+["\']([^"\']+)["\']', message, re.IGNORECASE)
                if title_match:
                    page_title = title_match.group(1)
                else:
                    page_title = f"Страница из чат-бота: {message[:50]}..."
            
            # Извлекаем пространство из сущностей или используем по умолчанию
            space_name = entities.get('space_name', 'TEST')
            
            # Создаем содержимое страницы
            content = f"""
<h2>Создано из чат-бота</h2>
<p><strong>Исходное сообщение:</strong> {message}</p>
<p><strong>Дата создания:</strong> {self._get_current_date()}</p>
<p><strong>Автор:</strong> AI Ассистент</p>
            """
            
            page_data = {
                'title': page_title,
                'body': content,
                'space': space_name,
                'type': 'page'
            }
            
            result = self.confluence.create_page(**page_data)
            page_id = result.get('id')
            page_url = f"{self.confluence_url}/pages/viewpage.action?pageId={page_id}"
            
            return f"✅ Создана страница: **{page_title}**\n\n🔗 [Открыть страницу]({page_url})\n📁 Пространство: {space_name}\n📝 Содержимое: {message[:100]}..."
        except Exception as e:
            return f"❌ Ошибка создания страницы: {str(e)}"
    
    def _search_pages_intelligent(self, message: str, intent_result) -> str:
        """Поиск страниц в Confluence на основе анализа намерений"""
        try:
            entities = intent_result.entities
            search_query = entities.get('search_query', '')
            
            # Используем поисковый запрос из сущностей или весь текст сообщения
            query = search_query if search_query else message
            
            # Определяем количество результатов
            import re
            count_match = re.search(r'(\d+)', message)
            limit = int(count_match.group(1)) if count_match else 5
            
            # Выполняем поиск
            cql = f'text ~ "{query}"'
            pages = self.confluence.cql(cql, limit=limit)
            
            if not pages or not pages.get('results'):
                return f"🔍 Страницы по запросу '{query}' не найдены"
            
            result = f"🔍 Найденные страницы по запросу '{query}':\n\n"
            for page in pages['results']:
                title = page.get('title', 'Без названия')
                page_id = page.get('id')
                space = page.get('space', {}).get('name', 'Неизвестно')
                page_url = f"{self.confluence_url}/pages/viewpage.action?pageId={page_id}"
                
                result += f"• **{title}**\n"
                result += f"  📁 Пространство: {space}\n"
                result += f"  🔗 [Открыть страницу]({page_url})\n\n"
            
            return result
        except Exception as e:
            return f"❌ Ошибка поиска: {str(e)}"
    
    def _list_pages_intelligent(self, message: str, intent_result) -> str:
        """Список страниц Confluence на основе анализа намерений"""
        try:
            entities = intent_result.entities
            space_name = entities.get('space_name', 'TEST')
            
            # Определяем количество страниц
            import re
            count_match = re.search(r'(\d+)', message)
            limit = int(count_match.group(1)) if count_match else 10
            
            # Получаем страницы из указанного пространства
            pages = self.confluence.get_all_pages_from_space(space_name, limit=limit)
            
            if not pages:
                return f"📋 В пространстве '{space_name}' нет страниц"
            
            result = f"📋 Последние {len(pages)} страниц в пространстве **{space_name}**:\n\n"
            for page in pages:
                title = page.get('title', 'Без названия')
                page_id = page.get('id')
                page_url = f"{self.confluence_url}/pages/viewpage.action?pageId={page_id}"
                created = page.get('created', '')
                author = page.get('version', {}).get('by', {}).get('displayName', 'Неизвестно')
                
                result += f"• **{title}**\n"
                result += f"  👤 Автор: {author}\n"
                result += f"  📅 Создана: {created[:10] if created else 'Неизвестно'}\n"
                result += f"  🔗 [Открыть страницу]({page_url})\n\n"
            
            return result
        except Exception as e:
            return f"❌ Ошибка получения списка: {str(e)}"
    
    def _get_current_date(self) -> str:
        """Возвращает текущую дату в формате строки"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _search_pages_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Ищет страницы через инструмент"""
        try:
            query = arguments.get('query', '')
            space_key = arguments.get('space_key')
            limit = arguments.get('limit', 5)
            
            if not query:
                return {'error': 'Не указан поисковый запрос'}
            
            # Формируем CQL запрос
            cql = f'text ~ "{query}"'
            if space_key:
                cql += f' AND space = "{space_key}"'
            
            pages = self.confluence.cql(cql, limit=limit)
            
            if not pages or not pages.get('results'):
                return {'results': []}
            
            result = []
            for page in pages['results']:
                result.append({
                    'id': page.get('id'),
                    'title': page.get('title', 'Без названия'),
                    'space': page.get('space', {}).get('name', 'Неизвестно'),
                    'url': f"{self.confluence_url}/pages/viewpage.action?pageId={page.get('id')}",
                    'created': page.get('created'),
                    'last_modified': page.get('last_modified')
                })
            
            return {'results': result}
        except Exception as e:
            return {'error': str(e)}
    
    def _create_page_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Создает страницу через инструмент"""
        try:
            title = arguments.get('title', '')
            content = arguments.get('content', '')
            space_key = arguments.get('space_key', 'TEST')
            parent_page_id = arguments.get('parent_page_id')
            
            if not all([title, content, space_key]):
                return {'error': 'Не указаны обязательные параметры: title, content, space_key'}
            
            # Формируем HTML контент
            html_content = f"<p>{content}</p>"
            
            page_data = {
                'title': title,
                'body': html_content,
                'space': space_key,
                'type': 'page'
            }
            
            if parent_page_id:
                page_data['parent_id'] = parent_page_id
            
            result = self.confluence.create_page(**page_data)
            page_id = result.get('id')
            
            return {
                'success': True,
                'id': page_id,
                'title': title,
                'space': space_key,
                'url': f"{self.confluence_url}/pages/viewpage.action?pageId={page_id}"
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _list_pages_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Получает список страниц через инструмент"""
        try:
            space_key = arguments.get('space_key', 'TEST')
            limit = arguments.get('limit', 10)
            
            pages = self.confluence.get_all_pages_from_space(space_key, limit=limit)
            
            if not pages:
                return {'pages': []}
            
            result = []
            for page in pages:
                result.append({
                    'id': page.get('id'),
                    'title': page.get('title', 'Без названия'),
                    'space': space_key,
                    'url': f"{self.confluence_url}/pages/viewpage.action?pageId={page.get('id')}",
                    'created': page.get('created'),
                    'last_modified': page.get('version', {}).get('when'),
                    'author': page.get('version', {}).get('by', {}).get('displayName', 'Неизвестно')
                })
            
            return {'pages': result, 'space': space_key}
        except Exception as e:
            return {'error': str(e)}
    
    def _get_page_content_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Получает содержимое страницы через инструмент"""
        try:
            page_id = arguments.get('page_id')
            
            if not page_id:
                return {'error': 'Не указан ID страницы'}
            
            page = self.confluence.get_page_by_id(page_id)
            
            if not page:
                return {'error': f'Страница с ID {page_id} не найдена'}
            
            return {
                'id': page.get('id'),
                'title': page.get('title'),
                'content': page.get('body', {}).get('storage', {}).get('value', ''),
                'space': page.get('space', {}).get('name'),
                'url': f"{self.confluence_url}/pages/viewpage.action?pageId={page_id}",
                'created': page.get('created'),
                'last_modified': page.get('version', {}).get('when'),
                'author': page.get('version', {}).get('by', {}).get('displayName', 'Неизвестно')
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _update_page_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Обновляет страницу через инструмент"""
        try:
            page_id = arguments.get('page_id')
            title = arguments.get('title')
            content = arguments.get('content', '')
            
            if not page_id or not content:
                return {'error': 'Не указаны обязательные параметры: page_id, content'}
            
            # Получаем текущую страницу
            page = self.confluence.get_page_by_id(page_id)
            if not page:
                return {'error': f'Страница с ID {page_id} не найдена'}
            
            # Формируем HTML контент
            html_content = f"<p>{content}</p>"
            
            # Обновляем страницу
            update_data = {
                'page_id': page_id,
                'body': html_content
            }
            
            if title:
                update_data['title'] = title
            
            self.confluence.update_page(**update_data)
            
            return {
                'success': True,
                'id': page_id,
                'title': title or page.get('title'),
                'url': f"{self.confluence_url}/pages/viewpage.action?pageId={page_id}"
            }
        except Exception as e:
            return {'error': str(e)}

    def get_tools(self) -> List[Dict[str, Any]]:
        """Возвращает список доступных инструментов Confluence"""
        return [
            {
                "name": "search_pages",
                "description": "Ищет страницы в Confluence",
                "parameters": {
                    "query": {"type": "string", "description": "Поисковый запрос"},
                    "space_key": {"type": "string", "description": "Ключ пространства"},
                    "limit": {"type": "integer", "description": "Максимальное количество результатов"}
                }
            },
            {
                "name": "create_page",
                "description": "Создает новую страницу в Confluence",
                "parameters": {
                    "title": {"type": "string", "description": "Заголовок страницы"},
                    "content": {"type": "string", "description": "Содержимое страницы"},
                    "space_key": {"type": "string", "description": "Ключ пространства"},
                    "parent_page_id": {"type": "string", "description": "ID родительской страницы"}
                }
            },
            {
                "name": "list_pages",
                "description": "Получает список страниц пространства",
                "parameters": {
                    "space_key": {"type": "string", "description": "Ключ пространства"},
                    "limit": {"type": "integer", "description": "Максимальное количество результатов"}
                }
            },
            {
                "name": "get_page_content",
                "description": "Получает содержимое страницы",
                "parameters": {
                    "page_id": {"type": "string", "description": "ID страницы"}
                }
            },
            {
                "name": "update_page",
                "description": "Обновляет содержимое страницы",
                "parameters": {
                    "page_id": {"type": "string", "description": "ID страницы"},
                    "title": {"type": "string", "description": "Новый заголовок"},
                    "content": {"type": "string", "description": "Новое содержимое"}
                }
            }
        ]

    def check_health(self) -> Dict[str, Any]:
        """Проверка состояния подключения к Confluence"""
        try:
            if self.confluence:
                # Проверяем подключение
                self.confluence.get_spaces()
                return {'status': 'connected', 'url': self.confluence_url}
            else:
                return {'status': 'not_configured', 'url': None}
        except Exception as e:
            return {'status': 'error', 'error': str(e), 'url': self.confluence_url}
