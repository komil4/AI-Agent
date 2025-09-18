#!/usr/bin/env python3
"""
Ollama провайдер для LLM с использованием готовой библиотеки
"""

import json
import asyncio
from typing import Dict, Any, List, Optional
from config.llm_config import LLMConfig
from llm_providers.base_provider import BaseLLMProvider

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

class OllamaProvider(BaseLLMProvider):
    """Ollama провайдер с использованием готовой библиотеки"""
    
    def _initialize_client(self):
        """Инициализирует Ollama клиент"""
        if not OLLAMA_AVAILABLE:
            raise ImportError("Библиотека ollama не установлена. Установите: pip install ollama")
        
        self.base_url = self.config.base_url or "http://localhost:11434"
        self.model = self.config.model
        
        # Настраиваем клиент
        self.client = ollama.Client(host=self.base_url)
    
    async def generate_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Генерирует ответ через Ollama API"""
        try:
            params = self._get_model_params(**kwargs)
            
            # Конвертируем сообщения в формат Ollama
            formatted_messages = self._format_messages_for_ollama(messages)
            
            # Используем синхронный клиент в асинхронном контексте
            def _generate():
                return self.client.chat(
                    model=self.model,
                    messages=formatted_messages,
                    options={
                        'temperature': params['temperature'],
                        'num_predict': params['max_tokens']
                    }
                )
            
            # Выполняем в отдельном потоке
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, _generate)
            
            return result['message']['content']
            
        except ConnectionError as e:
            raise Exception(f"Не удалось подключиться к Ollama. Проверьте, что Ollama запущен на {self.base_url}")
        except Exception as e:
            error_msg = str(e)
            if "Failed to connect" in error_msg or "Connection refused" in error_msg:
                raise Exception(f"Ollama недоступен. Проверьте, что Ollama запущен на {self.base_url}")
            elif "model not found" in error_msg.lower():
                raise Exception(f"Модель {self.model} не найдена. Доступные модели: {await self._get_available_models()}")
            else:
                raise Exception(f"Ошибка Ollama API: {error_msg}")
    
    async def _get_available_models(self) -> str:
        """Получает список доступных моделей"""
        try:
            def _get_models():
                return self.client.list()
            
            loop = asyncio.get_event_loop()
            models = await loop.run_in_executor(None, _get_models)
            model_names = [model['name'] for model in models.get('models', [])]
            return ', '.join(model_names) if model_names else 'нет доступных моделей'
        except:
            return 'не удалось получить список моделей'
    
    async def generate_with_tools(self, user_message: str, messages: List[Dict[str, str]], tools: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """Генерирует ответ с поддержкой инструментов"""
        try:
            # Проверяем, поддерживает ли модель инструменты
            if not await self._supports_tools():
                return await self._fallback_to_simple_generation(user_message, messages, tools, **kwargs)
            
            params = self._get_model_params(**kwargs)
            
            # Конвертируем сообщения в формат Ollama
            formatted_messages = self._format_messages_for_ollama(messages)
            
            # Форматируем инструменты для Ollama
            formatted_tools = self._format_tools_for_ollama(tools)
            
            # Используем синхронный клиент в асинхронном контексте
            def _generate_with_tools():
                return self.client.chat(
                    model=self.model,
                    messages=formatted_messages,
                    tools=formatted_tools,
                    options={
                        'temperature': params['temperature'],
                        'num_predict': params['max_tokens']
                    }
                )
            
            # Выполняем в отдельном потоке
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, _generate_with_tools)
            
            message = result.get('message', {})
            
            # Проверяем, есть ли вызов инструмента
            if message.get('tool_calls'):
                tool_call = message['tool_calls'][0]
                return {
                    'action': 'call_tool',
                    'server': tool_call['function']['name'].split('.')[0] if '.' in tool_call['function']['name'] else 'unknown',
                    'tool': tool_call['function']['name'].split('.')[1] if '.' in tool_call['function']['name'] else tool_call['function']['name'],
                    'arguments': tool_call['function']['arguments']
                }
            else:
                return {
                    'action': 'respond',
                    'message': message.get('content', 'Нет ответа')
                }
                
        except ConnectionError as e:
            # Если Ollama недоступен, возвращаем fallback ответ
            return {
                'action': 'respond',
                'message': f"Ollama недоступен. Проверьте, что Ollama запущен на {self.base_url}"
            }
        except Exception as e:
            error_msg = str(e)
            if "Failed to connect" in error_msg or "Connection refused" in error_msg:
                return {
                    'action': 'respond',
                    'message': f"Ollama недоступен. Проверьте, что Ollama запущен на {self.base_url}"
                }
            elif "model not found" in error_msg.lower():
                available_models = await self._get_available_models()
                return {
                    'action': 'respond',
                    'message': f"Модель {self.model} не найдена. Доступные модели: {available_models}"
                }
            else:
                # Если произошла другая ошибка с инструментами, пробуем простую генерацию
                print(f"⚠️ Ошибка с инструментами: {e}, пробуем простую генерацию")
                return await self._fallback_to_simple_generation(user_message, messages, tools, **kwargs)
    
    async def _supports_tools(self) -> bool:
        """Проверяет, поддерживает ли модель инструменты"""
        try:
            # Проверяем версию Ollama
            def _get_version():
                return self.client.version()
            
            loop = asyncio.get_event_loop()
            version_info = await loop.run_in_executor(None, _get_version)
            version = version_info.get('version', '0.0.0')
            
            # Проверяем, поддерживает ли версия инструменты
            return self._version_supports_tools(version)
        except:
            return False
    
    def _version_supports_tools(self, version: str) -> bool:
        """Проверяет, поддерживает ли версия Ollama инструменты"""
        try:
            parts = version.split('.')
            if len(parts) >= 2:
                major = int(parts[0])
                minor = int(parts[1])
                # Предполагаем, что инструменты поддерживаются с версии 0.1.20+
                return major > 0 or (major == 0 and minor >= 1)
            return False
        except:
            return False
    
    async def _fallback_to_simple_generation(self, user_message: str, messages: List[Dict[str, str]], tools: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """Fallback к простой генерации, если инструменты не поддерживаются"""
        try:
            # Добавляем информацию об инструментах в системное сообщение
            tools_info = []
            for tool in tools:
                parameters = json.dumps(tool['parameters'], ensure_ascii=False)
                tools_info.append(f"- Название:{tool['name']}; Описание: {tool['description']}; Параметры: {parameters}")
                tools_text = "\n".join(tools_info)
            
            system_message = f"""Вы - ассистент с доступом к внешним инструментам (tools). Ваша задача:
1. Анализировать запрос пользователя и определять необходимые инструменты
2. Генерировать ТОЧНО правильный JSON-запрос для вызова инструмента
3. Анализировать результаты и предоставлять четкий ответ
4. Если одного инструмента недостаточно - выполнять последовательные вызовы

ПРАВИЛА:
- Генерируй ТОЛЬКО валидный JSON для вызова инструментов
- Не добавляй лишний текст до или после JSON
- Если инструментов нет или запрос простой - отвечай напрямую
- Всегда проверяй корректность параметров
- Сообщай об ошибках если инструмент недоступен или не подходит
- Если действие можно сделать с помощью инструментов, ответь ТОЛЬКО в данном формате JSON:
{{
    "server": "имя_сервера",
    "tool": "имя_инструмента",
    "arguments": {{"параметр": "значение"}}
}}
- Обрати внимание на структуру arguments. Вложенные данные должны строго соответствовать структуре ответа поля parametersиз инструмента.

Подробное описание для формата ответа JSON: 
- Поле "server" - имя сервера (например, "gitlab", "jira", "atlassian")
- Поле "tool" - имя инструмента (например, "list_projects", "create_issue")
- Поле "arguments" - объект с параметрами

Доступные инструменты (tools):
{tools_text}"""
            
            # Добавляем системное сообщение
            enhanced_messages = messages + [{"role": "system", "content": system_message}]
            
            enhanced_messages.append({"role": "user", "content": user_message})

            # Используем простую генерацию
            response = await self.generate_response(enhanced_messages, **kwargs)
            
            # Пытаемся распарсить JSON ответ
            try:
                # Очищаем ответ от возможных лишних символов
                cleaned_response = response.strip()
                
                # Ищем JSON в ответе, если он не весь ответ
                if cleaned_response.startswith('{') and cleaned_response.endswith('}'):
                    json_text = cleaned_response
                else:
                    # Пытаемся найти JSON в тексте
                    start = cleaned_response.find('{')
                    end = cleaned_response.rfind('}')
                    if start != -1 and end != -1 and end > start:
                        json_text = cleaned_response[start:end+1]
                    else:
                        raise ValueError("JSON не найден в ответе")
                
                parsed = json.loads(json_text)
                if 'tool' in parsed:
                    parsed['action'] = 'call_tool'
                    return parsed
            except Exception as e:
                print(f"⚠️ Не удалось распарсить JSON ответ: {e}")
                print(f"Ответ: {response}")
                pass
            
            # Если не JSON, возвращаем как обычный ответ
            return {
                'action': 'respond',
                'message': response
            }
            
        except Exception as e:
            raise Exception(f"Ошибка fallback генерации: {str(e)}")
    
    async def check_health(self) -> Dict[str, Any]:
        """Проверяет доступность Ollama API"""
        try:
            if not OLLAMA_AVAILABLE:
                return {
                    'status': 'unhealthy',
                    'error': 'Библиотека ollama не установлена'
                }
            
            # Проверяем доступность API
            def _check_health():
                try:
                    # Проверяем список моделей
                    models = self.client.list()
                    # Проверяем версию
                    version = self.client.version()
                    return {
                        'models': models,
                        'version': version
                    }
                except ConnectionError as e:
                    raise Exception(f"Не удалось подключиться к Ollama на {self.base_url}. Проверьте, что Ollama запущен.")
                except Exception as e:
                    raise Exception(f"Ollama API недоступен: {str(e)}")
            
            loop = asyncio.get_event_loop()
            health_info = await loop.run_in_executor(None, _check_health)
            
            # Проверяем, есть ли нужная модель
            models = health_info.get('models', {}).get('models', [])
            model_names = [model['name'] for model in models]
            
            if self.model not in model_names:
                return {
                    'status': 'unhealthy',
                    'error': f'Модель {self.model} не найдена. Доступные модели: {", ".join(model_names)}'
                }
            
            version_info = health_info.get('version', {})
            version = version_info.get('version', 'unknown')
            supports_tools = self._version_supports_tools(version)
            
            return {
                'status': 'healthy',
                'provider': 'ollama',
                'model': self.model,
                'base_url': self.base_url,
                'version': version,
                'supports_tools': supports_tools,
                'available_models': model_names
            }
            
        except Exception as e:
            error_msg = str(e)
            if "Failed to connect" in error_msg or "Connection refused" in error_msg:
                return {
                    'status': 'unhealthy',
                    'provider': 'ollama',
                    'error': f'Ollama недоступен на {self.base_url}. Проверьте, что Ollama запущен.'
                }
            else:
                return {
                    'status': 'unhealthy',
                    'provider': 'ollama',
                    'error': error_msg
                }
    
    def _format_messages_for_ollama(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Форматирует сообщения для Ollama API"""
        formatted = []
        
        for msg in messages:
            role = msg['role']
            content = msg['content']
            
            # Ollama ожидает определенные роли
            if role == 'system':
                formatted.append({"role": "system", "content": content})
            elif role == 'user':
                formatted.append({"role": "user", "content": content})
            elif role == 'assistant':
                formatted.append({"role": "assistant", "content": content})
        
        return formatted
    
    def _format_tools_for_ollama(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Форматирует инструменты для Ollama API"""
        formatted_tools = []
        
        for tool in tools:
            server_name = tool.get('server', 'unknown')
            tool_name = tool['name']
            
            formatted_tool = {
                "type": "function",
                "function": {
                    "name": f"{server_name}.{tool_name}",
                    "description": tool['description'],
                    "parameters": tool.get('parameters', {})
                }
            }
            formatted_tools.append(formatted_tool)
        
        return formatted_tools