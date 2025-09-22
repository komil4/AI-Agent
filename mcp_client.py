#!/usr/bin/env python3
"""
Упрощенный MCP клиент без интеллектуального определения инструментов
Каждый MCP сервер имеет фиксированный набор инструментов, которые отправляются в LLM сразу
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from config.config_manager import ConfigManager

# Условный импорт MCP библиотеки
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    # Заглушки для типов
    ClientSession = Any
    StdioServerParameters = Any
    stdio_client = None

logger = logging.getLogger(__name__)

class MCPClient:
    """Упрощенный MCP клиент без интеллектуального анализа"""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.sessions: Dict[str, ClientSession] = {}
        self.available_tools: Dict[str, List[Dict]] = {}
        self.server_tools: Dict[str, List[Dict]] = {}
        self._load_config()
        self._define_tools()
    
    def _load_config(self):
        """Загружает конфигурацию MCP серверов"""
        self.mcp_config = self.config_manager.get_service_config('mcp_servers')
    
    async def _connect_onec_server(self):
        """Подключается к 1С MCP серверу"""
        if not MCP_AVAILABLE:
            logger.warning("⚠️ MCP библиотека недоступна, пропускаем подключение к 1С MCP серверу")
            return
            
        try:
            # Для 1С используем встроенный сервер
            onec_server = self.builtin_servers.get('onec')
            if onec_server:
                self.sessions['onec'] = onec_server
                # Используем предопределенные инструменты
                self.available_tools['onec'] = self.server_tools['onec']
                logger.info("✅ 1С MCP сервер подключен (встроенный)")
            else:
                logger.warning("⚠️ 1С MCP сервер не найден")
                    
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к 1С MCP серверу: {e}")
    
    def _define_tools(self):
        """Определяет предопределенные инструменты для каждого сервера"""
        self.server_tools = {
            'jira': [
                {
                    "name": "create_issue",
                    "description": "Создает новую задачу в Jira",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "summary": {"type": "string", "description": "Краткое описание задачи"},
                            "description": {"type": "string", "description": "Подробное описание задачи"},
                            "project_key": {"type": "string", "description": "Ключ проекта (например, TEST)"},
                            "issue_type": {"type": "string", "description": "Тип задачи (Task, Bug, Story)"}
                        },
                        "required": ["summary", "project_key"]
                    }
                },
                {
                    "name": "search_issues",
                    "description": "Ищет задачи в Jira по JQL запросу",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "jql": {"type": "string", "description": "JQL запрос для поиска"},
                            "max_results": {"type": "integer", "description": "Максимальное количество результатов"}
                        },
                        "required": ["jql"]
                    }
                }
            ],
            'gitlab': [
                {
                    "name": "list_projects",
                    "description": "Получает список проектов GitLab",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "search": {"type": "string", "description": "Поисковый запрос"},
                            "per_page": {"type": "integer", "description": "Количество результатов на странице"}
                        }
                    }
                },
                {
                    "name": "get_project_commits",
                    "description": "Получает коммиты проекта",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "project_name": {"type": "string", "description": "Название проекта"},
                            "per_page": {"type": "integer", "description": "Количество коммитов"},
                            "author_email": {"type": "string", "description": "Email автора для фильтрации"}
                        },
                        "required": ["project_name"]
                    }
                }
            ],
            'onec': [
                {
                    "name": "get_user_tasks",
                    "description": "Получает список задач пользователя в 1С",
                    "parameters": {
                        "user": {"type": "string", "description": "Имя пользователя для получения задач"}
                    }
                },
                {
                    "name": "get_task_info",
                    "description": "Получает детальную информацию по задаче в 1С",
                    "parameters": {
                        "task_id": {"type": "string", "description": "Идентификатор задачи"}
                    }
                }
            ],
            'confluence': [
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
                }
            ]
        }
    
    def _get_builtin_servers(self) -> Dict[str, Any]:
        """Получает экземпляры встроенных MCP серверов"""
        try:
            from mcp_servers.jira_server import JiraMCPServer
            from mcp_servers.gitlab_server import GitLabMCPServer
            from mcp_servers.atlassian_server import AtlassianMCPServer
            from mcp_servers.onec_server import OneCMCPServer
            
            servers = {
                'jira': JiraMCPServer(),
                'gitlab': GitLabMCPServer(),
                'confluence': AtlassianMCPServer(),
                'onec': OneCMCPServer()
            }
            
            # Проверяем, включен ли LDAP в конфигурации
            ad_config = self.config_manager.get_service_config('active_directory')
            if ad_config.get('enabled', False):
                from mcp_servers.ldap_server import LDAPMCPServer
                servers['ldap'] = LDAPMCPServer()
                logger.info("✅ LDAP сервер включен в конфигурации")
            else:
                logger.info("ℹ️ LDAP сервер отключен в конфигурации")
            
            return servers
        except Exception as e:
            logger.error(f"❌ Ошибка создания встроенных серверов: {e}")
            return {}
    
    async def initialize_servers(self):
        """Инициализирует подключения к MCP серверам"""
        try:
            if not MCP_AVAILABLE:
                logger.warning("⚠️ MCP библиотека недоступна, используем встроенные серверы")
                return
            
            # Jira MCP сервер
            if self.mcp_config.get('jira', {}).get('enabled', False):
                await self._connect_jira_server()
            
            # GitLab MCP сервер  
            if self.mcp_config.get('gitlab', {}).get('enabled', False):
                await self._connect_gitlab_server()
            
            # Confluence MCP сервер
            if self.mcp_config.get('confluence', {}).get('enabled', False):
                await self._connect_confluence_server()
            
            # 1С MCP сервер
            if self.mcp_config.get('onec', {}).get('enabled', False):
                await self._connect_onec_server()
                
            logger.info(f"✅ Инициализировано {len(self.sessions)} MCP серверов")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации MCP серверов: {e}")
    
    async def _connect_jira_server(self):
        """Подключается к Jira MCP серверу"""
        if not MCP_AVAILABLE:
            logger.warning("⚠️ MCP библиотека недоступна, пропускаем подключение к Jira MCP серверу")
            return
            
        try:
            jira_config = self.mcp_config.get('jira', {})
            server_params = StdioServerParameters(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-jira"],
                env={
                    "JIRA_URL": jira_config.get('url', ''),
                    "JIRA_USERNAME": jira_config.get('username', ''),
                    "JIRA_API_TOKEN": jira_config.get('api_token', '')
                }
            )
            
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    self.sessions['jira'] = session
                    # Используем предопределенные инструменты вместо загрузки с сервера
                    self.available_tools['jira'] = self.server_tools['jira']
                    
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к Jira MCP серверу: {e}")
    
    async def _connect_gitlab_server(self):
        """Подключается к GitLab MCP серверу"""
        if not MCP_AVAILABLE:
            logger.warning("⚠️ MCP библиотека недоступна, пропускаем подключение к GitLab MCP серверу")
            return
            
        try:
            gitlab_config = self.mcp_config.get('gitlab', {})
            server_params = StdioServerParameters(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-gitlab"],
                env={
                    "GITLAB_URL": gitlab_config.get('url', ''),
                    "GITLAB_TOKEN": gitlab_config.get('token', '')
                }
            )
            
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    self.sessions['gitlab'] = session
                    # Используем предопределенные инструменты вместо загрузки с сервера
                    self.available_tools['gitlab'] = self.server_tools['gitlab']
                    
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к GitLab MCP серверу: {e}")
    
    async def _connect_confluence_server(self):
        """Подключается к Confluence MCP серверу"""
        if not MCP_AVAILABLE:
            logger.warning("⚠️ MCP библиотека недоступна, пропускаем подключение к Confluence MCP серверу")
            return
            
        try:
            confluence_config = self.mcp_config.get('confluence', {})
            server_params = StdioServerParameters(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-confluence"],
                env={
                    "CONFLUENCE_URL": confluence_config.get('url', ''),
                    "CONFLUENCE_USERNAME": confluence_config.get('username', ''),
                    "CONFLUENCE_API_TOKEN": confluence_config.get('api_token', '')
                }
            )
            
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    self.sessions['confluence'] = session
                    # Используем предопределенные инструменты вместо загрузки с сервера
                    self.available_tools['confluence'] = self.server_tools['confluence']
                    
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к Confluence MCP серверу: {e}")
    
    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Вызывает инструмент на MCP сервере"""
        try:
            if server_name not in self.sessions:
                return {"error": f"MCP сервер {server_name} не подключен"}
            
            session = self.sessions[server_name]
            result = await session.call_tool(tool_name, arguments)
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка вызова инструмента {tool_name} на {server_name}: {e}")
            return {"error": str(e)}
    
    async def get_all_tools(self) -> List[Dict]:
        """Возвращает все доступные инструменты для отправки в LLM"""
        all_tools = []
        
        # Собираем инструменты от внешних MCP серверов
        for server_name, tools in self.available_tools.items():
            for tool in tools:
                # Добавляем информацию о сервере к каждому инструменту
                tool_with_server = tool.copy()
                tool_with_server['server'] = server_name
                all_tools.append(tool_with_server)
        
        # Собираем инструменты от встроенных серверов
        builtin_servers = self._get_builtin_servers()
        for server_name, server in builtin_servers.items():
            try:
                # Проверяем, что сервер доступен
                if self._is_server_available(server_name, server):
                    tools = server.get_tools()
                    for tool in tools:
                        tool_with_server = tool.copy()
                        tool_with_server['server'] = server_name
                        all_tools.append(tool_with_server)
            except Exception as e:
                logger.warning(f"⚠️ Не удалось получить инструменты от {server_name}: {e}")
        
        return all_tools
    
    def _is_server_available(self, server_name: str, server: Any) -> bool:
        """Проверяет доступность сервера"""
        try:
            if server_name == 'jira':
                return server.jira is not None
            elif server_name == 'gitlab':
                return server.gl is not None
            elif server_name == 'confluence':
                return server.confluence is not None
            elif server_name == 'onec':
                return server.auth is not None
            elif server_name == 'ldap':
                # Проверяем, включен ли LDAP в конфигурации
                ad_config = self.config_manager.get_service_config('active_directory')
                if not ad_config.get('enabled', False):
                    return False
                return server.connection is not None
            return False
        except Exception:
            return False
    
    async def process_message_with_llm(self, message: str, user_context: dict = None) -> str:
        """Обрабатывает сообщение с помощью LLM и всех доступных инструментов"""
        try:
            # Получаем все доступные инструменты
            all_tools = await self.get_all_tools()
            
            # Если MCP серверы не подключены, используем встроенные серверы
            if not self.sessions:
                return await self._handle_with_builtin_servers(message, user_context)
            
            # Отправляем запрос в LLM с полным набором инструментов
            from llm_client import LLMClient
            llm_client = LLMClient()
            
            # Формируем контекст с инструментами
            tools_context = {
                "available_tools": all_tools,
                "user_message": message,
                "user_context": user_context or {}
            }
            
            # Отправляем в LLM для обработки
            response = await llm_client.process_with_tools(tools_context)
            return response
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки сообщения: {e}")
            return f"Извините, произошла ошибка при обработке вашего запроса: {str(e)}"
    
    async def _handle_with_builtin_servers(self, message: str, user_context: dict) -> str:
        """Обрабатывает запросы с использованием встроенных серверов"""
        try:
            # Получаем все доступные инструменты от встроенных серверов
            all_tools = await self.get_all_tools()
            
            # Отправляем запрос в LLM с полным набором инструментов
            from llm_client import LLMClient
            llm_client = LLMClient()
            
            # Формируем контекст с инструментами
            tools_context = {
                "available_tools": all_tools,
                "user_message": message,
                "user_context": user_context or {}
            }
            
            # Отправляем в LLM для обработки
            response = await llm_client.process_with_tools(tools_context)
            return response
                
        except Exception as e:
            logger.error(f"❌ Ошибка работы с встроенными серверами: {e}")
            return f"Извините, произошла ошибка при обработке вашего запроса: {str(e)}"
    
    async def call_tool_builtin(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Вызывает инструмент на встроенном сервере"""
        try:
            # Получаем встроенные серверы
            builtin_servers = self._get_builtin_servers()
            
            if server_name not in builtin_servers:
                return {"error": f"Неизвестный сервер: {server_name}"}
            
            server = builtin_servers[server_name]
            
            # Проверяем доступность сервера
            if not self._is_server_available(server_name, server):
                return {"error": f"{server_name} не подключен"}
            
            # Вызываем инструмент
            return server.call_tool(tool_name, arguments)
                
        except Exception as e:
            logger.error(f"❌ Ошибка вызова инструмента {tool_name} на {server_name}: {e}")
            return {"error": f"Ошибка вызова инструмента: {str(e)}"}
    
    async def close_all_sessions(self):
        """Закрывает все MCP сессии"""
        for server_name, session in self.sessions.items():
            try:
                await session.close()
                logger.info(f"✅ Сессия {server_name} закрыта")
            except Exception as e:
                logger.error(f"❌ Ошибка закрытия сессии {server_name}: {e}")
        
        self.sessions.clear()
        self.available_tools.clear()

# Глобальный экземпляр упрощенного MCP клиента
mcp_client = MCPClient()
