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
            
            # Шаг 1: Извлекаем параметры из контекста и получаем инструменты, найденные LLM
            context_params, llm_found_tools = await self._extract_context_parameters(
                user_message, chat_history, user_context, available_tools
            )
            
            # Шаг 2: Определяем подходящий инструмент
            # Если LLM нашел инструменты, выбираем лучший из них
            if llm_found_tools:
                logger.info(f"🎯 LLM предложил {len(llm_found_tools)} инструментов, выбираем лучший")
                selected_tool = await self._select_best_tool_from_candidates(
                    user_message, llm_found_tools, context_params
                )
            else:
                # Если LLM не нашел инструменты, используем старую логику
                logger.info("🔍 LLM не нашел инструменты, используем общий поиск")
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
    ) -> Tuple[List[ContextParameter], List[Dict[str, Any]]]:
        """
        Извлекает параметры из контекста (приоритет последнему сообщению)
        
        Args:
            user_message: Текущее сообщение пользователя
            chat_history: История чата (ограничено последними 2 сообщениями)
            user_context: Контекст пользователя
            available_tools: Доступные инструменты
            
        Returns:
            Кортеж: (список извлеченных параметров, список найденных инструментов)
        """
        context_params = []
        
        try:
            # Ограничиваем контекст чата до последних 2 сообщений
            recent_history = chat_history[-2:] if chat_history else []
            
            # Собираем контекст с приоритетом последнему сообщению
            context_parts = [user_message]  # Приоритет текущему сообщению
            
            # Добавляем последние 2 сообщения из истории
            for msg in recent_history:
                if msg.get('content'):
                    context_parts.append(msg['content'])
            
            # Добавляем контекст пользователя (если есть)
            if user_context.get('user_additional_context'):
                context_parts.append(user_context['user_additional_context'])
            
            full_context = " ".join(context_parts)
            
            # Формируем системное сообщение с информацией об инструментах
            # Группируем инструменты по серверам с улучшенным форматом для Gemma3:12b
            from collections import defaultdict

            tools_by_server = defaultdict(list)
            for tool in available_tools:
                server = tool.get('server', 'Без сервера')
                tool_name = tool.get('name', '')
                tool_description = tool.get('description', '')
                # Получаем все параметры, а не только обязательные
                all_params = list(tool.get('inputSchema', {}).get('properties', {}).keys())
                
                # Формируем список параметров в читаемом виде
                params_list = ', '.join(all_params) if all_params else 'нет параметров'
                
                tool_info = f"- {tool_name}\n  - описание: {tool_description}\n  - параметры: {params_list}"
                tools_by_server[server].append(tool_info)

            grouped_tools_info = ""
            for server, tools in tools_by_server.items():
                #grouped_tools_info += f"\n### {server} Tools\n"
                grouped_tools_info += "\n".join(tools) + "\n"

            system_message = f"""Ты - системный парсер параметров. Твоя единственная задача - точно извлечь ВСЕ параметры из запроса пользователя для КАЖДОГО упомянутого инструмента и представить их в строго заданном формате.

ЖЕСТКИЕ ПРАВИЛА:
1. ИСПОЛЬЗУЙ ТОЧНЫЕ НАЗВАНИЯ ИНСТРУМЕНТОВ, как в примере ниже. НЕ изменяй и не творчески переименовывай инструменты.
2. ИЗВЛЕКИ ВСЕ параметры (как обязательные, так и опциональные), даже если они неявно упомянуты в запросе.
3. ДЛЯ КАЖДОГО инструмента продублируй параметры под именем, которое ОЖИДАЕТ этот конкретный инструмент.
4. Если параметр для инструмента не указан явно, попробуй вывести его из контекста или укажи `null`.
5. Формат вывода ТОЛЬКО JSON, как в примере.
6. ВАЖНО: Извлекай ВСЕ параметры из списка, не только обязательные!

СПИСОК ИНСТРУМЕНТОВ И ИХ ВСЕХ ПАРАМЕТРОВ:
{grouped_tools_info}

ФОРМАТ ОТВЕТА:
{{
    "parameters": {{
        "имя_параметра": "найденное_значение"
    }},
    "found_tools": ["название_инструмента_1", "название_инструмента_2"]
}}"""

            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ]
            
            response = await self.llm_client.llm_provider.generate_response(messages)
            
            # Парсим ответ с улучшенной обработкой для Gemma3:12b
            try:
                # Очищаем ответ от возможных лишних символов
                cleaned_response = response.strip()
                
                # Ищем JSON блок в ответе
                json_start = cleaned_response.find('{')
                json_end = cleaned_response.rfind('}') + 1
                
                if json_start != -1 and json_end > json_start:
                    json_str = cleaned_response[json_start:json_end]
                    extracted_data = json.loads(json_str)
                    
                    # Обрабатываем параметры из нового формата
                    parameters = extracted_data.get('parameters', {})
                    found_tools = extracted_data.get('found_tools', [])
                    
                    logger.info(f"🔍 Найденные параметры: {list(parameters.keys()) if isinstance(parameters, dict) else parameters}")
                    logger.info(f"🛠️ Подходящие инструменты: {found_tools}")

                    # Получаем ВСЕ параметры из всех инструментов (не только обязательные)
                    all_valid_params = set()
                    tool_all_param_map = {}
                    tool_required_param_map = {}
                    
                    for tool in available_tools:
                        tool_name = tool.get('name', '')
                        input_schema = tool.get('inputSchema', {})
                        properties = input_schema.get('properties', {})
                        required_params = input_schema.get('required', [])
                        
                        # Собираем ВСЕ параметры инструмента
                        all_tool_params = set(properties.keys())
                        all_valid_params.update(all_tool_params)
                        tool_all_param_map[tool_name] = all_tool_params
                        tool_required_param_map[tool_name] = set(required_params)

                    # Проверяем вложенность структуры параметров
                    if isinstance(parameters, dict):
                        # Если структура: {param: value, ...} (старый формат)
                        # или структура: {tool_name: {param: value, ...}, ...} (новый вложенный формат)
                        is_nested = False
                        # Проверяем, если ключи parameters совпадают с именами инструментов
                        if all(isinstance(k, str) and k in tool_required_param_map for k in parameters.keys()):
                            # Проверяем, что значения - dict (т.е. вложенная структура)
                            if all(isinstance(v, dict) for v in parameters.values()):
                                is_nested = True

                        if is_nested:
                            # Новый вложенный формат: {tool_name: {param: value, ...}, ...}
                            for tool_name, param_dict in parameters.items():
                                all_tool_params = tool_all_param_map.get(tool_name, set())
                                required_params = tool_required_param_map.get(tool_name, set())
                                
                                for param_name, param_value in param_dict.items():
                                    if param_name in all_tool_params:
                                        # Определяем приоритет: обязательные параметры получают более высокий confidence
                                        confidence = 0.95 if param_name in required_params else 0.85
                                        
                                        context_params.append(ContextParameter(
                                            name=param_name,
                                            value=str(param_value),
                                            source='llm_extraction',
                                            confidence=confidence
                                        ))
                                        param_type = "обязательный" if param_name in required_params else "опциональный"
                                        logger.info(f"✅ [{tool_name}] {param_type} параметр '{param_name}' = '{param_value}' добавлен")
                                    else:
                                        logger.warning(f"⚠️ [{tool_name}] LLM выдумал параметр '{param_name}' - не найден в инструменте")
                        else:
                            # Старый формат: {param: value, ...}
                            for param_name, param_value in parameters.items():
                                if param_name in all_valid_params:
                                    # Определяем, к какому инструменту принадлежит параметр
                                    param_tools = [tool for tool, params in tool_all_param_map.items() if param_name in params]
                                    is_required = any(param_name in tool_required_param_map.get(tool, set()) for tool in param_tools)
                                    
                                    # Определяем confidence на основе того, обязательный ли параметр
                                    confidence = 0.95 if is_required else 0.85
                                    
                                    context_params.append(ContextParameter(
                                        name=param_name,
                                        value=str(param_value),
                                        source='llm_extraction',
                                        confidence=confidence
                                    ))
                                    param_type = "обязательный" if is_required else "опциональный"
                                    tools_str = ", ".join(param_tools) if param_tools else "неизвестный инструмент"
                                    logger.info(f"✅ {param_type} параметр '{param_name}' = '{param_value}' добавлен (инструменты: {tools_str})")
                                else:
                                    logger.warning(f"⚠️ LLM выдумал параметр '{param_name}' - не найден в инструментах")
                    else:
                        logger.warning("⚠️ Неожиданный формат parameters: %s", type(parameters))
                else:
                    logger.warning("⚠️ JSON не найден в ответе Gemma3:12b")
                    
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ Не удалось распарсить извлеченные параметры от Gemma3:12b: {e}")
                logger.debug(f"Ответ Gemma3:12b: {response}")
                
                # Попытка извлечь параметры из текстового ответа
                if 'tool' in response.lower() or 'parameter' in response.lower():
                    # Простое извлечение параметров из текста
                    lines = response.split('\n')
                    for line in lines:
                        if ':' in line and any(keyword in line.lower() for keyword in ['project', 'task', 'user', 'file', 'search']):
                            parts = line.split(':', 1)
                            if len(parts) == 2:
                                param_name = parts[0].strip().lower().replace(' ', '_')
                                param_value = parts[1].strip()
                                if param_value and len(param_value) > 1:
                                    context_params.append(ContextParameter(
                                        name=param_name,
                                        value=param_value,
                                        source='text_extraction',
                                        confidence=0.6
                                    ))
            
            # Дополнительно извлекаем параметры с помощью регулярных выражений
            #regex_params = self._extract_params_with_regex(full_context)
            #context_params.extend(regex_params)
            
            # Дополнительная логика: если найдены инструменты, но не все их параметры извлечены,
            # попробуем извлечь недостающие параметры из контекста
            if found_tools and isinstance(parameters, dict):
                self._extract_missing_optional_params(
                    found_tools, parameters, tool_all_param_map, tool_required_param_map, 
                    full_context, context_params
                )
            
            logger.info(f"✅ Извлечено {len(context_params)} параметров из контекста")
            
            # Находим инструменты, которые были найдены LLM
            found_tools_objects = []
            if found_tools:
                for tool_name in found_tools:
                    for tool in available_tools:
                        if tool.get('name') == tool_name:
                            found_tools_objects.append(tool)
                            break
                
                logger.info(f"🛠️ LLM нашел инструменты: {[t.get('name') for t in found_tools_objects]}")
            
            return context_params, found_tools_objects
            
        except Exception as e:
            logger.error(f"❌ Ошибка извлечения параметров: {e}")
            return [], []
            
    def _extract_missing_optional_params(
        self, 
        found_tools: List[str], 
        extracted_params: Dict[str, Any], 
        tool_all_param_map: Dict[str, set],
        tool_required_param_map: Dict[str, set],
        context: str,
        context_params: List[ContextParameter]
    ):
        """
        Извлекает недостающие опциональные параметры из контекста
        
        Args:
            found_tools: Список найденных инструментов
            extracted_params: Уже извлеченные параметры
            tool_all_param_map: Карта всех параметров по инструментам
            tool_required_param_map: Карта обязательных параметров по инструментам
            context: Контекст для поиска
            context_params: Список параметров для дополнения
        """
        try:
            # Получаем уже извлеченные имена параметров
            extracted_param_names = set()
            for param in context_params:
                extracted_param_names.add(param.name)
            
            # Для каждого найденного инструмента проверяем недостающие параметры
            for tool_name in found_tools:
                all_tool_params = tool_all_param_map.get(tool_name, set())
                required_params = tool_required_param_map.get(tool_name, set())
                
                # Находим недостающие опциональные параметры
                missing_optional = all_tool_params - extracted_param_names - required_params
                
                if missing_optional:
                    logger.info(f"🔍 [{tool_name}] Ищем недостающие опциональные параметры: {missing_optional}")
                    
                    # Пытаемся извлечь недостающие параметры из контекста
                    for param_name in missing_optional:
                        # Простой поиск по ключевым словам в контексте
                        param_value = self._extract_param_from_context(param_name, context)
                        if param_value:
                            context_params.append(ContextParameter(
                                name=param_name,
                                value=param_value,
                                source='context_inference',
                                confidence=0.7
                            ))
                            logger.info(f"✅ [{tool_name}] Опциональный параметр '{param_name}' = '{param_value}' извлечен из контекста")
                        
        except Exception as e:
            logger.error(f"❌ Ошибка извлечения недостающих параметров: {e}")
    
    def _extract_param_from_context(self, param_name: str, context: str) -> Optional[str]:
        """
        Извлекает значение параметра из контекста на основе его имени
        
        Args:
            param_name: Имя параметра
            context: Контекст для поиска
            
        Returns:
            Найденное значение или None
        """
        try:
            context_lower = context.lower()
            param_lower = param_name.lower()
            
            # Простые правила извлечения на основе имени параметра
            if 'query' in param_lower or 'search' in param_lower:
                # Для параметров поиска ищем ключевые слова
                words = context.split()
                if len(words) > 2:
                    # Берем несколько слов как поисковый запрос
                    return ' '.join(words[:3])
                    
            elif 'limit' in param_lower or 'count' in param_lower:
                # Для лимитов ищем числа
                import re
                numbers = re.findall(r'\b\d+\b', context)
                if numbers:
                    return numbers[0]
                    
            elif 'sort' in param_lower or 'order' in param_lower:
                # Для сортировки ищем ключевые слова
                if 'asc' in context_lower or 'возраста' in context_lower:
                    return 'asc'
                elif 'desc' in context_lower or 'убыва' in context_lower:
                    return 'desc'
                    
            elif 'filter' in param_lower:
                # Для фильтров пытаемся найти условия
                if 'active' in context_lower or 'актив' in context_lower:
                    return 'active'
                elif 'inactive' in context_lower or 'неактив' in context_lower:
                    return 'inactive'
                    
            return None
            
        except Exception as e:
            logger.debug(f"Ошибка извлечения параметра {param_name}: {e}")
            return None
    
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
        Выбирает наиболее подходящий инструмент на основе параметров и описания
        
        Args:
            user_message: Сообщение пользователя
            available_tools: Доступные инструменты
            context_params: Извлеченные параметры
            
        Returns:
            Выбранный инструмент или None
        """
        try:
            # Сначала попробуем найти инструмент по параметрам
            selected_tool = self._select_tool_by_parameters(available_tools, context_params, user_message)
            if selected_tool:
                logger.info(f"✅ Инструмент выбран по параметрам: {selected_tool.get('name')}")
                return selected_tool
            
            # Если не найден по параметрам, используем LLM для выбора
            return await self._select_tool_with_llm(user_message, available_tools, context_params)
            
        except Exception as e:
            logger.error(f"❌ Ошибка выбора инструмента: {e}")
            return None
            
    async def _select_best_tool_from_candidates(
        self, 
        user_message: str, 
        candidate_tools: List[Dict[str, Any]], 
        context_params: List[ContextParameter]
    ) -> Optional[Dict[str, Any]]:
        """
        Выбирает лучший инструмент из кандидатов, предложенных LLM
        
        Args:
            user_message: Сообщение пользователя
            candidate_tools: Инструменты, предложенные LLM
            context_params: Извлеченные параметры
            
        Returns:
            Выбранный инструмент или None
        """
        try:
            if not candidate_tools:
                return None
            
            # Если только один инструмент, возвращаем его
            if len(candidate_tools) == 1:
                logger.info(f"✅ Выбран единственный инструмент от LLM: {candidate_tools[0].get('name')}")
                return candidate_tools[0]
            
            # Если несколько инструментов, выбираем лучший по параметрам
            logger.info(f"🔍 Выбираем лучший из {len(candidate_tools)} инструментов от LLM")
            
            best_tool = self._select_tool_by_parameters(candidate_tools, context_params, user_message)
            if best_tool:
                logger.info(f"✅ Выбран лучший инструмент от LLM: {best_tool.get('name')}")
                return best_tool
            
            # Если не удалось выбрать по параметрам, используем LLM для выбора из кандидатов
            logger.info("🤖 Используем LLM для выбора из кандидатов")
            return await self._select_tool_with_llm_from_candidates(user_message, candidate_tools, context_params)
            
        except Exception as e:
            logger.error(f"❌ Ошибка выбора инструмента из кандидатов: {e}")
            return None
    
    async def _select_tool_with_llm_from_candidates(
        self, 
        user_message: str, 
        candidate_tools: List[Dict[str, Any]], 
        context_params: List[ContextParameter]
    ) -> Optional[Dict[str, Any]]:
        """
        Использует LLM для выбора инструмента из кандидатов
        """
        try:
            # Формируем информацию об инструментах-кандидатах
            tools_info = []
            for tool in candidate_tools:
                tool_name = tool.get('name', '')
                tool_description = tool.get('description', '')
                input_schema = tool.get('inputSchema', {})
                all_params = list(input_schema.get('properties', {}).keys())
                required_params = input_schema.get('required', [])
                
                params_info = f"всего: {len(all_params)}, обязательных: {len(required_params)}"
                tools_info.append(f"- {tool_name}: {tool_description} (параметры: {params_info})")
            
            tools_text = "\n".join(tools_info)
            
            # Формируем параметры для отображения
            params_text = ""
            if context_params:
                params_list = [f"{p.name}={p.value}" for p in context_params]
                params_text = f"Найденные параметры: {', '.join(params_list)}"
            
            system_message = f"""Ты - эксперт по выбору инструментов. Из предложенных кандидатов выбери лучший инструмент для задачи пользователя.

КАНДИДАТЫ (инструменты, которые LLM уже выбрал как подходящие):
{tools_text}

{params_text}

ЗАДАЧА: Выбери ОДИН лучший инструмент из кандидатов выше.

ФОРМАТ ОТВЕТА (только JSON):
{{
    "selected_tool": "имя_инструмента",
    "reason": "краткое_объяснение_почему_этот_инструмент_лучший"
}}

ВАЖНО: Отвечай только в JSON формате! Выбирай ТОЛЬКО из кандидатов выше!"""

            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ]
            
            response = await self.llm_client.llm_provider.generate_response(messages)
            
            # Парсим ответ
            try:
                cleaned_response = response.strip()
                json_start = cleaned_response.find('{')
                json_end = cleaned_response.rfind('}') + 1
                
                if json_start != -1 and json_end > json_start:
                    json_str = cleaned_response[json_start:json_end]
                    selection_data = json.loads(json_str)
                    
                    selected_tool_name = selection_data.get('selected_tool', '')
                    reason = selection_data.get('reason', '')
                    
                    # Находим выбранный инструмент среди кандидатов
                    for tool in candidate_tools:
                        if tool.get('name') == selected_tool_name:
                            logger.info(f"✅ LLM выбрал из кандидатов: {selected_tool_name} (причина: {reason})")
                            return tool
                    
                    logger.warning(f"⚠️ LLM выбрал несуществующий инструмент из кандидатов: {selected_tool_name}")
                    # Возвращаем первый кандидат как fallback
                    return candidate_tools[0]
                else:
                    logger.warning("⚠️ JSON не найден в ответе LLM при выборе из кандидатов")
                    return candidate_tools[0]
                    
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ Не удалось распарсить выбор из кандидатов: {e}")
                return candidate_tools[0]
                
        except Exception as e:
            logger.error(f"❌ Ошибка выбора инструмента через LLM из кандидатов: {e}")
            return candidate_tools[0] if candidate_tools else None
    
    def _select_tool_by_parameters(
        self, 
        available_tools: List[Dict[str, Any]], 
        context_params: List[ContextParameter],
        user_message: str
    ) -> Optional[Dict[str, Any]]:
        """
        Выбирает инструмент на основе найденных параметров
        """
        if not context_params:
            return None
        
        # Фильтруем параметры, исключая те, что имеют значение None
        valid_context_params = [
            param for param in context_params 
            if param.value is not None and param.value.lower() not in ['null', 'none', '']
        ]
        
        if not valid_context_params:
            logger.info("🔍 Нет валидных параметров для выбора инструмента")
            return None
        
        # Получаем названия найденных параметров
        found_param_names = {param.name for param in valid_context_params}
        
        logger.info(f"🔍 Выбор инструмента по параметрам: {found_param_names}")
        
        best_tool = None
        best_score = 0
        
        for tool in available_tools:
            tool_name = tool.get('name', '')
            tool_description = tool.get('description', '')
            input_schema = tool.get('inputSchema', {})
            all_params = set(input_schema.get('properties', {}).keys())
            required_params = set(input_schema.get('required', []))
            
            # Подсчитываем количество совпадающих параметров (все параметры, не только обязательные)
            matching_all_params = len(all_params & found_param_names)
            matching_required_params = len(required_params & found_param_names)
            
            # Проверяем соответствие описания задаче
            description_match = self._check_description_match(tool_description, user_message)
            
            # Вычисляем общий балл с приоритетом обязательных параметров
            # Обязательные параметры получают больший вес
            score = (matching_required_params * 3) + (matching_all_params * 1) + (1 if description_match else 0)
            
            logger.debug(f"🔍 [{tool_name}] Обязательные: {matching_required_params}/{len(required_params)}, "
                        f"Всего: {matching_all_params}/{len(all_params)}, "
                        f"Описание: {description_match}, Балл: {score}")
            
            if score > best_score:
                best_score = score
                best_tool = tool
        
        return best_tool if best_score > 0 else None
    
    def _check_description_match(self, description: str, user_message: str) -> bool:
        """
        Проверяет соответствие описания инструмента задаче пользователя
        """
        if not description or not user_message:
            return False
        
        # Ключевые слова для сопоставления
        keywords_map = {
            'поиск': ['search', 'find', 'lookup', 'query'],
            'создание': ['create', 'add', 'new', 'make'],
            'обновление': ['update', 'modify', 'edit', 'change'],
            'удаление': ['delete', 'remove', 'drop'],
            'получение': ['get', 'fetch', 'retrieve', 'show'],
            'пользователь': ['user', 'person', 'account'],
            'проект': ['project', 'task', 'issue'],
            'файл': ['file', 'document', 'attachment']
        }
        
        user_lower = user_message.lower()
        desc_lower = description.lower()
        
        for ru_keyword, en_keywords in keywords_map.items():
            if ru_keyword in user_lower:
                if any(keyword in desc_lower for keyword in en_keywords):
                    return True
        
        return False
    
    async def _select_tool_with_llm(
        self, 
        user_message: str, 
        available_tools: List[Dict[str, Any]], 
        context_params: List[ContextParameter]
    ) -> Optional[Dict[str, Any]]:
        """
        Использует LLM для выбора инструмента
        """
        try:
            # Формируем информацию об инструментах
            tools_info = []
            for tool in available_tools:
                tool_name = tool.get('name', '')
                tool_description = tool.get('description', '')
                required_params = tool.get('inputSchema', {}).get('properties', {}).get('required', [])
                params_list = ', '.join(required_params) if required_params else 'нет параметров'
                
                tools_info.append(f"- {tool_name}: {tool_description} (параметры: {params_list})")
            
            tools_text = "\n".join(tools_info)
            
            # Формируем параметры для отображения
            params_text = ""
            if context_params:
                params_list = [f"{p.name}={p.value}" for p in context_params]
                params_text = f"Найденные параметры: {', '.join(params_list)}"
            
            system_message = f"""Ты - эксперт по выбору инструментов. Выбери лучший инструмент для задачи пользователя.

ДОСТУПНЫЕ ИНСТРУМЕНТЫ:
{tools_text}

{params_text}

ЗАДАЧА: Выбери инструмент, который лучше всего подходит для выполнения задачи пользователя.

ФОРМАТ ОТВЕТА (только JSON):
{{
    "selected_tool": "имя_инструмента",
    "reason": "краткое_объяснение"
}}

ВАЖНО: Отвечай только в JSON формате!"""

            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ]
            
            response = await self.llm_client.llm_provider.generate_response(messages)
            
            # Парсим ответ
            try:
                cleaned_response = response.strip()
                json_start = cleaned_response.find('{')
                json_end = cleaned_response.rfind('}') + 1
                
                if json_start != -1 and json_end > json_start:
                    json_str = cleaned_response[json_start:json_end]
                    selection_data = json.loads(json_str)
                    
                    selected_tool_name = selection_data.get('selected_tool', '')
                    
                    # Находим выбранный инструмент
                    for tool in available_tools:
                        if tool.get('name') == selected_tool_name:
                            logger.info(f"✅ LLM выбрал инструмент: {selected_tool_name}")
                            return tool
                    
                    logger.warning(f"⚠️ LLM выбрал несуществующий инструмент: {selected_tool_name}")
                    return None
                else:
                    logger.warning("⚠️ JSON не найден в ответе LLM при выборе инструмента")
                    return None
                    
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ Не удалось распарсить выбор инструмента: {e}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Ошибка выбора инструмента через LLM: {e}")
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
        input_schema = tool.get('inputSchema', {})
        all_params = set(input_schema.get('properties', {}).keys())
        required_params = set(input_schema.get('required', []))
        
        # Фильтруем параметры, исключая те, что имеют значение None
        valid_context_params = [
            param for param in context_params 
            if param.value is not None and param.value.lower() not in ['null', 'none', '']
        ]
        
        logger.info(f"🔧 Подготовка параметров для {tool.get('name', '')}: "
                   f"всего параметров {len(all_params)}, обязательных {len(required_params)}, "
                   f"валидных из контекста {len(valid_context_params)}")
        
        # Маппинг параметров из контекста
        param_mapping = {
            'project_id': ['project', 'project_id', 'project_key'],
            'task_id': ['task', 'task_id', 'issue', 'issue_id'],
            'username': ['user', 'username', 'assignee'],
            'keyword': ['query', 'search', 'keyword'],
            'file_path': ['path', 'file_path', 'file'],
            'commit_hash': ['commit', 'hash', 'commit_id']
        }
        
        # Заполняем ВСЕ параметры из контекста (не только обязательные)
        for param_name in all_params:
            best_param = None
            best_confidence = 0.0
            
            # Ищем подходящий параметр в контексте
            for context_param in valid_context_params:
                if context_param.name in param_mapping.get(param_name, [param_name]):
                    if context_param.confidence > best_confidence:
                        best_param = context_param
                        best_confidence = context_param.confidence
            
            if best_param and best_confidence > 0.5:
                tool_params[param_name] = best_param.value
                param_type = "обязательный" if param_name in required_params else "опциональный"
                logger.info(f"✅ [{param_type}] Параметр '{param_name}' = '{best_param.value}' (confidence: {best_confidence})")
            elif param_name in required_params:
                # Если обязательный параметр не найден, пытаемся извлечь из сообщения
                extracted_value = await self._extract_param_from_message(param_name, user_message)
                if extracted_value:
                    tool_params[param_name] = extracted_value
                    logger.info(f"✅ [обязательный] Параметр '{param_name}' = '{extracted_value}' извлечен из сообщения")
                else:
                    logger.warning(f"⚠️ [обязательный] Параметр '{param_name}' не найден и не может быть извлечен")
        
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
