#!/usr/bin/env python3
"""
MCP клиент для работы с MCP серверами
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from mcp_servers.server_discovery import MCPServerDiscovery
from mcp_servers.base_mcp_server import BaseMCPServer

logger = logging.getLogger(__name__)

class MCPClient:
    """Клиент для работы с MCP серверами"""
    
    def __init__(self):
        """Инициализирует MCP клиент"""
        self.servers = {}
        self.builtin_servers = {}
        self.server_discovery = MCPServerDiscovery()
        self._initialized = False
    
    async def initialize_servers(self):
        """Инициализирует все доступные серверы"""
        if self._initialized:
            return
        
        try:
            logger.info("[INIT] Инициализация MCP серверов...")
            
            # Обнаруживаем и инициализируем серверы
            discovered_server_names = self.server_discovery.get_server_names()
            
            for server_name in discovered_server_names:
                try:
                    server_class = self.server_discovery.get_server_class(server_name)
                    if server_class:
                        server_instance = server_class()
                        await server_instance.initialize()
                        
                        self.servers[server_name] = server_instance
                        logger.info(f"[OK] Сервер {server_name} инициализирован")
                    
                except Exception as e:
                    logger.error(f"[ERROR] Ошибка инициализации сервера {server_name}: {e}")
            
            # Инициализируем встроенные серверы
            await self._initialize_builtin_servers()
            
            self._initialized = True
            logger.info(f"[OK] Инициализировано {len(self.servers)} MCP серверов")
            
        except Exception as e:
            logger.error(f"[ERROR] Ошибка инициализации MCP серверов: {e}")
    
    async def _initialize_builtin_servers(self):
        """Инициализирует встроенные серверы"""
        try:
            # Импортируем встроенные серверы
            from mcp_servers.file_server import FileMCPServer
            from mcp_servers.ldap_server import LDAPMCPServer
            from mcp_servers.jira_server import JiraMCPServer
            from mcp_servers.gitlab_server import GitLabMCPServer
            from mcp_servers.atlassian_server import AtlassianMCPServer
            from mcp_servers.onec_server import OneCMCPServer
            
            builtin_server_classes = {
                'file': FileMCPServer,
                'ldap': LDAPMCPServer,
                'jira': JiraMCPServer,
                'gitlab': GitLabMCPServer,
                'atlassian': AtlassianMCPServer,
                'onec': OneCMCPServer
            }
            
            for server_name, server_class in builtin_server_classes.items():
                try:
                    server_instance = server_class()
                    await server_instance.initialize()
                    
                    self.builtin_servers[server_name] = server_instance
                    logger.info(f"[OK] Встроенный сервер {server_name} инициализирован")
                    
                except Exception as e:
                    logger.error(f"[ERROR] Ошибка инициализации встроенного сервера {server_name}: {e}")
                    
        except Exception as e:
            logger.error(f"[ERROR] Ошибка инициализации встроенных серверов: {e}")
    
    async def call_tool(self, server_name: str, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Вызывает инструмент на указанном сервере"""
        try:
            if server_name in self.servers:
                server = self.servers[server_name]
                return server.call_tool(tool_name, params)
            else:
                return {
                    'error': f'Сервер {server_name} не подключен',
                    'success': False
                }
                
        except Exception as e:
            logger.error(f"[ERROR] Ошибка вызова инструмента {tool_name} на сервере {server_name}: {e}")
            return {
                'error': str(e),
                'success': False
            }
    
    async def call_tool_builtin(self, server_name: str, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Вызывает инструмент на встроенном сервере"""
        try:
            if server_name in self.builtin_servers:
                server = self.builtin_servers[server_name]
                return server.call_tool(tool_name, params)
            else:
                return {
                    'error': f'Встроенный сервер {server_name} не найден',
                    'success': False
                }
                
        except Exception as e:
            logger.error(f"[ERROR] Ошибка вызова инструмента {tool_name} на встроенном сервере {server_name}: {e}")
            return {
                'error': str(e),
                'success': False
            }
    
    async def get_all_tools(self) -> List[Dict[str, Any]]:
        """Получает все доступные инструменты"""
        tools = []
        
        try:
            # Получаем инструменты от всех серверов
            for server_name, server in self.servers.items():
                try:
                    server_tools = server.get_tools()
                    for tool in server_tools:
                        tool['server'] = server_name
                        tools.append(tool)
                except Exception as e:
                    logger.error(f"[ERROR] Ошибка получения инструментов от сервера {server_name}: {e}")
            
            # Получаем инструменты от встроенных серверов
            for server_name, server in self.builtin_servers.items():
                try:
                    server_tools = server.get_tools()
                    for tool in server_tools:
                        tool['server'] = server_name
                        tools.append(tool)
                except Exception as e:
                    logger.error(f"[ERROR] Ошибка получения инструментов от встроенного сервера {server_name}: {e}")
            
            logger.info(f"[OK] Получено {len(tools)} инструментов")
            return tools
            
        except Exception as e:
            logger.error(f"[ERROR] Ошибка получения всех инструментов: {e}")
            return []
    
    def _get_builtin_servers(self) -> Dict[str, Any]:
        """Возвращает словарь встроенных серверов"""
        return self.builtin_servers
    
    async def process_message_with_llm(self, message: str, user_context: Dict[str, Any]) -> str:
        """Обрабатывает сообщение с использованием LLM"""
        try:
            # Получаем все доступные инструменты
            tools = await self.get_all_tools()
            
            if not tools:
                return "Извините, нет доступных инструментов для обработки вашего запроса."
            
            # Создаем контекст для intelligent_tool_processor
            tools_context = {
                'available_tools': tools,
                'user_message': message,
                'user_context': user_context,
                'chat_history': user_context.get('chat_history', [])
            }
            
            # Используем intelligent_tool_processor для обработки
            from intelligent_tool_processor import IntelligentToolProcessor
            from llm_client import LLMClient
            
            llm_client = LLMClient()
            processor = IntelligentToolProcessor(llm_client, self)
            
            result = await processor.process_with_intelligent_tools(tools_context)
            
            return result
            
        except Exception as e:
            logger.error(f"[ERROR] Ошибка обработки сообщения с LLM: {e}")
            return f"Извините, произошла ошибка при обработке вашего запроса: {str(e)}"
    
    async def close_all_sessions(self):
        """Закрывает все сессии серверов"""
        try:
            logger.info("[CLOSE] Закрытие всех MCP сессий...")
            
            # Закрываем внешние серверы
            for server_name, server in self.servers.items():
                try:
                    if hasattr(server, 'close'):
                        await server.close()
                    logger.info(f"[OK] Сессия сервера {server_name} закрыта")
                except Exception as e:
                    logger.error(f"[ERROR] Ошибка закрытия сессии сервера {server_name}: {e}")
            
            # Закрываем встроенные серверы
            for server_name, server in self.builtin_servers.items():
                try:
                    if hasattr(server, 'close'):
                        await server.close()
                    logger.info(f"[OK] Сессия встроенного сервера {server_name} закрыта")
                except Exception as e:
                    logger.error(f"[ERROR] Ошибка закрытия сессии встроенного сервера {server_name}: {e}")
            
            logger.info("[OK] Все MCP сессии закрыты")
            
        except Exception as e:
            logger.error(f"[ERROR] Ошибка закрытия сессий: {e}")
    
    def is_initialized(self) -> bool:
        """Проверяет, инициализирован ли клиент"""
        return self._initialized
    
    def get_server_status(self) -> Dict[str, Any]:
        """Возвращает статус всех серверов"""
        status = {
            'initialized': self._initialized,
            'servers': {},
            'builtin_servers': {}
        }
        
        for server_name, server in self.servers.items():
            try:
                status['servers'][server_name] = {
                    'connected': hasattr(server, 'is_connected') and server.is_connected(),
                    'tools_count': len(getattr(server, 'tools', []))
                }
            except Exception as e:
                status['servers'][server_name] = {
                    'connected': False,
                    'error': str(e)
                }
        
        for server_name, server in self.builtin_servers.items():
            try:
                status['builtin_servers'][server_name] = {
                    'connected': hasattr(server, 'is_connected') and server.is_connected(),
                    'tools_count': len(getattr(server, 'tools', []))
                }
            except Exception as e:
                status['builtin_servers'][server_name] = {
                    'connected': False,
                    'error': str(e)
                }
        
        return status

# Глобальный экземпляр MCP клиента
mcp_client = MCPClient()
