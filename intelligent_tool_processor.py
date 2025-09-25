"""
Интеллектуальный процессор инструментов для LLM
Реализует контекстно-зависимое извлечение параметров, автоматический подбор альтернативных инструментов
и связывание результатов разных инструментов.
"""

import json
import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ToolExecutionStatus(Enum):
    """Статусы выполнения инструмента"""
    SUCCESS = "success"
    MISSING_PARAMS = "missing_params"
    INVALID_PARAMS = "invalid_params"
    TOOL_ERROR = "tool_error"
    FALLBACK_NEEDED = "fallback_needed"

@dataclass
class ToolExecutionResult:
    """Результат выполнения инструмента"""
    status: ToolExecutionStatus
    result: Any = None
    error: str = None
    missing_params: List[str] = None
    suggested_fallback: str = None

@dataclass
class ContextParameter:
    """Параметр, извлеченный из контекста"""
    name: str
    value: Any
    source: str  # "current_message", "chat_history", "user_context"
    confidence: float  # 0.0 - 1.0

class IntelligentToolProcessor:
    """Интеллектуальный процессор инструментов"""
    
    def __init__(self, llm_client, mcp_client):
        self.llm_client = llm_client
        self.mcp_client = mcp_client
        self.max_fallback_attempts = 3
        self.max_tool_chains = 5
        
    async def process_with_intelligent_tools(self, tools_context: Dict[str, Any]) -> str:
        """
        Обрабатывает запрос с интеллектуальным использованием инструментов
        
        Args:
            tools_context: Контекст с инструментами и сообщением
            
        Returns:
            Результат обработки
        """
        try:
            available_tools = tools_context.get('available_tools', [])
            user_message = tools_context.get('user_message', '')
            user_context = tools_context.get('user_context', {})
            chat_history = tools_context.get('chat_history', [])
            
            logger.info(f"🧠 Начинаем интеллектуальную обработку: '{user_message[:50]}...'")
            
            # Шаг 1: Извлекаем параметры из контекста
            context_params = await self._extract_context_parameters(
                user_message, chat_history, user_context, available_tools
            )
            
            # Шаг 2: Определяем подходящий инструмент
            selected_tool = await self._select_best_tool(
                user_message, available_tools, context_params
            )
            
            if not selected_tool:
                return "Извините, не удалось найти подходящий инструмент для выполнения вашего запроса."
            
            # Шаг 3: Выполняем инструмент с интеллектуальным fallback
            result = await self._execute_tool_with_fallback(
                selected_tool, context_params, user_message, chat_history, user_context
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка интеллектуальной обработки: {e}")
            return f"Извините, произошла ошибка при обработке вашего запроса: {str(e)}"
    
    async def _extract_context_parameters(
        self, 
        user_message: str, 
        chat_history: List[Dict[str, Any]], 
        user_context: Dict[str, Any],
        available_tools: List[Dict[str, Any]]
    ) -> List[ContextParameter]:
        """
        Извлекает параметры из контекста предыдущих сообщений
        
        Args:
            user_message: Текущее сообщение пользователя
            chat_history: История чата
            user_context: Контекст пользователя
            available_tools: Доступные инструменты
            
        Returns:
            Список извлеченных параметров
        """
        context_params = []
        
        try:
            # Собираем весь текст для анализа
            full_context = user_message
            
            # Добавляем историю чата
            for msg in chat_history[-5:]:  # Берем последние 5 сообщений
                if msg.get('content'):
                    full_context += f" {msg['content']}"
            
            # Добавляем контекст пользователя
            if user_context.get('user_additional_context'):
                full_context += f" {user_context['user_additional_context']}"
            
            # Формируем системное сообщение с информацией об инструментах
            # Группируем инструменты по серверам
            from collections import defaultdict

            tools_by_server = defaultdict(list)
            for tool in available_tools:
                server = tool.get('server', 'Без сервера')
                tool_info = f"- {tool.get('name', '')} - {tool.get('description', '')} - Параметры: {tool.get('inputSchema', {}).get('properties', {}).get('required', [])}"
                tools_by_server[server].append(tool_info)

            grouped_tools_info = ""
            for server, tools in tools_by_server.items():
                grouped_tools_info += f"\n### {server} Tools\n"
                grouped_tools_info += "\n".join(tools) + "\n"

            system_message = f"""You are an AI assistant for system integrations. Your task: analyze user requests, select appropriate tools, and extract parameters.

INSTRUCTIONS:
1. Analyze the current request and chat history
2. Select the most suitable tool from the list below
3. Extract all relevant parameters
4. Respond ONLY in JSON format

AVAILABLE TOOLS:
{grouped_tools_info}

RESPONSE FORMAT:
{{
    "tool": "tool_name",
    "parameters": {{
        "param1": "value1",
        "param2": "value2"
    }},
    "reasoning": "brief explanation"
}}

CHAT HISTORY: {full_context}"""

            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ]
            
            response = await self.llm_client.llm_provider.generate_response(messages)
            
            # Парсим ответ с улучшенной обработкой для Llama 3.1:8b
            try:
                # Очищаем ответ от возможных лишних символов
                cleaned_response = response.strip()
                
                # Ищем JSON блок в ответе
                json_start = cleaned_response.find('{')
                json_end = cleaned_response.rfind('}') + 1
                
                if json_start != -1 and json_end > json_start:
                    json_str = cleaned_response[json_start:json_end]
                    extracted_data = json.loads(json_str)
                    
                    # Обрабатываем параметры
                    parameters = extracted_data.get('parameters', [])
                    if not parameters and 'tool' in extracted_data:
                        # Если параметры в другом формате
                        tool_params = extracted_data.get('parameters', {})
                        if isinstance(tool_params, dict):
                            for param_name, param_value in tool_params.items():
                                context_params.append(ContextParameter(
                                    name=param_name,
                                    value=str(param_value),
                                    source='llm_extraction',
                                    confidence=0.7
                                ))
                    else:
                        for param_data in parameters:
                            context_params.append(ContextParameter(
                                name=param_data.get('name', ''),
                                value=param_data.get('value', ''),
                                source=param_data.get('source', 'current_message'),
                                confidence=param_data.get('confidence', 0.5)
                            ))
                else:
                    logger.warning("⚠️ JSON не найден в ответе Llama")
                    
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ Не удалось распарсить извлеченные параметры: {e}")
                logger.debug(f"Ответ Llama: {response}")
            
            # Дополнительно извлекаем параметры с помощью регулярных выражений
            regex_params = self._extract_params_with_regex(full_context)
            context_params.extend(regex_params)
            
            logger.info(f"✅ Извлечено {len(context_params)} параметров из контекста")
            return context_params
            
        except Exception as e:
            logger.error(f"❌ Ошибка извлечения параметров: {e}")
            return []
    
    def _extract_params_with_regex(self, text: str) -> List[ContextParameter]:
        """Извлекает параметры с помощью регулярных выражений"""
        params = []
        
        # Паттерны для различных типов параметров (ищем в контексте, не в ключевых действиях)
        patterns = {
            'project_id': r'(?:проект|project)[\s:]*([A-Z][A-Z0-9-]+)',
            'task_id': r'(?:задача|task)[\s:]*([A-Z][A-Z0-9-]+)',
            'commit_hash': r'([a-f0-9]{7,40})',
            'file_path': r'(/[^\s]+\.\w+)',
            'username': r'(?:пользователь|user)[\s:]*([a-zA-Z0-9_-]+)',
            'keyword': r'(?:найди|поиск|search)[\s:]*([^\s]+)',
            'email': r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            'url': r'(https?://[^\s]+)',
            'version': r'v?(\d+\.\d+(?:\.\d+)?)',
            'number': r'\b(\d+)\b',
        }
        
        # Исключаем ключевые слова действий из поиска
        action_keywords = [
            'создай', 'найди', 'покажи', 'получи', 'обнови', 'удали', 'добавь',
            'create', 'find', 'show', 'get', 'update', 'delete', 'add',
            'поиск', 'список', 'детали', 'информация'
        ]
        
        for param_name, pattern in patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Проверяем, что найденное значение не является ключевым словом действия
                if not any(keyword.lower() in match.lower() for keyword in action_keywords):
                    params.append(ContextParameter(
                        name=param_name,
                        value=match,
                        source="regex_extraction",
                        confidence=0.8
                    ))
        
        return params
    
    async def _select_best_tool(
        self, 
        user_message: str, 
        available_tools: List[Dict[str, Any]], 
        context_params: List[ContextParameter]
    ) -> Optional[Dict[str, Any]]:
        """
        Выбирает наиболее подходящий инструмент для выполнения запроса
        
        Args:
            user_message: Сообщение пользователя
            available_tools: Доступные инструменты
            context_params: Извлеченные параметры
            
        Returns:
            Выбранный инструмент или None
        """
        try:
            # Формируем промпт для выбора инструмента
            tools_info = []
            for tool in available_tools:
                tool_info = {
                    'name': tool.get('name', ''),
                    'description': tool.get('description', ''),
                    'server': tool.get('server', ''),
                    'required_params': tool.get('inputSchema', {}).get('properties', {}).get('required', [])
                }
                tools_info.append(tool_info)
            
            # Группируем инструменты по серверам для лучшего понимания Llama
            from collections import defaultdict
            tools_by_server = defaultdict(list)
            for tool in available_tools:
                server = tool.get('server', 'No Server')
                tool_info = f"- {tool.get('name', '')}: {tool.get('description', '')} (Params: {tool.get('inputSchema', {}).get('properties', {}).get('required', [])})"
                tools_by_server[server].append(tool_info)

            grouped_tools_info = ""
            for server, tools in tools_by_server.items():
                grouped_tools_info += f"\n{server}:\n"
                grouped_tools_info += "\n".join(tools) + "\n"

            # Формируем системное сообщение с информацией об инструментах
            system_message = f"""You are a tool selection expert. Choose the most suitable tool for the user's request.

AVAILABLE TOOLS:
{grouped_tools_info}

TASK: Select the best tool based on:
1. Tool description matches user request
2. Required parameters are available
3. Request context and logic

RESPOND ONLY IN JSON FORMAT."""

            # Пользовательское сообщение с запросом и параметрами
            user_prompt = f"""Select the most suitable tool for this user request.

USER REQUEST: {user_message}

EXTRACTED PARAMETERS:
{json.dumps([{'name': p.name, 'value': p.value, 'confidence': p.confidence} for p in context_params], ensure_ascii=False, indent=2)}

RESPONSE FORMAT:
{{
    "selected_tool": "tool_name",
    "reason": "selection_reason",
    "confidence": 0.9
}}"""
            
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_prompt}
            ]
            
            response = await self.llm_client.llm_provider.generate_response(messages)
            
            # Парсим ответ с улучшенной обработкой для Llama 3.1:8b
            try:
                # Очищаем ответ от возможных лишних символов
                cleaned_response = response.strip()
                
                # Ищем JSON блок в ответе
                json_start = cleaned_response.find('{')
                json_end = cleaned_response.rfind('}') + 1
                
                if json_start != -1 and json_end > json_start:
                    json_str = cleaned_response[json_start:json_end]
                    selection_data = json.loads(json_str)
                    
                    selected_tool_name = selection_data.get('selected_tool', '')
                    
                    # Находим выбранный инструмент
                    for tool in available_tools:
                        if tool.get('name') == selected_tool_name:
                            logger.info(f"✅ Выбран инструмент: {selected_tool_name}")
                            return tool
                    
                    logger.warning(f"⚠️ Выбранный инструмент {selected_tool_name} не найден")
                    return None
                else:
                    logger.warning("⚠️ JSON не найден в ответе Llama при выборе инструмента")
                    return None
                
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ Не удалось распарсить выбор инструмента: {e}")
                logger.debug(f"Ответ Llama: {response}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Ошибка выбора инструмента: {e}")
            return None
    
    async def _execute_tool_with_fallback(
        self,
        tool: Dict[str, Any],
        context_params: List[ContextParameter],
        user_message: str,
        chat_history: List[Dict[str, Any]],
        user_context: Dict[str, Any]
    ) -> str:
        """
        Выполняет инструмент с интеллектуальным fallback
        
        Args:
            tool: Выбранный инструмент
            context_params: Извлеченные параметры
            user_message: Сообщение пользователя
            chat_history: История чата
            user_context: Контекст пользователя
            
        Returns:
            Результат выполнения
        """
        try:
            # Шаг 1: Подготавливаем параметры для инструмента
            tool_params = await self._prepare_tool_parameters(tool, context_params, user_message)
            
            # Шаг 2: Пытаемся выполнить инструмент
            execution_result = await self._execute_tool(tool, tool_params)
            
            # Шаг 3: Если инструмент выполнен успешно, возвращаем результат
            if execution_result.status == ToolExecutionStatus.SUCCESS:
                return await self._format_tool_result(execution_result.result, tool)
            
            # Шаг 4: Если нужен fallback, пытаемся найти альтернативный инструмент
            if execution_result.status == ToolExecutionStatus.FALLBACK_NEEDED:
                return await self._handle_tool_fallback(
                    tool, execution_result, context_params, user_message, chat_history, user_context
                )
            
            # Шаг 5: Если не хватает параметров, пытаемся их получить
            if execution_result.status == ToolExecutionStatus.MISSING_PARAMS:
                return await self._handle_missing_parameters(
                    tool, execution_result, context_params, user_message, chat_history, user_context
                )
            
            # Шаг 6: Возвращаем ошибку
            return f"Ошибка выполнения инструмента: {execution_result.error}"
            
        except Exception as e:
            logger.error(f"❌ Ошибка выполнения инструмента с fallback: {e}")
            return f"Извините, произошла ошибка при выполнении инструмента: {str(e)}"
    
    async def _prepare_tool_parameters(
        self, 
        tool: Dict[str, Any], 
        context_params: List[ContextParameter], 
        user_message: str
    ) -> Dict[str, Any]:
        """
        Подготавливает параметры для инструмента на основе контекста
        
        Args:
            tool: Инструмент
            context_params: Извлеченные параметры
            user_message: Сообщение пользователя
            
        Returns:
            Подготовленные параметры
        """
        tool_params = {}
        required_params = tool.get('inputSchema', {}).get('properties', {}).get('required', [])
        
        # Маппинг параметров из контекста
        param_mapping = {
            'project_id': ['project', 'project_id', 'project_key'],
            'task_id': ['task', 'task_id', 'issue', 'issue_id'],
            'username': ['user', 'username', 'assignee'],
            'keyword': ['query', 'search', 'keyword'],
            'file_path': ['path', 'file_path', 'file'],
            'commit_hash': ['commit', 'hash', 'commit_id']
        }
        
        # Заполняем параметры из контекста
        for param_name in required_params:
            best_param = None
            best_confidence = 0.0
            
            # Ищем подходящий параметр в контексте
            for context_param in context_params:
                if context_param.name in param_mapping.get(param_name, [param_name]):
                    if context_param.confidence > best_confidence:
                        best_param = context_param
                        best_confidence = context_param.confidence
            
            if best_param and best_confidence > 0.5:
                tool_params[param_name] = best_param.value
            else:
                # Если параметр не найден, пытаемся извлечь из сообщения
                extracted_value = await self._extract_param_from_message(param_name, user_message)
                if extracted_value:
                    tool_params[param_name] = extracted_value
        
        logger.info(f"✅ Подготовлены параметры для {tool.get('name')}: {tool_params}")
        return tool_params
    
    async def _extract_param_from_message(self, param_name: str, message: str) -> Optional[str]:
        """Извлекает параметр из сообщения пользователя"""
        # Исключаем ключевые слова действий из поиска
        action_keywords = [
            'создай', 'найди', 'покажи', 'получи', 'обнови', 'удали', 'добавь',
            'create', 'find', 'show', 'get', 'update', 'delete', 'add',
            'поиск', 'список', 'детали', 'информация'
        ]
        
        # Простая логика извлечения параметров
        if param_name in ['project_id', 'project']:
            match = re.search(r'проект[:\s]+([A-Z][A-Z0-9-]+)', message, re.IGNORECASE)
            if match and not any(keyword.lower() in match.group(1).lower() for keyword in action_keywords):
                return match.group(1)
        
        if param_name in ['task_id', 'task', 'issue']:
            match = re.search(r'(?:задача|task|issue)[:\s]+([A-Z][A-Z0-9-]+)', message, re.IGNORECASE)
            if match and not any(keyword.lower() in match.group(1).lower() for keyword in action_keywords):
                return match.group(1)
        
        if param_name in ['username', 'user']:
            match = re.search(r'(?:пользователь|user)[:\s]+([a-zA-Z0-9_-]+)', message, re.IGNORECASE)
            if match and not any(keyword.lower() in match.group(1).lower() for keyword in action_keywords):
                return match.group(1)
        
        if param_name in ['keyword', 'query', 'search']:
            # Ищем ключевые слова после действия поиска
            match = re.search(r'(?:найди|поиск|search)[:\s]+([^\s]+)', message, re.IGNORECASE)
            if match and not any(keyword.lower() in match.group(1).lower() for keyword in action_keywords):
                return match.group(1)
        
        if param_name in ['file_path', 'path', 'file']:
            match = re.search(r'(?:файл|file)[:\s]+([^\s]+)', message, re.IGNORECASE)
            if match and not any(keyword.lower() in match.group(1).lower() for keyword in action_keywords):
                return match.group(1)
        
        return None
    
    async def _execute_tool(self, tool: Dict[str, Any], params: Dict[str, Any]) -> ToolExecutionResult:
        """
        Выполняет инструмент и возвращает результат
        
        Args:
            tool: Инструмент
            params: Параметры
            
        Returns:
            Результат выполнения
        """
        try:
            server_name = tool.get('server', 'unknown')
            tool_name = tool.get('name', '')
            
            # Проверяем наличие обязательных параметров
            required_params = tool.get('inputSchema', {}).get('properties', {}).get('required', [])
            missing_params = [param for param in required_params if param not in params]
            
            if missing_params:
                return ToolExecutionResult(
                    status=ToolExecutionStatus.MISSING_PARAMS,
                    missing_params=missing_params
                )
            
            # Выполняем инструмент
            result = await self.mcp_client.call_tool(server_name, tool_name, params)
            
            if 'error' in result:
                # Если внешние серверы недоступны, пробуем встроенные
                if 'не подключен' in result['error']:
                    result = await self.mcp_client.call_tool_builtin(server_name, tool_name, params)
                
                if 'error' in result:
                    return ToolExecutionResult(
                        status=ToolExecutionStatus.TOOL_ERROR,
                        error=result['error']
                    )
            
            return ToolExecutionResult(
                status=ToolExecutionStatus.SUCCESS,
                result=result
            )
            
        except Exception as e:
            return ToolExecutionResult(
                status=ToolExecutionStatus.TOOL_ERROR,
                error=str(e)
            )
    
    async def _handle_tool_fallback(
        self,
        original_tool: Dict[str, Any],
        execution_result: ToolExecutionResult,
        context_params: List[ContextParameter],
        user_message: str,
        chat_history: List[Dict[str, Any]],
        user_context: Dict[str, Any]
    ) -> str:
        """
        Обрабатывает fallback на альтернативные инструменты
        
        Args:
            original_tool: Оригинальный инструмент
            execution_result: Результат выполнения
            context_params: Параметры контекста
            user_message: Сообщение пользователя
            chat_history: История чата
            user_context: Контекст пользователя
            
        Returns:
            Результат обработки
        """
        try:
            # Получаем все доступные инструменты
            available_tools = await self.mcp_client.get_all_tools()
            
            # Исключаем оригинальный инструмент
            fallback_tools = [tool for tool in available_tools if tool.get('name') != original_tool.get('name')]
            
            if not fallback_tools:
                return "Извините, не удалось найти альтернативные инструменты для выполнения вашего запроса."
            
            # Выбираем лучший fallback инструмент
            fallback_tool = await self._select_best_tool(user_message, fallback_tools, context_params)
            
            if not fallback_tool:
                return "Извините, не удалось найти подходящий альтернативный инструмент."
            
            logger.info(f"🔄 Используем fallback инструмент: {fallback_tool.get('name')}")
            
            # Выполняем fallback инструмент
            tool_params = await self._prepare_tool_parameters(fallback_tool, context_params, user_message)
            execution_result = await self._execute_tool(fallback_tool, tool_params)
            
            if execution_result.status == ToolExecutionStatus.SUCCESS:
                return await self._format_tool_result(execution_result.result, fallback_tool)
            else:
                return f"Fallback инструмент также не удалось выполнить: {execution_result.error}"
                
        except Exception as e:
            logger.error(f"❌ Ошибка fallback: {e}")
            return f"Извините, произошла ошибка при использовании альтернативного инструмента: {str(e)}"
    
    async def _handle_missing_parameters(
        self,
        tool: Dict[str, Any],
        execution_result: ToolExecutionResult,
        context_params: List[ContextParameter],
        user_message: str,
        chat_history: List[Dict[str, Any]],
        user_context: Dict[str, Any]
    ) -> str:
        """
        Обрабатывает отсутствующие параметры
        
        Args:
            tool: Инструмент
            execution_result: Результат выполнения
            context_params: Параметры контекста
            user_message: Сообщение пользователя
            chat_history: История чата
            user_context: Контекст пользователя
            
        Returns:
            Результат обработки
        """
        try:
            missing_params = execution_result.missing_params
            
            # Пытаемся получить недостающие параметры через другие инструменты
            for param in missing_params:
                param_value = await self._get_parameter_via_tools(param, user_message, chat_history, user_context)
                if param_value:
                    # Добавляем параметр в контекст и пытаемся выполнить инструмент снова
                    context_params.append(ContextParameter(
                        name=param,
                        value=param_value,
                        source="tool_extraction",
                        confidence=0.9
                    ))
            
            # Пытаемся выполнить инструмент снова с новыми параметрами
            tool_params = await self._prepare_tool_parameters(tool, context_params, user_message)
            execution_result = await self._execute_tool(tool, tool_params)
            
            if execution_result.status == ToolExecutionStatus.SUCCESS:
                return await self._format_tool_result(execution_result.result, tool)
            else:
                return f"Не удалось получить необходимые параметры: {', '.join(missing_params)}"
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки отсутствующих параметров: {e}")
            return f"Извините, произошла ошибка при получении параметров: {str(e)}"
    
    async def _get_parameter_via_tools(
        self, 
        param_name: str, 
        user_message: str, 
        chat_history: List[Dict[str, Any]], 
        user_context: Dict[str, Any]
    ) -> Optional[str]:
        """
        Получает параметр через другие инструменты
        
        Args:
            param_name: Название параметра
            user_message: Сообщение пользователя
            chat_history: История чата
            user_context: Контекст пользователя
            
        Returns:
            Значение параметра или None
        """
        try:
            # Логика получения параметров через другие инструменты
            if param_name in ['project_id', 'project']:
                # Пытаемся найти проекты через GitLab или Jira
                search_tools = await self.mcp_client.get_all_tools()
                for tool in search_tools:
                    if 'search' in tool.get('name', '').lower() or 'find' in tool.get('name', '').lower():
                        # Извлекаем ключевые слова из сообщения
                        keywords = re.findall(r'\b\w+\b', user_message)
                        if keywords:
                            # Пытаемся выполнить поиск
                            try:
                                result = await self.mcp_client.call_tool(
                                    tool.get('server', ''),
                                    tool.get('name', ''),
                                    {'query': ' '.join(keywords[:3])}  # Берем первые 3 слова
                                )
                                if 'error' not in result and result.get('data'):
                                    # Извлекаем первый найденный проект
                                    projects = result.get('data', [])
                                    if projects and len(projects) > 0:
                                        return projects[0].get('key') or projects[0].get('name')
                            except Exception:
                                continue
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения параметра {param_name}: {e}")
            return None
    
    async def _format_tool_result(self, result: Any, tool: Dict[str, Any]) -> str:
        """
        Форматирует результат выполнения инструмента
        
        Args:
            result: Результат инструмента
            tool: Инструмент
            
        Returns:
            Отформатированный результат
        """
        try:
            if isinstance(result, dict):
                if 'error' in result:
                    return f"Ошибка выполнения инструмента {tool.get('name', '')}: {result['error']}"
                
                if 'data' in result:
                    data = result['data']
                    if isinstance(data, list):
                        if len(data) == 0:
                            return f"По запросу '{tool.get('name', '')}' ничего не найдено."
                        
                        # Форматируем список результатов
                        formatted_items = []
                        for item in data[:5]:  # Показываем первые 5 элементов
                            if isinstance(item, dict):
                                # Форматируем объект
                                item_str = []
                                for key, value in item.items():
                                    if key in ['title', 'name', 'summary', 'subject']:
                                        item_str.append(f"**{value}**")
                                    elif key in ['id', 'key', 'number']:
                                        item_str.append(f"ID: {value}")
                                    elif key in ['status', 'state']:
                                        item_str.append(f"Статус: {value}")
                                    elif key in ['assignee', 'author']:
                                        item_str.append(f"Исполнитель: {value}")
                                
                                if item_str:
                                    formatted_items.append(" • ".join(item_str))
                                else:
                                    formatted_items.append(str(item))
                            else:
                                formatted_items.append(str(item))
                        
                        result_text = "\n".join(formatted_items)
                        if len(data) > 5:
                            result_text += f"\n\n... и еще {len(data) - 5} элементов"
                        
                        return result_text
                    else:
                        return str(data)
                else:
                    return str(result)
            else:
                return str(result)
                
        except Exception as e:
            logger.error(f"❌ Ошибка форматирования результата: {e}")
            return f"Результат выполнения инструмента {tool.get('name', '')}: {str(result)}"
