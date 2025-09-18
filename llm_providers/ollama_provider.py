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
    
    async def generate_response(self, messages: List[Dict[str, str]], temperature: float = -1,**kwargs) -> str:
        """Генерирует ответ через Ollama API"""
        try:
            params = self._get_model_params(**kwargs)
            
            # Конвертируем сообщения в формат Ollama
            formatted_messages = self._format_messages_for_ollama(messages)
            
            if temperature == -1:
                temperature = params['temperature']

            # Используем синхронный клиент в асинхронном контексте
            def _generate():
                return self.client.chat(
                    model=self.model,
                    messages=formatted_messages,
                    options={
                        'temperature': temperature,
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
            # Для Llama2 и других старых моделей принудительно используем fallback
            if 'llama2' in self.model.lower() or 'llama' in self.model.lower():
                return await self._fallback_to_simple_generation(user_message, messages, tools, **kwargs)
            
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
                param_names = ", ".join(tool.get('parameters', {}).keys())
                if param_names:
                    tools_info.append(f"{tool['name']}: {tool['description']} (параметры: {param_names})")
                else:
                    tools_info.append(f"{tool['name']}: {tool['description']}")
            tools_text = "\n".join(tools_info)
            
            system_message = f"""Ты - AI ассистент с доступом к инструментам.

Доступные инструменты:
{tools_text}

ВАЖНО: Ты должен отвечать СТРОГО в формате JSON. Никаких объяснений, советов или дополнительного текста!

Формат ответа для вызова инструментов:
{{"action": "call_tool", "server": "имя_сервера", "tool": "имя_инструмента", "arguments": {{"параметр": "значение"}}}}

Если не нужно использовать инструменты, отвечай:
{{"action": "respond", "message": "твой ответ"}}

ПРИМЕРЫ:
Запрос: "Создай задачу в Jira"
Ответ: {{"action": "call_tool", "server": "jira", "tool": "create_issue", "arguments": {{"summary": "Новая задача", "description": "Описание задачи"}}}}

Запрос: "Привет, как дела?"
Ответ: {{"action": "respond", "message": "Привет! У меня все хорошо, спасибо!"}}

Отвечай ТОЛЬКО JSON-объектом!"""
            
            # Добавляем системное сообщение
            enhanced_messages = messages + [{"role": "system", "content": system_message}]
            
            enhanced_messages.append({"role": "user", "content": user_message})

            # Используем простую генерацию
            response = await self.generate_response(enhanced_messages, **kwargs)
            
            # Логируем ответ для отладки
            print(f"🔍 Llama2 ответ: {response[:200]}...")
            
            # Пытаемся распарсить JSON ответ
            try:
                # Очищаем ответ от возможных лишних символов
                cleaned_response = response.strip()
                
                # Удаляем возможные markdown блоки
                if cleaned_response.startswith('```json'):
                    cleaned_response = cleaned_response[7:]
                if cleaned_response.endswith('```'):
                    cleaned_response = cleaned_response[:-3]
                cleaned_response = cleaned_response.strip()
                
                # Ищем JSON в ответе
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
                
                # Проверяем, что это валидный ответ
                if 'action' in parsed:
                    # Иногда LLM вставляет name в action, а не в tool
                    # Исправляем: если action совпадает с каким-либо tool.name, то это tool, а action=call_tool
                    action_value = parsed.get('action')
                    if isinstance(action_value, str):
                        for tool in tools:
                            if action_value == tool.get('name'):
                                parsed['tool'] = action_value
                                parsed['action'] = 'call_tool'
                                break
                    return parsed
                elif 'tool' in parsed:
                    # Конвертируем старый формат в новый
                    parsed['action'] = 'call_tool'
                    return parsed
                elif 'name' in parsed:
                    # Иногда LLM кладет tool name в поле name вместо tool/action
                    # Если name совпадает с каким-либо tool, считаем это tool
                    name_value = parsed.get('name')
                    for tool in tools:
                        if name_value == tool.get('name'):
                            parsed['tool'] = name_value
                            parsed['action'] = 'call_tool'
                            break
                    return parsed
                else:
                    raise ValueError("Неверный формат JSON ответа")
                    
            except Exception as e:
                print(f"⚠️ Не удалось распарсить JSON ответ: {e}")
                print(f"Ответ: {response}")
                
                # Пытаемся извлечь JSON более агрессивно
                try:
                    import re
                    # Ищем JSON с action
                    json_match = re.search(r'\{[^{}]*"action"[^{}]*\}', response)
                    if json_match:
                        parsed = json.loads(json_match.group())
                        return parsed
                    
                    # Ищем любой JSON объект
                    json_match = re.search(r'\{[^{}]*\}', response)
                    if json_match:
                        parsed = json.loads(json_match.group())
                        if 'tool' in parsed or 'action' in parsed:
                            if 'action' not in parsed:
                                parsed['action'] = 'call_tool'
                            return parsed
                except:
                    pass
                
                # Если все еще не JSON, пытаемся создать JSON из текста
                if any(keyword in response.lower() for keyword in ['создай', 'найди', 'покажи', 'получи', 'обнови', 'удали']):
                    # Пытаемся определить инструмент по контексту
                    tool_name = self._extract_tool_from_text(response, tools)
                    if tool_name:
                        return {
                            'action': 'call_tool',
                            'server': 'unknown',
                            'tool': tool_name,
                            'arguments': {}
                        }
            
            # Если не JSON, возвращаем как обычный ответ
            return {
                'action': 'respond',
                'message': response
            }
            
        except Exception as e:
            raise Exception(f"Ошибка fallback генерации: {str(e)}")
    
    def _extract_tool_from_text(self, text: str, tools: List[Dict[str, Any]]) -> Optional[str]:
        """Пытается извлечь название инструмента из текста"""
        text_lower = text.lower()
        
        # Простое сопоставление по ключевым словам
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
                for tool in tools:
                    if tool['name'] == tool_name:
                        return tool_name
        
        return None
    
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