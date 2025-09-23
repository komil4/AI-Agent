#!/usr/bin/env python3
"""
LLM клиент с поддержкой различных провайдеров
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from config.llm_config import LLMProvider, llm_config_manager
from llm_providers import LLMProviderFactory

# Настройка логирования
logger = logging.getLogger(__name__)

class LLMClient:
    """LLM клиент с поддержкой различных провайдеров"""
    
    def __init__(self, provider: Optional[LLMProvider] = None):
        """
        Инициализирует LLM клиент
        
        Args:
            provider: Конкретный провайдер для использования. Если None, используется провайдер по умолчанию.
        """
        self.provider = provider or llm_config_manager.get_default_provider()
        self.llm_provider = None
        self._initialize_provider()
    
    def _initialize_provider(self):
        """Инициализирует выбранный провайдер"""
        try:
            # Проверяем, что провайдер доступен
            available_providers = llm_config_manager.get_available_providers()
            if self.provider not in available_providers:
                logger.warning(f"⚠️ Провайдер {self.provider.value} недоступен, доступные: {[p.value for p in available_providers]}")
                # Пробуем найти доступный провайдер
                if available_providers:
                    self.provider = available_providers[0]
                    logger.info(f"🔄 Переключение на доступный провайдер: {self.provider.value}")
                else:
                    raise Exception("Нет доступных провайдеров")
            
            self.llm_provider = LLMProviderFactory.create_provider(self.provider)
            logger.info(f"✅ LLM провайдер {self.provider.value} инициализирован")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации провайдера {self.provider.value}: {e}")
            # Fallback к провайдеру по умолчанию
            try:
                self.provider = llm_config_manager.get_default_provider()
                available_providers = llm_config_manager.get_available_providers()
                if self.provider in available_providers:
                    self.llm_provider = LLMProviderFactory.create_provider(self.provider)
                    logger.info(f"✅ Fallback к провайдеру {self.provider.value}")
                else:
                    # Пробуем любой доступный провайдер
                    if available_providers:
                        self.provider = available_providers[0]
                        self.llm_provider = LLMProviderFactory.create_provider(self.provider)
                        logger.info(f"✅ Fallback к доступному провайдеру {self.provider.value}")
                    else:
                        raise Exception("Нет доступных провайдеров")
            except Exception as fallback_error:
                logger.error(f"❌ Критическая ошибка: не удалось инициализировать ни одного провайдера: {fallback_error}")
                self.llm_provider = None
    
    def switch_provider(self, provider: LLMProvider):
        """Переключает на другой провайдер"""
        try:
            self.provider = provider
            self.llm_provider = LLMProviderFactory.create_provider(provider)
            logger.info(f"✅ Переключен на провайдер {provider.value}")
        except Exception as e:
            logger.error(f"❌ Ошибка переключения на провайдер {provider.value}: {e}")
            raise
    
    def get_available_providers(self) -> List[LLMProvider]:
        """Возвращает список доступных провайдеров"""
        return LLMProviderFactory.get_available_providers()
    
    def get_current_provider(self) -> LLMProvider:
        """Возвращает текущий провайдер"""
        return self.provider
    
    def _get_fallback_response(self, message: str) -> str:
        """Возвращает fallback ответ, если провайдер недоступен"""
        return f"Извините, LLM провайдер недоступен. Ваше сообщение: {message}. Пожалуйста, проверьте конфигурацию провайдеров в админ-панели."
    
    async def generate_response(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Генерирует ответ на основе сообщения
        
        Args:
            message: Сообщение пользователя
            context: Дополнительный контекст
            
        Returns:
            Сгенерированный ответ
        """
        if not self.llm_provider:
            return self._get_fallback_response(message)
        
        try:
            # Формируем сообщения для LLM
            messages = self._format_messages(message, context)
            
            # Генерируем ответ
            response = await self.llm_provider.generate_response(messages)
            return response
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации ответа: {e}")
            return self._get_fallback_response(message)
    
    async def process_with_tools(self, tools_context: Dict[str, Any]) -> str:
        """
        Обрабатывает запрос с использованием инструментов
        
        Args:
            tools_context: Контекст с инструментами и сообщением
            
        Returns:
            Результат обработки
        """
        if not self.llm_provider:
            return "Извините, LLM провайдер недоступен"
        
        try:
            available_tools = tools_context.get('available_tools', [])
            user_message = tools_context.get('user_message', '')
            user_context = tools_context.get('user_context', {})
            
            # Формируем сообщения для LLM
            messages = self._format_messages_with_tools(user_message, available_tools, user_context)
            
            # Генерируем ответ с инструментами
            response = await self.llm_provider.generate_with_tools(user_message, messages, available_tools)
            
            # Обрабатываем ответ
            if response.get('action') == 'call_tool':
                # Вызываем инструмент через MCP клиент
                from mcp_client import mcp_client
                
                # Пытаемся вызвать через внешние MCP серверы
                tool_result = await mcp_client.call_tool(
                    response['server'],
                    response['tool'],
                    response['arguments']
                )
                
                # Если внешние серверы недоступны, используем встроенные
                if 'error' in tool_result and 'не подключен' in tool_result['error']:
                    tool_result = await mcp_client.call_tool_builtin(
                        response['server'],
                        response['tool'],
                        response['arguments']
                    )
                
                return await self._format_tool_result(tool_result, response)
            elif response.get('action') == 'respond':
                return response.get('message', 'Нет ответа')
            else:
                # Если ответ не в ожидаемом формате, пытаемся извлечь JSON
                if isinstance(response, str):
                    json_response = self._extract_json_from_text(response, available_tools)
                    if json_response and json_response.get('action') == 'call_tool':
                        # Рекурсивно обрабатываем извлеченный JSON
                        return await self.process_with_tools({'user_message': user_message, 'user_context': user_context})
                    else:
                        return response
                else:
                    return response.get('message', 'Нет ответа')
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки с инструментами: {e}")
            return f"Извините, произошла ошибка при обработке вашего запроса: {str(e)}"
    
    def _format_messages(self, message: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
        """Форматирует сообщения для LLM"""
        messages = []
        
        # Получаем информацию о включенных сервисах
        enabled_services = self._get_enabled_services_info()
        
        # Системное сообщение
        system_prompt = f"""
Ты - полезный AI ассистент, который работает с MCP серверами.
{enabled_services}

ВАЖНО: ВСЕГДА отвечай ТОЛЬКО на русском языке. Никогда не используй английский язык в ответах.

Доступные инструменты будут предоставлены в контексте. Используй их для выполнения запросов пользователя.

Отвечай на русском языке кратко и по делу.
"""
        
        # Добавляем контекст из чата, если он есть
        if context:
            context_info = self._format_context_for_prompt(context)
            if context_info:
                system_prompt += f"\n\nКонтекст чата:\n{context_info}"
        
        messages.append({"role": "system", "content": system_prompt})
        
        # Сообщение пользователя
        #messages.append({"role": "user", "content": message})
        
        return messages
    
    def _format_messages_with_tools(self, message: str, tools: List[Dict[str, Any]], context: Dict[str, Any]) -> List[Dict[str, str]]:
        """Форматирует сообщения с инструментами для LLM"""
        messages = []
        
        # Получаем информацию о включенных сервисах
        enabled_services = self._get_enabled_services_info()
        
        # Системное сообщение с описанием инструментов
        system_prompt = f"""
Ты - полезный AI ассистент, который работает с MCP серверами.
{enabled_services}

Доступные инструменты будут предоставлены в контексте.
Используй их для выполнения запросов пользователя.

Отвечай на русском языке кратко и по делу.
"""
        
        # Добавляем контекст из чата, если он есть
        if context:
            context_info = self._format_context_for_prompt(context)
            if context_info:
                system_prompt += f"\n\nКонтекст чата:\n{context_info}"
        
        messages.append({"role": "system", "content": system_prompt})
        
        
        # Сообщение пользователя
        #messages.append({"role": "user", "content": message})
        
        return messages
    
    def _get_enabled_services_info(self) -> str:
        """Получает информацию о включенных сервисах для промпта"""
        from mcp_client import mcp_client
        
        enabled_services = []
        
        # Получаем встроенные серверы
        builtin_servers = mcp_client._get_builtin_servers()
        
        # Проверяем каждый сервер
        for server_name, server in builtin_servers.items():
            try:
                if server.is_enabled():
                    description = server.get_description()
                    enabled_services.append(f"• {description}")
            except Exception as e:
                logger.warning(f"Не удалось получить описание сервера {server_name}: {e}")
        
        if enabled_services:
            return f"У тебя есть доступ к следующим сервисам:\n" + "\n".join(enabled_services)
        else:
            return "У тебя нет доступа к внешним сервисам. Ты можешь отвечать на общие вопросы."
    
    def _format_context_for_prompt(self, context: Dict[str, Any]) -> str:
        """Форматирует контекст чата для промпта"""
        context_parts = []
        
        # Информация о пользователе
        if context.get('user'):
            user_info = context['user']
            if user_info.get('username'):
                context_parts.append(f"Пользователь: {user_info['username']}")
            if user_info.get('display_name'):
                context_parts.append(f"Имя: {user_info['display_name']}")
            if user_info.get('email'):
                context_parts.append(f"Email: {user_info['email']}")
        
        # Информация о сессии
        if context.get('session'):
            session_info = context['session']
            if session_info.get('session_id'):
                context_parts.append(f"ID сессии: {session_info['session_id']}")
            if session_info.get('created_at'):
                context_parts.append(f"Сессия создана: {session_info['created_at']}")
        
        # История чата (последние сообщения)
        if context.get('chat_history'):
            history = context['chat_history']
            if isinstance(history, list) and len(history) > 0:
                context_parts.append("История чата:")
                for msg in history[-5:]:  # Последние 5 сообщений
                    if isinstance(msg, dict):
                        role = msg.get('role', 'unknown')
                        content = msg.get('content', '')
                        context_parts.append(f"  {role}: {content[:100]}...")
        
        # Дополнительные данные
        if context.get('additional_data'):
            additional = context['additional_data']
            for key, value in additional.items():
                if isinstance(value, (str, int, float)):
                    context_parts.append(f"{key}: {value}")
        
        return "\n".join(context_parts) if context_parts else ""
    
    def _extract_json_from_text(self, text: str, available_tools: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Пытается извлечь JSON из текстового ответа Llama2"""
        try:
            import re
            import json
            
            # Очищаем текст
            cleaned_text = text.strip()
            
            # Удаляем возможные markdown блоки
            if cleaned_text.startswith('```json'):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.endswith('```'):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()
            
            # Ищем JSON объект
            json_match = re.search(r'\{[^{}]*\}', cleaned_text)
            if json_match:
                json_text = json_match.group()
                parsed = json.loads(json_text)
                
                # Проверяем, что это валидный ответ с инструментами
                if 'action' in parsed or 'tool' in parsed:
                    if 'action' not in parsed:
                        parsed['action'] = 'call_tool'
                    return parsed
            
            # Если JSON не найден, пытаемся создать его из контекста
            if any(keyword in text.lower() for keyword in ['создай', 'найди', 'покажи', 'получи', 'обнови', 'удали']):
                tool_name = self._extract_tool_name_from_text(text, available_tools)
                if tool_name:
                    return {
                        'action': 'call_tool',
                        'server': 'unknown',
                        'tool': tool_name,
                        'arguments': {}
                    }
            
            return None
            
        except Exception as e:
            logger.warning(f"Не удалось извлечь JSON из текста: {e}")
            return None
    
    def _extract_tool_name_from_text(self, text: str, available_tools: List[Dict[str, Any]]) -> Optional[str]:
        """Извлекает название инструмента из текста"""
        text_lower = text.lower()
        
        # Сопоставление ключевых слов с инструментами
        tool_keywords = {
            'create_issue': ['создай задачу', 'создать задачу', 'новая задача', 'создать issue'],
            'search_issues': ['найди задачи', 'поиск задач', 'найти issue', 'поиск issue'],
            'list_issues': ['покажи задачи', 'список задач', 'все задачи', 'показать issue'],
            'update_issue': ['обнови задачу', 'изменить задачу', 'обновить issue', 'изменить issue'],
            'create_project': ['создай проект', 'создать проект', 'новый проект'],
            'list_projects': ['покажи проекты', 'список проектов', 'все проекты'],
            'create_merge_request': ['создай merge request', 'создать merge request', 'новый merge request'],
            'list_commits': ['покажи коммиты', 'список коммитов', 'все коммиты', 'история коммитов']
        }
        
        for tool_name, keywords in tool_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                # Проверяем, есть ли такой инструмент в списке
                for tool in available_tools:
                    if tool['name'] == tool_name:
                        return tool_name
        
        return None
    
    async def _format_tool_result(self, tool_result: Dict[str, Any], original_response: Dict[str, Any]) -> str:
        """Форматирует результат выполнения инструмента с гибкой обработкой любых структур данных"""
        if 'error' in tool_result:
            return f"❌ Ошибка выполнения инструмента {original_response.get('tool', 'unknown')}: {tool_result['error']}"
        
        # Определяем тип инструмента для более контекстного форматирования
        tool_name = original_response.get('tool', 'unknown')
        server_name = original_response.get('server', 'unknown')
        
        # Форматируем результат в зависимости от структуры данных
        return await self._format_any_data(tool_result, tool_name, server_name)
    
    async def _format_any_data(self, data: Any, tool_name: str = "unknown", server_name: str = "unknown", indent: int = 0, _llm_top_level: bool = True) -> str:
        """
        Рекурсивно форматирует любые данные в красивый текст.
        В конце дополнительно вызывает LLM для улучшения читабельности результата.
        """
        indent_str = "  " * indent

        # Вложенная функция для рекурсивного обхода без LLM beautify на каждом уровне
        async def _format(data, tool_name, server_name, indent, _llm_top_level):
            indent_str = "  " * indent

            if data is None:
                result_text = f"{indent_str}📋 Результат: пусто"
            elif isinstance(data, bool):
                result_text = f"{indent_str}📋 Результат: {'✅ Да' if data else '❌ Нет'}"
            elif isinstance(data, (str, int, float)):
                result_text = f"{indent_str}📋 Результат: {data}"
            elif isinstance(data, list):
                if len(data) == 0:
                    result_text = f"{indent_str}📋 Результат: пустой список"
                else:
                    context_emoji = self._get_context_emoji(tool_name, server_name)
                    result_text = f"{indent_str}{context_emoji} Найдено {len(data)} элементов:\n"
                    max_items = 15
                    for i, item in enumerate(data[:max_items], 1):
                        if isinstance(item, dict):
                            key_fields_list = self._extract_key_fields(item, tool_name)
                            if key_fields_list:
                                # Если найдено несколько ключевых полей, выводим их через запятую
                                if isinstance(key_fields_list, (list, tuple)):
                                    key_fields_str = ", ".join(str(f) for f in key_fields_list if f)
                                else:
                                    key_fields_str = str(key_fields_list)
                                result_text += f"{indent_str}  {i}. {key_fields_str}\n"
                            else:
                                formatted = await _format(item, tool_name, server_name, indent + 2, False)
                                result_text += f"{indent_str}  {i}. {formatted}\n"
                        elif isinstance(item, (str, int, float)):
                            result_text += f"{indent_str}  {i}. {item}\n"
                        else:
                            formatted = await _format(item, tool_name, server_name, indent + 2, False)
                            result_text += f"{indent_str}  {i}. {formatted}\n"
                    if len(data) > max_items:
                        result_text += f"{indent_str}  ... и еще {len(data) - max_items} элементов\n"
            elif isinstance(data, dict):
                context_emoji = self._get_context_emoji(tool_name, server_name)
                result_text = f"{indent_str}{context_emoji} Результат:\n"
                sorted_keys = self._sort_dict_keys(data)
                for key in sorted_keys:
                    value = data[key]
                    formatted_key = self._format_key_name(key)
                    if isinstance(value, (str, int, float, bool)) or value is None:
                        formatted_value = self._format_simple_value(value)
                        result_text += f"{indent_str}  {formatted_key}: {formatted_value}\n"
                    elif isinstance(value, list):
                        if len(value) == 0:
                            result_text += f"{indent_str}  {formatted_key}: пустой список\n"
                        elif len(value) <= 3 and all(isinstance(item, (str, int, float)) for item in value):
                            formatted_values = [self._format_simple_value(item) for item in value]
                            result_text += f"{indent_str}  {formatted_key}: {', '.join(formatted_values)}\n"
                        else:
                            result_text += f"{indent_str}  {formatted_key}:\n"
                            formatted = await _format(value, tool_name, server_name, indent + 2, False)
                            result_text += formatted
                    elif isinstance(value, dict):
                        result_text += f"{indent_str}  {formatted_key}:\n"
                        formatted = await _format(value, tool_name, server_name, indent + 2, False)
                        result_text += formatted
                    else:
                        formatted = await _format(value, tool_name, server_name, indent + 2, False)
                        result_text += f"{indent_str}  {formatted_key}: {formatted}\n"
            else:
                result_text = f"{indent_str}📋 Результат: {str(data)}"
            return result_text

        # Только на самом верхнем уровне вызываем LLM beautify
        result_text = await _format(data, tool_name, server_name, indent, _llm_top_level)
        if _llm_top_level:
            try:
                from llm_providers.provider_factory import LLMProviderFactory
                llm = LLMProviderFactory.create_default_provider()
                prompt = (
                    "Ты — помощник, который форматирует данные для пользователя. "
                    "Твоя задача — преобразовать полученный ниже текст в структурированный, "
                    "красиво оформленный и легко читаемый ответ на русском языке.\n\n"
                    "Используй:\n"
                    "- **Заголовки** и подзаголовки\n"
                    "- **Маркированные** и нумерованные списки\n"
                    "- Эмодзи для акцентов\n"
                    "- Разделители (--- или ***)\n"
                    "- **Жирный шрифт** для важных моментов\n\n"
                    "Не добавляй пояснений о своей работе, не объясняй, что ты делаешь. "
                    "Просто выдай готовый, красиво оформленный результат для пользователя."
                )

                result_text = (
                    "Преобразуй следующий результат в красивый и читабельный вид.\n\n"
                    + str(result_text)
                )

                # Передаем результат напрямую, без лишних инструкций и без перевода
                beautified = await llm.generate_response([
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": str(result_text)}
                ], temperature = 0.7)

                # Если beautified содержит блок <think>...</think>, удаляем его
                import re
                beautified = re.sub(r'<think>.*?</think>', '', beautified, flags=re.DOTALL | re.IGNORECASE).strip()


                print(f"🔍 LLM beautify: {beautified}")
                if beautified and isinstance(beautified, str) and len(beautified) > 0:
                    return beautified
            except Exception as e:
                import logging
                logging.getLogger("llm_client").warning(f"LLM beautify failed: {e}")

        return result_text
    
    def _get_context_emoji(self, tool_name: str, server_name: str) -> str:
        """Возвращает подходящий emoji в зависимости от контекста"""
        tool_lower = tool_name.lower()
        server_lower = server_name.lower()
        
        if 'project' in tool_lower:
            return "📁"
        elif 'commit' in tool_lower:
            return "💾"
        elif 'issue' in tool_lower or 'task' in tool_lower:
            return "🎫"
        elif 'user' in tool_lower or 'search' in tool_lower:
            return "👤"
        elif 'page' in tool_lower or 'document' in tool_lower:
            return "📄"
        elif 'merge' in tool_lower or 'branch' in tool_lower:
            return "🌿"
        elif 'gitlab' in server_lower:
            return "🦊"
        elif 'jira' in server_lower:
            return "🎯"
        elif 'confluence' in server_lower or 'atlassian' in server_lower:
            return "📚"
        elif 'ldap' in server_lower:
            return "🔐"
        else:
            return "📋"
    
    def _extract_key_fields(self, item: dict, tool_name: str) -> str:
        """Извлекает ключевые поля из словаря в зависимости от типа инструмента"""
        tool_lower = tool_name.lower()
        
        # Приоритетные поля для разных типов инструментов
        priority_fields = {
            'project': ['name', 'id', 'description', 'web_url', 'path'],
            'commit': ['id', 'title', 'author_name', 'created_at', 'message'],
            'issue': ['key', 'summary', 'status', 'assignee', 'priority', 'type'],
            'user': ['display_name', 'email', 'title', 'phone', 'department'],
            'page': ['title', 'id', 'space', 'url', 'type'],
            'branch': ['name', 'commit', 'protected', 'default'],
            'search': ['name', 'email', 'username', 'displayName', 'department', 'title', 'cn'],
            'list': ['name', 'email', 'username', 'displayName', 'department', 'title', 'cn']
        }
        
        # Находим подходящие поля и собираем их все
        found_fields = []
        for key, fields in priority_fields.items():
            if key in tool_lower:
                for field in fields:
                    if field in item:
                        value = item[field]
                        if isinstance(value, str) and len(value) > 50:
                            value = value[:47] + "..."
                        found_fields.append(f"{field}: {value}")
                
                # Если нашли поля для этого типа инструмента, возвращаем их
                if found_fields:
                    # Ограничиваем количество полей для читаемости
                    if tool_lower in ['user', 'search', 'list']:
                        max_fields = 5  # Для пользователей показываем больше полей
                    elif tool_lower in ['issue', 'commit']:
                        max_fields = 4  # Для задач и коммитов
                    else:
                        max_fields = len(found_fields)  # Для остальных
                    return ", ".join(found_fields[:max_fields])
        
        # Если не нашли приоритетные поля, берем первые доступные
        for key, value in item.items():
            if isinstance(value, (str, int, float)) and value is not None:
                if isinstance(value, str) and len(value) > 50:
                    value = value[:47] + "..."
                return f"{key}: {value}"
        
        return str(item)
    
    def _sort_dict_keys(self, data: dict) -> list:
        """Сортирует ключи словаря для лучшей читаемости"""
        # Приоритетные ключи идут первыми
        priority_keys = ['id', 'name', 'title', 'key', 'status', 'description', 'url', 'web_url', 'created_at', 'updated_at']
        
        # Сначала добавляем приоритетные ключи, которые есть в данных
        sorted_keys = []
        for key in priority_keys:
            if key in data:
                sorted_keys.append(key)
        
        # Затем добавляем остальные ключи в алфавитном порядке
        other_keys = sorted([k for k in data.keys() if k not in priority_keys])
        sorted_keys.extend(other_keys)
        
        return sorted_keys
    
    def _format_key_name(self, key: str) -> str:
        """Форматирует название ключа для лучшей читаемости"""
        # Заменяем подчеркивания на пробелы и делаем первую букву заглавной
        formatted = key.replace('_', ' ').replace('-', ' ')
        return formatted.title()
    
    def _format_simple_value(self, value: Any) -> str:
        """Форматирует простые значения для вывода"""
        if value is None:
            return "не указано"
        elif isinstance(value, bool):
            return "✅ Да" if value else "❌ Нет"
        elif isinstance(value, str):
            # Обрезаем длинные строки
            if len(value) > 100:
                return value[:97] + "..."
            return value
        else:
            return str(value)
    
    def _get_fallback_response(self, message: str) -> str:
        """Возвращает fallback ответ когда LLM недоступен"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['jira', 'джира', 'задача', 'тикет']):
            return "Для работы с Jira используйте соответствующие команды через MCP сервер. LLM провайдер временно недоступен."
        elif any(word in message_lower for word in ['gitlab', 'гитлаб', 'git', 'репозиторий', 'коммит']):
            return "Для работы с GitLab используйте соответствующие команды через MCP сервер. LLM провайдер временно недоступен."
        elif any(word in message_lower for word in ['confluence', 'конфлюенс', 'страница', 'документ']):
            return "Для работы с Confluence используйте соответствующие команды через MCP сервер. LLM провайдер временно недоступен."
        elif any(word in message_lower for word in ['ldap', 'пользователь', 'ад', 'active directory']):
            return "Для поиска пользователей в LDAP используйте соответствующие команды через MCP сервер. LLM провайдер временно недоступен."
        else:
            return "Извините, LLM провайдер временно недоступен. Попробуйте использовать прямые команды для работы с MCP серверами."
    
    async def check_health(self) -> Dict[str, Any]:
        """Проверяет состояние LLM клиента"""
        if not self.llm_provider:
            return {
                'status': 'unhealthy',
                'provider': self.provider.value if self.provider else 'none',
                'error': 'Провайдер не инициализирован'
            }
        
        try:
            health = await self.llm_provider.check_health()
            return health
        except Exception as e:
            return {
                'status': 'unhealthy',
                'provider': self.provider.value,
                'error': str(e)
            }
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Возвращает информацию о текущем провайдере"""
        if not self.llm_provider:
            return {
                'provider': self.provider.value if self.provider else 'none',
                'status': 'not_initialized'
            }
        
        config = llm_config_manager.get_config(self.provider)
        return {
            'provider': self.provider.value,
            'model': config.model if config else 'unknown',
            'status': 'initialized'
        }