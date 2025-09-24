#!/usr/bin/env python3
"""
Упрощенный MCP клиент без интеллектуального определения инструментов
Каждый MCP сервер имеет фиксированный набор инструментов, которые отправляются в LLM сразу
"""

import logging
from typing import Dict, Any, List
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
        
        # Кэширование серверов
        self._cached_servers: Dict[str, Any] = {}
        self._servers_initialized = False
        
        self._load_config()
        self._define_tools()
    
    def _load_config(self):
        """Загружает конфигурацию MCP серверов"""
        self.mcp_config = self.config_manager.get_service_config('mcp_servers')
    
    def _define_tools(self):
        """Определяет предопределенные инструменты для каждого сервера"""
        # Получаем информацию о включенных сервисах
        enabled_services = self._get_enabled_services()
        
        # Определяем инструменты только для включенных сервисов
        all_tools = {}
        
        # Получаем встроенные серверы
        builtin_servers = self._get_builtin_servers()
        
        # Добавляем инструменты только для включенных сервисов
        for server_name, server in builtin_servers.items():
            if server_name in enabled_services:
                try:
                    tools = server.get_tools()
                    if tools:
                        all_tools[server_name] = tools
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось получить инструменты от {server_name}: {e}")
        
        self.server_tools = all_tools
    
    def _get_builtin_servers(self) -> Dict[str, Any]:
        """Получает экземпляры встроенных MCP серверов через автоматическое обнаружение с кэшированием"""
        # Возвращаем кэшированные серверы, если они уже инициализированы
        if self._servers_initialized and self._cached_servers:
            logger.debug(f"🔄 Используем кэшированные серверы: {list(self._cached_servers.keys())}")
            return self._cached_servers
        
        servers = {}
        
        try:
            # Используем автоматическое обнаружение серверов
            from mcp_servers import get_discovered_servers, create_server_instance
            
            discovered_servers = get_discovered_servers()
            logger.info(f"🔍 Обнаружено серверов: {len(discovered_servers)}")
            
            for server_name in discovered_servers.keys():
                try:
                    # Создаем экземпляр сервера только если его нет в кэше
                    if server_name not in self._cached_servers:
                        server_instance = create_server_instance(server_name)
                        
                        if server_instance:
                            # Проверяем, включен ли сервер
                            if server_instance.is_enabled():
                                self._cached_servers[server_name] = server_instance
                                logger.info(f"✅ Сервер {server_name} загружен и включен")
                            else:
                                logger.info(f"ℹ️ Сервер {server_name} отключен")
                        else:
                            logger.warning(f"⚠️ Не удалось создать экземпляр сервера {server_name}")
                    else:
                        logger.debug(f"🔄 Используем кэшированный сервер {server_name}")
                    
                    # Добавляем в результат
                    if server_name in self._cached_servers:
                        servers[server_name] = self._cached_servers[server_name]
                        
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка загрузки сервера {server_name}: {e}")
            
            # Помечаем серверы как инициализированные
            self._servers_initialized = True
            
        except Exception as e:
            logger.error(f"❌ Ошибка автоматического обнаружения серверов: {e}")
        
        return servers
    
    def invalidate_server_cache(self):
        """Сбрасывает кэш серверов (полезно при изменении конфигурации)"""
        self._cached_servers.clear()
        self._servers_initialized = False
        logger.info("🔄 Кэш серверов сброшен")
    
    async def initialize_servers(self):
        """Инициализирует подключения к MCP серверам"""
        try:
            if not MCP_AVAILABLE:
                logger.warning("⚠️ MCP библиотека недоступна, используем встроенные серверы")
                return
            
            # Получаем список включенных серверов из конфигурации
            enabled_servers = self._get_enabled_servers_from_config()
            
            # Подключаемся только к включенным серверам
            for server_name in enabled_servers:
                try:
                    await self._connect_external_server(server_name)
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось подключиться к внешнему серверу {server_name}: {e}")
                
            logger.info(f"✅ Инициализировано {len(self.sessions)} внешних MCP серверов")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации MCP серверов: {e}")
    
    def _get_enabled_servers_from_config(self) -> List[str]:
        """Получает список включенных серверов из конфигурации"""
        enabled_servers = []
        
        # Получаем все секции конфигурации
        for section_name, section_config in self.mcp_config.items():
            if isinstance(section_config, dict) and section_config.get('enabled', False):
                enabled_servers.append(section_name)
        
        logger.info(f"🔧 Включенные серверы из конфигурации: {enabled_servers}")
        return enabled_servers
    
    async def _connect_external_server(self, server_name: str):
        """Подключается к внешнему MCP серверу по имени"""
        try:
            server_config = self.mcp_config.get(server_name, {})
            
            # Проверяем, что сервер включен
            if not server_config.get('enabled', False):
                logger.info(f"ℹ️ Сервер {server_name} отключен в конфигурации")
                return
            
            # Получаем параметры подключения
            command = server_config.get('command')
            args = server_config.get('args', [])
            
            if not command:
                logger.warning(f"⚠️ Не указана команда для сервера {server_name}")
                return
            
            # Создаем параметры сервера
            server_params = StdioServerParameters(
                command=command,
                args=args
            )
            
            # Подключаемся к серверу
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # Получаем список инструментов
                    tools_result = await session.list_tools()
                    tools = tools_result.tools
                    
                    # Сохраняем сессию и инструменты
                    self.sessions[server_name] = session
                    self.available_tools[server_name] = tools
                    
                    logger.info(f"✅ Подключен к внешнему серверу {server_name} с {len(tools)} инструментами")
                    
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к серверу {server_name}: {e}")
            raise
    
    async def get_all_tools(self) -> List[Dict]:
        """Возвращает все доступные инструменты для отправки в LLM"""
        all_tools = []
        
        # Получаем список включенных сервисов
        enabled_services = self._get_enabled_services()
        
        # Собираем инструменты от внешних MCP серверов
        for server_name, tools in self.available_tools.items():
            if server_name in enabled_services:
                for tool in tools:
                    # Добавляем информацию о сервере к каждому инструменту
                    tool_with_server = tool.copy()
                    tool_with_server['server'] = server_name
                    all_tools.append(tool_with_server)
        
        # Собираем инструменты от встроенных серверов
        builtin_servers = self._get_builtin_servers()
        for server_name, server in builtin_servers.items():
            if server_name in enabled_services:
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
        """Проверяет доступность сервера с кэшированием"""
        try:
            # Проверяем, что сервер включен
            if hasattr(server, 'is_enabled') and callable(server.is_enabled):
                if server.is_enabled():
                    # Используем кэшированную проверку подключения
                    if hasattr(server, 'test_connection') and callable(server.test_connection):
                        return server.test_connection()  # Уже использует кэширование
                    # Если нет методов проверки, считаем доступным
                    else:
                        logger.warning(f"⚠️ Сервер {server_name} не имеет методов проверки здоровья")
                        return True
            return False
        except Exception as e:
            logger.warning(f"⚠️ Ошибка проверки доступности сервера {server_name}: {e}")
            return False
    
    async def process_message_with_llm(self, message: str, user_context: dict = None) -> str:
        """Обрабатывает сообщение с помощью LLM и всех доступных инструментов"""
        try:
            # Проверяем, нужно ли использовать ReAct агента
            use_react = user_context.get('use_react', False) if user_context else False
            
            if use_react:
                return await self._process_with_react(message, user_context)
            else:
                return await self._process_with_simple_llm(message, user_context)
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки сообщения: {e}")
            return f"Извините, произошла ошибка при обработке вашего запроса: {str(e)}"
    
    async def _process_with_react(self, message: str, user_context: dict = None) -> str:
        """Обрабатывает сообщение с использованием ReAct агента"""
        try:
            from react_agent import get_react_agent
            from llm_client import LLMClient
            
            # Получаем ReAct агента
            llm_client = LLMClient()
            react_agent = get_react_agent(self, llm_client)
            
            if not react_agent or not react_agent.is_available():
                logger.warning("⚠️ ReAct агент недоступен, используем простую обработку")
                return await self._process_with_simple_llm(message, user_context)
            
            # Обрабатываем запрос через ReAct
            result = await react_agent.process_query(message, user_context)
            
            if result["success"]:
                logger.info(f"✅ ReAct агент выполнил {result['iterations']} итераций, использовал {result['tools_used']} инструментов")
                return result["result"]
            else:
                logger.error(f"❌ Ошибка ReAct агента: {result['error']}")
                return f"Ошибка ReAct агента: {result['error']}"
                
        except Exception as e:
            logger.error(f"❌ Ошибка ReAct обработки: {e}")
            return await self._process_with_simple_llm(message, user_context)
    
    async def _process_with_simple_llm(self, message: str, user_context: dict = None) -> str:
        """Обрабатывает сообщение с помощью простого LLM (старый способ)"""
        try:
            # Получаем все доступные инструменты
            all_tools = await self.get_all_tools()
            
            # Если MCP серверы не подключены, используем встроенные серверы
            if not self.sessions:
                return await self._handle_with_builtin_servers(message, user_context)
            
            # Отправляем запрос в LLM с полным набором инструментов
            from llm_client import LLMClient
            llm_client = LLMClient()
            
            # Формируем контекст с инструментами и историей чата
            tools_context = {
                "available_tools": all_tools,
                "user_message": message,
                "user_context": user_context or {},
                "chat_history": user_context.get('chat_history', []) if user_context else []
            }
            
            # Отправляем в LLM для обработки
            response = await llm_client.process_with_tools(tools_context)
            return response
                
        except Exception as e:
            logger.error(f"❌ Ошибка простой LLM обработки: {e}")
            return f"Извините, произошла ошибка при обработке вашего запроса: {str(e)}"
    
    async def _handle_with_builtin_servers(self, message: str, user_context: dict) -> str:
        """Обрабатывает запросы с использованием встроенных серверов"""
        try:
            # Получаем все доступные инструменты от встроенных серверов
            all_tools = await self.get_all_tools()
            
            # Отправляем запрос в LLM с полным набором инструментов
            from llm_client import LLMClient
            llm_client = LLMClient()
            
            # Формируем контекст с инструментами и историей чата
            tools_context = {
                "available_tools": all_tools,
                "user_message": message,
                "user_context": user_context or {},
                "chat_history": user_context.get('chat_history', []) if user_context else []
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
            
            # При ошибке сбрасываем кэш подключения для этого сервера
            if server_name in builtin_servers:
                server = builtin_servers[server_name]
                if hasattr(server, 'invalidate_connection_cache'):
                    server.invalidate_connection_cache()
            
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
    
    def _get_enabled_services(self) -> List[str]:
        """Получает список включенных сервисов"""
        enabled_services = []
        
        # Получаем встроенные серверы
        builtin_servers = self._get_builtin_servers()
        
        # Проверяем каждый сервер
        for server_name, server in builtin_servers.items():
            try:
                if server.is_enabled():
                    enabled_services.append(server_name)
            except Exception as e:
                logger.warning(f"Не удалось проверить статус сервера {server_name}: {e}")
        
        return enabled_services

# Глобальный экземпляр упрощенного MCP клиента
mcp_client = MCPClient()
